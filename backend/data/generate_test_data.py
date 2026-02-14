"""生成测试数据 - 事件中心模型：100个用户，包含完整的事件数据"""
import csv
import json
import random
from datetime import datetime, timedelta

# 商品数据
ITEMS = [
    {"item_id": f"item_{i:03d}", "category": "汽车", "brand": brand, "series": series, "name": f"{brand}{series}"}
    for i, (brand, series) in enumerate([
        ("宝马", "7系"), ("宝马", "5系"), ("宝马", "X5"),
        ("奔驰", "S级"), ("奔驰", "E级"), ("奔驰", "GLC"),
        ("奥迪", "A8"), ("奥迪", "A6"), ("奥迪", "Q7"),
        ("特斯拉", "Model S"), ("特斯拉", "Model 3"), ("特斯拉", "Model X"),
        ("保时捷", "Panamera"), ("保时捷", "Cayenne"), ("保时捷", "911"),
        ("雷克萨斯", "ES"), ("雷克萨斯", "RX"), ("雷克萨斯", "LX"),
        ("沃尔沃", "S90"), ("沃尔沃", "XC90"),
    ], 1)
]

# POI数据
POIS = [
    {"poi_id": f"poi_{i:03d}", "poi_name": name, "poi_type": poi_type}
    for i, (name, poi_type) in enumerate([
        ("朝阳区某小区", "住宅"), ("海淀区公寓", "住宅"), ("顺义别墅区", "住宅"),
        ("国贸CBD", "商业区"), ("中关村软件园", "科技园区"), ("金融街", "商业区"),
        ("宝马4S店", "汽车销售"), ("奔驰体验中心", "汽车销售"), ("特斯拉体验店", "汽车销售"),
        ("保时捷中心", "汽车销售"), ("奥迪展厅", "汽车销售"),
        ("三里屯", "商圈"), ("西单", "商圈"), ("王府井", "商圈"),
        ("首都机场", "交通枢纽"), ("北京南站", "交通枢纽"),
    ], 1)
]

# APP数据
APPS = [
    {"app_id": f"app_{i:03d}", "app_name": name, "app_type": app_type}
    for i, (name, app_type) in enumerate([
        ("汽车之家", "汽车资讯"), ("懂车帝", "汽车资讯"), ("易车", "汽车资讯"),
        ("特斯拉", "品牌官方"), ("宝马", "品牌官方"), ("奔驰", "品牌官方"),
        ("瓜子二手车", "二手车交易"), ("优信二手车", "二手车交易"),
        ("滴滴出行", "出行服务"), ("高德地图", "导航地图"),
        ("抖音", "短视频"), ("微信", "社交通讯"), ("今日头条", "新闻资讯"),
    ], 1)
]

def random_datetime(start_days_ago, end_days_ago):
    """生成随机日期时间"""
    days_ago = random.randint(end_days_ago, start_days_ago)
    hours = random.randint(8, 22)
    minutes = random.randint(0, 59)
    seconds = random.randint(0, 59)
    date = datetime.now() - timedelta(days=days_ago, hours=hours, minutes=minutes, seconds=seconds)
    return date.strftime("%Y-%m-%dT%H:%M:%S")

def generate_session_id(user_id, date):
    """生成会话ID"""
    return f"sess_{user_id}_{date.split('T')[0]}"

def generate_users(count=100):
    """生成用户基础信息"""
    users = []
    for i in range(1, count + 1):
        user = {
            "user_id": f"user_{i:03d}",
            "age": random.randint(25, 55),
            "gender": random.choice(["男", "女"]),
            "education": random.choice(["本科", "硕士", "博士", "专科"]),
            "income_level": random.choice(["低", "中等", "高", "很高"]),
            "city_tier": random.choice(["一线", "新一线", "二线"]),
            "occupation": random.choice(["工程师", "产品经理", "企业高管", "医生", "教师", "律师", "金融从业者"]),
            "has_house": random.choice([True, False]),
            "has_car": random.choice([True, False]),
            "marital_status": random.choice(["已婚", "未婚", "离异"]),
            "has_children": random.choice([True, False]),
        }
        users.append(user)
    return users

def generate_item_entities():
    """生成商品实体数据"""
    return ITEMS

def generate_poi_entities():
    """生成POI实体数据"""
    return POIS

def generate_app_entities():
    """生成APP实体数据"""
    return APPS

def generate_events(users):
    """生成事件数据 - 事件中心模型"""
    events = []
    event_counter = 0

    for user in users:
        user_id = user["user_id"]

        # 为每个用户生成5-15个事件
        num_events = random.randint(5, 15)

        for _ in range(num_events):
            # 随机选择事件类型
            action = random.choice([
                "browse", "browse", "browse",  # 浏览事件最多
                "click", "click",              # 点击事件次之
                "search",                      # 搜索事件
                "purchase",                    # 购买事件（较少）
                "add_to_cart",                 # 加购事件
                "compare"                      # 比价事件
            ])

            # 生成时间戳
            timestamp = random_datetime(30, 1)
            session_id = generate_session_id(user_id, timestamp)

            # 随机选择涉及的实体
            item = random.choice(ITEMS) if random.random() < 0.9 else None
            app = random.choice(APPS) if random.random() < 0.8 else None
            poi = random.choice(POIS) if random.random() < 0.7 else None

            # 生成事件持续时间（秒）
            if action == "browse":
                duration = random.randint(30, 600)
            elif action == "purchase":
                duration = random.randint(120, 1800)
            elif action == "click":
                duration = random.randint(1, 10)
            else:
                duration = random.randint(10, 300)

            event_counter += 1
            event = {
                "event_id": f"event_{event_counter:05d}",
                "user_id": user_id,
                "action": action,
                "timestamp": timestamp,
                "session_id": session_id,
                "duration": duration,
                "item_id": item["item_id"] if item else "",
                "app_id": app["app_id"] if app else "",
                "poi_id": poi["poi_id"] if poi else "",
            }

            # 根据事件类型添加额外属性
            if action == "purchase" and item:
                event["purchase_amount"] = random.randint(300000, 1500000)
            elif action == "search":
                event["search_keyword"] = item["name"] if item else random.choice(["宝马", "奔驰", "特斯拉"])
            elif action == "compare" and item:
                event["compared_items"] = f"{item['item_id']},{random.choice(ITEMS)['item_id']}"

            events.append(event)

    # 按时间排序
    events.sort(key=lambda e: e["timestamp"])

    return events

def save_to_csv():
    """保存所有数据到CSV文件"""

    # 1. 生成用户数据
    print("生成用户数据...")
    users = generate_users(100)
    with open('d:\\workplace\\adsagent\\backend\\data\\users.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=users[0].keys())
        writer.writeheader()
        writer.writerows(users)
    print(f"✓ 用户数据已保存: {len(users)} 条")

    # 2. 生成商品实体数据
    print("生成商品实体数据...")
    items = generate_item_entities()
    with open('d:\\workplace\\adsagent\\backend\\data\\items.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=items[0].keys())
        writer.writeheader()
        writer.writerows(items)
    print(f"✓ 商品实体数据已保存: {len(items)} 条")

    # 3. 生成POI实体数据
    print("生成POI实体数据...")
    pois = generate_poi_entities()
    with open('d:\\workplace\\adsagent\\backend\\data\\pois.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=pois[0].keys())
        writer.writeheader()
        writer.writerows(pois)
    print(f"✓ POI实体数据已保存: {len(pois)} 条")

    # 4. 生成APP实体数据
    print("生成APP实体数据...")
    apps = generate_app_entities()
    with open('d:\\workplace\\adsagent\\backend\\data\\apps.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=apps[0].keys())
        writer.writeheader()
        writer.writerows(apps)
    print(f"✓ APP实体数据已保存: {len(apps)} 条")

    # 5. 生成事件数据（替代原来的关系数据）
    print("生成事件数据...")
    events = generate_events(users)

    # 获取所有可能的字段
    all_fields = set()
    for event in events:
        all_fields.update(event.keys())
    fieldnames = ["event_id", "user_id", "action", "timestamp", "session_id", "duration",
                  "item_id", "app_id", "poi_id", "purchase_amount", "search_keyword", "compared_items"]

    with open('d:\\workplace\\adsagent\\backend\\data\\events.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(events)
    print(f"✓ 事件数据已保存: {len(events)} 条")

    # 统计信息
    print("\n=== 数据生成完成 ===")
    print(f"用户数量: {len(users)}")
    print(f"商品数量: {len(items)}")
    print(f"POI数量: {len(pois)}")
    print(f"APP数量: {len(apps)}")
    print(f"事件数量: {len(events)}")

    # 事件类型统计
    action_types = {}
    for event in events:
        action = event["action"]
        action_types[action] = action_types.get(action, 0) + 1

    print("\n事件类型分布:")
    for action, count in sorted(action_types.items()):
        print(f"  {action}: {count} 条")

    # 统计涉及的实体
    events_with_item = sum(1 for e in events if e.get("item_id"))
    events_with_app = sum(1 for e in events if e.get("app_id"))
    events_with_poi = sum(1 for e in events if e.get("poi_id"))

    print("\n事件关联实体统计:")
    print(f"  涉及商品的事件: {events_with_item} 条")
    print(f"  涉及APP的事件: {events_with_app} 条")
    print(f"  涉及POI的事件: {events_with_poi} 条")

if __name__ == "__main__":
    save_to_csv()
