"""
数据导出脚本 - 生成所有数据的JSON文件
"""
import json
import random
from datetime import datetime

# 设置随机种子确保可复现
random.seed(42)

# ==================== 常量定义 ====================
INCOME_DISTRIBUTION = {
    "低收入": 0.25,
    "中等收入": 0.35,
    "高收入": 0.30,
    "超高收入": 0.10
}

BRAND_PREFERENCES = {
    "宝马": {"7系": 0.50, "5系": 0.35, "3系": 0.15},
    "奔驰": {"S级": 0.45, "E级": 0.40, "C级": 0.15},
    "奥迪": {"A8": 0.40, "A6": 0.45, "A4": 0.15},
    "特斯拉": {"Model S": 0.50, "Model 3": 0.50}
}

INTEREST_CATEGORIES = {
    "体育运动": ["高尔夫", "网球", "游泳", "跑步", "滑雪"],
    "商务": ["财经", "商业", "投资", "房产"],
    "生活": ["旅游", "美食", "时尚", "汽车", "科技"]
}

AGE_BUCKETS = ["25-30", "30-40", "40-50", "50+"]
CITY_TIERS = ["一线", "新一线", "二线", "三线"]
OCCUPATIONS = ["企业高管", "中层管理", "技术专家", "自由职业", "公务员"]

INTENT_LEVELS = ["无", "低", "中", "高"]
LIFECYCLE_STAGES = ["空白", "认知", "意向", "转化", "流失"]

# ==================== Mock数据生成 ====================
def generate_mock_users(count=100):
    """生成Mock用户数据"""
    users = []
    for i in range(count):
        user_id = f"U{str(i+1).zfill(6)}"
        
        # 人口统计
        income = random.choices(list(INCOME_DISTRIBUTION.keys()), weights=list(INCOME_DISTRIBUTION.values()))[0]
        age = random.randint(25, 55)
        age_bucket = AGE_BUCKETS[0] if age < 30 else AGE_BUCKETS[1] if age < 40 else AGE_BUCKETS[2] if age < 50 else AGE_BUCKETS[3]
        
        # 兴趣
        num_interests = random.randint(2, 5)
        selected_interests = []
        for _ in range(num_interests):
            category = random.choice(list(INTEREST_CATEGORIES.keys()))
            interest = random.choice(INTEREST_CATEGORIES[category])
            if interest not in selected_interests:
                selected_interests.append(interest)
        
        # 品牌偏好
        brand = random.choice(list(BRAND_PREFERENCES.keys()))
        model = random.choice(list(BRAND_PREFERENCES[brand].keys()))
        
        # 行为
        behaviors = []
        num_brand_actions = random.randint(1, 10)
        for j in range(num_brand_actions):
            action = random.choice(["浏览", "搜索", "询价", "收藏", "分享"])
            behaviors.append({
                "action": action,
                "brand": brand,
                "model": model,
                "context": random.choice(["APP", "官网", "经销商", "朋友圈广告"])
            })
        
        for interest in selected_interests[:2]:
            num_interest_actions = random.randint(1, 5)
            for _ in range(num_interest_actions):
                behaviors.append({
                    "action": "浏览资讯",
                    "topic": interest,
                    "app_category": random.choice(["资讯", "社交", "短视频"])
                })
        
        # 意向
        num_high_value_actions = sum(1 for b in behaviors if b.get("action") in ["询价", "收藏", "分享"])
        if num_high_value_actions >= 5:
            intent_level = "高"
            intent_score = random.uniform(0.8, 1.0)
            stage = random.choice(["意向", "转化"])
        elif num_high_value_actions >= 2:
            intent_level = "中"
            intent_score = random.uniform(0.5, 0.8)
            stage = random.choice(["意向", "认知"])
        elif num_high_value_actions >= 1:
            intent_level = "低"
            intent_score = random.uniform(0.2, 0.5)
            stage = "认知"
        else:
            intent_level = "无"
            intent_score = random.uniform(0.0, 0.2)
            stage = "空白"
        
        # 流失概率（根据行为判断）- 提高流失率以满足1:10:5:5比例
        churn_prob = random.uniform(0.0, 0.6)
        if churn_prob > 0.35:
            stage = "流失"
        
        user = {
            "user_id": user_id,
            "demographics": {
                "age": age,
                "age_bucket": age_bucket,
                "gender": random.choice(["男", "女"]),
                "income_level": income,
                "city_tier": random.choice(CITY_TIERS),
                "occupation": random.choice(OCCUPATIONS)
            },
            "interests": selected_interests,
            "behaviors": behaviors,
            "brand_affinity": {
                "primary_brand": brand,
                "primary_model": model,
                "brand_score": BRAND_PREFERENCES[brand][model]
            },
            "purchase_intent": intent_level,
            "intent_score": intent_score,
            "lifecycle_stage": stage,
            "churn_probability": churn_prob,
            "industry": "汽车"
        }
        users.append(user)
    
    return users

# ==================== 样本数据生成 ====================
def generate_sample_data(users):
    """生成1:10:5:5比例的样本数据"""
    ratios = {"positive": 1, "churn": 10, "weak": 5, "control": 5}
    total_ratio = sum(ratios.values())
    
    # 简化用户数据
    def compress_user(user):
        return {
            "user_id": user["user_id"],
            "profile": {
                "age_bucket": user["demographics"]["age_bucket"],
                "income": user["demographics"]["income_level"],
                "city": user["demographics"]["city_tier"],
                "occupation": user["demographics"]["occupation"]
            },
            "interests": user["interests"][:5],
            "brand": user["brand_affinity"],
            "intent": user["purchase_intent"],
            "stage": user["lifecycle_stage"]
        }
    
    # 分类用户
    positive = []
    churn = []
    weak = []
    control = []
    
    positive_limit = len(users) * ratios["positive"] // total_ratio
    churn_limit = len(users) * ratios["churn"] // total_ratio
    weak_limit = len(users) * ratios["weak"] // total_ratio
    control_limit = len(users) * ratios["control"] // total_ratio
    
    for user in users:
        intent = user.get("purchase_intent", "无")
        stage = user.get("lifecycle_stage", "空白")
        
        if intent == "高" and stage in ["意向", "转化"]:
            if len(positive) < positive_limit:
                positive.append(compress_user(user))
        elif stage == "流失":
            if len(churn) < churn_limit:
                churn.append(compress_user(user))
        elif intent == "中":
            if len(weak) < weak_limit:
                weak.append(compress_user(user))
        else:
            if len(control) < control_limit:
                control.append(compress_user(user))
    
    return {
        "positive": positive,
        "churn": churn,
        "weak": weak,
        "control": control
    }

# ==================== 知识图谱数据生成 ====================
def generate_knowledge_graph(users):
    """生成知识图谱数据"""
    entities = []
    relations = []
    entity_ids = set()
    
    # 添加用户实体
    for user in users[:100]:  # 限制数量
        uid = f"user:{user['user_id']}"
        entities.append({
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
        entity_ids.add(uid)
    
    # 添加品牌实体
    for brand in BRAND_PREFERENCES.keys():
        brand_id = f"brand:{brand}"
        if brand_id not in entity_ids:
            entities.append({
                "id": brand_id,
                "type": "Brand",
                "properties": {"name": brand}
            })
            entity_ids.add(brand_id)
    
    # 添加车型实体
    for brand, models in BRAND_PREFERENCES.items():
        for model in models.keys():
            model_id = f"model:{model}"
            if model_id not in entity_ids:
                entities.append({
                    "id": model_id,
                    "type": "Model",
                    "properties": {"name": model, "brand": brand}
                })
                entity_ids.add(model_id)
    
    # 添加兴趣实体
    interest_category_map = {}
    for category, interests in INTEREST_CATEGORIES.items():
        for interest in interests:
            interest_category_map[interest] = category
    for interest, cat in interest_category_map.items():
        interest_id = f"interest:{interest}"
        if interest_id not in entity_ids:
            entities.append({
                "id": interest_id,
                "type": "Interest",
                "properties": {"name": interest, "category": cat}
            })
            entity_ids.add(interest_id)
    
    # 添加关系
    for user in users[:100]:
        uid = f"user:{user['user_id']}"
        
        # 用户-兴趣关系
        for interest in user["interests"][:5]:
            interest_id = f"interest:{interest}"
            relations.append({
                "from": uid,
                "to": interest_id,
                "type": "HAS_INTEREST",
                "weight": round(random.uniform(0.6, 0.9), 2)
            })
        
        # 用户-品牌关系
        brand = user["brand_affinity"]["primary_brand"]
        brand_id = f"brand:{brand}"
        score = user["brand_affinity"]["brand_score"]
        relations.append({
            "from": uid,
            "to": brand_id,
            "type": "PREFERS",
            "weight": round(score, 2)
        })
        
        # 用户-车型关系
        model = user["brand_affinity"]["primary_model"]
        model_id = f"model:{model}"
        relations.append({
            "from": uid,
            "to": model_id,
            "type": "INTERESTED_IN",
            "weight": round(score * 0.9, 2)
        })
    
    # 品牌-兴趣关联（领域知识）- 只使用INTEREST_CATEGORIES中定义的有效兴趣
    brand_interest_correlations = {
        "宝马": {"高尔夫": 0.75, "网球": 0.65, "滑雪": 0.70, "科技": 0.60},
        "奔驰": {"财经": 0.80, "投资": 0.75, "商业": 0.70, "房产": 0.65},
        "奥迪": {"商务": 0.70, "财经": 0.65, "旅游": 0.60, "美食": 0.55},
        "特斯拉": {"科技": 0.90}  # 只使用有效兴趣
    }
    
    for brand, correlations in brand_interest_correlations.items():
        brand_id = f"brand:{brand}"
        for interest, weight in correlations.items():
            interest_id = f"interest:{interest}"
            # 确保兴趣实体存在
            if interest_id not in entity_ids:
                entities.append({
                    "id": interest_id,
                    "type": "Interest",
                    "properties": {"name": interest, "category": "生活"}
                })
                entity_ids.add(interest_id)
            # 添加关系
            if not any(r["from"] == brand_id and r["to"] == interest_id for r in relations):
                relations.append({
                    "from": brand_id,
                    "to": interest_id,
                    "type": "CORRELATES_WITH",
                    "weight": weight
                })
    
    return {
        "entities": entities,
        "relations": relations,
        "stats": {
            "total_entities": len(entities),
            "total_relations": len(relations),
            "entity_types": list(set(e["type"] for e in entities)),
            "relation_types": list(set(r["type"] for r in relations))
        }
    }

# ==================== 事理图谱数据生成 ====================
def generate_event_graph(users):
    """生行事理图谱数据（因果链和事件）"""
    
    # 核心事件定义
    events = [
        {
            "id": "event:high_income_golf",
            "name": "高收入用户关注高尔夫",
            "type": "用户兴趣",
            "description": "年收入50万以上用户对高尔夫运动表现出明显兴趣"
        },
        {
            "id": "event:luxury_car_research",
            "name": "豪华车型深度调研",
            "type": "购车行为",
            "description": "用户浏览多款豪华车型并进行参数对比"
        },
        {
            "id": "event:brand_comparison",
            "name": "品牌对比行为",
            "类型": "购车决策",
            "description": "用户在宝马、奔驰、奥迪之间反复比较"
        },
        {
            "id": "event:price_inquiry",
            "name": "价格咨询行为",
            "type": "购车意向",
            "description": "用户主动询问车型价格和优惠政策"
        },
        {
            "id": "event:test_drive",
            "name": "预约试驾",
            "type": "转化行为",
            "description": "用户预约线下门店试驾体验"
        },
        {
            "id": "event:financing_inquiry",
            "name": "金融方案咨询",
            "type": "转化行为",
            "description": "用户关注贷款方案和月供信息"
        },
        {
            "id": "event:churn_risk",
            "name": "流失风险信号",
            "type": "风险预警",
            "description": "用户浏览频率下降或取消关注"
        },
        {
            "id": "event:purchase_complete",
            "name": "完成购车",
            "type": "转化完成",
            "description": "用户最终完成购车决策"
        }
    ]
    
    # 因果关系定义（事件链）
    causal_chains = [
        {
            "id": "chain:high_income_purchase_luxury",
            "name": "高收入用户购买豪华车因果链",
            "events": ["event:high_income_golf", "event:luxury_car_research", "event:brand_comparison", "event:purchase_complete"],
            "probability": 0.35,
            "confidence": 0.85,
            "description": "高收入高尔夫用户有35%概率最终购买豪华车型"
        },
        {
            "id": "chain:test_drive_conversion",
            "name": "试驾到成交转化链",
            "events": ["event:price_inquiry", "event:test_drive", "event:financing_inquiry", "event:purchase_complete"],
            "probability": 0.65,
            "confidence": 0.92,
            "description": "预约试驾的用户有65%概率最终成交"
        },
        {
            "id": "chain:churn_early_warning",
            "name": "流失预警因果链",
            "events": ["event:luxury_car_research", "event:brand_comparison", "event:churn_risk"],
            "probability": 0.25,
            "confidence": 0.78,
            "description": "深度调研后未采取下一步行动的用户有25%流失风险"
        }
    ]
    
    # 规则定义
    rules = [
        {
            "id": "rule:golf_bmw_correlation",
            "condition": "用户兴趣包含高尔夫 AND 年收入>=50万",
            "action": "推荐宝马7系/奔驰S级",
            "weight": 0.85,
            "description": "高尔夫用户对豪华轿车有强偏好"
        },
        {
            "id": "rule:business_user_preference",
            "condition": "职业=企业高管 AND 城市=一线",
            "action": "推荐奔驰S级/奥迪A8",
            "weight": 0.80,
            "description": "商务人士偏好德系豪华品牌"
        },
        {
            "id": "rule:tech_enthusiast_tesla",
            "condition": "兴趣=科技 AND 年龄<35",
            "action": "推荐特斯拉Model S",
            "weight": 0.75,
            "description": "年轻科技爱好者倾向选择特斯拉"
        },
        {
            "id": "rule:churn_warning",
            "condition": "30天内无品牌互动 AND 未完成试驾",
            "action": "触发流失预警",
            "weight": 0.70,
            "description": "长时间无互动的用户需要主动触达"
        }
    ]
    
    # 关键发现
    insights = [
        {
            "id": "insight:golf_bmw_7",
            "title": "高尔夫用户偏好宝马7系",
            "description": "在高尔夫爱好者中，42%最终购买宝马7系",
            "supporting_data": {
                "sample_size": 1250,
                "conversion_rate": 0.42,
                "avg_time_to_purchase": "45天"
            },
            "recommendation": "针对高尔夫App用户投放宝马7系广告"
        },
        {
            "id": "insight:business_elite_mercedes",
            "title": "商务精英首选奔驰S级",
            "description": "企业高管群体中，55%选择奔驰S级作为座驾",
            "supporting_data": {
                "sample_size": 890,
                "conversion_rate": 0.55,
                "avg_time_to_purchase": "60天"
            },
            "recommendation": "在财经/商业媒体投放奔驰S级广告"
        },
        {
            "id": "insight:young_professionals_tesla",
            "title": "年轻专业人士青睐特斯拉",
            "description": "35岁以下科技兴趣用户，60%选择特斯拉",
            "supporting_data": {
                "sample_size": 2100,
                "conversion_rate": 0.60,
                "avg_time_to_purchase": "30天"
            },
            "recommendation": "在科技类媒体投放特斯拉广告"
        }
    ]
    
    return {
        "events": events,
        "causal_chains": causal_chains,
        "rules": rules,
        "insights": insights,
        "stats": {
            "total_events": len(events),
            "total_chains": len(causal_chains),
            "total_rules": len(rules),
            "total_insights": len(insights)
        }
    }

# ==================== 主程序 ====================
def main():
    print("正在生成数据...")
    
    # 1. 生成Mock用户数据
    print("1/4 生成Mock用户数据...")
    users = generate_mock_users(1000)  # 生成1000个用户
    with open("data/mock_users.json", "w", encoding="utf-8") as f:
        json.dump({
            "metadata": {
                "count": len(users),
                "generated_at": datetime.now().isoformat(),
                "industry": "汽车"
            },
            "users": users
        }, f, ensure_ascii=False, indent=2)
    print(f"   已保存 mock_users.json ({len(users)} 用户)")
    
    # 2. 生成样本数据
    print("2/4 生成样本数据...")
    samples = generate_sample_data(users)
    sample_counts = {k: len(v) for k, v in samples.items()}
    with open("data/samples.json", "w", encoding="utf-8") as f:
        json.dump({
            "metadata": {
                "ratios": {"positive": 1, "churn": 10, "weak": 5, "control": 5},
                "generated_at": datetime.now().isoformat(),
                "sample_counts": sample_counts
            },
            "samples": samples
        }, f, ensure_ascii=False, indent=2)
    print(f"   已保存 samples.json {sample_counts}")
    
    # 3. 生成知识图谱数据
    print("3/4 生成知识图谱数据...")
    kg = generate_knowledge_graph(users)
    with open("data/knowledge_graph.json", "w", encoding="utf-8") as f:
        json.dump({
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "stats": kg["stats"]
            },
            "knowledge_graph": kg
        }, f, ensure_ascii=False, indent=2)
    print(f"   已保存 knowledge_graph.json (实体: {kg['stats']['total_entities']}, 关系: {kg['stats']['total_relations']})")
    
    # 4. 生成事理图谱数据
    print("4/4 行事理图谱数据...")
    eg = generate_event_graph(users)
    with open("data/event_graph.json", "w", encoding="utf-8") as f:
        json.dump({
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "stats": eg["stats"]
            },
            "event_graph": eg
        }, f, ensure_ascii=False, indent=2)
    print(f"   已保存 event_graph.json (事件: {eg['stats']['total_events']}, 因果链: {eg['stats']['total_chains']})")
    
    print("\n数据生成完成！所有文件保存在 data/ 目录下：")
    print("  - mock_users.json: Mock用户数据")
    print("  - samples.json: 样本数据（1:10:5:5比例）")
    print("  - knowledge_graph.json: 知识图谱数据")
    print("  - event_graph.json: 事理图谱数据")

if __name__ == "__main__":
    main()
