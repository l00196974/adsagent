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

            # 事理图谱表（新版本）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS causal_graphs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    graph_name TEXT NOT NULL,
                    analysis_focus TEXT,
                    source_pattern_ids TEXT,
                    total_users INTEGER,
                    total_patterns INTEGER,
                    graph_data TEXT NOT NULL,
                    insights TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS causal_graph_nodes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    graph_id INTEGER NOT NULL,
                    node_id TEXT NOT NULL,
                    node_type TEXT NOT NULL,
                    node_name TEXT NOT NULL,
                    description TEXT,
                    properties TEXT,
                    FOREIGN KEY (graph_id) REFERENCES causal_graphs(id) ON DELETE CASCADE
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS causal_graph_edges (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    graph_id INTEGER NOT NULL,
                    from_node_id TEXT NOT NULL,
                    to_node_id TEXT NOT NULL,
                    relation_type TEXT NOT NULL,
                    relation_desc TEXT,
                    probability REAL,
                    confidence REAL,
                    condition TEXT,
                    support_count INTEGER,
                    properties TEXT,
                    FOREIGN KEY (graph_id) REFERENCES causal_graphs(id) ON DELETE CASCADE
                )
            """)

            # 创建索引
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_relations_from ON relations(from_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_relations_to ON relations(to_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_relations_type ON relations(type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_behavior_user ON behavior_data(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_behavior_timestamp ON behavior_data(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_behavior_user_timestamp ON behavior_data(user_id, timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_extracted_events_user ON extracted_events(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_extracted_events_timestamp ON extracted_events(timestamp)")
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
        """批量保存实体（优化版：使用executemany）"""
        if not entities:
            return 0

        saved_count = 0
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 准备批量数据
                data = [
                    (
                        entity["id"],
                        entity["type"],
                        json.dumps(entity.get("properties", {}), ensure_ascii=False)
                    )
                    for entity in entities
                ]

                # 使用executemany批量插入（10-20倍性能提升）
                cursor.executemany(
                    "INSERT OR REPLACE INTO entities (id, type, properties) VALUES (?, ?, ?)",
                    data
                )
                saved_count = len(data)
                conn.commit()

        except Exception as e:
            logger.error(f"批量保存实体失败: {e}")

        return saved_count

    def batch_save_relations(self, relations: List[Dict]) -> int:
        """批量保存关系（优化版：使用executemany）"""
        if not relations:
            return 0

        saved_count = 0
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 准备批量数据
                data = [
                    (
                        rel["from"],
                        rel["to"],
                        rel["type"],
                        json.dumps(rel.get("properties", {}), ensure_ascii=False)
                    )
                    for rel in relations
                ]

                # 使用executemany批量插入（10-20倍性能提升）
                cursor.executemany(
                    "INSERT INTO relations (from_id, to_id, type, properties) VALUES (?, ?, ?, ?)",
                    data
                )
                saved_count = len(data)
                conn.commit()

        except Exception as e:
            logger.error(f"批量保存关系失败: {e}")
        return saved_count

    # ========== 事理图谱持久化（新版本）==========

    def save_causal_graph(self, graph_name: str, analysis_focus: str, source_pattern_ids: List[int],
                         total_users: int, total_patterns: int, graph_data: Dict, insights: List[str]) -> int:
        """保存事理图谱"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """INSERT INTO causal_graphs
                       (graph_name, analysis_focus, source_pattern_ids, total_users, total_patterns, graph_data, insights)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (graph_name, analysis_focus, json.dumps(source_pattern_ids),
                     total_users, total_patterns, json.dumps(graph_data, ensure_ascii=False),
                     json.dumps(insights, ensure_ascii=False))
                )
                graph_id = cursor.lastrowid
                conn.commit()
                logger.info(f"事理图谱已保存: {graph_id}")
                return graph_id
        except Exception as e:
            logger.error(f"保存事理图谱失败: {e}")
            return -1

    def save_causal_graph_nodes(self, graph_id: int, nodes: List[Dict]) -> int:
        """批量保存事理图谱节点（优化版：使用executemany）"""
        if not nodes:
            return 0

        saved_count = 0
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 准备批量数据
                data = [
                    (
                        graph_id,
                        node["id"],
                        node["type"],
                        node["name"],
                        node.get("description", ""),
                        json.dumps(node.get("properties", {}), ensure_ascii=False)
                    )
                    for node in nodes
                ]

                # 使用executemany批量插入
                cursor.executemany(
                    """INSERT INTO causal_graph_nodes
                       (graph_id, node_id, node_type, node_name, description, properties)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    data
                )
                saved_count = len(data)
                conn.commit()

        except Exception as e:
            logger.error(f"批量保存节点失败: {e}")

        return saved_count

    def save_causal_graph_edges(self, graph_id: int, edges: List[Dict]) -> int:
        """批量保存事理图谱边（优化版：使用executemany）"""
        if not edges:
            return 0

        saved_count = 0
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 准备批量数据
                data = [
                    (
                        graph_id,
                        edge["from"],
                        edge["to"],
                        edge["relation_type"],
                        edge.get("relation_desc", ""),
                        edge.get("probability", 0.0),
                        edge.get("confidence", 0.0),
                        edge.get("condition", ""),
                        edge.get("support_count", 0),
                        json.dumps(edge.get("properties", {}), ensure_ascii=False)
                    )
                    for edge in edges
                ]

                # 使用executemany批量插入
                cursor.executemany(
                    """INSERT INTO causal_graph_edges
                       (graph_id, from_node_id, to_node_id, relation_type, relation_desc,
                        probability, confidence, condition, support_count, properties)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    data
                )
                saved_count = len(data)
                conn.commit()

        except Exception as e:
            logger.error(f"批量保存边失败: {e}")

        return saved_count

    def get_causal_graph(self, graph_id: int) -> Optional[Dict]:
        """获取事理图谱"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """SELECT id, graph_name, analysis_focus, source_pattern_ids, total_users,
                              total_patterns, graph_data, insights, created_at, updated_at
                       FROM causal_graphs WHERE id = ?""",
                    (graph_id,)
                )
                row = cursor.fetchone()
                if not row:
                    return None

                return {
                    "id": row[0],
                    "graph_name": row[1],
                    "analysis_focus": row[2],
                    "source_pattern_ids": json.loads(row[3]),
                    "total_users": row[4],
                    "total_patterns": row[5],
                    "graph_data": json.loads(row[6]),
                    "insights": json.loads(row[7]),
                    "created_at": row[8],
                    "updated_at": row[9]
                }
        except Exception as e:
            logger.error(f"获取事理图谱失败: {e}")
            return None

    def list_causal_graphs(self, limit: int = 20, offset: int = 0) -> List[Dict]:
        """获取事理图谱列表"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """SELECT id, graph_name, analysis_focus, total_users, total_patterns,
                              created_at, updated_at
                       FROM causal_graphs
                       ORDER BY created_at DESC
                       LIMIT ? OFFSET ?""",
                    (limit, offset)
                )
                graphs = []
                for row in cursor.fetchall():
                    graphs.append({
                        "id": row[0],
                        "graph_name": row[1],
                        "analysis_focus": row[2],
                        "total_users": row[3],
                        "total_patterns": row[4],
                        "created_at": row[5],
                        "updated_at": row[6]
                    })
                return graphs
        except Exception as e:
            logger.error(f"获取事理图谱列表失败: {e}")
            return []

    def delete_causal_graph(self, graph_id: int) -> bool:
        """删除事理图谱"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM causal_graphs WHERE id = ?", (graph_id,))
                conn.commit()
                logger.info(f"事理图谱已删除: {graph_id}")
                return True
        except Exception as e:
            logger.error(f"删除事理图谱失败: {e}")
            return False


# 全局持久化实例
persistence = GraphPersistence()
