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
