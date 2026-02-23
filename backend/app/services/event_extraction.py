"""
事件抽象服务层
"""
import sqlite3
import json
import asyncio
from typing import Dict, List, Optional
from pathlib import Path
from datetime import datetime
from app.core.logger import app_logger
from app.core.openai_client import OpenAIClient


class EventExtractionService:
    """事件抽象服务"""

    def __init__(self):
        self.db_path = Path("data/graph.db")
        self.llm_client = OpenAIClient()

        # 进度跟踪状态
        self.task_progress = {
            "status": "idle",  # idle, running, completed, failed
            "total_users": 0,
            "processed_users": 0,
            "success_count": 0,
            "failed_count": 0,
            "current_batch": 0,
            "total_batches": 0,
            "current_user_ids": [],  # 当前批次正在处理的用户ID
            "start_time": None,
            "end_time": None,
            "error_message": None
        }

    def get_progress(self) -> Dict:
        """获取当前进度"""
        import time
        progress = self.task_progress.copy()

        # 计算进度百分比
        if progress["total_users"] > 0:
            progress["progress_percent"] = round(
                progress["processed_users"] / progress["total_users"] * 100, 1
            )
        else:
            progress["progress_percent"] = 0

        # 计算预估剩余时间
        if progress["status"] == "running" and progress["start_time"]:
            elapsed = time.time() - progress["start_time"]
            if progress["processed_users"] > 0:
                avg_time_per_user = elapsed / progress["processed_users"]
                remaining_users = progress["total_users"] - progress["processed_users"]
                progress["estimated_remaining_seconds"] = int(
                    avg_time_per_user * remaining_users
                )
            else:
                progress["estimated_remaining_seconds"] = None
        else:
            progress["estimated_remaining_seconds"] = None

        return progress

    def _update_progress(self, **kwargs):
        """更新进度状态"""
        self.task_progress.update(kwargs)

    def _get_user_profile(self, user_id: str) -> Optional[Dict]:
        """查询用户画像（非结构化格式）

        Args:
            user_id: 用户ID

        Returns:
            用户画像字典,如果不存在则返回None
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 从 user_profiles 表查询
                cursor.execute("""
                    SELECT user_id, profile_text
                    FROM user_profiles
                    WHERE user_id = ?
                """, (user_id,))
                row = cursor.fetchone()
                if row:
                    return {
                        "user_id": row[0],
                        "profile_text": row[1]
                    }
        except Exception as e:
            app_logger.warning(f"查询用户 [{user_id}] 画像失败: {e}")
        return None

    def _get_user_profiles_bulk(self, user_ids: List[str]) -> Dict[str, Dict]:
        """批量查询用户画像（优化N+1查询）

        Args:
            user_ids: 用户ID列表

        Returns:
            用户画像字典，key为user_id
        """
        profiles = {}
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                placeholders = ','.join('?' * len(user_ids))
                cursor.execute(f"""
                    SELECT user_id, profile_text
                    FROM user_profiles
                    WHERE user_id IN ({placeholders})
                """, user_ids)

                for row in cursor.fetchall():
                    profiles[row[0]] = {
                        "user_id": row[0],
                        "profile_text": row[1]
                    }
        except Exception as e:
            app_logger.warning(f"批量查询用户画像失败: {e}")

        return profiles

    def _enrich_behaviors_with_entities(self, behaviors: List[Dict]) -> List[Dict]:
        """为行为数据关联实体属性（非结构化格式直接返回）

        Args:
            behaviors: 原始行为数据列表

        Returns:
            行为数据（非结构化格式直接返回，不需要关联实体）
        """
        # 非结构化格式，直接返回
        return behaviors

    async def extract_events_for_user(self, user_id: str) -> Dict:
        """为单个用户抽象事件（内部调用批量接口）

        Args:
            user_id: 用户ID

        Returns:
            {
                "success": True,
                "user_id": "user_001",
                "event_count": 3,
                "events": [...]
            }
        """
        try:
            # 调用批量接口处理单个用户
            batch_result = await self.extract_events_batch([user_id])

            # 检查批量处理是否成功
            if not batch_result.get("success", False):
                app_logger.error(f"User {user_id} batch processing failed: {batch_result.get('error')}")
                return {
                    "success": False,
                    "user_id": user_id,
                    "error": f"批量处理失败: {batch_result.get('error', '未知错误')}",
                    "error_type": "batch_processing_error"
                }

            # 从results数组中查找该用户的结果
            results = batch_result.get("results", [])
            for result in results:
                if result.get("user_id") == user_id:
                    return result

            # 如果没有找到该用户的结果
            app_logger.error(f"User {user_id} not found in batch results")
            return {
                "success": False,
                "user_id": user_id,
                "error": "批量处理未返回该用户结果",
                "details": "可能是数据库查询失败或用户不存在"
            }

        except Exception as e:
            app_logger.error(f"Extract events for user {user_id} failed: {e}", exc_info=True)
            return {
                "success": False,
                "user_id": user_id,
                "error": f"处理异常: {str(e)}",
                "error_type": type(e).__name__
            }

    async def _process_single_batch(
        self,
        batch_idx: int,
        batch_user_ids: List[str],
        user_data_map: Dict,
        total_batches: int
    ) -> Dict:
        """处理单个批次（用于并行处理）

        Args:
            batch_idx: 批次索引
            batch_user_ids: 批次用户ID列表
            user_data_map: 用户数据映射
            total_batches: 总批次数

        Returns:
            批次处理结果
        """
        app_logger.info(f"处理第 {batch_idx}/{total_batches} 批，共 {len(batch_user_ids)} 个用户")

        # 准备批量数据
        batch_behaviors = {}
        batch_profiles = {}

        for user_id in batch_user_ids:
            user_data = user_data_map[user_id]
            batch_behaviors[user_id] = user_data["behaviors"]
            if user_data["profile"]:
                batch_profiles[user_id] = user_data["profile"]

        batch_results = []
        batch_success_count = 0
        batch_failed_count = 0

        # 批量调用LLM
        try:
            app_logger.info(f"调用LLM批量抽象 {len(batch_behaviors)} 个用户的事件")
            llm_result = await self.llm_client.abstract_events_batch(
                batch_behaviors,
                user_profiles=batch_profiles if batch_profiles else None
            )

            # 提取事件和LLM响应
            events_result = llm_result.get("events", {})
            llm_response = llm_result.get("llm_response", "")

            app_logger.info(f"LLM返回结果: {type(events_result)}, keys: {list(events_result.keys()) if isinstance(events_result, dict) else 'not a dict'}")
            app_logger.info(f"LLM响应长度: {len(llm_response)}, 前200字符: {llm_response[:200]}")

            # 打印每个用户的事件数量
            for uid, evts in events_result.items():
                app_logger.info(f"用户 [{uid}] 返回事件数: {len(evts) if isinstance(evts, list) else 'not a list'}, 内容: {evts[:2] if isinstance(evts, list) and len(evts) > 0 else evts}")

            # 保存结果
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                for user_id in batch_user_ids:
                    events = events_result.get(user_id, [])

                    if events:
                        # 删除该用户的旧事件
                        cursor.execute("DELETE FROM extracted_events WHERE user_id = ?", (user_id,))

                        event_ids = []
                        for idx, event in enumerate(events):
                            event_id = f"{user_id}_event_{idx+1}"
                            cursor.execute("""
                                INSERT INTO extracted_events
                                (event_id, user_id, event_type, timestamp, context, source_behavior_ids)
                                VALUES (?, ?, ?, ?, ?, ?)
                            """, (
                                event_id,
                                user_id,
                                event.get("event_type", ""),
                                event.get("timestamp", ""),
                                json.dumps(event.get("context", {}), ensure_ascii=False),
                                json.dumps([b["id"] for b in user_data_map[user_id]["raw_behaviors"]], ensure_ascii=False)
                            ))
                            event_ids.append(event_id)

                        # 更新event_sequences表
                        cursor.execute("DELETE FROM event_sequences WHERE user_id = ?", (user_id,))
                        behaviors = user_data_map[user_id]["raw_behaviors"]
                        cursor.execute("""
                            INSERT INTO event_sequences
                            (user_id, sequence, start_time, end_time, status)
                            VALUES (?, ?, ?, ?, ?)
                        """, (
                            user_id,
                            json.dumps(event_ids, ensure_ascii=False),
                            behaviors[0]["timestamp"] if behaviors else None,
                            behaviors[-1]["timestamp"] if behaviors else None,
                            "success"
                        ))

                        batch_results.append({
                            "success": True,
                            "user_id": user_id,
                            "event_count": len(events),
                            "events": events,
                            "llm_response": llm_response[:2000]  # 限制长度，每个用户最多2000字符
                        })
                        batch_success_count += 1
                        app_logger.info(f"✓ 用户 [{user_id}] 事件抽象完成: {len(events)} 个事件")
                    else:
                        # 保存失败信息到数据库
                        error_msg = "LLM返回空结果"
                        cursor.execute("DELETE FROM event_sequences WHERE user_id = ?", (user_id,))
                        cursor.execute("""
                            INSERT INTO event_sequences
                            (user_id, sequence, start_time, end_time, status, error_message)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (
                            user_id,
                            json.dumps([], ensure_ascii=False),
                            None,
                            None,
                            "failed",
                            error_msg
                        ))

                        batch_results.append({
                            "success": False,
                            "user_id": user_id,
                            "error": error_msg
                        })
                        batch_failed_count += 1
                        app_logger.warning(f"✗ 用户 [{user_id}] 事件抽象失败: {error_msg}")

                conn.commit()

            app_logger.info(f"✓ 第 {batch_idx} 批完成: 成功 {batch_success_count}/{len(batch_user_ids)}")

        except Exception as e:
            app_logger.error(f"✗ 第 {batch_idx} 批LLM调用失败: {type(e).__name__}: {str(e)}", exc_info=True)

            # 标记该批次所有用户为失败，并保存到数据库
            error_msg = f"LLM调用失败: {type(e).__name__}: {str(e)}"
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                for user_id in batch_user_ids:
                    cursor.execute("DELETE FROM event_sequences WHERE user_id = ?", (user_id,))
                    cursor.execute("""
                        INSERT INTO event_sequences
                        (user_id, sequence, start_time, end_time, status, error_message)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        user_id,
                        json.dumps([], ensure_ascii=False),
                        None,
                        None,
                        "failed",
                        error_msg
                    ))

                    batch_results.append({
                        "success": False,
                        "user_id": user_id,
                        "error": error_msg
                    })
                    batch_failed_count += 1
                conn.commit()

        return {
            "batch_idx": batch_idx,
            "results": batch_results,
            "success_count": batch_success_count,
            "failed_count": batch_failed_count
        }

    async def extract_events_batch(self, user_ids: Optional[List[str]] = None, enable_parallel: bool = True) -> Dict:
        """批量抽象事件（优化版：支持并行LLM调用）

        Args:
            user_ids: 用户ID列表,如果为None则处理所有未抽象的用户
            enable_parallel: 是否启用并行处理（默认True）

        Returns:
            {
                "success": True,
                "total_users": 10,
                "success_count": 8,
                "failed_count": 2,
                "results": [...]
            }
        """
        import time
        try:
            # 初始化进度
            self._update_progress(
                status="running",
                start_time=time.time(),
                processed_users=0,
                success_count=0,
                failed_count=0,
                current_batch=0,
                total_batches=0,
                current_user_ids=[],
                error_message=None,
                end_time=None
            )

            # 1. 如果user_ids为None,查询所有未成功抽象的用户（包括失败和未处理的）
            if user_ids is None:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT DISTINCT user_id
                        FROM behavior_data
                        WHERE user_id NOT IN (
                            SELECT user_id FROM event_sequences WHERE status = 'success'
                        )
                    """)
                    user_ids = [row[0] for row in cursor.fetchall()]

            if not user_ids:
                app_logger.info("没有需要抽象的用户")
                self._update_progress(
                    status="completed",
                    end_time=time.time(),
                    total_users=0
                )
                return {
                    "success": True,
                    "total_users": 0,
                    "success_count": 0,
                    "failed_count": 0,
                    "results": []
                }

            self._update_progress(total_users=len(user_ids))
            app_logger.info(f"========== 开始批量事件抽象: 共 {len(user_ids)} 个用户 ==========")

            # 2. 估算每个用户的token消耗，动态分组
            # 假设每个行为约50 tokens，每个用户画像约100 tokens
            # 优化：增加批次大小，提高并行度
            # LLM支持32K tokens，设置为25000留出足够的响应空间
            MAX_TOKENS_PER_BATCH = 25000  # 可以容纳约50个用户
            TOKENS_PER_BEHAVIOR = 50
            TOKENS_PER_PROFILE = 100

            results = []
            success_count = 0
            failed_count = 0

            # 3. 加载所有用户的行为数据和画像（批量查询优化）
            user_data_map = {}
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 批量查询所有用户的行为数据（单次查询替代N次查询）
                placeholders = ','.join('?' * len(user_ids))
                cursor.execute(f"""
                    SELECT user_id, id, timestamp, behavior_text
                    FROM behavior_data
                    WHERE user_id IN ({placeholders})
                    ORDER BY user_id, timestamp ASC
                """, user_ids)

                # 按用户分组行为数据
                behaviors_by_user = {}
                for row in cursor.fetchall():
                    user_id = row[0]
                    if user_id not in behaviors_by_user:
                        behaviors_by_user[user_id] = []
                    behaviors_by_user[user_id].append({
                        "id": row[1],
                        "timestamp": row[2],
                        "behavior_text": row[3]
                    })

            # 批量查询用户画像（优化N+1查询）
            profiles_by_user = self._get_user_profiles_bulk(user_ids)

            # 处理每个用户的数据
            for user_id in user_ids:
                behaviors = behaviors_by_user.get(user_id, [])

                if behaviors:
                    # 丰富行为数据
                    enriched_behaviors = self._enrich_behaviors_with_entities(behaviors)

                    # 获取用户画像（从批量查询结果中获取）
                    user_profile = profiles_by_user.get(user_id)

                    # 估算token数
                    estimated_tokens = len(enriched_behaviors) * TOKENS_PER_BEHAVIOR + TOKENS_PER_PROFILE

                    user_data_map[user_id] = {
                        "behaviors": enriched_behaviors,
                        "raw_behaviors": behaviors,
                        "profile": user_profile,
                        "estimated_tokens": estimated_tokens
                    }

            app_logger.info(f"已加载 {len(user_data_map)} 个用户的数据")

            # 4. 动态分组：按token数分批
            batches = []
            current_batch = []
            current_tokens = 0

            for user_id, user_data in user_data_map.items():
                estimated_tokens = user_data["estimated_tokens"]

                # 如果加入当前用户会超过限制，且当前批次不为空，则开始新批次
                if current_tokens + estimated_tokens > MAX_TOKENS_PER_BATCH and current_batch:
                    batches.append(current_batch)
                    current_batch = []
                    current_tokens = 0

                current_batch.append(user_id)
                current_tokens += estimated_tokens

            # 添加最后一批
            if current_batch:
                batches.append(current_batch)

            self._update_progress(total_batches=len(batches))
            app_logger.info(f"分为 {len(batches)} 批处理，每批平均 {len(user_ids)//len(batches) if batches else 0} 个用户")

            # 5. 批量调用LLM（支持并行处理）
            if enable_parallel:
                from app.core.config import settings
                max_workers = min(settings.max_llm_workers, len(batches))
                app_logger.info(f"启用并行处理: {max_workers} 个并发worker")

                # 使用 asyncio.Semaphore 控制并发数
                semaphore = asyncio.Semaphore(max_workers)

                async def process_with_semaphore(batch_idx, batch_user_ids):
                    async with semaphore:
                        batch_result = await self._process_single_batch(
                            batch_idx,
                            batch_user_ids,
                            user_data_map,
                            len(batches)
                        )

                        # 立即更新进度（每个批次完成后）
                        nonlocal success_count, failed_count
                        success_count += batch_result["success_count"]
                        failed_count += batch_result["failed_count"]

                        self._update_progress(
                            current_batch=batch_idx,
                            processed_users=success_count + failed_count,
                            success_count=success_count,
                            failed_count=failed_count
                        )

                        return batch_result

                # 并行处理所有批次
                tasks = [
                    process_with_semaphore(batch_idx, batch_user_ids)
                    for batch_idx, batch_user_ids in enumerate(batches, 1)
                ]
                batch_results_list = await asyncio.gather(*tasks, return_exceptions=True)

                # 聚合结果
                for batch_result in batch_results_list:
                    if isinstance(batch_result, Exception):
                        app_logger.error(f"批次处理异常: {batch_result}", exc_info=True)
                        continue

                    results.extend(batch_result["results"])

            else:
                # 顺序处理（兼容模式）
                app_logger.info("使用顺序处理模式")
                for batch_idx, batch_user_ids in enumerate(batches, 1):
                    self._update_progress(
                        current_batch=batch_idx,
                        current_user_ids=batch_user_ids
                    )

                    batch_result = await self._process_single_batch(
                        batch_idx,
                        batch_user_ids,
                        user_data_map,
                        len(batches)
                    )

                    results.extend(batch_result["results"])
                    success_count += batch_result["success_count"]
                    failed_count += batch_result["failed_count"]

                    # 更新进度
                    self._update_progress(
                        processed_users=success_count + failed_count,
                        success_count=success_count,
                        failed_count=failed_count
                    )

            app_logger.info(f"========== 批量事件抽象完成: 成功 {success_count}/{len(user_ids)}, 失败 {failed_count}/{len(user_ids)} ==========")

            # 完成
            self._update_progress(
                status="completed",
                end_time=time.time()
            )

            return {
                "success": True,
                "total_users": len(user_ids),
                "success_count": success_count,
                "failed_count": failed_count,
                "results": results
            }

        except Exception as e:
            app_logger.error(f"✗ 批量事件抽象异常: {type(e).__name__}: {str(e)}", exc_info=True)
            self._update_progress(
                status="failed",
                end_time=time.time(),
                error_message=str(e)
            )
            return {
                "success": False,
                "error": str(e)
            }

    def get_user_sequences(self, limit: int = 100, offset: int = 0) -> Dict:
        """查询用户序列列表（优化版：批量查询，避免N+1问题）

        Returns:
            {
                "items": [
                    {
                        "user_id": "user_001",
                        "behavior_sequence": ["2026-01-01 在4S店停留2h", ...],
                        "event_sequence": ["2026-01-01 看车", ...],
                        "behavior_count": 10,
                        "event_count": 3,
                        "has_events": true
                    }
                ],
                "total": 100
            }
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 查询所有有行为数据的用户
                cursor.execute("""
                    SELECT DISTINCT user_id
                    FROM behavior_data
                    ORDER BY user_id
                    LIMIT ? OFFSET ?
                """, (limit, offset))

                user_ids = [row[0] for row in cursor.fetchall()]

                if not user_ids:
                    return {
                        "items": [],
                        "total": 0,
                        "limit": limit,
                        "offset": offset
                    }

                # 查询总数
                cursor.execute("SELECT COUNT(DISTINCT user_id) FROM behavior_data")
                total = cursor.fetchone()[0]

                # 批量查询所有用户的行为数据（一次查询）
                placeholders = ','.join('?' * len(user_ids))
                cursor.execute(f"""
                    SELECT user_id, timestamp, behavior_text
                    FROM behavior_data
                    WHERE user_id IN ({placeholders})
                    ORDER BY user_id, timestamp ASC
                """, user_ids)

                # 按用户分组行为数据
                behaviors_by_user = {}
                for row in cursor.fetchall():
                    user_id = row[0]
                    if user_id not in behaviors_by_user:
                        behaviors_by_user[user_id] = []
                    action_desc = f"{row[1]} {row[2]}"  # timestamp + behavior_text
                    behaviors_by_user[user_id].append(action_desc)

                # 批量查询所有用户的事件数据（一次查询）
                cursor.execute(f"""
                    SELECT user_id, event_type, timestamp, context
                    FROM extracted_events
                    WHERE user_id IN ({placeholders})
                    ORDER BY user_id, timestamp ASC
                """, user_ids)

                # 按用户分组事件数据
                events_by_user = {}
                for row in cursor.fetchall():
                    user_id = row[0]
                    if user_id not in events_by_user:
                        events_by_user[user_id] = []
                    event_desc = f"{row[2]} {row[1]}"  # timestamp + event_type
                    events_by_user[user_id].append(event_desc)

                # 批量查询失败信息
                cursor.execute(f"""
                    SELECT user_id, status, error_message
                    FROM event_sequences
                    WHERE user_id IN ({placeholders})
                """, user_ids)

                # 按用户分组失败信息
                status_by_user = {}
                for row in cursor.fetchall():
                    user_id = row[0]
                    status_by_user[user_id] = {
                        "status": row[1],
                        "error_message": row[2]
                    }

                # 构建结果
                items = []
                for user_id in user_ids:
                    behaviors = behaviors_by_user.get(user_id, [])
                    events = events_by_user.get(user_id, [])
                    status_info = status_by_user.get(user_id, {})

                    items.append({
                        "user_id": user_id,
                        "behavior_sequence": behaviors,
                        "event_sequence": events,
                        "behavior_count": len(behaviors),
                        "event_count": len(events),
                        "has_events": len(events) > 0,
                        "status": status_info.get("status"),
                        "error_message": status_info.get("error_message")
                    })

                return {
                    "items": items,
                    "total": total,
                    "limit": limit,
                    "offset": offset
                }

        except Exception as e:
            app_logger.error(f"查询用户序列列表失败: {e}", exc_info=True)
            return {
                "items": [],
                "total": 0,
                "limit": limit,
                "offset": offset
            }

    def _format_behavior(self, row) -> str:
        """格式化行为数据为可读字符串"""
        action, timestamp, item_id, app_id, media_id, poi_id, duration = row

        desc_parts = [timestamp]

        if action == "visit_poi" and poi_id:
            desc_parts.append(f"在{poi_id}停留")
            if duration:
                desc_parts.append(f"{duration//3600}h")
        elif action == "search" and item_id:
            desc_parts.append(f"搜索:{item_id}")
        elif action == "view" and item_id:
            desc_parts.append(f"浏览{item_id}")
        elif action == "use_app" and app_id:
            desc_parts.append(f"使用{app_id}")
        else:
            desc_parts.append(action)
            if item_id:
                desc_parts.append(item_id)

        return " ".join(desc_parts)
