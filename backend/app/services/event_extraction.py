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
from app.core.anthropic_client import AnthropicClient


class EventExtractionService:
    """事件抽象服务"""

    def __init__(self):
        self.db_path = Path("data/graph.db")
        self.llm_client = AnthropicClient()

    async def extract_events_for_user(self, user_id: str) -> Dict:
        """为单个用户抽象事件

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
            app_logger.info(f"开始为用户 [{user_id}] 抽象事件")

            # 1. 查询用户的所有行为数据
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, action, timestamp, item_id, app_id, media_id, poi_id, duration, properties
                    FROM behavior_data
                    WHERE user_id = ?
                    ORDER BY timestamp ASC
                """, (user_id,))

                behaviors = []
                for row in cursor.fetchall():
                    behaviors.append({
                        "id": row[0],
                        "action": row[1],
                        "timestamp": row[2],
                        "item_id": row[3],
                        "app_id": row[4],
                        "media_id": row[5],
                        "poi_id": row[6],
                        "duration": row[7],
                        "properties": json.loads(row[8]) if row[8] else {}
                    })

            if not behaviors:
                app_logger.warning(f"用户 [{user_id}] 没有行为数据")
                return {
                    "success": False,
                    "user_id": user_id,
                    "error": "没有行为数据"
                }

            app_logger.info(f"用户 [{user_id}] 共有 {len(behaviors)} 条行为数据")

            # 2. 调用LLM抽象为事件
            events_result = await self.llm_client.abstract_events_batch({user_id: behaviors})
            events = events_result.get(user_id, [])

            if not events:
                app_logger.warning(f"用户 [{user_id}] 事件抽象失败")
                return {
                    "success": False,
                    "user_id": user_id,
                    "error": "事件抽象失败"
                }

            # 3. 保存到extracted_events表
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

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
                        json.dumps([b["id"] for b in behaviors], ensure_ascii=False)
                    ))
                    event_ids.append(event_id)

                # 4. 更新event_sequences表
                cursor.execute("DELETE FROM event_sequences WHERE user_id = ?", (user_id,))
                cursor.execute("""
                    INSERT INTO event_sequences
                    (user_id, sequence, start_time, end_time)
                    VALUES (?, ?, ?, ?)
                """, (
                    user_id,
                    json.dumps(event_ids, ensure_ascii=False),
                    behaviors[0]["timestamp"] if behaviors else None,
                    behaviors[-1]["timestamp"] if behaviors else None
                ))

                conn.commit()

            app_logger.info(f"✓ 用户 [{user_id}] 事件抽象完成: {len(events)} 个事件")
            return {
                "success": True,
                "user_id": user_id,
                "event_count": len(events),
                "events": events
            }

        except Exception as e:
            app_logger.error(f"✗ 用户 [{user_id}] 事件抽象异常: {type(e).__name__}: {str(e)}", exc_info=True)
            return {
                "success": False,
                "user_id": user_id,
                "error": str(e)
            }

    async def extract_events_batch(self, user_ids: Optional[List[str]] = None) -> Dict:
        """批量抽象事件

        Args:
            user_ids: 用户ID列表,如果为None则处理所有未抽象的用户

        Returns:
            {
                "success": True,
                "total_users": 10,
                "success_count": 8,
                "failed_count": 2,
                "results": [...]
            }
        """
        try:
            # 1. 如果user_ids为None,查询所有未在event_sequences表中的用户
            if user_ids is None:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT DISTINCT user_id
                        FROM behavior_data
                        WHERE user_id NOT IN (SELECT user_id FROM event_sequences)
                    """)
                    user_ids = [row[0] for row in cursor.fetchall()]

            if not user_ids:
                app_logger.info("没有需要抽象的用户")
                return {
                    "success": True,
                    "total_users": 0,
                    "success_count": 0,
                    "failed_count": 0,
                    "results": []
                }

            app_logger.info(f"========== 开始批量事件抽象: 共 {len(user_ids)} 个用户 ==========")

            # 2. 分批处理(每批10个用户)
            batch_size = 10
            results = []
            success_count = 0
            failed_count = 0

            for i in range(0, len(user_ids), batch_size):
                batch = user_ids[i:i + batch_size]
                batch_num = i // batch_size + 1
                total_batches = (len(user_ids) + batch_size - 1) // batch_size

                app_logger.info(f"处理第 {batch_num}/{total_batches} 批，共 {len(batch)} 个用户")

                # 3. 对每个用户调用extract_events_for_user
                for user_id in batch:
                    result = await self.extract_events_for_user(user_id)
                    results.append(result)

                    if result["success"]:
                        success_count += 1
                    else:
                        failed_count += 1

                app_logger.info(f"✓ 第 {batch_num} 批完成: 成功 {success_count}/{len(user_ids)}")

            app_logger.info(f"========== 批量事件抽象完成: 成功 {success_count}/{len(user_ids)}, 失败 {failed_count}/{len(user_ids)} ==========")

            return {
                "success": True,
                "total_users": len(user_ids),
                "success_count": success_count,
                "failed_count": failed_count,
                "results": results
            }

        except Exception as e:
            app_logger.error(f"✗ 批量事件抽象异常: {type(e).__name__}: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    def get_user_sequences(self, limit: int = 100, offset: int = 0) -> Dict:
        """查询用户序列列表

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

                # 查询总数
                cursor.execute("SELECT COUNT(DISTINCT user_id) FROM behavior_data")
                total = cursor.fetchone()[0]

                items = []
                for user_id in user_ids:
                    # 查询行为数据
                    cursor.execute("""
                        SELECT action, timestamp, item_id, app_id, media_id, poi_id, duration
                        FROM behavior_data
                        WHERE user_id = ?
                        ORDER BY timestamp ASC
                    """, (user_id,))

                    behaviors = []
                    for row in cursor.fetchall():
                        action_desc = self._format_behavior(row)
                        behaviors.append(action_desc)

                    # 查询事件数据
                    cursor.execute("""
                        SELECT event_type, timestamp, context
                        FROM extracted_events
                        WHERE user_id = ?
                        ORDER BY timestamp ASC
                    """, (user_id,))

                    events = []
                    for row in cursor.fetchall():
                        event_desc = f"{row[1]} {row[0]}"
                        events.append(event_desc)

                    items.append({
                        "user_id": user_id,
                        "behavior_sequence": behaviors,
                        "event_sequence": events,
                        "behavior_count": len(behaviors),
                        "event_count": len(events),
                        "has_events": len(events) > 0
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
