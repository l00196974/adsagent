import anthropic
from typing import Dict, List
import json
from app.core.config import settings

class AnthropicClient:
    def __init__(self):
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
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
        response = self.client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text
    
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
