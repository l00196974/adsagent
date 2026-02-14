"""CSV导入路由 - 支持分离的实体和关系CSV文件"""
from fastapi import APIRouter, HTTPException
from typing import Dict, List
import pandas as pd
import json
from pathlib import Path
from app.core.dependencies import get_kg_builder, get_graph_db
from app.services.knowledge_graph import KnowledgeGraphBuilder
from app.core.graph_db import GraphDatabase
from app.core.logger import app_logger
from fastapi import Depends

router = APIRouter()

@router.post("/import-separated-csv")
async def import_separated_csv(
    builder: KnowledgeGraphBuilder = Depends(get_kg_builder),
    graph_db: GraphDatabase = Depends(get_graph_db)
):
    """
    从分离的CSV文件导入数据构建事件中心知识图谱

    需要以下CSV文件:
    - users.csv: 用户基础信息
    - items.csv: 商品实体
    - pois.csv: POI实体
    - apps.csv: APP实体
    - events.csv: 事件数据（替代原来的relationships.csv）
    """
    try:
        data_dir = Path("d:/workplace/adsagent/backend/data")

        # 1. 读取用户数据
        app_logger.info("读取用户数据...")
        users_df = pd.read_csv(data_dir / "users.csv")
        users = users_df.to_dict(orient='records')
        app_logger.info(f"✓ 用户数据: {len(users)} 条")

        # 2. 读取商品实体
        app_logger.info("读取商品实体...")
        items_df = pd.read_csv(data_dir / "items.csv")
        items = items_df.to_dict(orient='records')
        app_logger.info(f"✓ 商品实体: {len(items)} 条")

        # 3. 读取POI实体
        app_logger.info("读取POI实体...")
        pois_df = pd.read_csv(data_dir / "pois.csv")
        pois = pois_df.to_dict(orient='records')
        app_logger.info(f"✓ POI实体: {len(pois)} 条")

        # 4. 读取APP实体
        app_logger.info("读取APP实体...")
        apps_df = pd.read_csv(data_dir / "apps.csv")
        apps = apps_df.to_dict(orient='records')
        app_logger.info(f"✓ APP实体: {len(apps)} 条")

        # 5. 读取事件数据
        app_logger.info("读取事件数据...")
        events_df = pd.read_csv(data_dir / "events.csv")
        # 填充空值为空字符串
        events_df = events_df.fillna("")
        events = events_df.to_dict(orient='records')
        app_logger.info(f"✓ 事件数据: {len(events)} 条")

        # 6. 清空旧数据
        app_logger.info("清空旧数据...")
        graph_db.clear_knowledge_graph()

        # 7. 创建用户实体
        app_logger.info("创建用户实体...")
        user_entities = []
        for user in users:
            user_id = user.pop('user_id')
            user_entities.append({
                "id": user_id,
                "type": "User",
                "properties": user
            })
        user_count = graph_db.batch_create_entities(user_entities)
        app_logger.info(f"✓ 用户实体创建完成: {user_count} 个")

        # 8. 创建商品实体
        app_logger.info("创建商品实体...")
        item_entities = []
        for item in items:
            item_id = item.pop('item_id')
            item_entities.append({
                "id": item_id,
                "type": "Item",
                "properties": item
            })
        item_count = graph_db.batch_create_entities(item_entities)
        app_logger.info(f"✓ 商品实体创建完成: {item_count} 个")

        # 9. 创建POI实体
        app_logger.info("创建POI实体...")
        poi_entities = []
        for poi in pois:
            poi_id = poi.pop('poi_id')
            poi_entities.append({
                "id": poi_id,
                "type": "POI",
                "properties": poi
            })
        poi_count = graph_db.batch_create_entities(poi_entities)
        app_logger.info(f"✓ POI实体创建完成: {poi_count} 个")

        # 10. 创建APP实体
        app_logger.info("创建APP实体...")
        app_entities = []
        for app in apps:
            app_id = app.pop('app_id')
            app_entities.append({
                "id": app_id,
                "type": "APP",
                "properties": app
            })
        app_count = graph_db.batch_create_entities(app_entities)
        app_logger.info(f"✓ APP实体创建完成: {app_count} 个")

        # 11. 创建事件实体和关系（事件中心模型）
        app_logger.info("创建事件实体和关系...")
        event_entities = []
        relation_list = []
        action_stats = {}

        for event in events:
            event_id = event['event_id']
            user_id = event['user_id']
            action = event['action']
            timestamp = event['timestamp']
            session_id = event.get('session_id', '')
            duration = event.get('duration', 0)
            item_id = event.get('item_id', '')
            app_id = event.get('app_id', '')
            poi_id = event.get('poi_id', '')

            # 统计事件类型
            action_stats[action] = action_stats.get(action, 0) + 1

            # 创建Event实体
            event_properties = {
                "action": action,
                "timestamp": timestamp,
                "session_id": session_id,
                "duration": duration
            }

            # 添加事件特定属性
            if 'purchase_amount' in event and event['purchase_amount']:
                event_properties['purchase_amount'] = event['purchase_amount']
            if 'search_keyword' in event and event['search_keyword']:
                event_properties['search_keyword'] = event['search_keyword']
            if 'compared_items' in event and event['compared_items']:
                event_properties['compared_items'] = event['compared_items']

            event_entities.append({
                "id": event_id,
                "type": "Event",
                "properties": event_properties
            })

            # 创建 User → Event 关系（INITIATED）
            relation_list.append({
                "from": user_id,
                "to": event_id,
                "type": "INITIATED",
                "properties": {"timestamp": timestamp}
            })

            # 创建 Event → Item 关系（INVOLVES）
            if item_id:
                relation_list.append({
                    "from": event_id,
                    "to": item_id,
                    "type": "INVOLVES",
                    "properties": {}
                })

            # 创建 Event → APP 关系（VIA）
            if app_id:
                relation_list.append({
                    "from": event_id,
                    "to": app_id,
                    "type": "VIA",
                    "properties": {}
                })

            # 创建 Event → POI 关系（AT）
            if poi_id:
                relation_list.append({
                    "from": event_id,
                    "to": poi_id,
                    "type": "AT",
                    "properties": {}
                })

        event_count = graph_db.batch_create_entities(event_entities)
        app_logger.info(f"✓ 事件实体创建完成: {event_count} 个")

        relation_count = graph_db.batch_create_relations(relation_list)
        app_logger.info(f"✓ 关系创建完成: {relation_count} 条")

        # 12. 统计信息
        stats = {
            "total_entities": user_count + item_count + poi_count + app_count + event_count,
            "total_relations": relation_count,
            "entity_breakdown": {
                "User": user_count,
                "Item": item_count,
                "POI": poi_count,
                "APP": app_count,
                "Event": event_count
            },
            "event_action_types": action_stats,
            "relation_types": {
                "INITIATED": event_count,  # 每个事件都有一个INITIATED关系
                "INVOLVES": sum(1 for e in events if e.get('item_id')),
                "VIA": sum(1 for e in events if e.get('app_id')),
                "AT": sum(1 for e in events if e.get('poi_id'))
            }
        }

        app_logger.info(f"事件中心知识图谱构建完成: {stats}")

        return {
            "code": 0,
            "data": {
                "stats": stats,
                "message": f"成功导入 {len(users)} 个用户, {len(items)} 个商品, {len(pois)} 个POI, {len(apps)} 个APP, {len(events)} 个事件, {relation_count} 条关系"
            }
        }

    except FileNotFoundError as e:
        app_logger.error(f"CSV文件未找到: {e}", exc_info=True)
        raise HTTPException(status_code=404, detail=f"CSV文件未找到: {str(e)}")
    except Exception as e:
        app_logger.error(f"导入CSV数据失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"导入失败: {str(e)}")
