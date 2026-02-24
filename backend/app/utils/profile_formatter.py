"""
用户画像格式化工具
将结构化数据转换为自然语言文本
"""
import json
from typing import Dict, Any


def format_profile_text(profile: Dict[str, Any]) -> str:
    """将结构化用户画像数据转换为自然语言文本

    Args:
        profile: 用户画像字典，可能包含以下字段:
            - age: 年龄
            - gender: 性别
            - city: 城市
            - occupation: 职业
            - income: 收入
            - interests: 兴趣爱好（列表或逗号分隔字符串）
            - budget: 购车预算
            - has_car: 是否有车
            - purchase_intent: 购车意向
            - properties: JSON字符串或字典（包含额外属性）

    Returns:
        格式化后的自然语言文本，例如: "35岁男性，上海工程师，年收入30万，喜欢高尔夫、科技"
    """
    parts = []

    # 基本信息
    if profile.get("age"):
        parts.append(f"{profile['age']}岁")

    if profile.get("gender"):
        parts.append(profile["gender"])

    if profile.get("city"):
        parts.append(f"{profile['city']}")

    if profile.get("occupation"):
        parts.append(profile["occupation"])

    # 处理 properties（可能是JSON字符串或字典）
    properties = profile.get("properties")
    if properties:
        if isinstance(properties, str):
            try:
                properties = json.loads(properties)
            except json.JSONDecodeError:
                properties = {}

        if isinstance(properties, dict):
            # 收入
            if "income" in properties and properties["income"]:
                income = properties["income"]
                if income >= 10000:
                    parts.append(f"年收入{income//10000}万")
                else:
                    parts.append(f"年收入{income}元")

            # 兴趣爱好
            if "interests" in properties and properties["interests"]:
                interests = properties["interests"]
                if isinstance(interests, list) and interests:
                    parts.append(f"喜欢{', '.join(interests)}")
                elif isinstance(interests, str) and interests:
                    parts.append(f"喜欢{interests}")

            # 购车预算
            if "budget" in properties and properties["budget"]:
                budget = properties["budget"]
                parts.append(f"购车预算{budget}万")

            # 是否有车
            if "has_car" in properties:
                has_car = properties["has_car"]
                if has_car:
                    parts.append("已有车")
                else:
                    parts.append("无车")

            # 购车意向
            if "purchase_intent" in properties and properties["purchase_intent"]:
                intent = properties["purchase_intent"]
                if intent != "无":
                    parts.append(f"购车意向: {intent}")

    # 直接从顶层字段获取（兼容不同格式）
    if not properties or "income" not in properties:
        if profile.get("income"):
            income = profile["income"]
            if income >= 10000:
                parts.append(f"年收入{income//10000}万")
            else:
                parts.append(f"年收入{income}元")

    if not properties or "interests" not in properties:
        if profile.get("interests"):
            interests = profile["interests"]
            if isinstance(interests, list) and interests:
                parts.append(f"喜欢{', '.join(interests)}")
            elif isinstance(interests, str) and interests:
                parts.append(f"喜欢{interests}")

    if not properties or "budget" not in properties:
        if profile.get("budget"):
            parts.append(f"购车预算{profile['budget']}万")

    if not properties or "has_car" not in properties:
        if "has_car" in profile:
            if profile["has_car"]:
                parts.append("已有车")
            else:
                parts.append("无车")

    if not properties or "purchase_intent" not in properties:
        if profile.get("purchase_intent") and profile["purchase_intent"] != "无":
            parts.append(f"购车意向: {profile['purchase_intent']}")

    # 如果没有任何信息，返回用户ID
    if not parts:
        user_id = profile.get("user_id", "未知")
        return f"{user_id}用户"

    return "，".join(parts)
