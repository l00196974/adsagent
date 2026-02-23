"""
LLM客户端 - 用于关系识别和商品ID映射
"""
import json
from typing import List, Dict, Optional
from app.core.openai_client import OpenAIClient
from app.core.logger import app_logger


class LLMRelationIdentifier:
    """LLM关系识别器 - 负责识别复杂关系并映射商品ID"""

    def __init__(self):
        self.llm_client = OpenAIClient()

    def identify_relations_batch(
        self,
        behavior_data: List[Dict],
        item_index: Dict[str, str],
        batch_size: int = 10
    ) -> List[Dict]:
        """
        批量识别关系并映射商品ID

        Args:
            behavior_data: 行为数据列表
            item_index: 商品名称→item_id的映射表
            batch_size: 每批处理的行为数量

        Returns:
            识别出的关系列表
        """
        all_relations = []

        # 分批处理
        for i in range(0, len(behavior_data), batch_size):
            batch = behavior_data[i:i + batch_size]
            try:
                relations = self._process_batch(batch, item_index)
                all_relations.extend(relations)
            except Exception as e:
                app_logger.error(f"LLM识别批次失败: {e}", exc_info=True)
                continue

        return all_relations

    def _process_batch(self, batch: List[Dict], item_index: Dict[str, str]) -> List[Dict]:
        """处理单个批次"""
        prompt = self._build_prompt(batch, item_index)

        try:
            response = self.llm_client.chat(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=4000
            )

            # 解析LLM返回的JSON
            result = json.loads(response)
            return result.get("relations", [])

        except json.JSONDecodeError as e:
            app_logger.error(f"LLM返回JSON解析失败: {e}")
            return []
        except Exception as e:
            app_logger.error(f"LLM调用失败: {e}", exc_info=True)
            return []

    def _build_prompt(self, batch: List[Dict], item_index: Dict[str, str]) -> str:
        """构建LLM提示词"""
        # 构建商品列表
        item_list = "\n".join([
            f"- {item_id}: {item_name}"
            for item_name, item_id in item_index.items()
        ])

        # 构建行为数据
        behavior_list = json.dumps(batch, ensure_ascii=False, indent=2)

        prompt = f"""你是知识图谱关系识别专家。请根据用户行为数据识别出对应的关系,并将商品名称匹配到正确的item_id。

可用的商品列表:
{item_list}

关系类型说明:
- 购买: 用户购买了某个商品
- 浏览: 用户浏览了某个商品
- 曝光: 用户看到了某个商品的广告
- 点击: 用户点击了某个商品的链接
- 搜索: 用户搜索了某个商品
- 比价过: 用户对比了多个商品
- 留资: 用户留下了联系方式表示对某个商品感兴趣

用户行为数据:
{behavior_list}

请识别关系并返回JSON格式,格式如下:
{{
  "relations": [
    {{
      "from_id": "user_001",
      "to_id": "item_001",
      "relation_type": "购买",
      "properties": {{
        "history": [{{
          "purchase_date": "2024-01-15",
          "purchase_amount": 800000,
          "item_id": "item_001"
        }}]
      }}
    }}
  ]
}}

注意事项:
1. 必须将商品名称匹配到商品列表中的item_id
2. 如果找不到匹配的商品,跳过该关系
3. properties中的history必须是数组格式
4. 只返回JSON,不要有其他文字说明
"""
        return prompt

    def build_item_index(self, users: List[Dict]) -> Dict[str, str]:
        """
        从用户数据中构建商品索引

        Args:
            users: 用户数据列表

        Returns:
            商品名称→item_id的映射表
        """
        item_index = {}

        for user in users:
            # 从owned_items中提取
            if "owned_items" in user and isinstance(user["owned_items"], list):
                for item in user["owned_items"]:
                    if isinstance(item, dict):
                        item_id = item.get("item_id")
                        name = item.get("name")
                        brand = item.get("brand")
                        series = item.get("series")

                        if item_id and name:
                            item_index[name] = item_id
                        if item_id and brand and series:
                            full_name = f"{brand}{series}"
                            item_index[full_name] = item_id

            # 从primary_brand和primary_model中提取(兼容旧格式)
            brand = user.get("primary_brand")
            model = user.get("primary_model")
            if brand and model:
                item_id = f"{brand}_{model}".replace(" ", "_")
                full_name = f"{brand}{model}"
                item_index[full_name] = f"item:{item_id}"
                item_index[model] = f"item:{item_id}"

        app_logger.info(f"构建商品索引完成: {len(item_index)} 个商品")
        return item_index


# 全局实例
llm_relation_identifier = LLMRelationIdentifier()
