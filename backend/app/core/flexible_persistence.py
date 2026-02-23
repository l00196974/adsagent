"""
灵活的持久化层 - 支持最小结构化的数据存储

核心设计:
- 只有必需字段是结构化的 (user_id, timestamp)
- 其他信息以文本形式存储，支持多种格式
- 延迟解析，只在需要时解析文本内容
"""

import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path

from app.core.data_parser import DataParser, BehaviorEventParser, UserProfileParser
from app.core.logger import app_logger


class FlexiblePersistence:
    """灵活的数据持久化层"""

    def __init__(self, db_path: str = "data/graph.db"):
        self.db_path = db_path
        self._ensure_tables()

    def _ensure_tables(self):
        """确保灵活数据表存在"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # 创建灵活的行为事件表
            # 核心设计：只有user_id和event_time是结构化的，其他都是非结构化文本
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS behavior_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    event_time DATETIME NOT NULL,
                    event_data TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 创建灵活的用户画像表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_profiles_v2 (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT UNIQUE NOT NULL,
                    profile_data TEXT NOT NULL,
                    profile_version INTEGER DEFAULT 1,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 创建灵活的事件序列表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS event_sequences_v2 (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    sequence_data TEXT NOT NULL,
                    start_time DATETIME,
                    end_time DATETIME,
                    event_count INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 创建索引（只为结构化字段创建索引）
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_behavior_events_user_time
                ON behavior_events(user_id, event_time)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_profiles_v2_user
                ON user_profiles_v2(user_id)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_event_sequences_v2_user
                ON event_sequences_v2(user_id)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_event_sequences_v2_time
                ON event_sequences_v2(start_time, end_time)
            """)

            conn.commit()

    # ==================== 行为事件操作 ====================

    def insert_behavior_event(
        self,
        user_id: str,
        event_time: datetime,
        event_data: str
    ) -> int:
        """插入单个行为事件

        Args:
            user_id: 用户ID（结构化）
            event_time: 事件时间（结构化）
            event_data: 事件数据（非结构化文本：JSON/键值对/自由文本）

        Returns:
            插入的记录ID
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO behavior_events (user_id, event_time, event_data)
                VALUES (?, ?, ?)
            """, (user_id, event_time, event_data))
            conn.commit()
            return cursor.lastrowid

    def batch_insert_behavior_events(self, events: List[Dict[str, Any]]) -> int:
        """批量插入行为事件

        Args:
            events: 事件列表，每个事件包含:
                - user_id: 用户ID（必需，结构化）
                - event_time: 事件时间（必需，结构化）
                - event_data: 事件数据（必需，非结构化文本）

        Returns:
            插入的记录数
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            data = [
                (
                    e["user_id"],
                    e["event_time"],
                    e["event_data"]
                )
                for e in events
            ]

            cursor.executemany("""
                INSERT INTO behavior_events (user_id, event_time, event_data)
                VALUES (?, ?, ?)
            """, data)

            conn.commit()
            return len(data)

    def query_behavior_events(
        self,
        user_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000,
        offset: int = 0,
        parse: bool = True
    ) -> List[Dict[str, Any]]:
        """查询行为事件

        Args:
            user_id: 用户ID过滤
            start_time: 开始时间
            end_time: 结束时间
            limit: 返回数量限制
            offset: 偏移量
            parse: 是否解析event_data

        Returns:
            事件列表
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # 构建查询条件
            conditions = []
            params = []

            if user_id:
                conditions.append("user_id = ?")
                params.append(user_id)

            if start_time:
                conditions.append("event_time >= ?")
                params.append(start_time)

            if end_time:
                conditions.append("event_time <= ?")
                params.append(end_time)

            where_clause = " AND ".join(conditions) if conditions else "1=1"

            cursor.execute(f"""
                SELECT id, user_id, event_time, event_data, created_at
                FROM behavior_events
                WHERE {where_clause}
                ORDER BY event_time DESC
                LIMIT ? OFFSET ?
            """, params + [limit, offset])

            events = []
            for row in cursor.fetchall():
                event = {
                    "id": row[0],
                    "user_id": row[1],
                    "event_time": row[2],
                    "event_data_raw": row[3],
                    "created_at": row[4]
                }

                # 解析event_data
                if parse:
                    event["event_data"] = BehaviorEventParser.parse_event(row[3])
                else:
                    event["event_data"] = row[3]

                events.append(event)

            return events

    # ==================== 用户画像操作 ====================

    def upsert_user_profile(
        self,
        user_id: str,
        profile_data: str,
        profile_version: int = 1
    ) -> None:
        """插入或更新用户画像

        Args:
            user_id: 用户ID
            profile_data: 画像数据（文本格式）
            profile_version: 画像版本号
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO user_profiles_v2 (user_id, profile_data, profile_version, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id) DO UPDATE SET
                    profile_data = excluded.profile_data,
                    profile_version = excluded.profile_version,
                    updated_at = CURRENT_TIMESTAMP
            """, (user_id, profile_data, profile_version))
            conn.commit()

    def batch_upsert_user_profiles(self, profiles: List[Dict[str, Any]]) -> int:
        """批量插入或更新用户画像

        Args:
            profiles: 画像列表，每个包含 user_id, profile_data, profile_version(可选)

        Returns:
            处理的记录数
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            for profile in profiles:
                cursor.execute("""
                    INSERT INTO user_profiles_v2 (user_id, profile_data, profile_version, updated_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(user_id) DO UPDATE SET
                        profile_data = excluded.profile_data,
                        profile_version = excluded.profile_version,
                        updated_at = CURRENT_TIMESTAMP
                """, (
                    profile["user_id"],
                    profile["profile_data"],
                    profile.get("profile_version", 1)
                ))

            conn.commit()
            return len(profiles)

    def query_user_profile(
        self,
        user_id: str,
        parse: bool = True
    ) -> Optional[Dict[str, Any]]:
        """查询用户画像

        Args:
            user_id: 用户ID
            parse: 是否解析profile_data

        Returns:
            用户画像或None
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT user_id, profile_data, profile_version, updated_at, created_at
                FROM user_profiles_v2
                WHERE user_id = ?
            """, (user_id,))

            row = cursor.fetchone()
            if not row:
                return None

            profile = {
                "user_id": row[0],
                "profile_data_raw": row[1],
                "profile_version": row[2],
                "updated_at": row[3],
                "created_at": row[4]
            }

            # 解析profile_data
            if parse:
                profile["profile_data"] = UserProfileParser.parse_profile(row[1])
            else:
                profile["profile_data"] = row[1]

            return profile

    # ==================== 事件序列操作 ====================

    def insert_event_sequence(
        self,
        user_id: str,
        sequence_data: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        event_count: Optional[int] = None
    ) -> int:
        """插入事件序列

        Args:
            user_id: 用户ID
            sequence_data: 序列数据（文本格式，通常是JSON数组）
            start_time: 序列开始时间
            end_time: 序列结束时间
            event_count: 事件数量

        Returns:
            插入的记录ID
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO event_sequences_v2 (user_id, sequence_data, start_time, end_time, event_count)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, sequence_data, start_time, end_time, event_count))
            conn.commit()
            return cursor.lastrowid

    def query_event_sequences(
        self,
        user_id: Optional[str] = None,
        limit: int = 1000,
        offset: int = 0,
        parse: bool = True
    ) -> List[Dict[str, Any]]:
        """查询事件序列

        Args:
            user_id: 用户ID过滤
            limit: 返回数量限制
            offset: 偏移量
            parse: 是否解析sequence_data

        Returns:
            序列列表
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            if user_id:
                cursor.execute("""
                    SELECT id, user_id, sequence_data, start_time, end_time, event_count, created_at
                    FROM event_sequences_v2
                    WHERE user_id = ?
                    ORDER BY start_time DESC
                    LIMIT ? OFFSET ?
                """, (user_id, limit, offset))
            else:
                cursor.execute("""
                    SELECT id, user_id, sequence_data, start_time, end_time, event_count, created_at
                    FROM event_sequences_v2
                    ORDER BY start_time DESC
                    LIMIT ? OFFSET ?
                """, (limit, offset))

            sequences = []
            for row in cursor.fetchall():
                sequence = {
                    "id": row[0],
                    "user_id": row[1],
                    "sequence_data_raw": row[2],
                    "start_time": row[3],
                    "end_time": row[4],
                    "event_count": row[5],
                    "created_at": row[6]
                }

                # 解析sequence_data
                if parse:
                    try:
                        sequence["sequence_data"] = json.loads(row[2])
                    except:
                        sequence["sequence_data"] = row[2]
                else:
                    sequence["sequence_data"] = row[2]

                sequences.append(sequence)

            return sequences

    # ==================== 统计操作 ====================

    def get_statistics(self) -> Dict[str, Any]:
        """获取数据统计信息

        Returns:
            统计信息字典
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            stats = {}

            # 行为事件统计
            cursor.execute("SELECT COUNT(*) FROM behavior_events")
            stats["behavior_events_count"] = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(DISTINCT user_id) FROM behavior_events")
            stats["behavior_events_users"] = cursor.fetchone()[0]

            # 用户画像统计
            cursor.execute("SELECT COUNT(*) FROM user_profiles_v2")
            stats["user_profiles_count"] = cursor.fetchone()[0]

            # 事件序列统计
            cursor.execute("SELECT COUNT(*) FROM event_sequences_v2")
            stats["event_sequences_count"] = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(DISTINCT user_id) FROM event_sequences_v2")
            stats["event_sequences_users"] = cursor.fetchone()[0]

            return stats
