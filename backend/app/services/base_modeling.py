"""
基础建模服务层
"""
import sqlite3
import json
import asyncio
from typing import Dict, List, Optional
from pathlib import Path
from app.core.logger import app_logger
from app.core.persistence import persistence
from app.core.openai_client import OpenAIClient


class BaseModelingService:
    """基础建模服务"""

    def __init__(self):
        self.db_path = Path("data/graph.db")
        self.llm_client = OpenAIClient()

    # ========== 行为数据管理 ==========

    def import_behavior_data(self, behaviors: List[Dict]) -> Dict:
        """导入行为数据（非结构化格式）"""
        try:
            saved_count = 0
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                for behavior in behaviors:
                    cursor.execute("""
                        INSERT INTO behavior_data
                        (user_id, timestamp, behavior_text, action)
                        VALUES (?, ?, ?, ?)
                    """, (
                        behavior.get("user_id"),
                        behavior.get("timestamp"),
                        behavior.get("behavior_text"),
                        "unstructured"
                    ))
                    saved_count += 1
                conn.commit()

            app_logger.info(f"成功导入 {saved_count} 条行为数据")
            return {
                "success": True,
                "saved_count": saved_count
            }
        except Exception as e:
            app_logger.error(f"导入行为数据失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    def query_behavior_data(self, user_id: Optional[str] = None, limit: int = 100, offset: int = 0) -> Dict:
        """查询行为数据（非结构化格式）"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 先查询总数
                if user_id:
                    cursor.execute("SELECT COUNT(*) FROM behavior_data WHERE user_id = ?", (user_id,))
                    total = cursor.fetchone()[0]

                    cursor.execute("""
                        SELECT id, user_id, timestamp, behavior_text
                        FROM behavior_data
                        WHERE user_id = ?
                        ORDER BY timestamp DESC
                        LIMIT ? OFFSET ?
                    """, (user_id, limit, offset))
                else:
                    cursor.execute("SELECT COUNT(*) FROM behavior_data")
                    total = cursor.fetchone()[0]

                    cursor.execute("""
                        SELECT id, user_id, timestamp, behavior_text
                        FROM behavior_data
                        ORDER BY timestamp DESC
                        LIMIT ? OFFSET ?
                    """, (limit, offset))

                items = []
                for row in cursor.fetchall():
                    items.append({
                        "id": row[0],
                        "user_id": row[1],
                        "timestamp": row[2],
                        "behavior_text": row[3]
                    })

                return {
                    "items": items,
                    "total": total,
                    "limit": limit,
                    "offset": offset
                }
        except Exception as e:
            app_logger.error(f"查询行为数据失败: {e}", exc_info=True)
            return {
                "items": [],
                "total": 0,
                "limit": limit,
                "offset": offset
            }

    # ========== APP标签管理 ==========
        except Exception as e:
            app_logger.error(f"查询行为数据失败: {e}", exc_info=True)
            return {
                "items": [],
                "total": 0,
                "limit": limit,
                "offset": offset
            }

    # ========== APP标签管理 ==========

    async def import_app_list(self, apps: List[Dict]) -> Dict:
        """导入APP列表并自动生成标签"""
        try:
            saved_count = 0
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                for app in apps:
                    cursor.execute("""
                        INSERT OR REPLACE INTO app_tags
                        (app_id, app_name, category, tags, llm_generated)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        app.get("app_id"),
                        app.get("app_name"),
                        app.get("category"),
                        json.dumps(app.get("tags", []), ensure_ascii=False),
                        0  # 初始未打标
                    ))
                    saved_count += 1
                conn.commit()

            app_logger.info(f"成功导入 {saved_count} 个APP，开始LLM打标...")

            # 异步调用LLM为所有APP生成标签
            import asyncio
            loop = asyncio.get_event_loop()
            loop.create_task(self._generate_app_tags_async())

            return {
                "success": True,
                "saved_count": saved_count,
                "tagging_status": "pending"
            }
        except Exception as e:
            app_logger.error(f"导入APP列表失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    async def _generate_app_tags_async(self):
        """异步为所有APP生成标签"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id, app_id, app_name, category FROM app_tags WHERE llm_generated = 0")
                apps = cursor.fetchall()

            if not apps:
                app_logger.info("没有需要打标的APP")
                return

            app_logger.info(f"========== 开始批量生成APP标签: 共 {len(apps)} 个APP ==========")

            # 转换为字典列表
            app_list = [
                {
                    "app_id": row[1],
                    "app_name": row[2],
                    "category": row[3]
                }
                for row in apps
            ]

            # 分批处理，每批100个
            batch_size = 100
            total_success = 0
            total_fail = 0

            for i in range(0, len(app_list), batch_size):
                batch = app_list[i:i + batch_size]
                batch_num = i // batch_size + 1
                total_batches = (len(app_list) + batch_size - 1) // batch_size

                app_logger.info(f"处理第 {batch_num}/{total_batches} 批，共 {len(batch)} 个APP")

                try:
                    # 批量调用LLM
                    tags_dict = await self.llm_client.generate_app_tags_batch(batch)

                    # 批量更新数据库
                    with sqlite3.connect(self.db_path) as conn:
                        cursor = conn.cursor()
                        for app in batch:
                            app_id = app['app_id']
                            tags = tags_dict.get(app_id, [])

                            cursor.execute("""
                                UPDATE app_tags
                                SET tags = ?, llm_generated = 1
                                WHERE app_id = ?
                            """, (json.dumps(tags, ensure_ascii=False), app_id))

                            if tags:
                                total_success += 1
                            else:
                                total_fail += 1

                        conn.commit()

                    app_logger.info(f"✓ 第 {batch_num} 批完成: 成功 {len([t for t in tags_dict.values() if t])}/{len(batch)}")

                except Exception as e:
                    total_fail += len(batch)
                    app_logger.error(f"✗ 第 {batch_num} 批处理失败: {type(e).__name__}: {str(e)}", exc_info=True)

            app_logger.info(f"========== APP标签生成完成: 成功 {total_success}/{len(app_list)}, 失败 {total_fail}/{len(app_list)} ==========")

        except Exception as e:
            app_logger.error(f"批量生成APP标签失败: {type(e).__name__}: {str(e)}", exc_info=True)

    def query_app_tags(self, limit: int = 100, offset: int = 0) -> Dict:
        """查询APP标签"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 先查询总数
                cursor.execute("SELECT COUNT(*) FROM app_tags")
                total = cursor.fetchone()[0]

                cursor.execute("""
                    SELECT id, app_id, app_name, category, tags, llm_generated, created_at
                    FROM app_tags
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?
                """, (limit, offset))

                items = []
                for row in cursor.fetchall():
                    items.append({
                        "id": row[0],
                        "app_id": row[1],
                        "app_name": row[2],
                        "category": row[3],
                        "tags": json.loads(row[4]) if row[4] else [],
                        "llm_generated": bool(row[5]),
                        "created_at": row[6]
                    })

                return {
                    "items": items,
                    "total": total,
                    "limit": limit,
                    "offset": offset
                }
        except Exception as e:
            app_logger.error(f"查询APP标签失败: {e}", exc_info=True)
            return {
                "items": [],
                "total": 0,
                "limit": limit,
                "offset": offset
            }

    # ========== 媒体标签管理 ==========

    async def import_media_list(self, media_list: List[Dict]) -> Dict:
        """导入媒体列表并自动生成标签"""
        try:
            saved_count = 0
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                for media in media_list:
                    cursor.execute("""
                        INSERT OR REPLACE INTO media_tags
                        (media_id, media_name, media_type, tags, llm_generated)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        media.get("media_id"),
                        media.get("media_name"),
                        media.get("media_type"),
                        json.dumps(media.get("tags", []), ensure_ascii=False),
                        0  # 初始未打标
                    ))
                    saved_count += 1
                conn.commit()

            app_logger.info(f"成功导入 {saved_count} 个媒体，开始LLM打标...")

            # 异步调用LLM为所有媒体生成标签
            asyncio.create_task(self._generate_media_tags_async())

            return {
                "success": True,
                "saved_count": saved_count,
                "tagging_status": "pending"
            }
        except Exception as e:
            app_logger.error(f"导入媒体列表失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    async def _generate_media_tags_async(self):
        """异步为所有媒体生成标签"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id, media_id, media_name, media_type FROM media_tags WHERE llm_generated = 0")
                media_list = cursor.fetchall()

            if not media_list:
                app_logger.info("没有需要打标的媒体")
                return

            app_logger.info(f"========== 开始批量生成媒体标签: 共 {len(media_list)} 个媒体 ==========")

            # 转换为字典列表
            media_dict_list = [
                {
                    "media_id": row[1],
                    "media_name": row[2],
                    "media_type": row[3]
                }
                for row in media_list
            ]

            # 分批处理，每批100个
            batch_size = 100
            total_success = 0
            total_fail = 0

            for i in range(0, len(media_dict_list), batch_size):
                batch = media_dict_list[i:i + batch_size]
                batch_num = i // batch_size + 1
                total_batches = (len(media_dict_list) + batch_size - 1) // batch_size

                app_logger.info(f"处理第 {batch_num}/{total_batches} 批，共 {len(batch)} 个媒体")

                try:
                    # 批量调用LLM
                    tags_dict = await self.llm_client.generate_media_tags_batch(batch)

                    # 批量更新数据库
                    with sqlite3.connect(self.db_path) as conn:
                        cursor = conn.cursor()
                        for media in batch:
                            media_id = media['media_id']
                            tags = tags_dict.get(media_id, [])

                            cursor.execute("""
                                UPDATE media_tags
                                SET tags = ?, llm_generated = 1
                                WHERE media_id = ?
                            """, (json.dumps(tags, ensure_ascii=False), media_id))

                            if tags:
                                total_success += 1
                            else:
                                total_fail += 1

                        conn.commit()

                    app_logger.info(f"✓ 第 {batch_num} 批完成: 成功 {len([t for t in tags_dict.values() if t])}/{len(batch)}")

                except Exception as e:
                    total_fail += len(batch)
                    app_logger.error(f"✗ 第 {batch_num} 批处理失败: {type(e).__name__}: {str(e)}", exc_info=True)

            app_logger.info(f"========== 媒体标签生成完成: 成功 {total_success}/{len(media_dict_list)}, 失败 {total_fail}/{len(media_dict_list)} ==========")

        except Exception as e:
            app_logger.error(f"批量生成媒体标签失败: {type(e).__name__}: {str(e)}", exc_info=True)

    def query_media_tags(self, limit: int = 100, offset: int = 0) -> Dict:
        """查询媒体标签"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 先查询总数
                cursor.execute("SELECT COUNT(*) FROM media_tags")
                total = cursor.fetchone()[0]

                cursor.execute("""
                    SELECT id, media_id, media_name, media_type, tags, llm_generated, created_at
                    FROM media_tags
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?
                """, (limit, offset))

                items = []
                for row in cursor.fetchall():
                    items.append({
                        "id": row[0],
                        "media_id": row[1],
                        "media_name": row[2],
                        "media_type": row[3],
                        "tags": json.loads(row[4]) if row[4] else [],
                        "llm_generated": bool(row[5]),
                        "created_at": row[6]
                    })

                return {
                    "items": items,
                    "total": total,
                    "limit": limit,
                    "offset": offset
                }
        except Exception as e:
            app_logger.error(f"查询媒体标签失败: {e}", exc_info=True)
            return {
                "items": [],
                "total": 0,
                "limit": limit,
                "offset": offset
            }

    # ========== 用户画像管理 ==========

    def import_user_profiles(self, profiles: List[Dict]) -> Dict:
        """导入用户画像（支持结构化和非结构化格式）

        支持两种格式:
        1. 结构化格式: {user_id, age, gender, city, occupation, income, interests, ...}
        2. 非结构化格式: {user_id, profile_text}

        系统会自动检测格式并处理:
        - 如果有 profile_text 字段，直接使用
        - 如果有结构化字段（age, gender等），自动生成 profile_text
        """
        try:
            from app.utils.profile_formatter import format_profile_text
            import json

            saved_count = 0
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                for profile in profiles:
                    user_id = profile.get("user_id")
                    if not user_id:
                        continue

                    # 检测格式：是否有 profile_text 字段
                    has_profile_text = "profile_text" in profile and profile["profile_text"]

                    # 提取结构化字段
                    age = profile.get("age")
                    gender = profile.get("gender")
                    city = profile.get("city")
                    occupation = profile.get("occupation")

                    # 构建 properties JSON（存储额外字段）
                    properties = {}
                    for key in ["income", "interests", "budget", "has_car", "purchase_intent"]:
                        if key in profile and profile[key] is not None:
                            properties[key] = profile[key]

                    properties_json = json.dumps(properties, ensure_ascii=False) if properties else None

                    # 生成或使用 profile_text
                    if has_profile_text:
                        # 使用提供的 profile_text
                        profile_text = profile["profile_text"]
                    else:
                        # 从结构化数据生成 profile_text
                        profile_text = format_profile_text(profile)

                    # 插入数据（支持所有字段）
                    cursor.execute("""
                        INSERT OR REPLACE INTO user_profiles
                        (user_id, age, gender, city, occupation, properties, profile_text)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        user_id,
                        age,
                        gender,
                        city,
                        occupation,
                        properties_json,
                        profile_text
                    ))
                    saved_count += 1

                conn.commit()

            app_logger.info(f"成功导入 {saved_count} 个用户画像")
            return {
                "success": True,
                "saved_count": saved_count
            }
        except Exception as e:
            app_logger.error(f"导入用户画像失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    def query_user_profiles(self, user_id: Optional[str] = None, limit: int = 100, offset: int = 0) -> Dict:
        """查询用户画像（支持结构化和非结构化格式）

        Args:
            user_id: 可选，指定用户ID则只查询该用户
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            返回包含结构化和非结构化数据的字典，包括:
            - id: 记录ID
            - user_id: 用户ID
            - age: 年龄
            - gender: 性别
            - city: 城市
            - occupation: 职业
            - properties: 额外属性（JSON）
            - profile_text: 自然语言描述
            - created_at: 创建时间
        """
        try:
            from app.utils.profile_formatter import format_profile_text
            import json

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                if user_id:
                    # 查询指定用户
                    cursor.execute("SELECT COUNT(*) FROM user_profiles WHERE user_id = ?", (user_id,))
                    total = cursor.fetchone()[0]

                    cursor.execute("""
                        SELECT id, user_id, age, gender, city, occupation, properties, profile_text, created_at
                        FROM user_profiles
                        WHERE user_id = ?
                        ORDER BY created_at DESC
                        LIMIT ? OFFSET ?
                    """, (user_id, limit, offset))
                else:
                    # 查询所有用户
                    cursor.execute("SELECT COUNT(*) FROM user_profiles")
                    total = cursor.fetchone()[0]

                    cursor.execute("""
                        SELECT id, user_id, age, gender, city, occupation, properties, profile_text, created_at
                        FROM user_profiles
                        ORDER BY created_at DESC
                        LIMIT ? OFFSET ?
                    """, (limit, offset))

                items = []
                for row in cursor.fetchall():
                    profile_data = {
                        "id": row[0],
                        "user_id": row[1],
                        "age": row[2],
                        "gender": row[3],
                        "city": row[4],
                        "occupation": row[5],
                        "properties": row[6],
                        "created_at": row[8]
                    }

                    # 如果 profile_text 为空，从结构化数据生成
                    profile_text = row[7]
                    if not profile_text:
                        # 构建完整的 profile 字典用于格式化
                        format_dict = {
                            "user_id": row[1],
                            "age": row[2],
                            "gender": row[3],
                            "city": row[4],
                            "occupation": row[5],
                            "properties": row[6]
                        }
                        profile_text = format_profile_text(format_dict)

                    profile_data["profile_text"] = profile_text
                    items.append(profile_data)

                return {
                    "items": items,
                    "total": total,
                    "limit": limit,
                    "offset": offset
                }
        except Exception as e:
            app_logger.error(f"查询用户画像失败: {e}", exc_info=True)
            return {
                "items": [],
                "total": 0,
                "limit": limit,
                "offset": offset
            }
