"""
图数据库服务 - 基于NetworkX的内存图数据库 + SQLite持久化
后续可替换为Neo4j
"""
import networkx as nx
from typing import Dict, List, Any, Optional
from collections import defaultdict
from app.core.persistence import persistence
from app.core.logger import app_logger

class GraphDatabase:
    """基于NetworkX的图数据库（带持久化）"""

    def __init__(self, enable_persistence: bool = True):
        self.knowledge_graph = nx.MultiDiGraph()
        self.event_graph = nx.DiGraph()
        self.entity_index = defaultdict(list)  # 实体索引
        self.relation_index = defaultdict(list)  # 关系索引
        self.enable_persistence = enable_persistence

        # 启动时自动加载持久化数据
        if self.enable_persistence:
            self._load_from_persistence()
    def _load_from_persistence(self):
        """从持久化层加载数据"""
        try:
            app_logger.info("正在从持久化层加载知识图谱...")
            entities = persistence.load_entities(limit=100000)
            relations = persistence.load_relations(limit=100000)

            for entity in entities:
                self.knowledge_graph.add_node(
                    entity["id"],
                    type=entity["type"],
                    **entity["properties"]
                )
                self.entity_index[entity["type"]].append(entity["id"])

            for rel in relations:
                if self.knowledge_graph.has_node(rel["from"]) and self.knowledge_graph.has_node(rel["to"]):
                    self.knowledge_graph.add_edge(
                        rel["from"],
                        rel["to"],
                        type=rel["type"],
                        weight=rel.get("weight", 0.5)
                    )
                    self.relation_index[rel["type"]].append((rel["from"], rel["to"]))

            app_logger.info(f"加载完成: {len(entities)} 个实体, {len(relations)} 个关系")
        except Exception as e:
            app_logger.warning(f"加载持久化数据失败: {e}")

    def clear_knowledge_graph(self):
        """清空知识图谱"""
        self.knowledge_graph.clear()
        self.entity_index.clear()
        self.relation_index.clear()

        # 同步清空持久化数据
        if self.enable_persistence:
            persistence.clear_knowledge_graph()
    
    def create_entity(self, entity_id: str, entity_type: str, properties: Dict = None):
        """创建实体"""
        props = properties or {}
        self.knowledge_graph.add_node(entity_id, type=entity_type, **props)
        self.entity_index[entity_type].append(entity_id)
        self.entity_index[f"type:{entity_type}"].append(entity_id)

        # 持久化到数据库
        if self.enable_persistence:
            persistence.save_entity(entity_id, entity_type, props)

        return {"id": entity_id, "type": entity_type, "properties": props}
    
    def create_relation(self, from_id: str, to_id: str, rel_type: str, properties: Dict = None):
        """创建关系"""
        if self.knowledge_graph.has_node(from_id) and self.knowledge_graph.has_node(to_id):
            props = properties or {}
            self.knowledge_graph.add_edge(from_id, to_id, type=rel_type, **props)
            self.relation_index[rel_type].append((from_id, to_id))

            # 持久化到数据库
            if self.enable_persistence:
                persistence.save_relation(from_id, to_id, rel_type, props)

            return {"from": from_id, "to": to_id, "type": rel_type, "properties": props}
        return None
    
    def query_entities(self, entity_type: str = None, limit: int = 100) -> List[Dict]:
        """查询实体"""
        entities = []
        if entity_type:
            ids = self.entity_index.get(entity_type, [])[:limit]
        else:
            ids = list(self.knowledge_graph.nodes())[:limit]
        
        for eid in ids:
            data = self.knowledge_graph.nodes.get(eid, {})
            entities.append({
                "id": eid,
                "type": data.get("type", "Unknown"),
                "properties": {k: v for k, v in data.items() if k != "type"}
            })
        return entities
    
    def query_relations(self, rel_type: str = None, limit: int = 100) -> List[Dict]:
        """查询关系"""
        relations = []
        edges = list(self.knowledge_graph.edges(data=True))[:limit]
        for u, v, data in edges:
            if not rel_type or data.get("type") == rel_type:
                relations.append({
                    "from": u,
                    "to": v,
                    "type": data.get("type", "RELATED"),
                    "weight": data.get("weight", 0.5)
                })
        return relations
    
    def find_path(self, source: str, target: str) -> List[str]:
        """查找路径"""
        try:
            path = nx.shortest_path(self.knowledge_graph, source, target)
            return path
        except nx.NetworkXNoPath:
            return []
    
    def find_related(self, entity_id: str, depth: int = 2) -> List[Dict]:
        """查找关联实体"""
        related = []
        visited = set()
        queue = [(entity_id, 0)]
        
        while queue and len(related) < 50:
            node, d = queue.pop(0)
            if node in visited:
                continue
            visited.add(node)
            
            if d > 0:
                data = self.knowledge_graph.nodes.get(node, {})
                related.append({
                    "id": node,
                    "type": data.get("type", "Unknown"),
                    "distance": d
                })
            
            if d < depth:
                for neighbor in self.knowledge_graph.successors(node):
                    queue.append((neighbor, d + 1))
                for predecessor in self.knowledge_graph.predecessors(node):
                    queue.append((predecessor, d + 1))
        
        return related
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        if self.enable_persistence:
            # 从持久化层获取准确统计
            return persistence.get_stats()
        else:
            return {
                "total_entities": self.knowledge_graph.number_of_nodes(),
                "total_relations": self.knowledge_graph.number_of_edges(),
                "entity_types": len(self.entity_index),
                "relation_types": len(self.relation_index)
            }
    
    def batch_create_entities(self, entities: List[Dict]) -> int:
        """批量创建实体（性能优化）"""
        created_count = 0
        for entity in entities:
            self.knowledge_graph.add_node(
                entity["id"],
                type=entity["type"],
                **entity.get("properties", {})
            )
            self.entity_index[entity["type"]].append(entity["id"])
            created_count += 1

        # 批量持久化
        if self.enable_persistence:
            persistence.batch_save_entities(entities)

        return created_count

    def batch_create_relations(self, relations: List[Dict]) -> int:
        """批量创建关系（性能优化）"""
        created_count = 0
        for rel in relations:
            if self.knowledge_graph.has_node(rel["from"]) and self.knowledge_graph.has_node(rel["to"]):
                self.knowledge_graph.add_edge(
                    rel["from"],
                    rel["to"],
                    type=rel["type"],
                    **rel.get("properties", {})
                )
                self.relation_index[rel["type"]].append((rel["from"], rel["to"]))
                created_count += 1

        # 批量持久化
        if self.enable_persistence:
            persistence.batch_save_relations(relations)

        return created_count

    # 事理图谱操作
    def clear_event_graph(self):
        """清空事理图谱"""
        self.event_graph.clear()

        # 同步清空持久化数据
        if self.enable_persistence:
            persistence.clear_event_graph()
    
    def create_event_node(self, node_id: str, node_type: str, properties: Dict = None):
        """创建事理节点"""
        self.event_graph.add_node(node_id, type=node_type, **(properties or {}))
        return {"id": node_id, "type": node_type, "properties": properties or {}}
    
    def create_event_edge(self, from_id: str, to_id: str, probability: float, confidence: float, relation: str = "causes"):
        """创建事理边"""
        if self.event_graph.has_node(from_id) and self.event_graph.has_node(to_id):
            self.event_graph.add_edge(from_id, to_id, 
                                     probability=probability, 
                                     confidence=confidence,
                                     relation=relation)
            return {
                "from": from_id, 
                "to": to_id, 
                "probability": probability, 
                "confidence": confidence
            }
        return None
    
    def query_causal_paths(self, source_type: str = None, target_type: str = None) -> List[Dict]:
        """查询因果路径"""
        paths = []
        for path in nx.all_simple_paths(self.event_graph, source_type, target_type, cutoff=3):
            edges = []
            for i in range(len(path) - 1):
                edge_data = self.event_graph.edges[path[i], path[i+1]]
                edges.append({
                    "from": path[i],
                    "to": path[i+1],
                    "probability": edge_data.get("probability", 0),
                    "relation": edge_data.get("relation", "causes")
                })
            paths.append({"path": path, "edges": edges})
        return paths
    
    def get_event_stats(self) -> Dict:
        """获取事理图谱统计"""
        return {
            "total_nodes": self.event_graph.number_of_nodes(),
            "total_edges": self.event_graph.number_of_edges()
        }

# 全局图数据库实例
graph_db = GraphDatabase()
