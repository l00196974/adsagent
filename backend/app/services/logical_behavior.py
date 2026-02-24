"""
逻辑行为生成服务 - 将原始行为抽象为逻辑行为序列
"""
import asyncio
import json
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

from app.core.logger import app_logger
from app.core.openai_client import OpenAIClient
from app.core.exceptions import LLMServiceError, DatabaseError


class LogicalBehaviorGenerator:
    """逻辑行为生成器"""

    def __init__(self, llm_client: OpenAIClient, db_path: str = "data/graph.db"):
        self.llm_client = llm_client
        self.db_path = Path(db_path)
        self.progress = {
            "total_users": 0,
            "processed_users": 0,
            "success_count": 0,
            "failed_count": 0,
            "current_user": None
        }

    async def generate_for_user(self, user_id: str) -> Dict:
        """为单个用户生成逻辑行为序列"""
        app_logger.info(f"开始为用户 {user_id} 生成逻辑行为")

        try:
            # 更新状态为processing
            self._update_sequence_status(user_id, "processing")

            # 1. 获取用户画像
            user_profile = self._get_user_profile(user_id)
            if not user_profile:
                raise DatabaseError(f"用户 {user_id} 画像不存在")

            # 2. 获取原始行为数据
            raw_behaviors = self._get_raw_behaviors(user_id)
            if not raw_behaviors:
                app_logger.warning(f"用户 {user_id} 没有行为数据")
                self._update_sequence_status(user_id, "success", 0)
                return {
                    "user_id": user_id,
                    "logical_behaviors": [],
                    "raw_behavior_count": 0,
                    "logical_behavior_count": 0
                }

            # 3. 丰富行为数据（关联app_tags和media_tags）
            enriched_behaviors = self._enrich_behaviors_with_tags(raw_behaviors)

            # 4. 调用LLM生成逻辑行为
            logical_behaviors = await self._generate_logical_behaviors(
                user_id, user_profile, enriched_behaviors
            )

            # 5. 保存到数据库
            saved_count = self._save_logical_behaviors(user_id, logical_behaviors)

            # 6. 更新状态为success
            self._update_sequence_status(user_id, "success", saved_count)

            app_logger.info(
                f"用户 {user_id} 逻辑行为生成完成: "
                f"{len(raw_behaviors)} 原始行为 -> {saved_count} 逻辑行为"
            )

            return {
                "user_id": user_id,
                "logical_behaviors": logical_behaviors,
                "raw_behavior_count": len(raw_behaviors),
                "logical_behavior_count": saved_count
            }

        except Exception as e:
            error_msg = str(e)
            app_logger.error(f"用户 {user_id} 逻辑行为生成失败: {error_msg}", exc_info=True)
            self._update_sequence_status(user_id, "failed", 0, error_msg)
            raise

    async def generate_batch(self, user_ids: List[str], max_workers: int = 4) -> Dict:
        """批量生成逻辑行为序列（并行处理）"""
        app_logger.info(f"开始批量生成逻辑行为: {len(user_ids)} 个用户, {max_workers} 并发")

        # 初始化进度
        self.progress = {
            "total_users": len(user_ids),
            "processed_users": 0,
            "success_count": 0,
            "failed_count": 0,
            "current_user": None
        }

        success_count = 0
        failed_count = 0
        results = []

        async def process_with_progress(user_id: str):
            nonlocal success_count, failed_count

            try:
                result = await self.generate_for_user(user_id)
                success_count += 1
                self._update_progress(
                    processed_users=success_count + failed_count,
                    success_count=success_count,
                    failed_count=failed_count
                )
                return {"user_id": user_id, "status": "success", "result": result}
            except Exception as e:
                failed_count += 1
                self._update_progress(
                    processed_users=success_count + failed_count,
                    success_count=success_count,
                    failed_count=failed_count
                )
                return {"user_id": user_id, "status": "failed", "error": str(e)}

        # 使用信号量控制并发
        semaphore = asyncio.Semaphore(max_workers)

        async def process_with_semaphore(user_id: str):
            async with semaphore:
                return await process_with_progress(user_id)

        # 并行处理
        tasks = [process_with_semaphore(user_id) for user_id in user_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        app_logger.info(
            f"批量生成完成: 成功 {success_count}, 失败 {failed_count}"
        )

        return {
            "total_users": len(user_ids),
            "success_count": success_count,
            "failed_count": failed_count,
            "results": results
        }

    def get_progress(self) -> Dict:
        """获取生成进度"""
        return self.progress.copy()

    def query_logical_behaviors(self, user_id: str) -> List[Dict]:
        """查询用户的逻辑行为序列"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """SELECT id, user_id, agent, scene, action, object,
                              start_time, end_time, raw_behavior_ids, confidence
                       FROM logical_behaviors
                       WHERE user_id = ?
                       ORDER BY start_time ASC""",
                    (user_id,)
                )

                behaviors = []
                for row in cursor.fetchall():
                    behaviors.append({
                        "id": row[0],
                        "user_id": row[1],
                        "agent": row[2],
                        "scene": row[3],
                        "action": row[4],
                        "object": row[5],
                        "start_time": row[6],
                        "end_time": row[7],
                        "raw_behavior_ids": row[8].split(",") if row[8] else [],
                        "confidence": row[9]
                    })

                return behaviors

        except Exception as e:
            app_logger.error(f"查询逻辑行为失败: {e}", exc_info=True)
            raise DatabaseError(f"查询逻辑行为失败: {e}")

    # ========== 私有方法 ==========

    def _get_user_profile(self, user_id: str) -> Optional[Dict]:
        """获取用户画像"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """SELECT user_id, age, gender, city, occupation, properties
                       FROM user_profiles
                       WHERE user_id = ?""",
                    (user_id,)
                )
                row = cursor.fetchone()
                if not row:
                    return None

                properties = json.loads(row[5]) if row[5] else {}

                return {
                    "user_id": row[0],
                    "age": row[1],
                    "gender": row[2],
                    "city": row[3],
                    "occupation": row[4],
                    "age_bucket": properties.get("age_bucket", ""),
                    "education": properties.get("education", ""),
                    "income_level": properties.get("income_level", ""),
                    "interests": properties.get("interests", []),
                    "behaviors": properties.get("behaviors", [])
                }

        except Exception as e:
            app_logger.error(f"获取用户画像失败: {e}", exc_info=True)
            return None

    def _get_raw_behaviors(self, user_id: str) -> List[Dict]:
        """获取原始行为数据"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """SELECT id, user_id, action, timestamp, item_id, app_id,
                              media_id, poi_id, duration, properties
                       FROM behavior_data
                       WHERE user_id = ?
                       ORDER BY timestamp ASC""",
                    (user_id,)
                )

                behaviors = []
                for row in cursor.fetchall():
                    properties = json.loads(row[9]) if row[9] else {}
                    behaviors.append({
                        "id": row[0],
                        "user_id": row[1],
                        "action": row[2],
                        "timestamp": row[3],
                        "item_id": row[4],
                        "app_id": row[5],
                        "media_id": row[6],
                        "poi_id": row[7],
                        "duration": row[8],
                        "properties": properties
                    })

                return behaviors

        except Exception as e:
            app_logger.error(f"获取原始行为失败: {e}", exc_info=True)
            return []

    def _enrich_behaviors_with_tags(self, behaviors: List[Dict]) -> List[Dict]:
        """丰富行为数据（关联app_tags和media_tags）"""
        if not behaviors:
            return behaviors

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 提取所有app_id和media_id
                app_ids = list(set(b["app_id"] for b in behaviors if b.get("app_id")))
                media_ids = list(set(b["media_id"] for b in behaviors if b.get("media_id")))

                # 批量查询app_tags
                app_tags_map = {}
                if app_ids:
                    placeholders = ",".join("?" * len(app_ids))
                    cursor.execute(
                        f"""SELECT app_id, app_name, category, tags
                           FROM app_tags
                           WHERE app_id IN ({placeholders})""",
                        app_ids
                    )
                    for row in cursor.fetchall():
                        app_tags_map[row[0]] = {
                            "app_name": row[1],
                            "category": row[2],
                            "tags": row[3]
                        }

                # 批量查询media_tags
                media_tags_map = {}
                if media_ids:
                    placeholders = ",".join("?" * len(media_ids))
                    cursor.execute(
                        f"""SELECT media_id, media_name, media_type, tags
                           FROM media_tags
                           WHERE media_id IN ({placeholders})""",
                        media_ids
                    )
                    for row in cursor.fetchall():
                        media_tags_map[row[0]] = {
                            "media_name": row[1],
                            "media_type": row[2],
                            "tags": row[3]
                        }

                # 丰富行为数据
                enriched = []
                for behavior in behaviors:
                    enriched_behavior = behavior.copy()

                    # 添加app信息
                    if behavior.get("app_id") and behavior["app_id"] in app_tags_map:
                        app_info = app_tags_map[behavior["app_id"]]
                        enriched_behavior["app_name"] = app_info["app_name"]
                        enriched_behavior["app_category"] = app_info["category"]
                        enriched_behavior["app_tags"] = app_info["tags"]

                    # 添加media信息
                    if behavior.get("media_id") and behavior["media_id"] in media_tags_map:
                        media_info = media_tags_map[behavior["media_id"]]
                        enriched_behavior["media_name"] = media_info["media_name"]
                        enriched_behavior["media_type"] = media_info["media_type"]
                        enriched_behavior["media_tags"] = media_info["tags"]

                    enriched.append(enriched_behavior)

                return enriched

        except Exception as e:
            app_logger.error(f"丰富行为数据失败: {e}", exc_info=True)
            return behaviors

    def _format_raw_behaviors(self, behaviors: List[Dict]) -> str:
        """格式化原始行为供LLM分析（包含完整属性）"""
        lines = []
        for b in behaviors:
            parts = [f"[{b['timestamp']}]", b['action']]

            # 添加APP信息
            if b.get("app_name"):
                app_str = f"APP:{b['app_name']}"
                if b.get("app_category"):
                    app_str += f"({b['app_category']})"
                parts.append(app_str)

            # 添加媒体信息
            if b.get("media_name"):
                media_str = f"媒体:{b['media_name']}"
                if b.get("media_type"):
                    media_str += f"({b['media_type']})"
                parts.append(media_str)

            # 添加商品信息
            if b.get("item_id"):
                parts.append(f"商品:{b['item_id']}")

            # 添加POI信息
            if b.get("poi_id"):
                parts.append(f"POI:{b['poi_id']}")

            # 添加时长
            if b.get("duration"):
                parts.append(f"时长:{b['duration']}秒")

            # 添加额外属性
            if b.get("properties"):
                for key, value in b["properties"].items():
                    parts.append(f"{key}:{value}")

            lines.append(" | ".join(parts))

        return "\n".join(lines)

    def _build_prompt(self, user_profile: Dict, formatted_behaviors: str) -> str:
        """构建LLM prompt"""
        # 提取用户画像字段
        age = user_profile.get("age", "未知")
        age_bucket = user_profile.get("age_bucket", "")
        gender = user_profile.get("gender", "未知")
        city = user_profile.get("city", "未知")
        occupation = user_profile.get("occupation", "未知")
        education = user_profile.get("education", "")
        income_level = user_profile.get("income_level", "")
        interests = ", ".join(user_profile.get("interests", []))
        behaviors = ", ".join(user_profile.get("behaviors", []))

        prompt = f"""你是一个用户行为分析专家，需要将用户的原始行为序列抽象为逻辑行为序列。

## 用户画像
- 用户ID: {user_profile['user_id']}
- 年龄: {age}岁 ({age_bucket})
- 性别: {gender}
- 城市: {city}
- 职业: {occupation}
- 教育: {education}
- 收入: {income_level}
- 兴趣: {interests}
- 行为特征: {behaviors}

## 原始行为序列
{formatted_behaviors}

## 核心任务：泛化与合并
你的任务是将碎片化的原始行为**抽象为更高层次的逻辑行为**，而不是简单复制。关键要求：

### 1. 智能合并策略（必须执行）

**紧密合并**（5分钟内）：
- 相邻5分钟内的相似行为必须合并
- 示例：[12:00] 浏览宝马X5 → [12:03] 浏览奔驰GLE → [12:05] 浏览奥迪Q7
- 合并为：对比豪华SUV车型

**主题合并**（同一时段内）：
- 同一时段（如上午、下午、晚上）的相同主题行为应该聚合
- 即使时间跨度较大（1-2小时），只要主题一致就合并
- 示例：
  - [10:00] 浏览吉利帝豪 → [11:00] 浏览吉利博越 → [13:00] 浏览吉利星越
  - 合并为：研究吉利品牌车型（上午到下午，主题一致）

**跨时段合并**（同一天内）：
- 同一天内多次出现的相同主题行为可以合并
- 示例：
  - [09:00] 浏览汽车之家 → [14:00] 浏览汽车之家 → [19:00] 浏览汽车之家
  - 合并为：全天持续关注汽车资讯

**判断标准**：
- 相同品牌/品类 → 必须合并
- 相同平台/APP → 可以合并
- 相同行为类型（如都是浏览、都是使用APP） → 可以合并
- 不同主题 → 不合并（如浏览汽车+浏览美妆）

### 2. 主题维度聚合（必须执行）
- 相同品类/主题的多次行为应该聚合
- 示例：
  - 原始：浏览本田CR-V → 浏览丰田RAV4 → 浏览日产奇骏
  - 逻辑：对比日系合资SUV（而不是分别记录3次）

### 3. 意图抽象（核心）
从具体行为推断用户的真实意图：
- "浏览宝马7系+奔驰S级+奥迪A8" → "对比豪华轿车"（购车意图）
- "深夜多次浏览美妆+点击广告" → "种草美妆产品"（消费意图）
- "工作日午间短时浏览" → "碎片时间信息获取"（浏览意图）
- "周末长时间停留4S店" → "深度看车体验"（转化意图）

### 4. 对象泛化（必须执行）
将具体对象抽象为品类/类型：
- "本田CR-V" → "日系合资SUV"
- "宝马7系+奔驰S级" → "豪华行政轿车"
- "抖音+快手" → "短视频平台"
- "汽车之家+懂车帝" → "汽车资讯平台"
- "星巴克+瑞幸" → "连锁咖啡品牌"
- "LV+Gucci" → "奢侈品牌"

## 输出4个维度

1. **本体(Agent)**: 基于用户画像的简洁标签
   - 结合年龄段+性别+职业/身份
   - 示例：Z世代年轻女性学生、中年高收入男性白领、退休老年男性

2. **环境(Scene)**: 时间+场景特征
   - 时间段：深夜(22:00-02:00)、午休(12:00-14:00)、周末、工作日
   - 场景：休闲娱乐、碎片时间、深度研究、商务活动
   - 示例：深夜宿舍休闲娱乐场景、工作日午休碎片时间、周末深度购车研究

3. **行动(Action)**: 泛化的行为意图
   - 不要简单说"浏览"、"使用"，要说明目的
   - 示例：对比豪华SUV车型、种草美妆产品、研究购车方案、碎片时间娱乐

4. **对象(Object)**: 泛化的目标品类
   - 不要具体品牌/型号，要品类/类型
   - 示例：日系合资SUV、豪华行政轿车、平价美妆产品、短视频娱乐平台

## 泛化示例对比

❌ 错误（没有泛化）：
中年女性教师|工作日上午|浏览汽车资讯|本田CR-V|...|user_0136_b0|0.9
中年女性教师|工作日上午|浏览汽车资讯|丰田RAV4|...|user_0136_b1|0.9
中年女性教师|工作日上午|浏览汽车资讯|日产奇骏|...|user_0136_b2|0.9

✓ 正确（已泛化合并）：
中年女性教师|工作日上午碎片时间|对比日系合资SUV车型|20-30万家用SUV|...|user_0136_b0,user_0136_b1,user_0136_b2|0.95

❌ 错误（没有泛化）：
Z世代女性学生|深夜|浏览|抖音短视频|...|b5|0.8
Z世代女性学生|深夜|浏览|小红书|...|b6|0.8

✓ 正确（已泛化合并）：
Z世代女性学生|深夜宿舍休闲娱乐|种草美妆内容|短视频+社区平台|...|b5,b6|0.9

## 输出格式（严格遵守）

**必须使用管道符分隔的纯文本格式，不要使用JSON！**

每行一个逻辑行为，格式如下：
```
agent|scene|action|object|start_time|end_time|raw_behavior_ids|confidence
```

**示例输出**：
```
50岁上海男性互联网从业者|工作日全天持续关注|研究豪华SUV车型|30-50万豪华SUV|2025-11-26 09:00:00|2025-11-26 18:00:00|user_0035_b0,user_0035_b2,user_0035_b3,user_0035_b4,user_0035_b5|0.92
50岁上海男性互联网从业者|晚间商务社交|高端商务会所活动|商务社交场所|2025-11-27 19:00:00|2025-11-29 21:00:00|user_0035_b6,user_0035_b12,user_0035_b13|0.97
```

**严格要求**：
1. ❌ 不要输出JSON格式（不要用花括号、方括号、引号等）
2. ❌ 不要输出原始行为的详细列表
3. ❌ 不要输出多个版本（详细版、简化版等）
4. ✅ 只输出最终的泛化合并后的逻辑行为
5. ✅ 每行一个逻辑行为，使用管道符|分隔
6. ✅ 直接输出结果，不要任何前缀、标题、说明

**字段说明**：
- raw_behavior_ids: 逗号分隔的行为ID列表（如：user_0035_b0,user_0035_b2,user_0035_b3）
- confidence: 0-1之间的数字（如：0.92）
- 时间格式: YYYY-MM-DD HH:MM:SS

## 关键提醒
- 必须合并相邻的相似行为，不要一对一映射
- 必须泛化对象，不要保留具体品牌/型号
- 必须抽象意图，不要简单复制动作
- 逻辑行为数量应该远少于原始行为数量（建议压缩到30-50%）
"""
        return prompt

    async def _generate_logical_behaviors(
        self, user_id: str, user_profile: Dict, enriched_behaviors: List[Dict]
    ) -> List[Dict]:
        """调用LLM生成逻辑行为"""
        try:
            # 格式化行为数据
            formatted_behaviors = self._format_raw_behaviors(enriched_behaviors)

            # 构建prompt
            prompt = self._build_prompt(user_profile, formatted_behaviors)

            # 调用LLM（流式）
            stream_generator = self.llm_client.chat_completion(
                prompt=prompt,
                max_tokens=8000,
                temperature=0.3
            )

            # 收集完整响应
            full_response = await self.llm_client._collect_stream_response(stream_generator)

            if not full_response:
                raise LLMServiceError("LLM返回空结果")

            app_logger.info(f"LLM响应长度: {len(full_response)} 字符")

            # 解析响应
            logical_behaviors = self._parse_llm_response(user_id, full_response, enriched_behaviors)

            return logical_behaviors

        except Exception as e:
            app_logger.error(f"LLM生成逻辑行为失败: {e}", exc_info=True)
            raise LLMServiceError(f"LLM生成失败: {e}")

    def _parse_llm_response(
        self, user_id: str, response: str, enriched_behaviors: List[Dict]
    ) -> List[Dict]:
        """解析LLM响应（管道分隔格式）"""
        logical_behaviors = []

        # 移除markdown代码块标记
        response = response.replace("```text", "").replace("```", "").strip()

        # 按行解析
        lines = response.strip().split("\n")
        behavior_index = 0

        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            try:
                parts = line.split("|")
                if len(parts) < 8:
                    app_logger.warning(f"跳过格式不正确的行: {line}")
                    continue

                agent = parts[0].strip()
                scene = parts[1].strip()
                action = parts[2].strip()
                obj = parts[3].strip()
                start_time = parts[4].strip()
                end_time = parts[5].strip()
                raw_behavior_ids = parts[6].strip()
                confidence = float(parts[7].strip())

                # 生成逻辑行为ID
                lb_id = f"lb_{user_id}_{behavior_index}"
                behavior_index += 1

                logical_behaviors.append({
                    "id": lb_id,
                    "user_id": user_id,
                    "agent": agent,
                    "scene": scene,
                    "action": action,
                    "object": obj,
                    "start_time": start_time,
                    "end_time": end_time,
                    "raw_behavior_ids": raw_behavior_ids,
                    "confidence": confidence
                })

            except Exception as e:
                app_logger.warning(f"解析行失败: {line}, 错误: {e}")
                continue

        app_logger.info(f"解析出 {len(logical_behaviors)} 个逻辑行为")
        return logical_behaviors

    def _save_logical_behaviors(self, user_id: str, logical_behaviors: List[Dict]) -> int:
        """保存逻辑行为到数据库"""
        if not logical_behaviors:
            return 0

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 先删除该用户的旧数据
                cursor.execute("DELETE FROM logical_behaviors WHERE user_id = ?", (user_id,))

                # 批量插入
                data = [
                    (
                        lb["id"],
                        lb["user_id"],
                        lb["agent"],
                        lb["scene"],
                        lb["action"],
                        lb["object"],
                        lb["start_time"],
                        lb["end_time"],
                        lb["raw_behavior_ids"],
                        lb["confidence"]
                    )
                    for lb in logical_behaviors
                ]

                cursor.executemany(
                    """INSERT INTO logical_behaviors
                       (id, user_id, agent, scene, action, object, start_time, end_time,
                        raw_behavior_ids, confidence)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    data
                )

                conn.commit()
                app_logger.info(f"保存了 {len(data)} 个逻辑行为")
                return len(data)

        except Exception as e:
            app_logger.error(f"保存逻辑行为失败: {e}", exc_info=True)
            raise DatabaseError(f"保存逻辑行为失败: {e}")

    def _update_sequence_status(
        self, user_id: str, status: str, behavior_count: int = 0, error_message: str = None
    ):
        """更新逻辑行为序列状态"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """INSERT OR REPLACE INTO logical_behavior_sequences
                       (user_id, status, behavior_count, error_message, updated_at)
                       VALUES (?, ?, ?, ?, ?)""",
                    (user_id, status, behavior_count, error_message, datetime.now())
                )
                conn.commit()

        except Exception as e:
            app_logger.error(f"更新序列状态失败: {e}", exc_info=True)

    def _update_progress(self, processed_users: int, success_count: int, failed_count: int):
        """更新进度"""
        self.progress["processed_users"] = processed_users
        self.progress["success_count"] = success_count
        self.progress["failed_count"] = failed_count
