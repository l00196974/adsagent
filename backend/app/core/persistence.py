"""
数据持久化层 - 基于SQLite的图数据库持久化
"""
import sqlite3
import json
import pickle
from typing import Dict, List, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class GraphPersistence:
    """图数据库持久化服务"""

    def __init__(self, db_path: str = "data/graph.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()

    def _init_database(self):
        """初始化数据库表结构"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # 实体表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS entities (
                    id TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    properties TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 关系表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS relations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    from_id TEXT NOT NULL,
                    to_id TEXT NOT NULL,
                    type TEXT NOT NULL,
                    properties TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (from_id) REFERENCES entities(id),
                    FOREIGN KEY (to_id) REFERENCES entities(id)
                )
            """)

            # 事理图谱节点表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS event_nodes (
                    id TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    properties TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 事理图谱边表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS event_edges (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    from_id TEXT NOT NULL,
                    to_id TEXT NOT NULL,
                    probability REAL NOT NULL,
                    confidence REAL NOT NULL,
                    relation TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (from_id) REFERENCES event_nodes(id),
                    FOREIGN KEY (to_id) REFERENCES event_nodes(id)
                )
            """)

            # 基础建模模块表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS behavior_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    timestamp DATETIME NOT NULL,
                    item_id TEXT,
                    app_id TEXT,
                    media_id TEXT,
                    poi_id TEXT,
                    duration INTEGER,
                    properties TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS app_tags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    app_id TEXT UNIQUE NOT NULL,
                    app_name TEXT NOT NULL,
                    category TEXT,
                    tags TEXT,
                    llm_generated INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS media_tags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    media_id TEXT UNIQUE NOT NULL,
                    media_name TEXT NOT NULL,
                    media_type TEXT,
                    tags TEXT,
                    llm_generated INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_profiles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT UNIQUE NOT NULL,
                    age INTEGER,
                    gender TEXT,
                    city TEXT,
                    occupation TEXT,
                    properties TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 事件提取模块表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS extracted_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT UNIQUE NOT NULL,
                    user_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    timestamp DATETIME NOT NULL,
                    context TEXT,
                    source_behavior_ids TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS event_sequences (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    sequence TEXT,
                    start_time DATETIME,
                    end_time DATETIME,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 序列模式挖掘模块表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS frequent_patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pattern_id TEXT UNIQUE NOT NULL,
                    pattern_sequence TEXT,
                    support REAL,
                    confidence REAL,
                    occurrence_count INTEGER,
                    user_count INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 因果逻辑归纳模块表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS causal_rules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    rule_id TEXT UNIQUE NOT NULL,
                    antecedent TEXT,
                    consequent TEXT,
                    confidence REAL,
                    support REAL,
                    lift REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS event_graph_nodes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    node_id TEXT UNIQUE NOT NULL,
                    node_type TEXT NOT NULL,
                    properties TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS event_graph_edges (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    from_node TEXT NOT NULL,
                    to_node TEXT NOT NULL,
                    edge_type TEXT NOT NULL,
                    probability REAL,
                    confidence REAL,
                    properties TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 创建索引
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_relations_from ON relations(from_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_relations_to ON relations(to_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_relations_type ON relations(type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_behavior_user ON behavior_data(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_behavior_timestamp ON behavior_data(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_extracted_events_user ON extracted_events(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_event_sequences_user ON event_sequences(user_id)")

            conn.commit()
            logger.info(f"数据库初始化完成: {self.db_path}")

    # ========== 知识图谱持久化 ==========

    def save_entity(self, entity_id: str, entity_type: str, properties: Dict) -> bool:
        """保存实体"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT OR REPLACE INTO entities (id, type, properties) VALUES (?, ?, ?)",
                    (entity_id, entity_type, json.dumps(properties, ensure_ascii=False))
                )
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"保存实体失败: {e}")
            return False

    def save_relation(self, from_id: str, to_id: str, rel_type: str, properties: Dict) -> bool:
        """保存关系"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO relations (from_id, to_id, type, properties) VALUES (?, ?, ?, ?)",
                    (from_id, to_id, rel_type, json.dumps(properties, ensure_ascii=False))
                )
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"保存关系失败: {e}")
            return False

    def load_entities(self, entity_type: Optional[str] = None, limit: int = 1000) -> List[Dict]:
        """加载实体"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                if entity_type:
                    cursor.execute(
                        "SELECT id, type, properties FROM entities WHERE type = ? LIMIT ?",
                        (entity_type, limit)
                    )
                else:
                    cursor.execute("SELECT id, type, properties FROM entities LIMIT ?", (limit,))

                entities = []
                for row in cursor.fetchall():
                    entities.append({
                        "id": row[0],
                        "type": row[1],
                        "properties": json.loads(row[2])
                    })
                return entities
        except Exception as e:
            logger.error(f"加载实体失败: {e}")
            return []

    def load_relations(self, rel_type: Optional[str] = None, limit: int = 1000) -> List[Dict]:
        """加载关系"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                if rel_type:
                    cursor.execute(
                        "SELECT from_id, to_id, type, properties FROM relations WHERE type = ? LIMIT ?",
                        (rel_type, limit)
                    )
                else:
                    cursor.execute("SELECT from_id, to_id, type, properties FROM relations LIMIT ?", (limit,))

                relations = []
                for row in cursor.fetchall():
                    props = json.loads(row[3])
                    relations.append({
                        "from": row[0],
                        "to": row[1],
                        "type": row[2],
                        "weight": props.get("weight", 0.5)
                    })
                return relations
        except Exception as e:
            logger.error(f"加载关系失败: {e}")
            return []

    def clear_knowledge_graph(self) -> bool:
        """清空知识图谱"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM relations")
                cursor.execute("DELETE FROM entities")
                conn.commit()
                logger.info("知识图谱已清空")
                return True
        except Exception as e:
            logger.error(f"清空知识图谱失败: {e}")
            return False

    def get_stats(self) -> Dict:
        """获取统计信息"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute("SELECT COUNT(*) FROM entities")
                entity_count = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM relations")
                relation_count = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(DISTINCT type) FROM entities")
                entity_types = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(DISTINCT type) FROM relations")
                relation_types = cursor.fetchone()[0]

                return {
                    "total_entities": entity_count,
                    "total_relations": relation_count,
                    "entity_types": entity_types,
                    "relation_types": relation_types
                }
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {
                "total_entities": 0,
                "total_relations": 0,
                "entity_types": 0,
                "relation_types": 0
            }

    # ========== 事理图谱持久化 ==========

    def save_event_node(self, node_id: str, node_type: str, properties: Dict) -> bool:
        """保存事理节点"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT OR REPLACE INTO event_nodes (id, type, properties) VALUES (?, ?, ?)",
                    (node_id, node_type, json.dumps(properties, ensure_ascii=False))
                )
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"保存事理节点失败: {e}")
            return False

    def save_event_edge(self, from_id: str, to_id: str, probability: float,
                       confidence: float, relation: str) -> bool:
        """保存事理边"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """INSERT INTO event_edges
                       (from_id, to_id, probability, confidence, relation)
                       VALUES (?, ?, ?, ?, ?)""",
                    (from_id, to_id, probability, confidence, relation)
                )
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"保存事理边失败: {e}")
            return False

    def clear_event_graph(self) -> bool:
        """清空事理图谱"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM event_edges")
                cursor.execute("DELETE FROM event_nodes")
                conn.commit()
                logger.info("事理图谱已清空")
                return True
        except Exception as e:
            logger.error(f"清空事理图谱失败: {e}")
            return False

    # ========== 批量操作 ==========

    def batch_save_entities(self, entities: List[Dict]) -> int:
        """批量保存实体"""
        saved_count = 0
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                for entity in entities:
                    try:
                        cursor.execute(
                            "INSERT OR REPLACE INTO entities (id, type, properties) VALUES (?, ?, ?)",
                            (entity["id"], entity["type"], json.dumps(entity.get("properties", {}), ensure_ascii=False))
                        )
                        saved_count += 1
                    except Exception as e:
                        logger.warning(f"保存实体 {entity.get('id')} 失败: {e}")
                conn.commit()
        except Exception as e:
            logger.error(f"批量保存实体失败: {e}")
        return saved_count

    def batch_save_relations(self, relations: List[Dict]) -> int:
        """批量保存关系"""
        saved_count = 0
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                for rel in relations:
                    try:
                        cursor.execute(
                            "INSERT INTO relations (from_id, to_id, type, properties) VALUES (?, ?, ?, ?)",
                            (rel["from"], rel["to"], rel["type"], json.dumps(rel.get("properties", {}), ensure_ascii=False))
                        )
                        saved_count += 1
                    except Exception as e:
                        logger.warning(f"保存关系失败: {e}")
                conn.commit()
        except Exception as e:
            logger.error(f"批量保存关系失败: {e}")
        return saved_count


# 全局持久化实例
persistence = GraphPersistence()
