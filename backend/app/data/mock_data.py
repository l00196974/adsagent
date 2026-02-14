"""
汽车行业Mock数据 - 模拟真实用户行为数据
包含：通勤距离、婚姻状况、生子信息、APP使用、搜索浏览、比价、付费、广告数据、位置、天气等
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

CITIES = ["北京", "上海", "广州", "深圳", "杭州", "成都", "重庆", "武汉", "西安", "南京"]
EDUCATION_LEVELS = ["高中", "大专", "本科", "硕士", "博士"]
MARITAL_STATUS = ["未婚", "已婚", "订婚", "离异"]
PHONE_PRICES = ["1000-3000", "3000-5000", "5000-8000", "8000+"]
WEATHER_CONDITIONS = ["晴", "多云", "阴", "雨", "雪"]

_age_buckets = ["25-30", "30-40", "40-50", "50+"]

def generate_user(user_id: str) -> Dict:
    """生成包含完整汽车行业行为数据的用户"""
    income = random.choices(
        list(INCOME_DISTRIBUTION.keys()),
        weights=list(INCOME_DISTRIBUTION.values())
    )[0]

    age = random.randint(25, 55)
    age_bucket = _age_buckets[0] if age < 30 else _age_buckets[1] if age < 40 else _age_buckets[2] if age < 50 else _age_buckets[3]
    gender = random.choice(["男", "女"])

    # 基础信息
    city = random.choice(CITIES)
    education = random.choice(EDUCATION_LEVELS)
    marital = random.choice(MARITAL_STATUS)
    has_children = random.choice([True, False]) if marital == "已婚" else False

    # 资产信息
    has_house = random.random() > 0.3  # 70%有房
    has_car = random.random() > 0.4    # 60%有车
    phone_price = random.choice(PHONE_PRICES)

    # 通勤距离（公里）
    commute_distance = round(random.uniform(5, 50), 1) if random.random() > 0.2 else 0

    # 兴趣爱好
    num_interests = random.randint(2, 5)
    selected_interests = []
    for _ in range(num_interests):
        category = random.choice(list(INTEREST_CATEGORIES.keys()))
        interest = random.choice(INTEREST_CATEGORIES[category])
        if interest not in selected_interests:
            selected_interests.append(interest)

    # 品牌和车型
    brand = random.choice(list(BRAND_PREFERENCES.keys()))
    model = random.choice(list(BRAND_PREFERENCES[brand].keys()))
    brand_score = BRAND_PREFERENCES[brand][model] + random.uniform(-0.1, 0.1)
    brand_score = max(0.1, min(1.0, brand_score))

    # APP使用行为
    app_open_count = random.randint(0, 100)
    app_usage_duration = random.randint(0, 3600)  # 秒
    miniprogram_open_count = random.randint(0, 50)

    # 汽车相关行为
    car_search_count = random.randint(0, 30)
    car_browse_count = random.randint(0, 50)
    car_compare_count = random.randint(0, 15)
    car_app_payment = random.random() > 0.9  # 10%付费

    # 广告和消息数据
    push_exposure = random.randint(0, 200)
    push_click = random.randint(0, push_exposure // 10)
    ad_exposure = random.randint(0, 500)
    ad_click = random.randint(0, ad_exposure // 20)

    # 位置数据
    near_4s_store = random.random() > 0.7  # 30%在4S店附近
    weather_info = random.choice(WEATHER_CONDITIONS)

    # 消费频率（每月）
    consumption_frequency = random.randint(0, 20)

    # 生成行为列表
    behaviors = generate_enhanced_behaviors(
        brand, model, selected_interests,
        car_search_count, car_browse_count, car_compare_count
    )

    # 计算购买意向
    intent_level = calculate_enhanced_intent(
        behaviors, car_search_count, car_browse_count,
        car_compare_count, app_open_count, near_4s_store
    )

    return {
        # 基础标识
        "user_id": user_id,

        # 人口统计信息
        "age": age,
        "age_bucket": age_bucket,
        "gender": gender,
        "education": education,
        "income_level": income,
        "city": city,
        "city_tier": random.choice(["一线", "新一线", "二线", "三线"]),
        "occupation": random.choice(["企业高管", "中层管理", "技术专家", "自由职业", "公务员"]),

        # 资产信息
        "has_house": has_house,
        "has_car": has_car,
        "phone_price": phone_price,

        # 家庭信息
        "marital_status": marital,
        "has_children": has_children,
        "commute_distance": commute_distance,

        # 兴趣和行为
        "interests": selected_interests,
        "behaviors": behaviors,

        # 品牌偏好
        "primary_brand": brand,
        "primary_model": model,
        "brand_score": round(brand_score, 2),

        # 购买意向
        "purchase_intent": intent_level["level"],
        "intent_score": intent_level["score"],
        "lifecycle_stage": intent_level["stage"],

        # APP使用行为
        "app_open_count": app_open_count,
        "app_usage_duration": app_usage_duration,
        "miniprogram_open_count": miniprogram_open_count,

        # 汽车相关行为
        "car_search_count": car_search_count,
        "car_browse_count": car_browse_count,
        "car_compare_count": car_compare_count,
        "car_app_payment": car_app_payment,

        # 广告和消息
        "push_exposure": push_exposure,
        "push_click": push_click,
        "ad_exposure": ad_exposure,
        "ad_click": ad_click,

        # 位置和天气
        "near_4s_store": near_4s_store,
        "weather_info": weather_info,

        # 消费行为
        "consumption_frequency": consumption_frequency,

        # 行业标识
        "industry": INDUSTRY
    }

def generate_enhanced_behaviors(
    brand: str,
    model: str,
    interests: List[str],
    search_count: int,
    browse_count: int,
    compare_count: int
) -> List[str]:
    """生成增强的行为列表（简化版，返回行为标签）"""
    behaviors = []

    # 汽车相关行为
    if search_count > 0:
        behaviors.append("汽车搜索")
    if browse_count > 0:
        behaviors.append("汽车浏览")
    if compare_count > 0:
        behaviors.append("比价行为")

    # 品牌相关行为
    if search_count > 5 or browse_count > 10:
        behaviors.append(f"{brand}品牌关注")

    # 兴趣相关行为
    for interest in interests[:3]:
        behaviors.append(f"{interest}相关内容浏览")

    return behaviors


def calculate_enhanced_intent(
    behaviors: List[str],
    search_count: int,
    browse_count: int,
    compare_count: int,
    app_open_count: int,
    near_4s_store: bool
) -> Dict:
    """基于多维度行为计算购买意向"""
    score = 0.0

    # 搜索行为权重
    score += min(search_count * 0.02, 0.3)

    # 浏览行为权重
    score += min(browse_count * 0.01, 0.2)

    # 比价行为权重（强意向信号）
    score += min(compare_count * 0.03, 0.25)

    # APP使用频率
    score += min(app_open_count * 0.002, 0.15)

    # 4S店附近（强意向信号）
    if near_4s_store:
        score += 0.15

    # 归一化到0-1
    score = min(score, 1.0)

    # 确定意向等级和生命周期阶段
    if score >= 0.7:
        return {"level": "高", "score": round(score, 2), "stage": "转化"}
    elif score >= 0.5:
        return {"level": "中", "score": round(score, 2), "stage": "意向"}
    elif score >= 0.3:
        return {"level": "低", "score": round(score, 2), "stage": "考虑"}
    elif score >= 0.1:
        return {"level": "弱", "score": round(score, 2), "stage": "认知"}
    else:
        return {"level": "无", "score": round(score, 2), "stage": "空白"}


def generate_behaviors(brand: str, model: str, interests: List[str]) -> List[Dict]:
    """旧版行为生成函数（保持兼容性）"""
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
    """旧版意向计算函数（保持兼容性）"""
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
