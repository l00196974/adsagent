from typing import Dict, List
import json
import httpx
import asyncio
from app.core.config import settings
from app.core.logger import app_logger as logger

class OpenAIClient:
    def __init__(self):
        # 使用 httpx 直接调用 API,避免 SDK 兼容性问题
        self.api_key = settings.openai_api_key
        self.base_url = settings.openai_base_url or "https://api.openai.com/v1"
        self.primary_model = settings.primary_model
        self.reasoning_model = settings.reasoning_model
        logger.info(f"使用 API: {self.base_url}")

    def _format_enriched_behavior(self, behavior: Dict) -> str:
        """将丰富后的行为数据格式化为适合 LLM 理解的文本

        Args:
            behavior: 丰富后的行为数据

        Returns:
            格式化的文本描述
        """
        action = behavior.get("action", "")
        timestamp = behavior.get("timestamp", "")
        duration = behavior.get("duration", 0)

        # 构建行为描述 - 在前面加上 action 标识
        parts = [f"[action={action}]", timestamp]

        if action == "visit_poi" and "poi_info" in behavior:
            poi = behavior["poi_info"]
            duration_hours = duration // 3600 if duration else 0
            parts.append(f"在{poi['poi_name']}({poi['poi_type']})停留{duration_hours}小时")

        elif action == "use_app" and "app_info" in behavior:
            app = behavior["app_info"]
            duration_min = duration // 60 if duration else 0
            tags_str = ",".join(app["tags"][:3]) if app["tags"] else ""
            if tags_str:
                parts.append(f"使用{app['app_name']}({tags_str})应用{duration_min}分钟")
            else:
                parts.append(f"使用{app['app_name']}应用{duration_min}分钟")

        elif action == "browse":
            media = behavior.get("media_info", {})
            item = behavior.get("item_info", {})
            media_name = media.get("media_name", behavior.get("media_id", ""))
            item_name = item.get("item_name", behavior.get("item_id", ""))
            parts.append(f"在{media_name}浏览{item_name}")

        elif action == "search":
            query = behavior.get("item_id", "")
            app = behavior.get("app_info", {})
            app_name = app.get("app_name", "")
            if app_name:
                parts.append(f"在{app_name}搜索:{query}")
            else:
                parts.append(f"搜索:{query}")

        elif action == "purchase" and "item_info" in behavior:
            item = behavior["item_info"]
            poi_id = behavior.get("poi_id", "")
            if poi_id:
                parts.append(f"购买{item['item_name']}在{poi_id}")
            else:
                parts.append(f"购买{item['item_name']}")

        elif action == "add_cart" and "item_info" in behavior:
            item = behavior["item_info"]
            app_info = behavior.get("app_info", {})
            app_name = app_info.get("app_name", behavior.get("app_id", ""))
            if app_name:
                parts.append(f"将{item['item_name']}加入购物车在{app_name}")
            else:
                parts.append(f"将{item['item_name']}加入购物车")

        else:
            # 默认格式
            parts.append(action)
            if "item_info" in behavior:
                parts.append(behavior["item_info"]["item_name"])
            elif behavior.get("item_id"):
                parts.append(behavior["item_id"])

        return " ".join(parts)

    async def summarize_behavior_sequence(
        self,
        behaviors: List[Dict],
        user_profile: Dict = None
    ) -> str:
        """总结用户行为序列

        Args:
            behaviors: 丰富后的行为数据列表
            user_profile: 用户画像(可选)

        Returns:
            行为序列的自然语言总结
        """
        # 构建行为描述
        behavior_lines = []
        for behavior in behaviors:
            formatted = self._format_enriched_behavior(behavior)
            behavior_lines.append(f"  - {formatted}")

        behavior_text = "\n".join(behavior_lines)

        # 构建用户画像描述
        profile_text = ""
        if user_profile:
            profile_parts = []
            if user_profile.get("age"):
                profile_parts.append(f"{user_profile['age']}岁")
            if user_profile.get("gender"):
                profile_parts.append(user_profile['gender'])
            if user_profile.get("occupation"):
                profile_parts.append(user_profile['occupation'])
            if user_profile.get("city"):
                profile_parts.append(f"来自{user_profile['city']}")

            if profile_parts:
                profile_text = f"\n用户画像: {', '.join(profile_parts)}"

        prompt = f"""你是一个用户行为分析专家。请用2-3句话总结以下用户的行为序列,帮助理解用户的兴趣和意图。
{profile_text}

用户行为序列:
{behavior_text}

要求:
1. 用自然、流畅的语言描述
2. 突出关键行为模式和用户意图
3. 2-3句话,简洁明了
4. 直接返回总结文本,不要其他说明

总结:"""

        try:
            # 使用流式调用
            stream_generator = self.chat_completion(prompt, max_tokens=300, temperature=0.5)
            summary = await self._collect_stream_response(stream_generator)

            # 移除可能的 <think> 标签
            if '<think>' in summary:
                summary = summary.split('</think>')[-1].strip()

            # 移除可能的 markdown 代码块
            if '```' in summary:
                summary = summary.split('```')[0].strip()

            logger.info(f"行为序列总结生成成功: {summary[:100]}...")
            return summary.strip()
        except Exception as e:
            logger.error(f"行为序列总结生成失败: {e}", exc_info=True)
            return "无法生成行为总结"

    async def chat_completion(
        self,
        prompt: str,
        model: str = None,
        max_tokens: int = 4000,
        temperature: float = 0.3
    ):
        """调用LLM进行对话补全（流式调用）

        Args:
            prompt: 提示词
            model: 模型名称（可选，默认使用配置的模型）
            max_tokens: 最大token数
            temperature: 温度参数

        Returns:
            返回异步生成器，逐块yield响应内容
        """
        model = model or self.primary_model

        # 计算超时时间
        is_batch_operation = "批量" in prompt or "用户 user_" in prompt or len(prompt) > 5000
        if is_batch_operation:
            timeout_seconds = 300.0  # 批量操作：5分钟
        elif max_tokens >= 8000:
            timeout_seconds = 300.0  # 大量输出：5分钟
        elif max_tokens > 2000:
            timeout_seconds = 180.0  # 中等输出：3分钟
        else:
            timeout_seconds = 60.0   # 小量输出：1分钟

        logger.info(f"调用LLM: model={model}, max_tokens={max_tokens}, stream=True, base_url={self.base_url}")
        logger.debug(f"LLM请求prompt: {prompt[:200]}...")

        # 直接yield，使chat_completion成为async generator
        async for chunk in self._stream_chat(prompt, model, max_tokens, temperature, timeout_seconds):
            yield chunk

    async def _collect_stream_response(self, stream_generator):
        """收集流式响应为完整字符串的辅助方法"""
        response = ""
        async for chunk in stream_generator:
            response += chunk
        return response

    async def _stream_chat_wrapper(self, prompt: str, model: str, max_tokens: int, temperature: float, timeout_seconds: float):
        """Wrapper for stream chat to ensure it returns an async generator"""
        async for chunk in self._stream_chat(prompt, model, max_tokens, temperature, timeout_seconds):
            yield chunk

    async def _stream_chat(self, prompt: str, model: str, max_tokens: int, temperature: float, timeout_seconds: float):
        """流式调用 LLM"""
        # 为流式响应配置超时：连接超时30s，读取超时使用传入的timeout_seconds
        timeout_config = httpx.Timeout(
            connect=30.0,  # 连接超时
            read=timeout_seconds,  # 读取超时（流式响应可能很长）
            write=30.0,  # 写入超时
            pool=30.0   # 连接池超时
        )
        client = httpx.AsyncClient(timeout=timeout_config)
        try:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "stream": True
                }
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]  # 移除 "data: " 前缀
                        if data_str == "[DONE]":
                            break
                        try:
                            data = json.loads(data_str)
                            if "choices" in data and len(data["choices"]) > 0:
                                delta = data["choices"][0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    yield content
                        except json.JSONDecodeError:
                            continue
        except httpx.ReadError as e:
            logger.error(f"LLM流式读取错误: {e}", exc_info=True)
            raise Exception(f"LLM API读取超时或网络中断，请重试")
        except httpx.TimeoutException as e:
            logger.error(f"LLM调用超时: {e}", exc_info=True)
            raise Exception(f"LLM API调用超时（{timeout_seconds}秒），请重试")
        finally:
            await client.aclose()

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
            # 使用流式调用
            stream_generator = self.chat_completion(prompt, max_tokens=4000)
            response = await self._collect_stream_response(stream_generator)
            original_response = response
            logger.debug(f"批量APP打标原始响应: [{original_response[:500]}...]")

            # 移除MiniMax的<think>标签
            if '<think>' in response:
                response = response.split('</think>')[-1].strip()
                logger.info(f"移除<think>后长度: {len(response)}, 前500字符: [{response[:500]}...]")

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
            # 使用流式调用
            stream_generator = self.chat_completion(prompt, max_tokens=4000)
            response = await self._collect_stream_response(stream_generator)
            original_response = response
            logger.debug(f"批量媒体打标原始响应: [{original_response[:500]}...]")

            # 移除MiniMax的<think>标签
            if '<think>' in response:
                response = response.split('</think>')[-1].strip()
                logger.info(f"移除<think>后长度: {len(response)}, 前500字符: [{response[:500]}...]")

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
            # 使用流式调用
            stream_generator = self.chat_completion(prompt, max_tokens=200)
            response = await self._collect_stream_response(stream_generator)
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
            # 使用流式调用
            stream_generator = self.chat_completion(prompt, max_tokens=200)
            response = await self._collect_stream_response(stream_generator)
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

    async def abstract_events_batch(
        self,
        user_behaviors: Dict[str, List[Dict]],
        user_profiles: Dict[str, Dict] = None,
        batch_size: int = 20  # 每批处理的行为数量
    ) -> Dict[str, List[Dict]]:
        """批量抽象用户行为为事件（支持单用户行为分批）

        Args:
            user_behaviors: 用户行为数据(已丰富,包含实体详细信息)
            user_profiles: 用户画像数据(可选)
            batch_size: 每批处理的行为数量（默认20条）

        Returns:
            {
                "events": {
                    "user_001": [
                        {
                            "event_type": "看车",
                            "timestamp": "2026-01-01 10:00",
                            "context": {"poi_type": "4S店", "duration": "2小时"},
                            "category": "conversion"
                        }
                    ]
                },
                "llm_response": "..."
            }
        """
        logger.info(f"开始批量抽象 {len(user_behaviors)} 个用户的行为为事件（每批{batch_size}条）")

        # 最终结果
        final_result = {}
        all_llm_responses = []

        # 对每个用户的行为进行分批处理
        for user_id, behaviors in user_behaviors.items():
            final_result[user_id] = []

            # 如果行为数量超过batch_size，分批处理
            if len(behaviors) > batch_size:
                logger.info(f"用户 [{user_id}] 有 {len(behaviors)} 条行为，分为 {(len(behaviors) + batch_size - 1) // batch_size} 批处理")

                for batch_idx in range(0, len(behaviors), batch_size):
                    batch_behaviors = behaviors[batch_idx:batch_idx + batch_size]
                    logger.info(f"处理用户 [{user_id}] 第 {batch_idx // batch_size + 1} 批（{len(batch_behaviors)} 条行为）")

                    # 调用LLM处理这一批
                    batch_result = await self._abstract_events_single_batch(
                        {user_id: batch_behaviors},
                        user_profiles
                    )

                    # 合并结果
                    if user_id in batch_result.get("events", {}):
                        final_result[user_id].extend(batch_result["events"][user_id])
                    all_llm_responses.append(batch_result.get("llm_response", ""))
            else:
                # 行为数量不多，直接处理
                batch_result = await self._abstract_events_single_batch(
                    {user_id: behaviors},
                    user_profiles
                )
                final_result[user_id] = batch_result.get("events", {}).get(user_id, [])
                all_llm_responses.append(batch_result.get("llm_response", ""))

        logger.info(f"✓ 批量事件抽象完成: 成功 {len([v for v in final_result.values() if v])}/{len(user_behaviors)}")

        return {
            "events": final_result,
            "llm_response": "\n\n---\n\n".join(all_llm_responses)
        }

    async def _abstract_events_single_batch(
        self,
        user_behaviors: Dict[str, List[Dict]],
        user_profiles: Dict[str, Dict] = None
    ) -> Dict:
        """处理单批用户行为（内部方法）

        Args:
            user_behaviors: 单批用户行为数据
            user_profiles: 用户画像数据

        Returns:
            {
                "events": {"user_id": [...]},
                "llm_response": "..."
            }
        """

        # 构建批量请求的prompt
        user_behaviors_str = ""
        for user_id, behaviors in user_behaviors.items():
            user_behaviors_str += f"\n用户 {user_id}"

            # 添加用户画像信息
            if user_profiles and user_id in user_profiles:
                profile = user_profiles[user_id]
                profile_parts = []
                if profile.get("age"):
                    profile_parts.append(f"年龄{profile['age']}岁")
                if profile.get("gender"):
                    profile_parts.append(f"{profile['gender']}")
                if profile.get("income_level"):
                    profile_parts.append(f"收入{profile['income_level']}")
                if profile.get("interests"):
                    interests_str = ",".join(profile['interests'][:3])
                    profile_parts.append(f"兴趣:{interests_str}")

                if profile_parts:
                    user_behaviors_str += f" ({', '.join(profile_parts)})"

            user_behaviors_str += ":\n"

            # 格式化行为描述
            for behavior in behaviors:
                # 优先使用 behavior_text（非结构化格式）
                if "behavior_text" in behavior:
                    timestamp = behavior.get("timestamp", "")
                    behavior_text = behavior.get("behavior_text", "")
                    # 在behavior_text前面加上时间戳
                    user_behaviors_str += f"  - {timestamp} {behavior_text}\n"
                else:
                    # 兼容结构化格式（使用丰富后的数据）
                    formatted = self._format_enriched_behavior(behavior)
                    user_behaviors_str += f"  - {formatted}\n"

        prompt = f"""你是用户行为分析专家。请将用户的原始行为抽象为高层次事件。

## 【关键】转化行为识别规则（必须严格遵守）

原始数据中的 [action=xxx] 标签表示行为类型，**必须按以下规则处理**：

1. **[action=purchase]**
   → 必须输出：事件类型="购买"，事件分类="conversion"
   → 示例：user_001|购买|2026-01-01 10:00|长城_WEY VV7,长城4S店|conversion

2. **[action=add_cart]**
   → 必须输出：事件类型="加购"，事件分类="conversion"
   → 示例：user_001|加购|2025-12-25 22:00|长城_哈弗H6,汽车之家|conversion

3. **[action=visit_poi] 且包含"4S店"或"经销商"**
   → 必须输出：事件类型="到店"，事件分类="conversion"
   → 示例：user_001|到店|2025-12-26 14:00|长城4S店,停留1小时|conversion

4. **其他 [action=xxx]**（如 browse, use_app, search 等）
   → 根据行为内容抽象事件类型，事件分类="engagement"
   → 示例：user_001|浏览车型|2025-11-26 09:00|长城_哈弗H6,汽车之家|engagement

**重要提醒**：
- 看到 [action=purchase] 就必须输出"购买|conversion"，不要抽象成其他事件
- 看到 [action=add_cart] 就必须输出"加购|conversion"，不要抽象成其他事件
- 不要将转化行为误判为"使用APP"、"浏览车型"等互动事件

## 用户行为数据
{user_behaviors_str}

## 输出格式
每行一个事件，格式：用户ID|事件类型|时间戳|上下文信息|事件分类

请直接输出，不要有任何解释："""

        try:
            # 使用流式调用
            logger.info(f"开始批量抽象 {len(user_behaviors)} 个用户的行为为事件")
            stream_generator = self.chat_completion(prompt, max_tokens=8000)
            response = await self._collect_stream_response(stream_generator)
            original_response = response
            logger.info(f"批量事件抽象LLM响应长度: {len(response)}")
            logger.info(f"批量事件抽象原始响应前2000字符: [{original_response[:2000]}...]")
            logger.info(f"批量事件抽象原始响应后500字符: [...{original_response[-500:]}]")
            logger.debug(f"批量事件抽象原始响应: [{original_response[:500]}...]")

            # 移除MiniMax的<think>标签
            if '<think>' in response:
                response = response.split('</think>')[-1].strip()
                logger.info(f"移除<think>后长度: {len(response)}, 前500字符: [{response[:500]}...]")

            # 移除 markdown 代码块标记
            if '```' in response:
                # 提取代码块内容
                parts = response.split('```')
                if len(parts) >= 3:
                    response = parts[1].strip()
                    # 移除可能的语言标识（如 "text"）
                    if '\n' in response:
                        first_line = response.split('\n')[0].strip()
                        if first_line.isalpha() and len(first_line) < 20:
                            response = '\n'.join(response.split('\n')[1:])

            # 解析文本格式的事件数据
            # 格式: 用户ID|事件类型|时间戳|上下文信息
            result = {}
            for user_id in user_behaviors.keys():
                result[user_id] = []

            lines = response.strip().split('\n')
            logger.info(f"开始解析文本格式，共 {len(lines)} 行")
            logger.info(f"前10行内容: {lines[:10]}")

            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                if not line:
                    continue

                # 解析每行: 用户ID|事件类型|时间戳|上下文信息|事件分类
                parts = line.split('|')
                if len(parts) < 3:
                    logger.warning(f"第{line_num}行格式错误，跳过: {line}")
                    continue

                user_id = parts[0].strip()
                event_type = parts[1].strip()
                timestamp = parts[2].strip()
                context_str = parts[3].strip() if len(parts) > 3 else ""
                category = parts[4].strip() if len(parts) > 4 else "engagement"  # 默认为互动

                # 解析上下文信息（逗号分隔的键值对或简单列表）
                context = {}
                if context_str:
                    context_items = [item.strip() for item in context_str.split(',')]
                    context['details'] = context_items

                # 添加到对应用户的事件列表
                if user_id in result:
                    result[user_id].append({
                        "event_type": event_type,
                        "timestamp": timestamp,
                        "context": context,
                        "category": category  # 新增：事件分类
                    })
                    logger.debug(f"解析事件: {user_id} - {event_type} @ {timestamp} [{category}]")

            # 记录解析结果
            for user_id in user_behaviors.keys():
                event_count = len(result.get(user_id, []))
                if event_count > 0:
                    logger.info(f"✓ 用户 [{user_id}] 抽象了 {event_count} 个事件")
                else:
                    logger.warning(f"✗ 用户 [{user_id}] 未找到事件")

            logger.info(f"✓ 批量事件抽象完成: 成功 {len([v for v in result.values() if v])}/{len(user_behaviors)}")

            # 返回结果和原始响应
            return_data = {
                "events": result,
                "llm_response": original_response[:5000]  # 限制长度，避免响应过大
            }
            logger.info(f"返回数据结构: keys={list(return_data.keys())}, llm_response长度={len(return_data['llm_response'])}")
            return return_data

        except json.JSONDecodeError as e:
            logger.error(f"✗ 批量事件抽象JSON解析失败: {e}, 响应=[{response[:500]}...]", exc_info=True)
            return {
                "events": {user_id: [] for user_id in user_behaviors.keys()},
                "llm_response": original_response[:5000] if 'original_response' in locals() else ""
            }
        except Exception as e:
            logger.error(f"✗ 批量事件抽象异常: {type(e).__name__}: {str(e)}", exc_info=True)
            return {
                "events": {user_id: [] for user_id in user_behaviors.keys()},
                "llm_response": ""
            }

    async def abstract_events_batch_stream(
        self,
        user_behaviors: Dict[str, List[Dict]],
        user_profiles: Dict[str, Dict] = None,
        stream_callback=None
    ):
        """批量抽象用户行为为事件（流式版本，实时返回LLM响应）

        Args:
            user_behaviors: 用户行为数据
            user_profiles: 用户画像数据
            stream_callback: 流式回调函数，接收LLM实时输出的每个chunk

        Yields:
            LLM的实时响应内容
        """
        logger.info(f"开始流式批量抽象 {len(user_behaviors)} 个用户的行为为事件")

        # 构建批量请求的prompt（与非流式版本相同）
        user_behaviors_str = ""
        for user_id, behaviors in user_behaviors.items():
            user_behaviors_str += f"\n用户 {user_id}"

            # 添加用户画像信息
            if user_profiles and user_id in user_profiles:
                profile = user_profiles[user_id]
                profile_parts = []
                if profile.get("age"):
                    profile_parts.append(f"年龄{profile['age']}岁")
                if profile.get("gender"):
                    profile_parts.append(f"{profile['gender']}")
                if profile.get("income_level"):
                    profile_parts.append(f"收入{profile['income_level']}")
                if profile.get("interests"):
                    interests_str = ",".join(profile['interests'][:3])
                    profile_parts.append(f"兴趣:{interests_str}")

                if profile_parts:
                    user_behaviors_str += f" ({', '.join(profile_parts)})"

            user_behaviors_str += ":\n"

            # 格式化行为描述
            for behavior in behaviors:
                # 优先使用 behavior_text（非结构化格式）
                if "behavior_text" in behavior:
                    timestamp = behavior.get("timestamp", "")
                    behavior_text = behavior.get("behavior_text", "")
                    # 在behavior_text前面加上时间戳
                    user_behaviors_str += f"  - {timestamp} {behavior_text}\n"
                else:
                    # 兼容结构化格式（使用丰富后的数据）
                    formatted = self._format_enriched_behavior(behavior)
                    user_behaviors_str += f"  - {formatted}\n"

        prompt = f"""你是用户行为分析专家。请将用户的原始行为抽象为高层次事件。

## 【关键】转化行为识别规则（必须严格遵守）

原始数据中的 [action=xxx] 标签表示行为类型，**必须按以下规则处理**：

1. **[action=purchase]**
   → 必须输出：事件类型="购买"，事件分类="conversion"
   → 示例：user_001|购买|2026-01-01 10:00|长城_WEY VV7,长城4S店|conversion

2. **[action=add_cart]**
   → 必须输出：事件类型="加购"，事件分类="conversion"
   → 示例：user_001|加购|2025-12-25 22:00|长城_哈弗H6,汽车之家|conversion

3. **[action=visit_poi] 且包含"4S店"或"经销商"**
   → 必须输出：事件类型="到店"，事件分类="conversion"
   → 示例：user_001|到店|2025-12-26 14:00|长城4S店,停留1小时|conversion

4. **其他 [action=xxx]**（如 browse, use_app, search 等）
   → 根据行为内容抽象事件类型，事件分类="engagement"
   → 示例：user_001|浏览车型|2025-11-26 09:00|长城_哈弗H6,汽车之家|engagement

**重要提醒**：
- 看到 [action=purchase] 就必须输出"购买|conversion"，不要抽象成其他事件
- 看到 [action=add_cart] 就必须输出"加购|conversion"，不要抽象成其他事件
- 不要将转化行为误判为"使用APP"、"浏览车型"等互动事件

## 用户行为数据
{user_behaviors_str}

## 输出格式
每行一个事件，格式：用户ID|事件类型|时间戳|上下文信息|事件分类

请直接输出，不要有任何解释："""

        try:
            # 使用流式调用
            stream_generator = self.chat_completion(prompt, max_tokens=8000)

            # 实时yield每个chunk
            full_response = ""
            async for chunk in stream_generator:
                full_response += chunk
                # 实时回调
                if stream_callback:
                    await stream_callback(chunk)
                # yield给调用者
                yield chunk

            logger.info(f"流式批量事件抽象完成，总长度: {len(full_response)}")

        except Exception as e:
            logger.error(f"✗ 流式批量事件抽象异常: {type(e).__name__}: {str(e)}", exc_info=True)
            raise

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
        # 使用流式调用
        stream_generator = self.chat_completion(prompt, temperature=0.3)
        response = await self._collect_stream_response(stream_generator)
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
        # 使用流式调用
        stream_generator = self.chat_completion(prompt, temperature=0.5)
        answer = await self._collect_stream_response(stream_generator)
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
