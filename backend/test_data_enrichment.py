"""
测试数据丰富化方案
演示如何在事件抽取时关联实体属性
"""
import sqlite3
import json
from pathlib import Path


def enrich_behavior_with_entities(behaviors, db_path="data/graph.db"):
    """
    为行为数据关联实体属性

    Args:
        behaviors: 原始行为数据列表

    Returns:
        丰富后的行为数据,包含实体的详细信息
    """
    enriched_behaviors = []

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()

        for behavior in behaviors:
            enriched = behavior.copy()

            # 1. 关联 APP 信息
            if behavior.get("app_id"):
                cursor.execute("""
                    SELECT app_name, category, tags
                    FROM app_tags
                    WHERE app_id = ?
                """, (behavior["app_id"],))
                app_row = cursor.fetchone()
                if app_row:
                    enriched["app_info"] = {
                        "app_id": behavior["app_id"],
                        "app_name": app_row[0],
                        "category": app_row[1],
                        "tags": json.loads(app_row[2]) if app_row[2] else []
                    }

            # 2. 关联媒体信息
            if behavior.get("media_id"):
                cursor.execute("""
                    SELECT media_name, media_type, tags
                    FROM media_tags
                    WHERE media_id = ?
                """, (behavior["media_id"],))
                media_row = cursor.fetchone()
                if media_row:
                    enriched["media_info"] = {
                        "media_id": behavior["media_id"],
                        "media_name": media_row[0],
                        "media_type": media_row[1],
                        "tags": json.loads(media_row[2]) if media_row[2] else []
                    }

            # 3. 关联 POI 信息(从知识图谱实体表)
            if behavior.get("poi_id"):
                cursor.execute("""
                    SELECT properties
                    FROM entities
                    WHERE id = ? AND type = 'POI'
                """, (behavior["poi_id"],))
                poi_row = cursor.fetchone()
                if poi_row:
                    poi_props = json.loads(poi_row[0])
                    enriched["poi_info"] = {
                        "poi_id": behavior["poi_id"],
                        "poi_name": poi_props.get("name", ""),
                        "poi_type": poi_props.get("type", ""),
                        "address": poi_props.get("address", "")
                    }

            # 4. 关联 Item 信息(从知识图谱实体表)
            if behavior.get("item_id"):
                cursor.execute("""
                    SELECT type, properties
                    FROM entities
                    WHERE id = ?
                """, (behavior["item_id"],))
                item_row = cursor.fetchone()
                if item_row:
                    item_props = json.loads(item_row[1])
                    enriched["item_info"] = {
                        "item_id": behavior["item_id"],
                        "item_type": item_row[0],
                        "item_name": item_props.get("name", ""),
                        "properties": item_props
                    }

            enriched_behaviors.append(enriched)

    return enriched_behaviors


def format_behavior_for_llm(enriched_behavior):
    """
    将丰富后的行为数据格式化为适合 LLM 理解的文本

    Args:
        enriched_behavior: 丰富后的行为数据

    Returns:
        格式化的文本描述
    """
    action = enriched_behavior.get("action", "")
    timestamp = enriched_behavior.get("timestamp", "")
    duration = enriched_behavior.get("duration", 0)

    # 构建行为描述
    parts = [f"{timestamp}"]

    if action == "visit_poi" and "poi_info" in enriched_behavior:
        poi = enriched_behavior["poi_info"]
        duration_hours = duration // 3600 if duration else 0
        parts.append(f"在{poi['poi_name']}({poi['poi_type']})停留{duration_hours}小时")

    elif action == "use_app" and "app_info" in enriched_behavior:
        app = enriched_behavior["app_info"]
        duration_min = duration // 60 if duration else 0
        tags_str = ",".join(app["tags"][:3]) if app["tags"] else ""
        parts.append(f"使用{app['app_name']}({tags_str})应用{duration_min}分钟")

    elif action == "browse" and "media_info" in enriched_behavior:
        media = enriched_behavior["media_info"]
        item = enriched_behavior.get("item_info", {})
        item_name = item.get("item_name", enriched_behavior.get("item_id", ""))
        parts.append(f"在{media['media_name']}浏览{item_name}")

    elif action == "search":
        query = enriched_behavior.get("item_id", "")
        app = enriched_behavior.get("app_info", {})
        app_name = app.get("app_name", "")
        parts.append(f"在{app_name}搜索:{query}")

    elif action == "purchase" and "item_info" in enriched_behavior:
        item = enriched_behavior["item_info"]
        parts.append(f"购买{item['item_name']}")

    else:
        parts.append(f"{action}")
        if "item_info" in enriched_behavior:
            parts.append(enriched_behavior["item_info"]["item_name"])

    return " ".join(parts)


def demo_enrichment():
    """演示数据丰富化效果"""

    # 模拟原始行为数据(只有ID)
    raw_behaviors = [
        {
            "id": 1,
            "action": "visit_poi",
            "timestamp": "2026-02-13 10:00:00",
            "poi_id": "poi_bmw_4s_001",
            "duration": 7200
        },
        {
            "id": 2,
            "action": "use_app",
            "timestamp": "2026-02-13 14:30:00",
            "app_id": "app_002",
            "duration": 1800
        },
        {
            "id": 3,
            "action": "search",
            "timestamp": "2026-02-13 15:00:00",
            "app_id": "app_007",
            "item_id": "宝马7系价格"
        },
        {
            "id": 4,
            "action": "browse",
            "timestamp": "2026-02-13 16:00:00",
            "media_id": "media_001",
            "item_id": "item_005",
            "duration": 300
        }
    ]

    print("=" * 80)
    print("原始行为数据(只有ID)")
    print("=" * 80)
    for b in raw_behaviors:
        print(json.dumps(b, ensure_ascii=False, indent=2))

    print("\n" + "=" * 80)
    print("丰富后的行为数据(包含实体详细信息)")
    print("=" * 80)

    # 注意: 这里需要数据库中有对应的数据才能演示
    # enriched = enrich_behavior_with_entities(raw_behaviors)
    # for b in enriched:
    #     print(json.dumps(b, ensure_ascii=False, indent=2))

    # 模拟丰富后的数据
    enriched_demo = [
        {
            "id": 1,
            "action": "visit_poi",
            "timestamp": "2026-02-13 10:00:00",
            "poi_id": "poi_bmw_4s_001",
            "duration": 7200,
            "poi_info": {
                "poi_id": "poi_bmw_4s_001",
                "poi_name": "宝马4S店(朝阳店)",
                "poi_type": "汽车4S店",
                "address": "北京市朝阳区"
            }
        },
        {
            "id": 2,
            "action": "use_app",
            "timestamp": "2026-02-13 14:30:00",
            "app_id": "app_002",
            "duration": 1800,
            "app_info": {
                "app_id": "app_002",
                "app_name": "高尔夫助手",
                "category": "运动",
                "tags": ["高尔夫", "运动", "社交"]
            }
        },
        {
            "id": 3,
            "action": "search",
            "timestamp": "2026-02-13 15:00:00",
            "app_id": "app_007",
            "item_id": "宝马7系价格",
            "app_info": {
                "app_id": "app_007",
                "app_name": "汽车之家",
                "category": "汽车",
                "tags": ["汽车资讯", "购车", "评测"]
            }
        },
        {
            "id": 4,
            "action": "browse",
            "timestamp": "2026-02-13 16:00:00",
            "media_id": "media_001",
            "item_id": "item_005",
            "duration": 300,
            "media_info": {
                "media_id": "media_001",
                "media_name": "爱奇艺",
                "media_type": "视频平台",
                "tags": ["视频", "影视", "综艺"]
            },
            "item_info": {
                "item_id": "item_005",
                "item_type": "Video",
                "item_name": "豪华轿车评测:宝马7系vs奔驰S级",
                "properties": {"category": "汽车评测", "duration": 1200}
            }
        }
    ]

    for b in enriched_demo:
        print(json.dumps(b, ensure_ascii=False, indent=2))
        print()

    print("\n" + "=" * 80)
    print("格式化为 LLM 可理解的文本")
    print("=" * 80)
    for b in enriched_demo:
        formatted = format_behavior_for_llm(b)
        print(f"  - {formatted}")

    print("\n" + "=" * 80)
    print("传给 LLM 的完整 Prompt 示例")
    print("=" * 80)

    user_profile = {
        "user_id": "user_001",
        "age": 35,
        "gender": "男",
        "income_level": "高",
        "interests": ["高尔夫", "豪华轿车", "商务旅行"]
    }

    prompt = f"""你是一个用户行为分析专家。请将以下用户的原始行为数据抽象为高层次的事件。

用户画像:
- 年龄: {user_profile['age']}岁
- 性别: {user_profile['gender']}
- 收入水平: {user_profile['income_level']}
- 兴趣标签: {', '.join(user_profile['interests'])}

用户行为数据:
"""

    for b in enriched_demo:
        formatted = format_behavior_for_llm(b)
        prompt += f"  - {formatted}\n"

    prompt += """
要求:
1. 将细粒度的行为抽象为有业务意义的事件
2. 事件类型要简洁(2-6个中文字)
3. 保留时间信息
4. 提取关键上下文信息
5. 必须返回JSON格式

输出格式示例:
{
  "user_001": [
    {
      "event_type": "看车",
      "timestamp": "2026-02-13 10:00:00",
      "context": {"brand": "宝马", "poi_type": "4S店", "duration": "2小时"}
    },
    {
      "event_type": "关注豪华轿车",
      "timestamp": "2026-02-13 16:00:00",
      "context": {"brands": ["宝马", "奔驰"], "model": "7系/S级"}
    }
  ]
}

请严格按照上述JSON格式输出:"""

    print(prompt)


if __name__ == "__main__":
    demo_enrichment()
