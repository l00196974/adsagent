"""
事理图谱服务 - 基于高频子序列挖掘结果生成事理图谱
"""
import json
import logging
import re
import sqlite3
from typing import Dict, List, Optional
from pathlib import Path

from app.core.openai_client import OpenAIClient
from app.core.persistence import persistence

logger = logging.getLogger(__name__)


class CausalGraphService:
    """事理图谱服务"""

    def __init__(self, llm_client: OpenAIClient):
        self.llm = llm_client
        self.db_path = Path("data/graph.db")

    async def generate_from_patterns(
        self,
        pattern_ids: List[int] = None,
        analysis_focus: str = "comprehensive",
        graph_name: str = None
    ) -> Dict:
        """基于高频模式生成事理图谱

        Args:
            pattern_ids: 选择的模式ID列表，None表示使用所有模式
            analysis_focus: 分析重点（comprehensive/conversion/churn/profile）
            graph_name: 图谱名称

        Returns:
            生成的事理图谱数据
        """
        logger.info(f"开始生成事理图谱: pattern_ids={pattern_ids}, focus={analysis_focus}")

        # 1. 加载高频模式数据
        patterns = self._load_patterns(pattern_ids)
        if not patterns:
            raise ValueError("未找到高频模式数据")

        logger.info(f"加载了 {len(patterns)} 个高频模式")

        # 2. 提取用户示例和画像数据
        user_examples = self._extract_user_examples(patterns)
        user_profiles = self._extract_user_profiles(user_examples)

        logger.info(f"提取了 {len(user_examples)} 个用户示例")

        # 3. 构建LLM Prompt
        prompt = self._build_prompt(patterns, user_examples, user_profiles, analysis_focus)

        # 4. 调用LLM生成事理图谱（使用流式调用）
        logger.info("调用LLM生成事理图谱...")
        stream_generator = self.llm.chat_completion(prompt, max_tokens=8000, temperature=0.3)
        response = await self.llm._collect_stream_response(stream_generator)

        # 5. 解析JSON结果
        graph_data = self._parse_graph_response(response)

        if "error" in graph_data:
            raise ValueError(f"解析事理图谱失败: {graph_data['error']}")

        # 6. 保存到数据库
        if not graph_name:
            graph_name = f"事理图谱_{analysis_focus}_{len(patterns)}模式"

        graph_id = self._save_graph(
            graph_name=graph_name,
            analysis_focus=analysis_focus,
            source_pattern_ids=pattern_ids or [],
            total_users=len(user_examples),
            total_patterns=len(patterns),
            graph_data=graph_data
        )

        logger.info(f"事理图谱生成完成: graph_id={graph_id}")

        return {
            "graph_id": graph_id,
            "graph_name": graph_name,
            "nodes_count": len(graph_data.get("nodes", [])),
            "edges_count": len(graph_data.get("edges", [])),
            "insights": graph_data.get("insights", []),
            "graph_data": graph_data
        }

    def _load_patterns(self, pattern_ids: Optional[List[int]]) -> List[Dict]:
        """加载高频模式数据"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                if pattern_ids:
                    placeholders = ','.join('?' * len(pattern_ids))
                    cursor.execute(
                        f"""SELECT id, pattern_id, pattern_sequence, support, confidence,
                                  occurrence_count, user_count
                           FROM frequent_patterns
                           WHERE id IN ({placeholders})""",
                        pattern_ids
                    )
                else:
                    cursor.execute(
                        """SELECT id, pattern_id, pattern_sequence, support, confidence,
                                  occurrence_count, user_count
                           FROM frequent_patterns
                           ORDER BY support DESC
                           LIMIT 50"""
                    )

                patterns = []
                for row in cursor.fetchall():
                    patterns.append({
                        "id": row[0],
                        "pattern_id": row[1],
                        "pattern_sequence": row[2],
                        "support": row[3],
                        "confidence": row[4],
                        "occurrence_count": row[5],
                        "user_count": row[6]
                    })
                return patterns
        except Exception as e:
            logger.error(f"加载高频模式失败: {e}", exc_info=True)
            return []

    def _extract_user_examples(self, patterns: List[Dict]) -> List[Dict]:
        """从模式中提取用户示例"""
        # 简化实现：从event_sequences表中提取用户序列
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """SELECT user_id, sequence, start_time, end_time
                       FROM event_sequences
                       LIMIT 100"""
                )

                examples = []
                for row in cursor.fetchall():
                    examples.append({
                        "user_id": row[0],
                        "sequence": row[1],
                        "start_time": row[2],
                        "end_time": row[3]
                    })
                return examples
        except Exception as e:
            logger.error(f"提取用户示例失败: {e}", exc_info=True)
            return []

    def _extract_user_profiles(self, user_examples: List[Dict]) -> Dict[str, Dict]:
        """提取用户画像数据"""
        if not user_examples:
            return {}

        try:
            user_ids = [ex["user_id"] for ex in user_examples]
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                placeholders = ','.join('?' * len(user_ids))
                cursor.execute(
                    f"""SELECT user_id, age, gender, city, occupation, properties
                       FROM user_profiles
                       WHERE user_id IN ({placeholders})""",
                    user_ids
                )

                profiles = {}
                for row in cursor.fetchall():
                    profiles[row[0]] = {
                        "age": row[1],
                        "gender": row[2],
                        "city": row[3],
                        "occupation": row[4],
                        "properties": json.loads(row[5]) if row[5] else {}
                    }
                return profiles
        except Exception as e:
            logger.error(f"提取用户画像失败: {e}", exc_info=True)
            return {}

    def _build_prompt(
        self,
        patterns: List[Dict],
        user_examples: List[Dict],
        user_profiles: Dict[str, Dict],
        analysis_focus: str
    ) -> str:
        """构建LLM Prompt"""
        # 格式化高频模式
        patterns_text = ""
        for i, pattern in enumerate(patterns[:20], 1):  # 限制20个模式
            patterns_text += f"{i}. 模式: {pattern['pattern_sequence']}\n"
            patterns_text += f"   支持度: {pattern['support']:.2%}, "
            patterns_text += f"用户数: {pattern['user_count']}\n"

        # 格式化用户示例
        examples_text = ""
        for i, example in enumerate(user_examples[:10], 1):  # 限制10个示例
            examples_text += f"{i}. 用户 {example['user_id']}: {example['sequence']}\n"
            if example['user_id'] in user_profiles:
                profile = user_profiles[example['user_id']]
                examples_text += f"   画像: {profile.get('age')}岁, {profile.get('gender')}, {profile.get('occupation')}\n"

        # 分析重点描述
        focus_desc = {
            "comprehensive": "全面分析用户行为模式、转化路径和流失原因",
            "conversion": "重点分析用户转化路径和影响转化的关键因素",
            "churn": "重点分析用户流失原因和预警信号",
            "profile": "重点分析不同用户画像的行为差异"
        }.get(analysis_focus, "全面分析")

        prompt = f"""你是一个广告营销领域的事理图谱专家。请基于以下高频事件序列模式，生成一个完整的事理图谱。

## 高频事件序列模式

{patterns_text}

## 用户示例数据

{examples_text}

## 分析重点

{focus_desc}

## 输出要求

请输出JSON格式的事理图谱，**必须包含三种类型的节点**：

1. **event（事件节点）**：用户的行为事件，如"浏览车型"、"对比车型"、"查看详情"
2. **feature（特征节点）**：用户的画像特征，如"男性"、"30-40岁"、"互联网从业者"
3. **result（结果节点）**：最终的转化结果或行为模式，如"购买意向"、"多次浏览"、"对比行为"、"流失"

**图谱结构要求**：
- 事件节点之间用 sequential 关系连接（表示行为序列）
- 特征节点到事件节点用 causal 关系连接（表示特征影响行为）
- 事件节点到结果节点用 causal 或 conditional 关系连接（表示行为导致结果）
- **至少包含2个结果节点**，展示不同的转化路径

输出格式示例：

{{
    "nodes": [
        {{"id": "event_browse_car", "type": "event", "name": "浏览车型", "description": "用户浏览车型列表"}},
        {{"id": "event_compare_car", "type": "event", "name": "对比车型", "description": "用户对比不同车型"}},
        {{"id": "feature_male", "type": "feature", "name": "男性用户", "description": "用户性别为男性"}},
        {{"id": "feature_high_income", "type": "feature", "name": "高收入", "description": "月收入2万以上"}},
        {{"id": "result_purchase_intent", "type": "result", "name": "购买意向", "description": "表现出明确的购买意向"}},
        {{"id": "result_churn", "type": "result", "name": "流失", "description": "用户停止互动"}}
    ],
    "edges": [
        {{"from": "event_browse_car", "to": "event_compare_car", "relation_type": "sequential", "relation_desc": "浏览后进行对比", "probability": 0.65, "confidence": 0.80, "support_count": 130}},
        {{"from": "feature_male", "to": "event_browse_car", "relation_type": "causal", "relation_desc": "男性用户更倾向浏览车型", "probability": 0.75, "confidence": 0.85, "support_count": 150}},
        {{"from": "event_compare_car", "to": "result_purchase_intent", "relation_type": "causal", "relation_desc": "对比行为表明购买意向", "probability": 0.45, "confidence": 0.70, "support_count": 90}},
        {{"from": "event_browse_car", "to": "result_churn", "relation_type": "conditional", "relation_desc": "仅浏览未深入则可能流失", "probability": 0.30, "confidence": 0.60, "support_count": 60}}
    ],
    "insights": [
        "男性高收入用户从浏览到购买的转化率为15%",
        "对比行为是购买意向的强信号，转化率达45%"
    ]
}}

## 关系类型说明

1. **sequential（顺承关系）**：事件A之后通常发生事件B
2. **causal（因果关系）**：特征/事件A导致事件/结果B
3. **conditional（条件关系）**：在特定条件下发生

## 注意事项

1. 节点ID格式：event_xxx, feature_xxx, result_xxx
2. **必须包含至少2个result类型节点**
3. **必须有边连接到result节点**，展示完整的因果链
4. 概率和置信度基于实际数据
5. 不要创建自环边（from和to相同）
6. 只输出JSON，不要有其他文字
"""
        return prompt

    def _parse_graph_response(self, response: str) -> Dict:
        """解析LLM返回的事理图谱JSON"""
        try:
            # 移除MiniMax的<think>标签
            if '<think>' in response:
                response = response.split('</think>')[-1].strip()

            # 移除markdown代码块
            if '```json' in response:
                response = response.split('```json')[1].split('```')[0].strip()
            elif '```' in response:
                parts = response.split('```')
                if len(parts) >= 3:
                    response = parts[1].strip()

            # 提取JSON对象
            start = response.find('{')
            end = response.rfind('}') + 1
            if start == -1 or end == 0:
                return {"error": "未找到JSON对象"}

            json_str = response[start:end]
            graph_data = json.loads(json_str)

            # 验证必需字段
            if "nodes" not in graph_data or "edges" not in graph_data:
                return {"error": "缺少必需字段nodes或edges"}

            logger.info(f"成功解析事理图谱: {len(graph_data['nodes'])}个节点, {len(graph_data['edges'])}条边")
            return graph_data

        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {e}, 响应: {response[:500]}", exc_info=True)
            return {"error": f"JSON解析失败: {str(e)}", "raw_response": response[:500]}
        except Exception as e:
            logger.error(f"解析事理图谱失败: {e}", exc_info=True)
            return {"error": str(e)}

    def _save_graph(
        self,
        graph_name: str,
        analysis_focus: str,
        source_pattern_ids: List[int],
        total_users: int,
        total_patterns: int,
        graph_data: Dict
    ) -> int:
        """保存事理图谱到数据库"""
        try:
            # 保存主图谱记录
            graph_id = persistence.save_causal_graph(
                graph_name=graph_name,
                analysis_focus=analysis_focus,
                source_pattern_ids=source_pattern_ids,
                total_users=total_users,
                total_patterns=total_patterns,
                graph_data=graph_data,
                insights=graph_data.get("insights", [])
            )

            if graph_id == -1:
                raise ValueError("保存事理图谱失败")

            # 保存节点
            nodes = graph_data.get("nodes", [])
            if nodes:
                persistence.save_causal_graph_nodes(graph_id, nodes)

            # 保存边
            edges = graph_data.get("edges", [])
            if edges:
                persistence.save_causal_graph_edges(graph_id, edges)

            return graph_id

        except Exception as e:
            logger.error(f"保存事理图谱失败: {e}", exc_info=True)
            raise

    async def get_graph_by_id(self, graph_id: int) -> Dict:
        """获取指定的事理图谱"""
        graph = persistence.get_causal_graph(graph_id)
        if not graph:
            raise ValueError(f"未找到事理图谱: {graph_id}")
        return graph

    async def list_graphs(self, limit: int = 20, offset: int = 0) -> Dict:
        """获取事理图谱列表"""
        graphs = persistence.list_causal_graphs(limit, offset)
        return {
            "graphs": graphs,
            "total": len(graphs),
            "limit": limit,
            "offset": offset
        }

    async def delete_graph(self, graph_id: int):
        """删除事理图谱"""
        success = persistence.delete_causal_graph(graph_id)
        if not success:
            raise ValueError(f"删除事理图谱失败: {graph_id}")

    async def answer_question_with_graph(
        self,
        graph_id: int,
        question: str,
        user_context: Dict = None
    ) -> Dict:
        """基于事理图谱回答问题"""
        # 获取事理图谱
        graph = await self.get_graph_by_id(graph_id)

        # 构建上下文
        context = {
            "graph_name": graph["graph_name"],
            "analysis_focus": graph["analysis_focus"],
            "graph_data": graph["graph_data"],
            "insights": graph["insights"]
        }

        if user_context:
            context["user_context"] = user_context

        # 构建prompt
        prompt = f"""你是广告营销领域的智能助手。基于以下事理图谱数据回答用户问题。

## 事理图谱信息

图谱名称: {context['graph_name']}
分析重点: {context['analysis_focus']}

节点数量: {len(context['graph_data'].get('nodes', []))}
边数量: {len(context['graph_data'].get('edges', []))}

关键洞察:
{chr(10).join(f"- {insight}" for insight in context['insights'])}

图谱数据:
{json.dumps(context['graph_data'], ensure_ascii=False, indent=2)}

## 用户问题

{question}

## 回答要求

1. 给出明确结论
2. 基于图谱数据进行推理
3. 列出推理依据
4. 如有必要，给出投放建议
5. 标注置信度（0-1）

请用专业、简洁的语言回答。
"""

        # 调用LLM（使用流式调用）
        stream_generator = self.llm.chat_completion(prompt, max_tokens=2000, temperature=0.5)
        answer = await self.llm._collect_stream_response(stream_generator)

        return {
            "question": question,
            "answer": answer,
            "graph_id": graph_id,
            "graph_name": graph["graph_name"]
        }

    async def generate_from_patterns_stream(
        self,
        pattern_ids: Optional[List[int]] = None,
        analysis_focus: str = "comprehensive",
        graph_name: Optional[str] = None
    ):
        """基于高频模式生成事理图谱（流式）

        Yields:
            字典格式的事件流：
            - type: 'progress' | 'content' | 'result'
            - message: 进度消息
            - content: LLM 输出内容（流式）
            - data: 最终结果数据
        """
        try:
            # 1. 加载高频模式数据
            yield {"type": "progress", "message": "正在加载高频模式数据..."}
            patterns = self._load_patterns(pattern_ids)
            if not patterns:
                raise ValueError("未找到高频模式数据")

            yield {"type": "progress", "message": f"已加载 {len(patterns)} 个高频模式"}

            # 2. 提取用户示例和画像数据
            yield {"type": "progress", "message": "正在提取用户示例..."}
            user_examples = self._extract_user_examples(patterns)
            user_profiles = self._extract_user_profiles(user_examples)

            yield {"type": "progress", "message": f"已提取 {len(user_examples)} 个用户示例"}

            # 3. 构建LLM Prompt
            yield {"type": "progress", "message": "正在构建分析提示词..."}
            prompt = self._build_prompt(patterns, user_examples, user_profiles, analysis_focus)

            # 4. 流式调用LLM生成事理图谱
            yield {"type": "progress", "message": "正在调用 AI 生成事理图谱..."}

            full_response = ""
            async for chunk in self.llm.chat_completion(prompt, max_tokens=8000, temperature=0.3):
                full_response += chunk
                yield {"type": "content", "content": chunk}

            # 5. 解析JSON结果
            yield {"type": "progress", "message": "正在解析生成结果..."}
            graph_data = self._parse_graph_response(full_response)

            if "error" in graph_data:
                raise ValueError(f"解析事理图谱失败: {graph_data['error']}")

            # 6. 保存到数据库
            yield {"type": "progress", "message": "正在保存到数据库..."}
            if not graph_name:
                graph_name = f"事理图谱_{analysis_focus}_{len(patterns)}模式"

            graph_id = self._save_graph(
                graph_name=graph_name,
                analysis_focus=analysis_focus,
                source_pattern_ids=pattern_ids or [],
                total_users=len(user_examples),
                total_patterns=len(patterns),
                graph_data=graph_data
            )

            # 7. 返回最终结果
            yield {
                "type": "result",
                "data": {
                    "graph_id": graph_id,
                    "graph_name": graph_name,
                    "nodes_count": len(graph_data.get("nodes", [])),
                    "edges_count": len(graph_data.get("edges", [])),
                    "insights": graph_data.get("insights", []),
                    "graph_data": graph_data
                }
            }

        except Exception as e:
            logger.error(f"流式生成事理图谱失败: {e}", exc_info=True)
            yield {"type": "error", "message": str(e)}

