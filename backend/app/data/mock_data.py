"""
汽车行业Mock数据 - 模拟5亿用户中的样本数据
"""
import random
from typing import List, Dict

random.seed(42)

TOTAL_USERS = 100000
INDUSTRY = "汽车"

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

_age_buckets = ["25-30", "30-40", "40-50", "50+"]

def generate_user(user_id: str) -> Dict:
    income = random.choices(
        list(INCOME_DISTRIBUTION.keys()),
        weights=list(INCOME_DISTRIBUTION.values())
    )[0]
    
    age = random.randint(25, 55)
    age_bucket = _age_buckets[0] if age < 30 else _age_buckets[1] if age < 40 else _age_buckets[2] if age < 50 else _age_buckets[3]
    
    num_interests = random.randint(2, 5)
    selected_interests = []
    for _ in range(num_interests):
        category = random.choice(list(INTEREST_CATEGORIES.keys()))
        interest = random.choice(INTEREST_CATEGORIES[category])
        if interest not in selected_interests:
            selected_interests.append(interest)
    
    brand = random.choice(list(BRAND_PREFERENCES.keys()))
    model = random.choice(list(BRAND_PREFERENCES[brand].keys()))
    
    behaviors = generate_behaviors(brand, model, selected_interests)
    intent_level = calculate_intent(behaviors)
    
    return {
        "user_id": user_id,
        "demographics": {
            "age": age,
            "age_bucket": age_bucket,
            "gender": random.choice(["男", "女"]),
            "income_level": income,
            "city_tier": random.choice(["一线", "新一线", "二线", "三线"]),
            "occupation": random.choice(["企业高管", "中层管理", "技术专家", "自由职业", "公务员"])
        },
        "interests": selected_interests,
        "behaviors": behaviors,
        "brand_affinity": {
            "primary_brand": brand,
            "primary_model": model,
            "brand_score": BRAND_PREFERENCES[brand][model]
        },
        "purchase_intent": intent_level["level"],
        "intent_score": intent_level["score"],
        "lifecycle_stage": intent_level["stage"],
        "industry": INDUSTRY
    }

def generate_behaviors(brand: str, model: str, interests: List[str]) -> List[Dict]:
    behaviors = []
    num_brand_actions = random.randint(1, 10)
    for i in range(num_brand_actions):
        action = random.choice(["浏览", "搜索", "询价", "收藏", "分享"])
        behaviors.append({
            "action": action,
            "brand": brand,
            "model": model,
            "context": random.choice(["APP", "官网", "经销商", "朋友圈广告"])
        })
    
    for interest in interests[:2]:
        num_interest_actions = random.randint(1, 5)
        for _ in range(num_interest_actions):
            behaviors.append({
                "action": "浏览资讯",
                "topic": interest,
                "app_category": random.choice(["资讯", "社交", "短视频"])
            })
    
    random.shuffle(behaviors)
    return behaviors

def calculate_intent(behaviors: List[Dict]) -> Dict:
    brand_actions = [b for b in behaviors if "brand" in b]
    
    if len(brand_actions) >= 8:
        has_inquiry = any(b["action"] == "询价" for b in brand_actions)
        if has_inquiry:
            return {"level": "高", "score": 0.9, "stage": "转化"}
        return {"level": "高", "score": 0.75, "stage": "意向"}
    elif len(brand_actions) >= 4:
        return {"level": "中", "score": 0.5, "stage": "考虑"}
    elif len(brand_actions) >= 1:
        return {"level": "低", "score": 0.25, "stage": "认知"}
    else:
        return {"level": "无", "score": 0.05, "stage": "空白"}

_mock_users_cache = {}

def get_mock_users(count: int = 1000) -> List[Dict]:
    global _mock_users_cache
    if len(_mock_users_cache) < count:
        for i in range(len(_mock_users_cache), count):
            _mock_users_cache[f"U{i:06d}"] = generate_user(f"U{i:06d}")
    return list(_mock_users_cache.values())[:count]

KNOWLEDGE_GRAPH_ENTITIES = [
    {"id": "brand_宝马", "type": "品牌", "name": "宝马", "tier": "豪华"},
    {"id": "brand_奔驰", "type": "品牌", "name": "奔驰", "tier": "豪华"},
    {"id": "brand_奥迪", "type": "品牌", "name": "奥迪", "tier": "豪华"},
    {"id": "model_宝马7系", "type": "车型", "name": "宝马7系", "price": "80-150万", "target": "商务人士"},
    {"id": "model_奔驰S级", "type": "车型", "name": "奔驰S级", "price": "80-180万", "target": "企业高管"},
    {"id": "interest_高尔夫", "type": "兴趣", "name": "高尔夫", "category": "体育"},
    {"id": "scene_商务出行", "type": "场景", "name": "商务出行"},
    {"id": "audience_企业高管", "type": "人群", "name": "企业高管", "features": "高收入、高频商务出行"},
]

KNOWLEDGE_GRAPH_RELATIONS = [
    {"from": "interest_高尔夫", "to": "model_宝马7系", "weight": 0.85},
    {"from": "interest_高尔夫", "to": "model_奔驰S级", "weight": 0.80},
    {"from": "scene_商务出行", "to": "model_奔驰S级", "weight": 0.90},
    {"from": "scene_商务出行", "to": "model_宝马7系", "weight": 0.85},
    {"from": "audience_企业高管", "to": "model_奔驰S级", "weight": 0.95},
    {"from": "audience_企业高管", "to": "model_宝马7系", "weight": 0.88},
]

SAMPLE_CONFIG = {
    "industry": "汽车",
    "category": "豪华轿车",
    "ratios": {"positive": 1, "churn": 10, "weak": 5, "control": 5}
}
