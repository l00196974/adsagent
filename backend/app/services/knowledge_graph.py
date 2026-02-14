"""
知识图谱构建服务 - 支持分批处理和进度显示
"""
from typing import List, Dict, Callable, Optional
from collections import defaultdict
from app.data.mock_data import get_mock_users, KNOWLEDGE_GRAPH_ENTITIES, KNOWLEDGE_GRAPH_RELATIONS
from app.core.graph_db import graph_db
from app.core.logger import app_logger
from app.core.llm_client import llm_relation_identifier

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
        """批量提取实体和关系 - 使用批量操作提升性能"""
        entities_to_create = []
        relations_to_create = []
        seen_entities = set()

        for user in users:
            uid = f"user:{user['user_id']}"

            # 收集用户实体
            entities_to_create.append({
                "id": uid,
                "type": "User",
                "properties": {
                    "user_id": user["user_id"],
                    "income_level": user["demographics"]["income_level"],
                    "age_bucket": user["demographics"]["age_bucket"],
                    "city_tier": user["demographics"]["city_tier"],
                    "purchase_intent": user["purchase_intent"],
                    "lifecycle_stage": user["lifecycle_stage"]
                }
            })
            seen_entities.add(uid)

            # 收集兴趣实体
            for interest in user["interests"]:
                iid = f"interest:{interest}"
                if iid not in seen_entities and not graph_db.knowledge_graph.has_node(iid):
                    entities_to_create.append({
                        "id": iid,
                        "type": "Interest",
                        "properties": {"name": interest}
                    })
                    seen_entities.add(iid)

            # 收集品牌和车型实体
            brand = user["brand_affinity"]["primary_brand"]
            model = user["brand_affinity"]["primary_model"]

            brand_id = f"brand:{brand}"
            if brand_id not in seen_entities and not graph_db.knowledge_graph.has_node(brand_id):
                entities_to_create.append({
                    "id": brand_id,
                    "type": "Brand",
                    "properties": {"name": brand}
                })
                seen_entities.add(brand_id)

            model_id = f"model:{model}"
            if model_id not in seen_entities and not graph_db.knowledge_graph.has_node(model_id):
                entities_to_create.append({
                    "id": model_id,
                    "type": "Model",
                    "properties": {"name": model, "brand": brand}
                })
                seen_entities.add(model_id)

            # 收集关系
            for interest in user["interests"]:
                relations_to_create.append({
                    "from": uid,
                    "to": f"interest:{interest}",
                    "type": "HAS_INTEREST",
                    "properties": {"weight": 0.8}
                })

            score = user["brand_affinity"]["brand_score"]
            relations_to_create.append({
                "from": uid,
                "to": f"brand:{brand}",
                "type": "PREFERS",
                "properties": {"weight": score}
            })

            relations_to_create.append({
                "from": uid,
                "to": f"model:{model}",
                "type": "INTERESTED_IN",
                "properties": {"weight": score * 0.9}
            })

        # 批量创建实体和关系
        entity_count = graph_db.batch_create_entities(entities_to_create)
        relation_count = graph_db.batch_create_relations(relations_to_create)

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
    
    def build_from_csv_data(
        self,
        users: List[Dict],
        progress_callback: Optional[Callable] = None
    ) -> Dict:
        """从CSV导入的真实用户数据构建知识图谱"""
        self.progress = {
            "current_step": "初始化",
            "step_progress": 0,
            "total_steps": 5,
            "current_batch": 0,
            "total_batches": (len(users) + self.BATCH_SIZE - 1) // self.BATCH_SIZE,
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
            app_logger.info(f"[进度] {step}: {progress:.1%}")

        # Step 1: 清空旧数据
        notify_progress("清空旧数据", 0.1, {"step_name": "清除历史数据"})
        graph_db.clear_knowledge_graph()

        # Step 2: 构建商品索引(用于LLM识别)
        notify_progress("构建商品索引", 0.15, {"step_name": "构建商品名称映射"})
        item_index = llm_relation_identifier.build_item_index(users)
        app_logger.info(f"商品索引构建完成: {len(item_index)} 个商品")

        # Step 3: 统计数据
        notify_progress("分析数据", 0.2, {"step_name": "统计数据分布"})
        stats = self._calculate_statistics(users)

        total_batches = len(users) // self.BATCH_SIZE + (1 if len(users) % self.BATCH_SIZE else 0)
        self.progress["total_batches"] = total_batches

        # Step 3-4: 分批处理
        notify_progress("构建图谱", 0.3, {"step_name": "分批处理用户数据"})

        for batch_idx in range(total_batches):
            start_idx = batch_idx * self.BATCH_SIZE
            end_idx = min((batch_idx + 1) * self.BATCH_SIZE, len(users))
            batch_users = users[start_idx:end_idx]

            self.progress["current_batch"] = batch_idx + 1
            self.progress["batch_users"] = len(batch_users)

            batch_progress = 0.3 + 0.5 * (batch_idx + 1) / total_batches
            notify_progress(
                f"处理批次 {batch_idx + 1}/{total_batches}",
                batch_progress,
                {
                    "step_name": f"批次 {batch_idx + 1}/{total_batches}",
                    "batch_info": f"用户 {start_idx+1} - {end_idx}"
                }
            )

            batch_result = self._extract_csv_batch(batch_users, stats)
            self.progress["entities_created"] += batch_result["entity_count"]
            self.progress["relations_created"] += batch_result["relation_count"]
            self.progress["batches_completed"].append(batch_idx + 1)

            app_logger.info(f"[批次] {batch_idx + 1}/{total_batches} 完成, 实体: {batch_result['entity_count']}, 关系: {batch_result['relation_count']}")

        # Step 5: 生成统计信息
        notify_progress("生成统计信息", 0.9, {"step_name": "计算统计信息"})
        final_stats = graph_db.get_stats()

        notify_progress("构建完成", 1.0, {
            "step_name": "完成",
            "total_entities": final_stats["total_entities"],
            "total_relations": final_stats["total_relations"]
        })

        return {
            "entities": graph_db.query_entities(limit=200),
            "relations": graph_db.query_relations(limit=500),
            "stats": final_stats,
            "progress": {
                "total_batches": total_batches,
                "batches_completed": self.progress["batches_completed"],
                "entities_created": self.progress["entities_created"],
                "relations_created": self.progress["relations_created"]
            }
        }

    def _calculate_statistics(self, users: List[Dict]) -> Dict:
        """计算数据统计信息 - 新模型统计"""
        stats = {
            "total_users": len(users),
            "item_counts": defaultdict(int),
            "poi_counts": defaultdict(int),
            "app_counts": defaultdict(int),
            "relation_counts": defaultdict(int)
        }

        for user in users:
            # 统计Item
            if "owned_items" in user and isinstance(user["owned_items"], list):
                for item in user["owned_items"]:
                    if isinstance(item, dict):
                        item_id = item.get("item_id")
                        if item_id:
                            stats["item_counts"][item_id] += 1

            # 统计POI
            if "home_poi" in user:
                poi = user["home_poi"]
                poi_id = poi.get("poi_id") if isinstance(poi, dict) else poi
                if poi_id:
                    stats["poi_counts"][poi_id] += 1

            if "work_poi" in user:
                poi = user["work_poi"]
                poi_id = poi.get("poi_id") if isinstance(poi, dict) else poi
                if poi_id:
                    stats["poi_counts"][poi_id] += 1

            # 统计APP
            if "app_usage" in user and isinstance(user["app_usage"], list):
                for app in user["app_usage"]:
                    if isinstance(app, dict):
                        app_id = app.get("app_id")
                        if app_id:
                            stats["app_counts"][app_id] += 1

            # 统计关系类型
            if "owned_items" in user:
                stats["relation_counts"]["拥有"] += 1
            if "purchase_history" in user:
                stats["relation_counts"]["购买"] += len(user["purchase_history"])
            if "browse_history" in user:
                stats["relation_counts"]["浏览"] += len(user["browse_history"])

        return stats

    def _extract_csv_batch(self, users: List[Dict], stats: Dict) -> Dict:
        """从CSV数据批量提取实体和关系 - 新模型: User, Item, POI, APP"""
        entities_to_create = []
        relations_to_create = []
        seen_entities = set()

        for user in users:
            user_id = user.get("user_id")
            if not user_id:
                continue

            uid = f"user:{user_id}"

            # 收集用户实体
            user_props = {"user_id": user_id}
            # 添加可选属性
            for field in ["age", "age_bucket", "gender", "education", "income_level", "city_tier",
                         "occupation", "has_house", "has_car", "marital_status", "has_children"]:
                if field in user:
                    user_props[field] = user[field]

            entities_to_create.append({
                "id": uid,
                "type": "User",
                "properties": user_props
            })
            seen_entities.add(uid)

            # 收集Item实体(商品: 品类/品牌/系列/名称)
            # 支持多种数据格式: owned_items列表 或 primary_brand/primary_model字段
            items_data = []

            # 方式1: owned_items字段(对象数组)
            if "owned_items" in user and isinstance(user["owned_items"], list):
                items_data.extend(user["owned_items"])

            # 方式2: primary_brand/primary_model字段(兼容旧数据)
            if "primary_brand" in user or "primary_model" in user:
                item_obj = {}
                if "item_id" in user:
                    item_obj["item_id"] = user["item_id"]
                if "category" in user:
                    item_obj["category"] = user["category"]
                if "primary_brand" in user:
                    item_obj["brand"] = user["primary_brand"]
                if "series" in user:
                    item_obj["series"] = user["series"]
                if "primary_model" in user:
                    item_obj["name"] = user["primary_model"]
                if item_obj:
                    items_data.append(item_obj)

            # 创建Item实体
            for item in items_data:
                if not isinstance(item, dict):
                    continue

                # 生成item_id
                item_id = item.get("item_id")
                if not item_id:
                    # 如果没有item_id,使用brand+name组合
                    brand = item.get("brand", "")
                    name = item.get("name", "")
                    if brand and name:
                        item_id = f"{brand}_{name}".replace(" ", "_")
                    else:
                        continue

                iid = f"item:{item_id}"
                if iid not in seen_entities and not graph_db.knowledge_graph.has_node(iid):
                    item_props = {"item_id": item_id}
                    for field in ["category", "brand", "series", "name"]:
                        if field in item:
                            item_props[field] = item[field]

                    entities_to_create.append({
                        "id": iid,
                        "type": "Item",
                        "properties": item_props
                    })
                    seen_entities.add(iid)

            # 收集POI实体(地点)
            poi_data = []

            # home_poi和work_poi
            for poi_field in ["home_poi", "work_poi"]:
                if poi_field in user:
                    poi = user[poi_field]
                    if isinstance(poi, dict):
                        poi_data.append(poi)
                    elif isinstance(poi, str):
                        # 如果是字符串,转换为字典
                        poi_data.append({"poi_id": poi, "poi_name": poi})

            # visit_history中的POI
            if "visit_history" in user and isinstance(user["visit_history"], list):
                for visit in user["visit_history"]:
                    if isinstance(visit, dict) and "poi_id" in visit:
                        poi_data.append(visit)

            # 创建POI实体
            for poi in poi_data:
                if not isinstance(poi, dict):
                    continue

                poi_id = poi.get("poi_id")
                if not poi_id:
                    continue

                pid = f"poi:{poi_id}"
                if pid not in seen_entities and not graph_db.knowledge_graph.has_node(pid):
                    poi_props = {"poi_id": poi_id}
                    for field in ["poi_name", "poi_type"]:
                        if field in poi:
                            poi_props[field] = poi[field]

                    entities_to_create.append({
                        "id": pid,
                        "type": "POI",
                        "properties": poi_props
                    })
                    seen_entities.add(pid)

            # 收集APP实体
            app_data = []

            if "app_usage" in user and isinstance(user["app_usage"], list):
                app_data.extend(user["app_usage"])

            # 创建APP实体
            for app in app_data:
                if not isinstance(app, dict):
                    continue

                app_id = app.get("app_id")
                if not app_id:
                    continue

                aid = f"app:{app_id}"
                if aid not in seen_entities and not graph_db.knowledge_graph.has_node(aid):
                    app_props = {"app_id": app_id}
                    for field in ["app_name", "app_type"]:
                        if field in app:
                            app_props[field] = app[field]

                    entities_to_create.append({
                        "id": aid,
                        "type": "APP",
                        "properties": app_props
                    })
                    seen_entities.add(aid)

            # 创建关系 - 简单关系直接识别
            # 1. 拥有关系(owned_items)
            if "owned_items" in user and isinstance(user["owned_items"], list):
                for item in user["owned_items"]:
                    if not isinstance(item, dict):
                        continue
                    item_id = item.get("item_id")
                    if not item_id:
                        brand = item.get("brand", "")
                        name = item.get("name", "")
                        if brand and name:
                            item_id = f"{brand}_{name}".replace(" ", "_")
                    if item_id:
                        relations_to_create.append({
                            "from": uid,
                            "to": f"item:{item_id}",
                            "type": "拥有",
                            "properties": {
                                "history": [{"owned_date": item.get("owned_date", ""), "item_id": item_id}]
                            }
                        })

            # 2. 常驻POI关系
            if "home_poi" in user:
                poi = user["home_poi"]
                poi_id = poi.get("poi_id") if isinstance(poi, dict) else poi
                if poi_id:
                    relations_to_create.append({
                        "from": uid,
                        "to": f"poi:{poi_id}",
                        "type": "常驻POI",
                        "properties": {
                            "history": [{"start_date": poi.get("start_date", "") if isinstance(poi, dict) else "", "poi_id": poi_id}]
                        }
                    })

            # 3. 工作POI关系
            if "work_poi" in user:
                poi = user["work_poi"]
                poi_id = poi.get("poi_id") if isinstance(poi, dict) else poi
                if poi_id:
                    relations_to_create.append({
                        "from": uid,
                        "to": f"poi:{poi_id}",
                        "type": "工作POI",
                        "properties": {
                            "history": [{"start_date": poi.get("start_date", "") if isinstance(poi, dict) else "", "poi_id": poi_id}]
                        }
                    })

            # 4. 高频出现在POI关系
            if "visit_history" in user and isinstance(user["visit_history"], list):
                for visit in user["visit_history"]:
                    if not isinstance(visit, dict):
                        continue
                    poi_id = visit.get("poi_id")
                    if poi_id:
                        relations_to_create.append({
                            "from": uid,
                            "to": f"poi:{poi_id}",
                            "type": "高频出现在POI",
                            "properties": {
                                "history": [{
                                    "visit_date": visit.get("visit_date", ""),
                                    "visit_duration": visit.get("visit_duration", 0),
                                    "poi_id": poi_id
                                }]
                            }
                        })

            # 5. 使用APP关系
            if "app_usage" in user and isinstance(user["app_usage"], list):
                for app in user["app_usage"]:
                    if not isinstance(app, dict):
                        continue
                    app_id = app.get("app_id")
                    if app_id:
                        relations_to_create.append({
                            "from": uid,
                            "to": f"app:{app_id}",
                            "type": "使用",
                            "properties": {
                                "history": [{
                                    "usage_date": app.get("usage_date", ""),
                                    "usage_duration": app.get("usage_duration", 0),
                                    "app_id": app_id
                                }]
                            }
                        })

            # 复杂关系(购买、浏览、点击等)将在后续Phase 4中使用LLM识别
            # 这里先处理简单的行为历史数据
            if "purchase_history" in user and isinstance(user["purchase_history"], list):
                for purchase in user["purchase_history"]:
                    if not isinstance(purchase, dict):
                        continue
                    item_id = purchase.get("item_id")
                    if item_id:
                        relations_to_create.append({
                            "from": uid,
                            "to": f"item:{item_id}",
                            "type": "购买",
                            "properties": {
                                "history": [{
                                    "purchase_date": purchase.get("purchase_date", ""),
                                    "purchase_amount": purchase.get("purchase_amount", 0),
                                    "item_id": item_id
                                }]
                            }
                        })

            if "browse_history" in user and isinstance(user["browse_history"], list):
                for browse in user["browse_history"]:
                    if not isinstance(browse, dict):
                        continue
                    item_id = browse.get("item_id")
                    if item_id:
                        relations_to_create.append({
                            "from": uid,
                            "to": f"item:{item_id}",
                            "type": "浏览",
                            "properties": {
                                "history": [{
                                    "browse_date": browse.get("browse_date", ""),
                                    "browse_duration": browse.get("browse_duration", 0),
                                    "item_id": item_id
                                }]
                            }
                        })

            # 6. 曝光关系
            if "exposure_history" in user and isinstance(user["exposure_history"], list):
                for exposure in user["exposure_history"]:
                    if not isinstance(exposure, dict):
                        continue
                    item_id = exposure.get("item_id")
                    if item_id:
                        relations_to_create.append({
                            "from": uid,
                            "to": f"item:{item_id}",
                            "type": "曝光",
                            "properties": {
                                "history": [{
                                    "exposure_date": exposure.get("exposure_date", ""),
                                    "exposure_channel": exposure.get("exposure_channel", ""),
                                    "item_id": item_id
                                }]
                            }
                        })

            # 7. 点击关系
            if "click_history" in user and isinstance(user["click_history"], list):
                for click in user["click_history"]:
                    if not isinstance(click, dict):
                        continue
                    item_id = click.get("item_id")
                    if item_id:
                        relations_to_create.append({
                            "from": uid,
                            "to": f"item:{item_id}",
                            "type": "点击",
                            "properties": {
                                "history": [{
                                    "click_date": click.get("click_date", ""),
                                    "click_source": click.get("click_source", ""),
                                    "item_id": item_id
                                }]
                            }
                        })

            # 8. 搜索关系
            if "search_history" in user and isinstance(user["search_history"], list):
                for search in user["search_history"]:
                    if not isinstance(search, dict):
                        continue
                    item_id = search.get("item_id")
                    if item_id:
                        relations_to_create.append({
                            "from": uid,
                            "to": f"item:{item_id}",
                            "type": "搜索",
                            "properties": {
                                "history": [{
                                    "search_date": search.get("search_date", ""),
                                    "search_keyword": search.get("search_keyword", ""),
                                    "item_id": item_id
                                }]
                            }
                        })

            # 9. 比价过关系
            if "compare_history" in user and isinstance(user["compare_history"], list):
                for compare in user["compare_history"]:
                    if not isinstance(compare, dict):
                        continue
                    item_id = compare.get("item_id")
                    compared_items = compare.get("compared_items", [])
                    if item_id:
                        relations_to_create.append({
                            "from": uid,
                            "to": f"item:{item_id}",
                            "type": "比价过",
                            "properties": {
                                "history": [{
                                    "compare_date": compare.get("compare_date", ""),
                                    "compared_items": compared_items,
                                    "item_id": item_id
                                }]
                            }
                        })

            # 10. 留资关系
            if "register_history" in user and isinstance(user["register_history"], list):
                for register in user["register_history"]:
                    if not isinstance(register, dict):
                        continue
                    item_id = register.get("item_id")
                    if item_id:
                        relations_to_create.append({
                            "from": uid,
                            "to": f"item:{item_id}",
                            "type": "留资",
                            "properties": {
                                "history": [{
                                    "register_date": register.get("register_date", ""),
                                    "register_channel": register.get("register_channel", ""),
                                    "item_id": item_id
                                }]
                            }
                        })

        # 批量创建实体和关系
        entity_count = graph_db.batch_create_entities(entities_to_create)
        relation_count = graph_db.batch_create_relations(relations_to_create)

        return {"entity_count": entity_count, "relation_count": relation_count}

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
    
    def search_entities(self, keyword: str = None, entity_type: str = None, limit: int = 20) -> Dict:
        """搜索实体"""
        entities = graph_db.query_entities(entity_type, limit=limit * 2)
        
        if not keyword:
            return {
                "entities": entities[:limit],
                "total": len(entities),
                "keyword": keyword,
                "entity_type": entity_type
            }
        
        # 关键词搜索
        keyword_lower = keyword.lower()
        matching = []
        
        for entity in entities:
            # 在ID中搜索
            if keyword_lower in entity["id"].lower():
                matching.append(entity)
                continue
            
            # 在属性值中搜索
            props = entity.get("properties", {})
            for key, value in props.items():
                if isinstance(value, str) and keyword_lower in value.lower():
                    matching.append(entity)
                    break
                elif isinstance(value, (int, float)) and keyword_lower in str(value).lower():
                    matching.append(entity)
                    break
        
        # 去重并限制数量
        seen = set()
        unique_results = []
        for e in matching:
            if e["id"] not in seen:
                seen.add(e["id"])
                unique_results.append(e)
        
        return {
            "entities": unique_results[:limit],
            "total": len(unique_results),
            "keyword": keyword,
            "entity_type": entity_type
        }
    
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
