"""
知识图谱构建服务 - 支持分批处理和进度显示
"""
from typing import List, Dict, Callable, Optional
from app.data.mock_data import get_mock_users, KNOWLEDGE_GRAPH_ENTITIES, KNOWLEDGE_GRAPH_RELATIONS
from app.core.graph_db import graph_db

class KnowledgeGraphBuilder:
    """知识图谱构建服务 - 使用NetworkX图数据库"""
    
    BATCH_SIZE = 5000
    
    def __init__(self):
        self.entities = []
        self.relations = []
        self.progress = {
            "current_step": "",
            "step_progress": 0,
            "total_steps": 6,
            "current_batch": 0,
            "total_batches": 0,
            "batches_completed": [],
            "entities_created": 0,
            "relations_created": 0
        }
    
    def build(
        self, 
        user_count: int = 1000,
        progress_callback: Optional[Callable] = None
    ) -> Dict:
        """从用户数据构建知识图谱并存入图数据库"""
        self.progress = {
            "current_step": "初始化",
            "step_progress": 0,
            "total_steps": 6,
            "current_batch": 0,
            "total_batches": (user_count + self.BATCH_SIZE - 1) // self.BATCH_SIZE,
            "batches_completed": [],
            "entities_created": 0,
            "relations_created": 0
        }
        
        def notify_progress(step: str, progress: float, details: Dict = None):
            self.progress["current_step"] = step
            self.progress["step_progress"] = progress
            if details:
                self.progress.update(details)
            if progress_callback:
                progress_callback(step, progress, self.progress)
            print(f"[进度] {step}: {progress:.1%}")
        
        # Step 1: 清空旧数据
        notify_progress("清空旧数据", 0.05, {"step_name": "清除历史数据"})
        graph_db.clear_knowledge_graph()
        
        # Step 2: 加载用户数据
        notify_progress("加载用户数据", 0.1, {"step_name": "加载用户数据"})
        users = get_mock_users(user_count)
        
        total_batches = len(users) // self.BATCH_SIZE + (1 if len(users) % self.BATCH_SIZE else 0)
        self.progress["total_batches"] = total_batches
        
        # Step 3-5: 分批处理
        notify_progress("抽取实体和关系", 0.15, {"step_name": "分批处理用户数据"})
        
        for batch_idx in range(total_batches):
            start_idx = batch_idx * self.BATCH_SIZE
            end_idx = min((batch_idx + 1) * self.BATCH_SIZE, len(users))
            batch_users = users[start_idx:end_idx]
            
            self.progress["current_batch"] = batch_idx + 1
            self.progress["batch_users"] = len(batch_users)
            
            batch_progress = 0.15 + 0.55 * (batch_idx + 1) / total_batches
            notify_progress(
                f"处理批次 {batch_idx + 1}/{total_batches}", 
                batch_progress,
                {
                    "step_name": f"批次 {batch_idx + 1}/{total_batches}",
                    "batch_info": f"用户 {start_idx+1} - {end_idx}"
                }
            )
            
            batch_result = self._extract_batch(batch_users)
            self.progress["entities_created"] += batch_result["entity_count"]
            self.progress["relations_created"] += batch_result["relation_count"]
            self.progress["batches_completed"].append(batch_idx + 1)
            
            print(f"[批次] {batch_idx + 1}/{total_batches} 完成, 实体: {batch_result['entity_count']}, 关系: {batch_result['relation_count']}")
        
        # Step 6: 添加领域知识
        notify_progress("添加领域知识", 0.85, {"step_name": "添加汽车行业知识"})
        self._add_domain_entities()
        
        notify_progress("生成统计信息", 0.95, {"step_name": "计算统计信息"})
        stats = graph_db.get_stats()
        
        notify_progress("构建完成", 1.0, {
            "step_name": "完成",
            "total_entities": stats["total_entities"],
            "total_relations": stats["total_relations"]
        })
        
        return {
            "entities": graph_db.query_entities(limit=200),
            "relations": graph_db.query_relations(limit=500),
            "stats": stats,
            "progress": {
                "total_batches": total_batches,
                "batches_completed": self.progress["batches_completed"],
                "entities_created": self.progress["entities_created"],
                "relations_created": self.progress["relations_created"]
            }
        }
    
    def _extract_batch(self, users: List[Dict]) -> Dict:
        entity_count = 0
        relation_count = 0
        
        for user in users:
            uid = f"user:{user['user_id']}"
            
            graph_db.create_entity(
                entity_id=uid,
                entity_type="User",
                properties={
                    "user_id": user["user_id"],
                    "income_level": user["demographics"]["income_level"],
                    "age_bucket": user["demographics"]["age_bucket"],
                    "city_tier": user["demographics"]["city_tier"],
                    "purchase_intent": user["purchase_intent"],
                    "lifecycle_stage": user["lifecycle_stage"]
                }
            )
            entity_count += 1
            
            for interest in user["interests"]:
                iid = f"interest:{interest}"
                if not graph_db.knowledge_graph.has_node(iid):
                    graph_db.create_entity(iid, "Interest", {"name": interest})
                    entity_count += 1
            
            brand = user["brand_affinity"]["primary_brand"]
            model = user["brand_affinity"]["primary_model"]
            
            brand_id = f"brand:{brand}"
            if not graph_db.knowledge_graph.has_node(brand_id):
                graph_db.create_entity(brand_id, "Brand", {"name": brand})
                entity_count += 1
            
            model_id = f"model:{model}"
            if not graph_db.knowledge_graph.has_node(model_id):
                graph_db.create_entity(model_id, "Model", {"name": model, "brand": brand})
                entity_count += 1
            
            for interest in user["interests"]:
                graph_db.create_relation(uid, f"interest:{interest}", "HAS_INTEREST", {"weight": 0.8})
                relation_count += 1
            
            score = user["brand_affinity"]["brand_score"]
            graph_db.create_relation(uid, f"brand:{brand}", "PREFERS", {"weight": score})
            relation_count += 1
            
            graph_db.create_relation(uid, f"model:{model}", "INTERESTED_IN", {"weight": score * 0.9})
            relation_count += 1
        
        return {"entity_count": entity_count, "relation_count": relation_count}
    
    def _add_domain_entities(self):
        for entity in KNOWLEDGE_GRAPH_ENTITIES:
            graph_db.create_entity(
                entity_id=entity["id"],
                entity_type=entity["type"],
                properties={k: v for k, v in entity.items() if k not in ["id", "type"]}
            )
        
        for rel in KNOWLEDGE_GRAPH_RELATIONS:
            graph_db.create_relation(
                rel["from"], rel["to"], "RELATED", {"weight": rel.get("weight", 0.5)}
            )
    
    def get_progress(self) -> Dict:
        return self.progress


class GraphQueryEngine:
    def __init__(self):
        pass
    
    def query_by_entity(self, entity_name: str, depth: int = 2) -> Dict:
        entities = graph_db.query_entities()
        matching = [e for e in entities if entity_name in e.get("properties", {}).get("name", "")]
        if not matching:
            matching = [e for e in entities if entity_name.lower() in e["id"].lower()]
        
        results = {"entities": matching, "relations": []}
        if matching:
            for entity in matching[:5]:
                related = graph_db.find_related(entity["id"], depth)
                results["relations"].extend([
                    {"from": entity["id"], "to": r["id"], "type": "RELATED", "weight": 0.5}
                    for r in related
                ])
        return results
    
    def query_brand_interest_correlation(self, brand: str) -> Dict:
        brand_entity = f"brand:{brand}"
        correlations = []
        relations = graph_db.query_relations()
        for rel in relations:
            if rel["from"] == brand_entity:
                interest_id = rel["to"]
                interest_entity = graph_db.query_entities()
                for ie in interest_entity:
                    if ie["id"] == interest_id:
                        correlations.append({
                            "interest": ie["properties"].get("name", interest_id),
                            "weight": rel.get("weight", 0)
                        })
        correlations.sort(key=lambda x: x["weight"], reverse=True)
        return {"brand": brand, "correlations": correlations[:10]}
    
    def query_user_segment(self, criteria: Dict) -> List[Dict]:
        users = graph_db.query_entities("User")
        matching = []
        for user in users:
            props = user.get("properties", {})
            if all(props.get(k) == v for k, v in criteria.items()):
                matching.append(user)
        return matching
