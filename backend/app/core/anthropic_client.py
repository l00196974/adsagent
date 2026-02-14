from openai import AsyncOpenAI
from typing import Dict, List
import json
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

class AnthropicClient:
    def __init__(self):
        # 使用OpenAI SDK连接MiniMax API
        if settings.anthropic_base_url:
            self.client = AsyncOpenAI(
                api_key=settings.anthropic_api_key,
                base_url=settings.anthropic_base_url
            )
            logger.info(f"使用MiniMax API: {settings.anthropic_base_url}")
        else:
            self.client = AsyncOpenAI(api_key=settings.anthropic_api_key)
            logger.info("使用OpenAI官方API")

        self.primary_model = settings.primary_model
        self.reasoning_model = settings.reasoning_model

    async def chat_completion(
        self,
        prompt: str,
        model: str = None,
        max_tokens: int = 4000,
        temperature: float = 0.3
    ) -> str:
        model = model or self.primary_model
        try:
            logger.info(f"调用LLM: model={model}, max_tokens={max_tokens}")
            response = await self.client.chat.completions.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[{"role": "user", "content": prompt}]
            )
            logger.info(f"LLM响应对象: {response}")
            result = response.choices[0].message.content if response.choices else ""
            logger.info(f"LLM响应内容: [{result}]")
            logger.info(f"LLM响应长度: {len(result)} 字符")
            return result
        except Exception as e:
            logger.error(f"LLM调用失败: {e}", exc_info=True)
            raise

    async def generate_app_tags(self, app_name: str, category: str = None) -> List[str]:
        """为APP生成标签"""
        logger.info(f"开始为APP {app_name} 生成标签")
        prompt = f"""你是一个移动应用分析专家。请为以下APP生成3-5个精准的标签。

APP名称: {app_name}
分类: {category or '未知'}

要求:
1. 标签应该描述APP的核心功能、用户群体、使用场景
2. 标签要简洁(2-4个字)
3. 只返回JSON数组格式,例如: ["社交", "即时通讯", "年轻人"]

请直接返回JSON数组,不要其他说明:"""

        try:
            logger.info(f"准备调用chat_completion for {app_name}")
            response = await self.chat_completion(prompt, max_tokens=200)
            logger.info(f"chat_completion返回,响应长度: {len(response)}")

            # 移除MiniMax的<think>标签
            if '<think>' in response:
                # 提取</think>之后的内容
                response = response.split('</think>')[-1].strip()

            logger.info(f"处理后的响应: [{response}]")

            # 尝试从响应中提取JSON数组
            import re
            json_match = re.search(r'\[.*?\]', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                tags = json.loads(json_str)
                logger.info(f"成功解析标签: {tags}")
                return tags if isinstance(tags, list) else []
            else:
                logger.warning(f"未找到JSON数组: {response}")
                return []
        except Exception as e:
            logger.error(f"为APP {app_name} 生成标签失败: {e}", exc_info=True)
            return []

    async def generate_media_tags(self, media_name: str, media_type: str = None) -> List[str]:
        """为媒体生成标签"""
        logger.info(f"开始为媒体 {media_name} 生成标签")
        prompt = f"""你是一个媒体分析专家。请为以下媒体生成3-5个精准的标签。

媒体名称: {media_name}
媒体类型: {media_type or '未知'}

要求:
1. 标签应该描述媒体的内容类型、受众群体、传播特点
2. 标签要简洁(2-4个字)
3. 只返回JSON数组格式,例如: ["视频平台", "长视频", "影视剧"]

请直接返回JSON数组,不要其他说明:"""

        try:
            logger.info(f"准备调用chat_completion for {media_name}")
            response = await self.chat_completion(prompt, max_tokens=200)
            logger.info(f"chat_completion返回,响应长度: {len(response)}")

            # 移除MiniMax的<think>标签
            if '<think>' in response:
                # 提取</think>之后的内容
                response = response.split('</think>')[-1].strip()

            logger.info(f"处理后的响应: [{response}]")

            # 尝试从响应中提取JSON数组
            import re
            json_match = re.search(r'\[.*?\]', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                tags = json.loads(json_str)
                logger.info(f"成功解析标签: {tags}")
                return tags if isinstance(tags, list) else []
            else:
                logger.warning(f"未找到JSON数组: {response}")
                return []
        except Exception as e:
            logger.error(f"为媒体 {media_name} 生成标签失败: {e}", exc_info=True)
            return []
    
    async def generate_event_graph(
        self,
        statistics: Dict,
        typical_cases: Dict,
        analysis_focus: str
    ) -> Dict:
        prompt = f"""你是一个广告营销领域的事理图谱专家。

## 任务
基于提供的用户样本统计数据和典型案例，分析因果关系，生成事理图谱。

## 样本统计
{json.dumps(statistics, ensure_ascii=False, indent=2)}

## 典型案例
{json.dumps(typical_cases, ensure_ascii=False, indent=2)}

## 分析重点
{analysis_focus}

## 输出要求
请输出JSON格式的事理图谱：
{{
    "nodes": [
        {{
            "id": "节点ID",
            "type": "行为特征|偏好特征|转化结果|流失原因",
            "name": "节点名称",
            "description": "描述"
        }}
    ],
    "edges": [
        {{
            "from": "源节点ID",
            "to": "目标节点ID",
            "relation": "因果关系描述",
            "probability": 转化概率(0-1),
            "confidence": 置信度(0-1)
        }}
    ],
    "insights": ["关键发现1", "关键发现2"]
}}

## 注意事项
1. 只输出JSON，不要有其他文字
2. 概率要有数据支撑
3. 因果关系要有业务意义
4. 节点ID使用简洁的英文标识
"""
        response = await self.chat_completion(prompt, temperature=0.3)
        return self._parse_json(response)
    
    async def answer_question(
        self,
        question: str,
        context: Dict
    ) -> Dict:
        prompt = f"""你是广告营销领域的智能助手。基于以下知识图谱和事理图谱数据回答用户问题。

## 知识图谱数据
{json.dumps(context.get('knowledge_graph', {}), ensure_ascii=False)}

## 事理图谱数据  
{json.dumps(context.get('event_graph', {}), ensure_ascii=False)}

## 用户问题
{question}

## 回答要求
1. 给出明确结论
2. 标注置信度
3. 列出推理依据
4. 如有必要，给出投放建议

请用专业、简洁的语言回答。
"""
        answer = await self.chat_completion(prompt, temperature=0.5)
        return {
            "question": question,
            "answer": answer,
            "confidence": 0.85,
            "sources": {"knowledge_graph": True, "event_graph": True}
        }
    
    def _parse_json(self, response: str) -> Dict:
        try:
            start = response.find("{")
            end = response.rfind("}") + 1
            json_str = response[start:end]
            return json.loads(json_str)
        except Exception as e:
            print(f"JSON解析失败: {e}, 响应: {response}")
            return {"error": "解析失败", "raw_response": response}
