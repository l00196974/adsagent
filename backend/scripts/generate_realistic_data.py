"""
生成真实的用户画像和行为序列数据

模拟汽车购买决策过程，包含：
1. 用户画像：年龄、性别、收入、职业、兴趣等
2. 行为序列：浏览、搜索、点击、对比、加购、购买等
3. 行为逻辑：从兴趣萌芽 -> 信息收集 -> 对比评估 -> 决策购买
"""

import random
import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path
import sys

# 添加项目路径
sys.path.append(str(Path(__file__).parent.parent))

from app.core.logger import app_logger


class RealisticDataGenerator:
    """真实数据生成器"""

    def __init__(self):
        self.db_path = Path("data/graph.db")

        # 用户画像配置
        self.age_groups = {
            "25-30": {"weight": 0.15, "income_range": (8000, 15000)},
            "30-35": {"weight": 0.25, "income_range": (12000, 25000)},
            "35-40": {"weight": 0.30, "income_range": (15000, 35000)},
            "40-45": {"weight": 0.20, "income_range": (18000, 45000)},
            "45-50": {"weight": 0.10, "income_range": (20000, 50000)},
        }

        self.occupations = {
            "互联网从业者": 0.20,
            "金融从业者": 0.15,
            "企业管理者": 0.15,
            "医生": 0.10,
            "教师": 0.10,
            "工程师": 0.15,
            "销售": 0.10,
            "自由职业": 0.05
        }

        self.cities = {
            "北京": 0.15, "上海": 0.15, "深圳": 0.12, "广州": 0.10,
            "杭州": 0.08, "成都": 0.08, "南京": 0.06, "武汉": 0.06,
            "西安": 0.05, "重庆": 0.05, "苏州": 0.05, "天津": 0.05
        }

        self.interests = {
            "高尔夫": ["高收入", "商务"],
            "旅游": ["中高收入", "休闲"],
            "科技": ["互联网", "年轻"],
            "健身": ["健康", "活力"],
            "摄影": ["艺术", "品味"],
            "美食": ["生活", "品质"],
            "阅读": ["文化", "修养"],
            "音乐": ["艺术", "情调"]
        }

        # 汽车品牌和车型配置
        self.car_brands = {
            "豪华品牌": {
                "宝马": {
                    "models": ["3系", "5系", "7系", "X3", "X5"],
                    "price_range": (30, 100),
                    "target_income": 20000
                },
                "奔驰": {
                    "models": ["C级", "E级", "S级", "GLC", "GLE"],
                    "price_range": (35, 120),
                    "target_income": 22000
                },
                "奥迪": {
                    "models": ["A4L", "A6L", "A8L", "Q5", "Q7"],
                    "price_range": (28, 110),
                    "target_income": 18000
                },
                "雷克萨斯": {
                    "models": ["ES", "LS", "RX", "NX"],
                    "price_range": (30, 90),
                    "target_income": 20000
                }
            },
            "中高端品牌": {
                "大众": {
                    "models": ["帕萨特", "迈腾", "途观", "途昂"],
                    "price_range": (18, 40),
                    "target_income": 12000
                },
                "丰田": {
                    "models": ["凯美瑞", "汉兰达", "RAV4", "亚洲龙"],
                    "price_range": (18, 35),
                    "target_income": 12000
                },
                "本田": {
                    "models": ["雅阁", "CR-V", "冠道", "奥德赛"],
                    "price_range": (17, 35),
                    "target_income": 11000
                }
            },
            "经济品牌": {
                "吉利": {
                    "models": ["博越", "星越", "帝豪", "缤越"],
                    "price_range": (8, 18),
                    "target_income": 8000
                },
                "比亚迪": {
                    "models": ["汉", "唐", "宋", "秦"],
                    "price_range": (10, 30),
                    "target_income": 9000
                },
                "长城": {
                    "models": ["哈弗H6", "哈弗H9", "WEY VV7"],
                    "price_range": (10, 25),
                    "target_income": 9000
                }
            }
        }

        # 行为类型权重（不同阶段）
        self.behavior_stages = {
            "兴趣萌芽": {
                "browse": 0.50,      # 浏览内容
                "use_app": 0.30,     # 使用APP
                "visit_poi": 0.20    # 访问POI
            },
            "信息收集": {
                "search": 0.40,      # 搜索
                "browse": 0.35,      # 浏览
                "click": 0.25        # 点击
            },
            "对比评估": {
                "compare": 0.35,     # 对比
                "click": 0.30,       # 点击
                "browse": 0.25,      # 浏览
                "visit_poi": 0.10    # 到店
            },
            "决策购买": {
                "visit_poi": 0.40,   # 到店
                "add_cart": 0.30,    # 加购
                "purchase": 0.20,    # 购买
                "compare": 0.10      # 最后对比
            }
        }

        # APP和媒体配置
        self.apps = {
            "汽车之家": {"category": "汽车资讯", "tags": ["汽车", "资讯", "评测"]},
            "懂车帝": {"category": "汽车资讯", "tags": ["汽车", "短视频", "导购"]},
            "易车": {"category": "汽车资讯", "tags": ["汽车", "报价", "评测"]},
            "小红书": {"category": "生活方式", "tags": ["种草", "分享", "生活"]},
            "抖音": {"category": "短视频", "tags": ["娱乐", "短视频", "推荐"]},
            "微信": {"category": "社交", "tags": ["社交", "通讯", "支付"]},
            "高德地图": {"category": "导航", "tags": ["导航", "地图", "出行"]},
            "大众点评": {"category": "本地生活", "tags": ["美食", "团购", "评价"]}
        }

        self.media = {
            "汽车之家": {"type": "汽车媒体", "tags": ["专业", "评测", "资讯"]},
            "懂车帝": {"type": "汽车媒体", "tags": ["视频", "导购", "互动"]},
            "易车网": {"type": "汽车媒体", "tags": ["报价", "评测", "论坛"]},
            "新浪汽车": {"type": "汽车媒体", "tags": ["资讯", "评测", "行业"]},
            "爱卡汽车": {"type": "汽车媒体", "tags": ["论坛", "评测", "社区"]}
        }

        self.pois = {
            "4S店": ["宝马4S店", "奔驰4S店", "奥迪4S店", "大众4S店", "丰田4S店"],
            "汽车展厅": ["汽车城", "汽车广场", "汽车展览中心"],
            "高尔夫球场": ["XX高尔夫俱乐部", "XX高尔夫球场"],
            "商务会所": ["XX商务会所", "XX私人会所"],
            "高档餐厅": ["XX西餐厅", "XX日料店", "XX私房菜"]
        }

    def weighted_choice(self, choices_dict):
        """根据权重随机选择"""
        choices = list(choices_dict.keys())
        weights = list(choices_dict.values())
        return random.choices(choices, weights=weights)[0]

    def generate_user_profile(self, user_id):
        """生成用户画像"""
        # 年龄段
        age_group = self.weighted_choice({k: v["weight"] for k, v in self.age_groups.items()})
        age = random.randint(int(age_group.split("-")[0]), int(age_group.split("-")[1]))

        # 收入（基于年龄段）
        income_range = self.age_groups[age_group]["income_range"]
        income = random.randint(income_range[0], income_range[1])

        # 性别
        gender = random.choice(["男", "女"])

        # 职业
        occupation = self.weighted_choice(self.occupations)

        # 城市
        city = self.weighted_choice(self.cities)

        # 兴趣（根据收入和职业）
        num_interests = random.randint(2, 4)
        interests = random.sample(list(self.interests.keys()), num_interests)

        # 如果高收入，更可能喜欢高尔夫
        if income > 20000 and "高尔夫" not in interests and random.random() < 0.6:
            interests.append("高尔夫")

        # 购车预算（基于收入）
        budget_ratio = random.uniform(0.3, 0.8)  # 年收入的30%-80%
        budget = int(income * 12 * budget_ratio / 10000)  # 转换为万元

        # 是否有车
        has_car = random.random() < 0.5  # 50%的人已有车

        # 购车意向（基于是否有车）
        if has_car:
            purchase_intent = random.choices(
                ["换车", "增购", "无"],
                weights=[0.15, 0.05, 0.80]  # 15%换车, 5%增购, 80%无意向
            )[0]
        else:
            purchase_intent = random.choices(
                ["首购", "观望"],
                weights=[0.25, 0.75]  # 25%首购, 75%观望
            )[0]

        return {
            "user_id": user_id,
            "age": age,
            "gender": gender,
            "income": income,
            "occupation": occupation,
            "city": city,
            "interests": interests,
            "budget": budget,
            "has_car": has_car,
            "purchase_intent": purchase_intent
        }

    def select_target_brands(self, profile):
        """根据用户画像选择目标品牌"""
        income = profile["income"]
        budget = profile["budget"]

        target_brands = []

        # 根据收入和预算选择品牌层级
        if income >= 20000 and budget >= 30:
            # 高收入，关注豪华品牌
            target_brands.extend(random.sample(list(self.car_brands["豪华品牌"].keys()),
                                              random.randint(2, 3)))

        if income >= 12000 and budget >= 18:
            # 中高收入，关注中高端品牌
            target_brands.extend(random.sample(list(self.car_brands["中高端品牌"].keys()),
                                              random.randint(1, 2)))

        if budget < 20:
            # 预算有限，关注经济品牌
            target_brands.extend(random.sample(list(self.car_brands["经济品牌"].keys()),
                                              random.randint(1, 2)))

        # 去重
        target_brands = list(set(target_brands))

        # 如果没有选中任何品牌，默认选择中高端品牌
        if not target_brands:
            target_brands = [random.choice(list(self.car_brands["中高端品牌"].keys()))]

        return target_brands

    def generate_behavior_sequence(self, profile, target_brands):
        """生成用户行为序列"""
        behaviors = []
        start_date = datetime.now() - timedelta(days=90)  # 90天前开始
        current_date = start_date

        # 根据购车意向决定行为数量和转化概率
        if profile["purchase_intent"] in ["首购", "换车"]:
            num_behaviors = random.randint(120, 180)
            conversion_prob = 0.12  # 12%转化率
        elif profile["purchase_intent"] == "增购":
            num_behaviors = random.randint(100, 150)
            conversion_prob = 0.08  # 8%转化率
        elif profile["purchase_intent"] == "观望":
            num_behaviors = random.randint(80, 120)
            conversion_prob = 0.03  # 3%转化率
        else:  # 无意向
            num_behaviors = random.randint(50, 80)
            conversion_prob = 0.005  # 0.5%转化率

        # 决定是否最终购买
        will_purchase = random.random() < conversion_prob

        # 行为阶段划分（根据是否购买调整）
        if will_purchase:
            # 会购买的用户：完整的四个阶段
            stage_behaviors = {
                "兴趣萌芽": int(num_behaviors * 0.25),
                "信息收集": int(num_behaviors * 0.35),
                "对比评估": int(num_behaviors * 0.30),
                "决策购买": int(num_behaviors * 0.10)
            }
        else:
            # 不会购买的用户：只有前三个阶段，且对比评估阶段较短
            stage_behaviors = {
                "兴趣萌芽": int(num_behaviors * 0.35),
                "信息收集": int(num_behaviors * 0.45),
                "对比评估": int(num_behaviors * 0.20),
                "决策购买": 0  # 不进入决策购买阶段
            }

        behavior_id = 0

        # 第一阶段：兴趣萌芽
        for _ in range(stage_behaviors["兴趣萌芽"]):
            action = self.weighted_choice(self.behavior_stages["兴趣萌芽"])
            behavior = self._generate_behavior(
                profile, action, current_date, behavior_id,
                target_brands, stage="兴趣萌芽"
            )
            behaviors.append(behavior)
            behavior_id += 1
            current_date += timedelta(hours=random.randint(1, 12))

        # 第二阶段：信息收集
        for _ in range(stage_behaviors["信息收集"]):
            action = self.weighted_choice(self.behavior_stages["信息收集"])
            behavior = self._generate_behavior(
                profile, action, current_date, behavior_id,
                target_brands, stage="信息收集"
            )
            behaviors.append(behavior)
            behavior_id += 1
            current_date += timedelta(hours=random.randint(1, 8))

        # 第三阶段：对比评估
        for _ in range(stage_behaviors["对比评估"]):
            action = self.weighted_choice(self.behavior_stages["对比评估"])
            behavior = self._generate_behavior(
                profile, action, current_date, behavior_id,
                target_brands, stage="对比评估"
            )
            behaviors.append(behavior)
            behavior_id += 1
            current_date += timedelta(hours=random.randint(1, 6))

        # 第四阶段：决策购买（仅购买用户）
        if stage_behaviors["决策购买"] > 0:
            for i in range(stage_behaviors["决策购买"]):
                # 如果决定购买，最后几个行为包含购买
                if will_purchase and i >= stage_behaviors["决策购买"] - 3:
                    if i == stage_behaviors["决策购买"] - 1:
                        action = "purchase"
                    else:
                        action = self.weighted_choice({"visit_poi": 0.5, "add_cart": 0.5})
                else:
                    action = self.weighted_choice(self.behavior_stages["决策购买"])

                behavior = self._generate_behavior(
                    profile, action, current_date, behavior_id,
                    target_brands, stage="决策购买"
                )
                behaviors.append(behavior)
                behavior_id += 1
                current_date += timedelta(hours=random.randint(1, 24))

        return behaviors

    def _generate_behavior(self, profile, action, timestamp, behavior_id, target_brands, stage):
        """生成单个行为"""
        behavior = {
            "user_id": profile["user_id"],
            "action": action,
            "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "behavior_id": f"{profile['user_id']}_b{behavior_id}"
        }

        # 根据行为类型生成详细信息
        if action == "browse":
            media = random.choice(list(self.media.keys()))
            brand = random.choice(target_brands)
            brand_info = self._get_brand_info(brand)
            model = random.choice(brand_info["models"])

            behavior.update({
                "media_id": media,
                "item_id": f"{brand}_{model}",
                "duration": random.randint(30, 300)
            })

        elif action == "search":
            brand = random.choice(target_brands)
            brand_info = self._get_brand_info(brand)
            model = random.choice(brand_info["models"])

            search_queries = [
                f"{brand}{model}",
                f"{brand}{model}怎么样",
                f"{brand}{model}价格",
                f"{brand}{model}油耗",
                f"{brand}{model}配置",
                f"{brand}和{random.choice(target_brands)}对比"
            ]

            behavior.update({
                "app_id": random.choice(["汽车之家", "懂车帝", "易车"]),
                "item_id": random.choice(search_queries)
            })

        elif action == "click":
            brand = random.choice(target_brands)
            brand_info = self._get_brand_info(brand)
            model = random.choice(brand_info["models"])

            behavior.update({
                "media_id": random.choice(list(self.media.keys())),
                "item_id": f"{brand}_{model}_详情页"
            })

        elif action == "compare":
            brands_to_compare = random.sample(target_brands, min(2, len(target_brands)))
            models = []
            for brand in brands_to_compare:
                brand_info = self._get_brand_info(brand)
                models.append(f"{brand}_{random.choice(brand_info['models'])}")

            behavior.update({
                "app_id": "汽车之家",
                "item_id": f"对比_{','.join(models)}",
                "duration": random.randint(120, 600)
            })

        elif action == "use_app":
            app = random.choice(list(self.apps.keys()))
            behavior.update({
                "app_id": app,
                "duration": random.randint(60, 1800)
            })

        elif action == "visit_poi":
            if stage in ["对比评估", "决策购买"]:
                # 访问4S店
                brand = random.choice(target_brands)
                poi = f"{brand}4S店"
                poi_type = "4S店"
                duration = random.randint(3600, 7200)  # 1-2小时
            else:
                # 访问其他POI
                if "高尔夫" in profile["interests"]:
                    poi_type = random.choice(["高尔夫球场", "商务会所", "高档餐厅"])
                else:
                    poi_type = random.choice(["商务会所", "高档餐厅"])
                poi = random.choice(self.pois[poi_type])
                duration = random.randint(1800, 5400)

            behavior.update({
                "poi_id": poi,
                "poi_type": poi_type,
                "duration": duration
            })

        elif action == "add_cart":
            brand = random.choice(target_brands)
            brand_info = self._get_brand_info(brand)
            model = random.choice(brand_info["models"])

            behavior.update({
                "item_id": f"{brand}_{model}",
                "app_id": "汽车之家"
            })

        elif action == "purchase":
            brand = random.choice(target_brands)
            brand_info = self._get_brand_info(brand)
            model = random.choice(brand_info["models"])

            behavior.update({
                "item_id": f"{brand}_{model}",
                "poi_id": f"{brand}4S店"
            })

        return behavior

    def _get_brand_info(self, brand):
        """获取品牌信息"""
        for category in self.car_brands.values():
            if brand in category:
                return category[brand]
        return None

    def clear_database(self):
        """清空数据库"""
        app_logger.info("清空数据库...")
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM behavior_data")
            cursor.execute("DELETE FROM user_profiles")
            cursor.execute("DELETE FROM app_tags")
            cursor.execute("DELETE FROM media_tags")
            cursor.execute("DELETE FROM extracted_events")
            cursor.execute("DELETE FROM event_sequences")
            cursor.execute("DELETE FROM frequent_patterns")
            conn.commit()
        app_logger.info("数据库已清空")

    def save_to_database(self, users_data):
        """保存数据到数据库"""
        app_logger.info(f"开始保存 {len(users_data)} 个用户的数据...")

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # 保存用户画像
            for user_data in users_data:
                profile = user_data["profile"]
                cursor.execute(
                    """INSERT INTO user_profiles
                       (user_id, age, gender, city, occupation, properties)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        profile["user_id"],
                        profile["age"],
                        profile["gender"],
                        profile["city"],
                        profile["occupation"],
                        json.dumps({
                            "income": profile["income"],
                            "interests": profile["interests"],
                            "budget": profile["budget"],
                            "has_car": profile["has_car"],
                            "purchase_intent": profile["purchase_intent"]
                        }, ensure_ascii=False)
                    )
                )

            # 保存行为数据
            behavior_count = 0
            for user_data in users_data:
                for behavior in user_data["behaviors"]:
                    cursor.execute(
                        """INSERT INTO behavior_data
                           (user_id, action, timestamp, item_id, app_id, media_id,
                            poi_id, duration, properties)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            behavior["user_id"],
                            behavior["action"],
                            behavior["timestamp"],
                            behavior.get("item_id"),
                            behavior.get("app_id"),
                            behavior.get("media_id"),
                            behavior.get("poi_id"),
                            behavior.get("duration"),
                            json.dumps({
                                "behavior_id": behavior["behavior_id"],
                                "poi_type": behavior.get("poi_type")
                            }, ensure_ascii=False)
                        )
                    )
                    behavior_count += 1

            # 保存APP标签
            for app_name, app_info in self.apps.items():
                cursor.execute(
                    """INSERT OR REPLACE INTO app_tags
                       (app_id, app_name, category, tags, llm_generated)
                       VALUES (?, ?, ?, ?, ?)""",
                    (
                        app_name,
                        app_name,
                        app_info["category"],
                        json.dumps(app_info["tags"], ensure_ascii=False),
                        0
                    )
                )

            # 保存媒体标签
            for media_name, media_info in self.media.items():
                cursor.execute(
                    """INSERT OR REPLACE INTO media_tags
                       (media_id, media_name, media_type, tags, llm_generated)
                       VALUES (?, ?, ?, ?, ?)""",
                    (
                        media_name,
                        media_name,
                        media_info["type"],
                        json.dumps(media_info["tags"], ensure_ascii=False),
                        0
                    )
                )

            conn.commit()

        app_logger.info(f"数据保存完成: {len(users_data)} 个用户, {behavior_count} 条行为")

    def generate(self, num_users=500):
        """生成所有数据"""
        app_logger.info(f"开始生成 {num_users} 个用户的数据...")

        users_data = []

        for i in range(num_users):
            user_id = f"user_{i+1:04d}"

            # 生成用户画像
            profile = self.generate_user_profile(user_id)

            # 选择目标品牌
            target_brands = self.select_target_brands(profile)

            # 生成行为序列
            behaviors = self.generate_behavior_sequence(profile, target_brands)

            users_data.append({
                "profile": profile,
                "behaviors": behaviors,
                "target_brands": target_brands
            })

            if (i + 1) % 50 == 0:
                app_logger.info(f"已生成 {i+1}/{num_users} 个用户")

        app_logger.info(f"数据生成完成: {num_users} 个用户")

        # 统计信息
        total_behaviors = sum(len(u["behaviors"]) for u in users_data)
        avg_behaviors = total_behaviors / num_users

        purchase_count = sum(
            1 for u in users_data
            if any(b["action"] == "purchase" for b in u["behaviors"])
        )

        app_logger.info(f"统计信息:")
        app_logger.info(f"  总行为数: {total_behaviors}")
        app_logger.info(f"  平均行为数: {avg_behaviors:.1f}")
        app_logger.info(f"  购买用户数: {purchase_count} ({purchase_count/num_users*100:.1f}%)")

        return users_data


def main():
    """主函数"""
    generator = RealisticDataGenerator()

    # 清空数据库
    generator.clear_database()

    # 生成数据
    users_data = generator.generate(num_users=500)

    # 保存到数据库
    generator.save_to_database(users_data)

    app_logger.info("✅ 所有数据生成并保存完成！")


if __name__ == "__main__":
    main()
