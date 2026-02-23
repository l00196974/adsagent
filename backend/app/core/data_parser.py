"""
数据解析器 - 支持多种格式的灵活数据解析

支持的格式:
1. JSON格式: {"key": "value", ...}
2. 键值对格式: key=value,key2=value2
3. 自由文本格式: 任意文本内容
"""

import json
from typing import Dict, Any


class DataParser:
    """统一的数据解析器，支持多种格式"""

    @staticmethod
    def parse(text: str) -> Dict[str, Any]:
        """自动识别格式并解析

        Args:
            text: 待解析的文本

        Returns:
            解析后的字典
        """
        if not text or not isinstance(text, str):
            return {}

        text = text.strip()
        if not text:
            return {}

        # 1. 尝试JSON格式
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                return data
            # 如果是其他类型（列表、字符串等），包装成字典
            return {"value": data}
        except (json.JSONDecodeError, ValueError):
            pass

        # 2. 尝试键值对格式 (key=value,key2=value2)
        if '=' in text:
            try:
                return DataParser._parse_kv(text)
            except Exception:
                pass

        # 3. 返回原始文本
        return {"raw_text": text}

    @staticmethod
    def _parse_kv(text: str) -> Dict[str, Any]:
        """解析key=value,key=value格式

        支持的分隔符:
        - 逗号: key=value,key2=value2
        - 分号: key=value;key2=value2
        - 换行: key=value\\nkey2=value2

        Args:
            text: 键值对文本

        Returns:
            解析后的字典
        """
        result = {}

        # 尝试不同的分隔符
        for separator in [',', ';', '\n']:
            if separator in text or '=' in text:
                pairs = text.split(separator)
                for pair in pairs:
                    pair = pair.strip()
                    if '=' in pair:
                        key, value = pair.split('=', 1)
                        key = key.strip()
                        value = value.strip()

                        # 尝试转换数值类型
                        result[key] = DataParser._parse_value(value)

        return result if result else {"raw_text": text}

    @staticmethod
    def _parse_value(value: str) -> Any:
        """尝试将字符串转换为合适的类型

        Args:
            value: 字符串值

        Returns:
            转换后的值
        """
        # 尝试整数
        try:
            return int(value)
        except ValueError:
            pass

        # 尝试浮点数
        try:
            return float(value)
        except ValueError:
            pass

        # 尝试布尔值
        if value.lower() in ['true', 'yes', '是', '真']:
            return True
        if value.lower() in ['false', 'no', '否', '假']:
            return False

        # 返回原始字符串
        return value

    @staticmethod
    def serialize(data: Dict[str, Any], format: str = "json") -> str:
        """将字典序列化为指定格式

        Args:
            data: 待序列化的字典
            format: 目标格式 (json, kv, text)

        Returns:
            序列化后的字符串
        """
        if format == "json":
            return json.dumps(data, ensure_ascii=False)

        elif format == "kv":
            # 转换为key=value,key2=value2格式
            pairs = []
            for key, value in data.items():
                if isinstance(value, (list, dict)):
                    value = json.dumps(value, ensure_ascii=False)
                pairs.append(f"{key}={value}")
            return ",".join(pairs)

        elif format == "text":
            # 转换为自由文本
            if "raw_text" in data:
                return data["raw_text"]
            return json.dumps(data, ensure_ascii=False, indent=2)

        else:
            raise ValueError(f"不支持的格式: {format}")


class BehaviorEventParser(DataParser):
    """行为事件专用解析器"""

    @staticmethod
    def parse_event(text: str) -> Dict[str, Any]:
        """解析行为事件数据

        Args:
            text: 事件数据文本

        Returns:
            包含标准字段的字典
        """
        data = DataParser.parse(text)

        # 标准化常见字段名
        field_mapping = {
            "action": ["action", "event_type", "行为类型", "类型"],
            "item": ["item", "item_id", "物品", "商品"],
            "duration": ["duration", "时长", "停留时间"],
            "app": ["app", "app_id", "应用"],
            "media": ["media", "media_id", "媒体"],
            "poi": ["poi", "poi_id", "地点", "位置"],
        }

        result = {}
        for standard_key, aliases in field_mapping.items():
            for alias in aliases:
                if alias in data:
                    result[standard_key] = data[alias]
                    break

        # 保留其他字段
        for key, value in data.items():
            if key not in result.values():
                result[key] = value

        return result


class UserProfileParser(DataParser):
    """用户画像专用解析器"""

    @staticmethod
    def parse_profile(text: str) -> Dict[str, Any]:
        """解析用户画像数据

        Args:
            text: 画像数据文本

        Returns:
            包含标准字段的字典
        """
        data = DataParser.parse(text)

        # 标准化常见字段名
        field_mapping = {
            "age": ["age", "年龄"],
            "gender": ["gender", "性别"],
            "income": ["income", "收入", "月收入"],
            "city": ["city", "城市", "地区"],
            "occupation": ["occupation", "职业", "工作"],
            "interests": ["interests", "兴趣", "爱好"],
        }

        result = {}
        for standard_key, aliases in field_mapping.items():
            for alias in aliases:
                if alias in data:
                    result[standard_key] = data[alias]
                    break

        # 保留其他字段
        for key, value in data.items():
            if key not in result.values():
                result[key] = value

        return result
