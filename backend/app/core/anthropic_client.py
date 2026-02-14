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
            logger.info(f"调用LLM: model={model}, max_tokens={max_tokens}, base_url={self.client.base_url}")
            logger.debug(f"LLM请求prompt: {prompt[:200]}...")  # 记录前200字符

            response = await self.client.chat.completions.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[{"role": "user", "content": prompt}]
            )

            result = response.choices[0].message.content if response.choices else ""
            logger.info(f"LLM响应成功: 长度={len(result)}字符")
            logger.debug(f"LLM完整响应: [{result}]")
            return result
        except Exception as e:
            logger.error(f"LLM调用失败: model={model}, base_url={self.client.base_url}, error={str(e)}", exc_info=True)
            raise

    async def generate_app_tags_batch(self, apps: List[Dict]) -> Dict[str, List[str]]:
        """批量为APP生成标签

        Args:
            apps: APP列表，每个元素包含 app_id, app_name, category

        Returns:
            字典，key为app_id，value为标签列表
        """
        logger.info(f"开始批量为 {len(apps)} 个APP生成标签")

        # 构建批量请求的prompt
        app_list_str = "\n".join([
            f"{i+1}. APP名称: {app['app_name']}, 分类: {app.get('category', '未知')}"
            for i, app in enumerate(apps)
        ])

        prompt = f"""你是一个移动应用分析专家。请为以下 {len(apps)} 个APP生成标签。

APP列表:
{app_list_str}

要求:
1. 为每个APP生成3-5个精准的标签
2. 标签应该描述APP的核心功能、用户群体、使用场景
3. 标签要简洁(2-4个中文字)
4. 必须返回JSON对象格式，key为APP名称，value为标签数组

输出格式示例:
{{
  "微信": ["社交", "即时通讯", "移动支付", "朋友圈"],
  "抖音": ["短视频", "娱乐", "内容创作", "年轻人"],
  "淘宝": ["电商", "购物", "网购", "在线支付"],
  "美团": ["外卖", "本地生活", "团购", "配送"],
  "滴滴": ["出行", "打车", "网约车", "交通"]
}}

请严格按照上述JSON格式输出，不要添加任何其他说明文字:"""

        try:
            response = await self.chat_completion(prompt, max_tokens=4000)
            original_response = response
            logger.debug(f"批量APP打标原始响应: [{original_response[:500]}...]")

            # 移除MiniMax的<think>标签
            if '<think>' in response:
                response = response.split('</think>')[-1].strip()
                logger.debug(f"移除<think>后: [{response[:500]}...]")

            # 提取JSON对象
            import re
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                tags_dict = json.loads(json_str)

                # 将APP名称映射回app_id
                result = {}
                for app in apps:
                    app_name = app['app_name']
                    if app_name in tags_dict:
                        tags = tags_dict[app_name]
                        if isinstance(tags, list):
                            result[app['app_id']] = tags
                            logger.info(f"✓ APP [{app_name}] 标签: {tags}")
                        else:
                            result[app['app_id']] = []
                            logger.warning(f"✗ APP [{app_name}] 标签格式错误: {tags}")
                    else:
                        result[app['app_id']] = []
                        logger.warning(f"✗ APP [{app_name}] 未在响应中找到")

                logger.info(f"✓ 批量打标完成: 成功 {len([v for v in result.values() if v])}/{len(apps)}")
                return result
            else:
                logger.error(f"✗ 批量APP打标未找到JSON对象, 原始响应=[{original_response}], 处理后=[{response}]")
                return {app['app_id']: [] for app in apps}

        except json.JSONDecodeError as e:
            logger.error(f"✗ 批量APP打标JSON解析失败: {e}, 响应=[{response[:500]}...]", exc_info=True)
            return {app['app_id']: [] for app in apps}
        except Exception as e:
            logger.error(f"✗ 批量APP打标异常: {type(e).__name__}: {str(e)}", exc_info=True)
            return {app['app_id']: [] for app in apps}

    async def generate_media_tags_batch(self, media_list: List[Dict]) -> Dict[str, List[str]]:
        """批量为媒体生成标签

        Args:
            media_list: 媒体列表，每个元素包含 media_id, media_name, media_type

        Returns:
            字典，key为media_id，value为标签列表
        """
        logger.info(f"开始批量为 {len(media_list)} 个媒体生成标签")

        # 构建批量请求的prompt
        media_list_str = "\n".join([
            f"{i+1}. 媒体名称: {media['media_name']}, 类型: {media.get('media_type', '未知')}"
            for i, media in enumerate(media_list)
        ])

        prompt = f"""你是一个媒体分析专家。请为以下 {len(media_list)} 个媒体生成标签。

媒体列表:
{media_list_str}

要求:
1. 为每个媒体生成3-5个精准的标签
2. 标签应该描述媒体的内容类型、受众群体、传播特点
3. 标签要简洁(2-4个中文字)
4. 必须返回JSON对象格式，key为媒体名称，value为标签数组

输出格式示例:
{{
  "爱奇艺": ["视频平台", "长视频", "影视剧", "综艺"],
  "B站": ["视频社区", "二次元", "年轻人", "UP主"],
  "微博": ["社交媒体", "资讯", "热点", "明星"],
  "知乎": ["问答社区", "知识分享", "专业", "深度"],
  "小红书": ["生活方式", "种草", "女性", "美妆"]
}}

请严格按照上述JSON格式输出，不要添加任何其他说明文字:"""

        try:
            response = await self.chat_completion(prompt, max_tokens=4000)
            original_response = response
            logger.debug(f"批量媒体打标原始响应: [{original_response[:500]}...]")

            # 移除MiniMax的<think>标签
            if '<think>' in response:
                response = response.split('</think>')[-1].strip()
                logger.debug(f"移除<think>后: [{response[:500]}...]")

            # 提取JSON对象
            import re
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                tags_dict = json.loads(json_str)

                # 将媒体名称映射回media_id
                result = {}
                for media in media_list:
                    media_name = media['media_name']
                    if media_name in tags_dict:
                        tags = tags_dict[media_name]
                        if isinstance(tags, list):
                            result[media['media_id']] = tags
                            logger.info(f"✓ 媒体 [{media_name}] 标签: {tags}")
                        else:
                            result[media['media_id']] = []
                            logger.warning(f"✗ 媒体 [{media_name}] 标签格式错误: {tags}")
                    else:
                        result[media['media_id']] = []
                        logger.warning(f"✗ 媒体 [{media_name}] 未在响应中找到")

                logger.info(f"✓ 批量打标完成: 成功 {len([v for v in result.values() if v])}/{len(media_list)}")
                return result
            else:
                logger.error(f"✗ 批量媒体打标未找到JSON对象, 原始响应=[{original_response}], 处理后=[{response}]")
                return {media['media_id']: [] for media in media_list}

        except json.JSONDecodeError as e:
            logger.error(f"✗ 批量媒体打标JSON解析失败: {e}, 响应=[{response[:500]}...]", exc_info=True)
            return {media['media_id']: [] for media in media_list}
        except Exception as e:
            logger.error(f"✗ 批量媒体打标异常: {type(e).__name__}: {str(e)}", exc_info=True)
            return {media['media_id']: [] for media in media_list}

    async def generate_app_tags(self, app_name: str, category: str = None) -> List[str]:
        """为APP生成标签"""
        logger.info(f"开始为APP [{app_name}] 生成标签, 分类=[{category}]")
        prompt = f"""你是一个移动应用分析专家。请为以下APP生成3-5个精准的标签。

APP名称: {app_name}
分类: {category or '未知'}

要求:
1. 标签应该描述APP的核心功能、用户群体、使用场景
2. 标签要简洁(2-4个字)
3. 只返回JSON数组格式,例如: ["社交", "即时通讯", "年轻人"]

请直接返回JSON数组,不要其他说明:"""

        try:
            response = await self.chat_completion(prompt, max_tokens=200)
            original_response = response
            logger.debug(f"APP [{app_name}] 原始LLM响应: [{original_response}]")

            # 移除MiniMax的<think>标签
            if '<think>' in response:
                response = response.split('</think>')[-1].strip()
                logger.debug(f"APP [{app_name}] 移除<think>后: [{response}]")

            # 尝试从响应中提取JSON数组
            import re
            json_match = re.search(r'\[.*?\]', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                tags = json.loads(json_str)
                logger.info(f"✓ APP [{app_name}] 成功生成标签: {tags}")
                return tags if isinstance(tags, list) else []
            else:
                logger.warning(f"✗ APP [{app_name}] 未找到JSON数组, 原始响应=[{original_response}], 处理后=[{response}]")
                return []
        except json.JSONDecodeError as e:
            logger.error(f"✗ APP [{app_name}] JSON解析失败: {e}, 响应内容=[{response}]", exc_info=True)
            return []
        except Exception as e:
            logger.error(f"✗ APP [{app_name}] 生成标签异常: {type(e).__name__}: {str(e)}", exc_info=True)
            return []

    async def generate_media_tags(self, media_name: str, media_type: str = None) -> List[str]:
        """为媒体生成标签"""
        logger.info(f"开始为媒体 [{media_name}] 生成标签, 类型=[{media_type}]")
        prompt = f"""你是一个媒体分析专家。请为以下媒体生成3-5个精准的标签。

媒体名称: {media_name}
媒体类型: {media_type or '未知'}

要求:
1. 标签应该描述媒体的内容类型、受众群体、传播特点
2. 标签要简洁(2-4个字)
3. 只返回JSON数组格式,例如: ["视频平台", "长视频", "影视剧"]

请直接返回JSON数组,不要其他说明:"""

        try:
            response = await self.chat_completion(prompt, max_tokens=200)
            original_response = response
            logger.debug(f"媒体 [{media_name}] 原始LLM响应: [{original_response}]")

            # 移除MiniMax的<think>标签
            if '<think>' in response:
                response = response.split('</think>')[-1].strip()
                logger.debug(f"媒体 [{media_name}] 移除<think>后: [{response}]")

            # 尝试从响应中提取JSON数组
            import re
            json_match = re.search(r'\[.*?\]', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                tags = json.loads(json_str)
                logger.info(f"✓ 媒体 [{media_name}] 成功生成标签: {tags}")
                return tags if isinstance(tags, list) else []
            else:
                logger.warning(f"✗ 媒体 [{media_name}] 未找到JSON数组, 原始响应=[{original_response}], 处理后=[{response}]")
                return []
        except json.JSONDecodeError as e:
            logger.error(f"✗ 媒体 [{media_name}] JSON解析失败: {e}, 响应内容=[{response}]", exc_info=True)
            return []
        except Exception as e:
            logger.error(f"✗ 媒体 [{media_name}] 生成标签异常: {type(e).__name__}: {str(e)}", exc_info=True)
            return []

    async def abstract_events_batch(self, user_behaviors: Dict[str, List[Dict]]) -> Dict[str, List[Dict]]:
        """批量抽象用户行为为事件

        Args:
            user_behaviors: {
                "user_001": [
                    {"timestamp": "2026-01-01 10:00", "action": "visit_poi", "poi_id": "4s_store_001", "duration": 7200},
                    {"timestamp": "2026-01-01 14:00", "action": "search", "item_id": "宝马7系价格"},
                    ...
                ],
                "user_002": [...]
            }

        Returns:
            {
                "user_001": [
                    {
                        "event_type": "看车",
                        "timestamp": "2026-01-01 10:00",
                        "context": {"poi_type": "4S店", "duration": "2小时"}
                    },
                    {
                        "event_type": "关注豪华轿车",
                        "timestamp": "2026-01-01 14:00",
                        "context": {"brand": "宝马", "model": "7系"}
                    }
                ],
                "user_002": [...]
            }
        """
        logger.info(f"开始批量抽象 {len(user_behaviors)} 个用户的行为为事件")

        # 构建批量请求的prompt
        user_behaviors_str = ""
        for user_id, behaviors in user_behaviors.items():
            user_behaviors_str += f"\n用户 {user_id}:\n"
            for behavior in behaviors:
                timestamp = behavior.get("timestamp", "")
                action = behavior.get("action", "")

                # 格式化行为描述
                if action == "visit_poi":
                    poi_id = behavior.get("poi_id", "")
                    duration = behavior.get("duration", 0)
                    duration_hours = duration // 3600 if duration else 0
                    user_behaviors_str += f"  - {timestamp} 在{poi_id}停留{duration_hours}小时\n"
                elif action == "search":
                    query = behavior.get("item_id", "")
                    user_behaviors_str += f"  - {timestamp} 搜索:{query}\n"
                elif action == "view":
                    item = behavior.get("item_id", "")
                    user_behaviors_str += f"  - {timestamp} 浏览{item}\n"
                elif action == "use_app":
                    app = behavior.get("app_id", "")
                    user_behaviors_str += f"  - {timestamp} 使用{app}\n"
                else:
                    user_behaviors_str += f"  - {timestamp} {action}\n"

        prompt = f"""你是一个用户行为分析专家。请将以下用户的原始行为数据抽象为高层次的事件。

用户行为数据:
{user_behaviors_str}

要求:
1. 将细粒度的行为抽象为有业务意义的事件
2. 事件类型要简洁(2-6个中文字)
3. 保留时间信息
4. 提取关键上下文信息
5. 必须返回JSON对象格式

抽象规则示例:
- "在4S店停留2小时" → "看车"
- "使用挂号APP" → "医疗需求"
- "搜索:马尔代夫自由行" → "关注海岛游"
- "浏览宝马7系+点击配置+对比价格" → "关注豪华轿车"

输出格式示例:
{{
  "user_001": [
    {{
      "event_type": "看车",
      "timestamp": "2026-01-01 10:00",
      "context": {{"poi_type": "4S店", "duration": "2小时"}}
    }},
    {{
      "event_type": "关注豪华轿车",
      "timestamp": "2026-01-01 14:00",
      "context": {{"brand": "宝马", "model": "7系"}}
    }}
  ],
  "user_002": [...]
}}

请严格按照上述JSON格式输出,不要添加任何其他说明文字:"""

        try:
            response = await self.chat_completion(prompt, max_tokens=4000)
            original_response = response
            logger.debug(f"批量事件抽象原始响应: [{original_response[:500]}...]")

            # 移除MiniMax的<think>标签
            if '<think>' in response:
                response = response.split('</think>')[-1].strip()
                logger.debug(f"移除<think>后: [{response[:500]}...]")

            # 提取JSON对象
            import re
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                events_dict = json.loads(json_str)

                # 验证结果格式
                result = {}
                for user_id in user_behaviors.keys():
                    if user_id in events_dict:
                        events = events_dict[user_id]
                        if isinstance(events, list):
                            result[user_id] = events
                            logger.info(f"✓ 用户 [{user_id}] 抽象了 {len(events)} 个事件")
                        else:
                            result[user_id] = []
                            logger.warning(f"✗ 用户 [{user_id}] 事件格式错误: {events}")
                    else:
                        result[user_id] = []
                        logger.warning(f"✗ 用户 [{user_id}] 未在响应中找到")

                logger.info(f"✓ 批量事件抽象完成: 成功 {len([v for v in result.values() if v])}/{len(user_behaviors)}")
                return result
            else:
                logger.error(f"✗ 批量事件抽象未找到JSON对象, 原始响应=[{original_response}], 处理后=[{response}]")
                return {user_id: [] for user_id in user_behaviors.keys()}

        except json.JSONDecodeError as e:
            logger.error(f"✗ 批量事件抽象JSON解析失败: {e}, 响应=[{response[:500]}...]", exc_info=True)
            return {user_id: [] for user_id in user_behaviors.keys()}
        except Exception as e:
            logger.error(f"✗ 批量事件抽象异常: {type(e).__name__}: {str(e)}", exc_info=True)
            return {user_id: [] for user_id in user_behaviors.keys()}
    
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
