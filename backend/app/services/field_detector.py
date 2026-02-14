"""
智能字段识别器 - 自动识别CSV列名并映射到系统字段
"""
from typing import List, Dict, Optional


class FieldDetector:
    """智能字段识别器"""

    # 字段映射模式 - 支持中英文和同义词
    FIELD_PATTERNS = {
        # 基础用户信息
        "user_id": ["用户id", "userid", "user_id", "uid", "用户编号", "id"],
        "age": ["年龄", "age", "用户年龄"],
        "age_bucket": ["年龄段", "age_bucket", "年龄区间", "age_range"],
        "gender": ["性别", "gender", "sex"],
        "education": ["学历", "education", "教育程度", "学位"],
        "income_level": ["收入", "income", "收入等级", "income_level", "收入水平"],
        "city_tier": ["城市", "city", "城市等级", "city_tier", "城市级别"],
        "city": ["常驻城市", "resident_city", "居住城市", "所在城市"],
        "occupation": ["职业", "occupation", "工作"],

        # 资产信息
        "has_house": ["有房", "house", "房产", "has_house", "是否有房"],
        "has_car": ["有车", "car", "车辆", "has_car", "是否有车"],
        "phone_price": ["手机价格", "phone_price", "手机价位", "手机消费"],

        # 家庭信息
        "marital_status": ["婚姻状况", "marital", "结婚", "订婚", "婚姻"],
        "has_children": ["生子", "children", "孩子", "二胎", "子女"],
        "commute_distance": ["通勤距离", "commute", "上班距离", "通勤"],

        # 兴趣和行为
        "interests": ["兴趣", "interest", "爱好", "hobby", "兴趣爱好"],
        "behaviors": ["行为", "behavior", "行为数据"],

        # 品牌和车型
        "primary_brand": ["品牌", "brand", "偏好品牌", "primary_brand", "主要品牌"],
        "primary_model": ["车型", "model", "型号", "primary_model", "主要车型"],
        "brand_score": ["品牌分数", "brand_score", "品牌评分", "亲和度"],

        # 购买意向
        "purchase_intent": ["购买意向", "intent", "意向", "purchase_intent"],
        "intent_score": ["意向分数", "intent_score", "意向评分"],
        "lifecycle_stage": ["生命周期", "stage", "阶段", "lifecycle_stage", "生命周期阶段"],

        # APP使用行为
        "app_open_count": ["app打开次数", "打开次数", "启动次数", "app_open"],
        "app_usage_duration": ["使用时长", "app时长", "使用时间", "duration"],
        "miniprogram_open_count": ["小程序打开", "小程序次数", "miniprogram"],

        # 汽车相关行为
        "car_search_count": ["汽车搜索", "搜索次数", "car_search", "搜索行为"],
        "car_browse_count": ["汽车浏览", "浏览次数", "car_browse", "浏览行为"],
        "car_compare_count": ["比价行为", "比价次数", "car_compare", "对比"],
        "car_app_payment": ["汽车app付费", "付费行为", "car_payment", "付费"],

        # 广告和消息
        "push_exposure": ["push曝光", "消息曝光", "push_exposure", "推送曝光"],
        "push_click": ["push点击", "消息点击", "push_click", "推送点击"],
        "ad_exposure": ["广告曝光", "ad_exposure", "曝光"],
        "ad_click": ["广告点击", "ad_click", "广告点击数"],

        # 位置和天气
        "near_4s_store": ["4s店附近", "4s店位置", "near_4s", "附近4s"],
        "location_history": ["历史位置", "location", "位置数据", "地理位置"],
        "weather_info": ["天气信息", "weather", "天气", "气象"],

        # 消费行为
        "consumption_frequency": ["消费频率", "consumption", "购买频率", "消费次数"],

        # POI相关字段
        "poi_id": ["poi_id", "poi编号", "地点id", "位置id"],
        "poi_name": ["poi_name", "poi名称", "地点名称", "位置名称"],
        "poi_type": ["poi_type", "poi类型", "地点类型", "位置类型"],
        "home_poi": ["home_poi", "常驻地", "居住地", "家庭地址", "住宅poi"],
        "work_poi": ["work_poi", "工作地", "办公地", "工作地点", "办公poi"],
        "visit_poi": ["visit_poi", "访问地点", "到访poi", "出现地点"],
        "visit_duration": ["visit_duration", "访问时长", "停留时长", "到访时长"],
        "visit_history": ["visit_history", "访问历史", "到访记录", "位置历史"],

        # APP相关字段
        "app_id": ["app_id", "应用id", "app编号", "应用编号"],
        "app_name": ["app_name", "应用名称", "app名称", "应用名"],
        "app_type": ["app_type", "应用类型", "app类型", "应用分类"],
        "app_usage": ["app_usage", "app使用", "应用使用", "app使用记录"],

        # Item相关字段(替代Brand和Model)
        "item_id": ["item_id", "商品id", "item编号", "商品编号", "产品id"],
        "item_category": ["category", "品类", "类别", "商品类别"],
        "item_brand": ["brand", "品牌", "商品品牌"],
        "item_series": ["series", "系列", "商品系列"],
        "item_name": ["name", "商品名称", "产品名称", "item名称"],
        "owned_items": ["owned_items", "拥有商品", "持有商品", "已购商品"],

        # 行为历史字段
        "purchase_history": ["purchase_history", "购买历史", "购买记录", "消费记录"],
        "browse_history": ["browse_history", "浏览历史", "浏览记录", "访问记录"],
        "exposure_history": ["exposure_history", "曝光历史", "曝光记录"],
        "click_history": ["click_history", "点击历史", "点击记录"],
        "search_history": ["search_history", "搜索历史", "搜索记录", "查询记录"],
        "compare_history": ["compare_history", "比价历史", "比价记录", "对比记录"],
        "register_history": ["register_history", "留资历史", "留资记录", "注册记录"],

        # 行为时间字段
        "purchase_date": ["purchase_date", "购买时间", "购买日期", "下单时间"],
        "browse_date": ["browse_date", "浏览时间", "浏览日期", "访问时间"],
        "exposure_date": ["exposure_date", "曝光时间", "曝光日期"],
        "click_date": ["click_date", "点击时间", "点击日期"],
        "search_date": ["search_date", "搜索时间", "搜索日期"],
        "compare_date": ["compare_date", "比价时间", "比价日期", "对比时间"],
        "register_date": ["register_date", "留资时间", "留资日期", "注册时间"],
        "owned_date": ["owned_date", "拥有时间", "购买时间"],
        "usage_date": ["usage_date", "使用时间", "使用日期"],
        "visit_date": ["visit_date", "访问时间", "到访时间"],

        # 通用字段
        "behavior_type": ["行为类型", "behavior_type", "行为", "action_type"],
        "timestamp": ["时间", "time", "日期", "date", "timestamp", "创建时间"],
        "event_type": ["事件类型", "event_type", "事件", "event"],
        "page_view": ["浏览", "page_view", "pv", "访问"],
        "click": ["点击", "click"],
        "search": ["搜索", "search", "查询"],
        "purchase": ["购买", "purchase", "下单"],
    }

    def __init__(self):
        """初始化字段识别器"""
        # 构建反向索引以提高匹配速度
        self._pattern_to_field = {}
        for field, patterns in self.FIELD_PATTERNS.items():
            for pattern in patterns:
                self._pattern_to_field[pattern.lower()] = field

    def auto_detect_fields(self, columns: List[str]) -> Dict[str, str]:
        """
        自动检测字段映射

        Args:
            columns: CSV列名列表

        Returns:
            字段映射字典 {原始列名: 系统字段名}
        """
        mapping = {}

        for col in columns:
            col_lower = col.lower().strip()

            # 1. 精确匹配
            if col_lower in self._pattern_to_field:
                mapping[col] = self._pattern_to_field[col_lower]
                continue

            # 2. 模糊匹配（使用更严格的匹配规则）
            matched = False
            for field, patterns in self.FIELD_PATTERNS.items():
                for pattern in patterns:
                    pattern_lower = pattern.lower()
                    # 完整单词匹配或精确包含匹配（避免部分匹配导致错误）
                    # 例如：避免 "app_usage_duration" 匹配到 "age"
                    if col_lower == pattern_lower or (pattern_lower in col_lower and len(pattern_lower) > 3):
                        mapping[col] = field
                        matched = True
                        break
                if matched:
                    break

            # 3. 如果没有匹配到,保留原始列名
            if col not in mapping:
                mapping[col] = col

        return mapping

    def normalize_csv_data(
        self,
        data: List[Dict],
        field_mapping: Dict[str, str]
    ) -> List[Dict]:
        """
        根据字段映射标准化CSV数据

        Args:
            data: 原始CSV数据(字典列表)
            field_mapping: 字段映射

        Returns:
            标准化后的数据
        """
        normalized_data = []

        for row in data:
            normalized_row = {}
            for original_col, value in row.items():
                # 使用映射后的字段名
                target_field = field_mapping.get(original_col, original_col)
                normalized_row[target_field] = value

            # 特殊处理: 兴趣字段可能是逗号分隔的字符串
            if "interests" in normalized_row:
                interests = normalized_row["interests"]
                if isinstance(interests, str):
                    normalized_row["interests"] = [
                        i.strip() for i in interests.split(",") if i.strip()
                    ]
                elif not isinstance(interests, list):
                    normalized_row["interests"] = []

            # 特殊处理: 行为字段可能是逗号分隔的字符串
            if "behaviors" in normalized_row:
                behaviors = normalized_row["behaviors"]
                if isinstance(behaviors, str):
                    normalized_row["behaviors"] = [
                        b.strip() for b in behaviors.split(",") if b.strip()
                    ]
                elif not isinstance(behaviors, list):
                    normalized_row["behaviors"] = []

            normalized_data.append(normalized_row)

        return normalized_data

    def get_field_statistics(
        self,
        field_mapping: Dict[str, str]
    ) -> Dict[str, any]:
        """
        获取字段识别统计信息

        Args:
            field_mapping: 字段映射

        Returns:
            统计信息
        """
        stats = {
            "total_fields": len(field_mapping),
            "recognized_fields": 0,
            "unrecognized_fields": 0,
            "field_types": {}
        }

        for original_col, target_field in field_mapping.items():
            if target_field in self.FIELD_PATTERNS:
                stats["recognized_fields"] += 1
            else:
                stats["unrecognized_fields"] += 1

            # 统计字段类型分布
            stats["field_types"][target_field] = stats["field_types"].get(target_field, 0) + 1

        return stats


# 全局实例
field_detector = FieldDetector()
