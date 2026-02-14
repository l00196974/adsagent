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
from app.core.anthropic_client import AnthropicClient


class BaseModelingService:
    """基础建模服务"""

    def __init__(self):
        self.db_path = Path("data/graph.db")
        self.llm_client = AnthropicClient()

    # ========== 行为数据管理 ==========

    def import_behavior_data(self, behaviors: List[Dict]) -> Dict:
        """导入行为数据"""
        try:
            saved_count = 0
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                for behavior in behaviors:
                    cursor.execute("""
                        INSERT INTO behavior_data
                        (user_id, action, timestamp, item_id, app_id, media_id, poi_id, duration, properties)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        behavior.get("user_id"),
                        behavior.get("action"),
                        behavior.get("timestamp"),
                        behavior.get("item_id"),
                        behavior.get("app_id"),
                        behavior.get("media_id"),
                        behavior.get("poi_id"),
                        behavior.get("duration"),
                        json.dumps(behavior.get("properties", {}), ensure_ascii=False)
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
        """查询行为数据"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 先查询总数
                if user_id:
                    cursor.execute("SELECT COUNT(*) FROM behavior_data WHERE user_id = ?", (user_id,))
                    total = cursor.fetchone()[0]

                    cursor.execute("""
                        SELECT id, user_id, action, timestamp, item_id, app_id, media_id, poi_id, duration, properties
                        FROM behavior_data
                        WHERE user_id = ?
                        ORDER BY timestamp DESC
                        LIMIT ? OFFSET ?
                    """, (user_id, limit, offset))
                else:
                    cursor.execute("SELECT COUNT(*) FROM behavior_data")
                    total = cursor.fetchone()[0]

                    cursor.execute("""
                        SELECT id, user_id, action, timestamp, item_id, app_id, media_id, poi_id, duration, properties
                        FROM behavior_data
                        ORDER BY timestamp DESC
                        LIMIT ? OFFSET ?
                    """, (limit, offset))

                items = []
                for row in cursor.fetchall():
                    items.append({
                        "id": row[0],
                        "user_id": row[1],
                        "action": row[2],
                        "timestamp": row[3],
                        "item_id": row[4],
                        "app_id": row[5],
                        "media_id": row[6],
                        "poi_id": row[7],
                        "duration": row[8],
                        "properties": json.loads(row[9]) if row[9] else {}
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

            app_logger.info(f"开始为 {len(apps)} 个APP生成标签")

            for app_row in apps:
                app_id, app_name, category = app_row[1], app_row[2], app_row[3]
                try:
                    # 调用LLM生成标签
                    tags = await self.llm_client.generate_app_tags(app_name, category)

                    # 更新数据库
                    with sqlite3.connect(self.db_path) as conn:
                        cursor = conn.cursor()
                        cursor.execute("""
                            UPDATE app_tags
                            SET tags = ?, llm_generated = 1
                            WHERE app_id = ?
                        """, (json.dumps(tags, ensure_ascii=False), app_id))
                        conn.commit()

                    app_logger.info(f"为APP {app_name} 生成标签: {tags}")
                except Exception as e:
                    app_logger.error(f"为APP {app_name} 生成标签失败: {e}")

            app_logger.info("APP标签生成完成")
        except Exception as e:
            app_logger.error(f"批量生成APP标签失败: {e}", exc_info=True)

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

            app_logger.info(f"开始为 {len(media_list)} 个媒体生成标签")

            for media_row in media_list:
                media_id, media_name, media_type = media_row[1], media_row[2], media_row[3]
                try:
                    # 调用LLM生成标签
                    tags = await self.llm_client.generate_media_tags(media_name, media_type)

                    # 更新数据库
                    with sqlite3.connect(self.db_path) as conn:
                        cursor = conn.cursor()
                        cursor.execute("""
                            UPDATE media_tags
                            SET tags = ?, llm_generated = 1
                            WHERE media_id = ?
                        """, (json.dumps(tags, ensure_ascii=False), media_id))
                        conn.commit()

                    app_logger.info(f"为媒体 {media_name} 生成标签: {tags}")
                except Exception as e:
                    app_logger.error(f"为媒体 {media_name} 生成标签失败: {e}")

            app_logger.info("媒体标签生成完成")
        except Exception as e:
            app_logger.error(f"批量生成媒体标签失败: {e}", exc_info=True)

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
        """导入用户画像"""
        try:
            saved_count = 0
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                for profile in profiles:
                    cursor.execute("""
                        INSERT OR REPLACE INTO user_profiles
                        (user_id, age, gender, city, occupation, properties)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        profile.get("user_id"),
                        profile.get("age"),
                        profile.get("gender"),
                        profile.get("city"),
                        profile.get("occupation"),
                        json.dumps(profile.get("properties", {}), ensure_ascii=False)
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

    def query_user_profiles(self, limit: int = 100, offset: int = 0) -> Dict:
        """查询用户画像"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 先查询总数
                cursor.execute("SELECT COUNT(*) FROM user_profiles")
                total = cursor.fetchone()[0]

                cursor.execute("""
                    SELECT id, user_id, age, gender, city, occupation, properties, created_at
                    FROM user_profiles
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?
                """, (limit, offset))

                items = []
                for row in cursor.fetchall():
                    items.append({
                        "id": row[0],
                        "user_id": row[1],
                        "age": row[2],
                        "gender": row[3],
                        "city": row[4],
                        "occupation": row[5],
                        "properties": json.loads(row[6]) if row[6] else {},
                        "created_at": row[7]
                    })

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
