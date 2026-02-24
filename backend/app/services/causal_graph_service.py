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

        # 3. 计算真实统计数据
        statistics = self._compute_statistics(patterns, user_examples, user_profiles)
        logger.info(f"计算统计数据完成: 总用户{statistics.get('total_users', 0)}, 转化率{statistics.get('conversion_rate', 0):.2f}%")

        # 4. 构建LLM Prompt
        prompt = self._build_prompt(patterns, user_examples, user_profiles, analysis_focus, statistics)

        # 5. 调用LLM生成事理图谱（使用流式调用）
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

    def _compute_statistics(self, patterns: List[Dict], user_examples: List[Dict], user_profiles: Dict[str, Dict]) -> Dict:
        """计算真实的统计数据

        Args:
            patterns: 高频模式列表
            user_examples: 用户示例列表
            user_profiles: 用户画像字典

        Returns:
            包含各种统计指标的字典
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 1. 总用户数
                cursor.execute("SELECT COUNT(DISTINCT user_id) FROM event_sequences WHERE status = 'success'")
                total_users = cursor.fetchone()[0]

                # 2. 转化率统计
                cursor.execute("""
                    SELECT COUNT(DISTINCT user_id)
                    FROM extracted_events
                    WHERE event_type IN ('购买', '加购')
                """)
                converted_users = cursor.fetchone()[0]
                conversion_rate = (converted_users / total_users * 100) if total_users > 0 else 0

                # 3. 为每个高频模式计算用户画像分布
                pattern_profile_stats = {}
                for pattern in patterns[:10]:  # 只统计前10个模式
                    pattern_sequence = json.loads(pattern['pattern_sequence'])

                    # 找出包含该模式的用户
                    cursor.execute("SELECT user_id, sequence FROM event_sequences WHERE status = 'success'")

                    matching_users = []
                    for row in cursor.fetchall():
                        user_id = row[0]
                        event_ids = json.loads(row[1])

                        # 获取事件类型序列
                        if event_ids:
                            placeholders = ','.join('?' * len(event_ids))
                            cursor.execute(
                                f"""SELECT event_type FROM extracted_events
                                   WHERE event_id IN ({placeholders})
                                   ORDER BY timestamp""",
                                event_ids
                            )
                            event_types = [r[0] for r in cursor.fetchall()]

                            # 检查是否包含该模式
                            if self._contains_pattern(event_types, pattern_sequence):
                                matching_users.append(user_id)

                    # 统计这些用户的画像分布
                    if matching_users:
                        profile_dist = self._compute_profile_distribution(cursor, matching_users)
                        pattern_profile_stats[' → '.join(pattern_sequence)] = {
                            'user_count': len(matching_users),
                            'profile_distribution': profile_dist
                        }

                # 4. 事件转移概率矩阵
                cursor.execute("""
                    SELECT es.user_id, es.sequence
                    FROM event_sequences es
                    WHERE es.status = 'success'
                """)

                transition_counts = {}  # {(event_a, event_b): count}
                event_counts = {}  # {event: count}

                for row in cursor.fetchall():
                    user_id = row[0]
                    event_ids = json.loads(row[1])

                    # 获取该用户的事件类型序列
                    if not event_ids:
                        continue

                    placeholders = ','.join('?' * len(event_ids))
                    cursor.execute(
                        f"""SELECT event_id, event_type
                           FROM extracted_events
                           WHERE event_id IN ({placeholders})
                           ORDER BY timestamp""",
                        event_ids
                    )

                    event_type_map = {row[0]: row[1] for row in cursor.fetchall()}
                    event_types = [event_type_map.get(eid) for eid in event_ids if eid in event_type_map]

                    # 计算转移
                    for i in range(len(event_types) - 1):
                        event_a = event_types[i]
                        event_b = event_types[i + 1]

                        if event_a and event_b:
                            transition_counts[(event_a, event_b)] = transition_counts.get((event_a, event_b), 0) + 1
                            event_counts[event_a] = event_counts.get(event_a, 0) + 1

                # 计算转移概率
                transition_probs = {}
                for (event_a, event_b), count in transition_counts.items():
                    prob = count / event_counts[event_a] if event_counts.get(event_a, 0) > 0 else 0
                    transition_probs[(event_a, event_b)] = {
                        "probability": round(prob, 3),
                        "count": count,
                        "total": event_counts[event_a]
                    }

                # 5. 按性别分组统计（全局）
                gender_stats = {}
                for gender in ['男', '女']:
                    cursor.execute("""
                        SELECT COUNT(DISTINCT es.user_id)
                        FROM event_sequences es
                        JOIN user_profiles up ON es.user_id = up.user_id
                        WHERE up.gender = ? AND es.status = 'success'
                    """, (gender,))
                    gender_total = cursor.fetchone()[0]

                    cursor.execute("""
                        SELECT COUNT(DISTINCT ee.user_id)
                        FROM extracted_events ee
                        JOIN user_profiles up ON ee.user_id = up.user_id
                        WHERE up.gender = ? AND ee.event_type IN ('购买', '加购')
                    """, (gender,))
                    gender_converted = cursor.fetchone()[0]

                    gender_stats[gender] = {
                        "total": gender_total,
                        "converted": gender_converted,
                        "conversion_rate": round((gender_converted / gender_total * 100) if gender_total > 0 else 0, 2)
                    }

                # 6. 按年龄段分组统计（全局）
                age_groups = [
                    ("25-35岁", 25, 35),
                    ("35-45岁", 35, 45),
                    ("45岁以上", 45, 100)
                ]
                age_stats = {}
                for label, min_age, max_age in age_groups:
                    cursor.execute("""
                        SELECT COUNT(DISTINCT es.user_id)
                        FROM event_sequences es
                        JOIN user_profiles up ON es.user_id = up.user_id
                        WHERE up.age >= ? AND up.age < ? AND es.status = 'success'
                    """, (min_age, max_age))
                    age_total = cursor.fetchone()[0]

                    cursor.execute("""
                        SELECT COUNT(DISTINCT ee.user_id)
                        FROM extracted_events ee
                        JOIN user_profiles up ON ee.user_id = up.user_id
                        WHERE up.age >= ? AND up.age < ? AND ee.event_type IN ('购买', '加购')
                    """, (min_age, max_age))
                    age_converted = cursor.fetchone()[0]

                    age_stats[label] = {
                        "total": age_total,
                        "converted": age_converted,
                        "conversion_rate": round((age_converted / age_total * 100) if age_total > 0 else 0, 2)
                    }

                # 7. 按职业分组统计（全局，只统计人数>=5的职业）
                cursor.execute("""
                    SELECT up.occupation, COUNT(DISTINCT es.user_id) as total,
                           COUNT(DISTINCT CASE WHEN ee.event_type IN ('购买', '加购') THEN ee.user_id END) as converted
                    FROM event_sequences es
                    JOIN user_profiles up ON es.user_id = up.user_id
                    LEFT JOIN extracted_events ee ON es.user_id = ee.user_id
                    WHERE es.status = 'success' AND up.occupation IS NOT NULL
                    GROUP BY up.occupation
                    HAVING total >= 5
                    ORDER BY converted DESC
                """)

                occupation_stats = {}
                for row in cursor.fetchall():
                    occupation = row[0]
                    total = row[1]
                    converted = row[2]
                    occupation_stats[occupation] = {
                        "total": total,
                        "converted": converted,
                        "conversion_rate": round((converted / total * 100) if total > 0 else 0, 2)
                    }

                return {
                    "total_users": total_users,
                    "converted_users": converted_users,
                    "conversion_rate": round(conversion_rate, 2),
                    "pattern_profile_stats": pattern_profile_stats,
                    "transition_probs": transition_probs,
                    "gender_stats": gender_stats,
                    "age_stats": age_stats,
                    "occupation_stats": occupation_stats
                }

        except Exception as e:
            logger.error(f"计算统计数据失败: {e}", exc_info=True)
            return {}

    def _contains_pattern(self, sequence: List[str], pattern: List[str]) -> bool:
        """检查序列是否包含指定模式（子序列）"""
        if not pattern or not sequence:
            return False

        pattern_len = len(pattern)
        for i in range(len(sequence) - pattern_len + 1):
            if sequence[i:i+pattern_len] == pattern:
                return True
        return False

    def _compute_profile_distribution(self, cursor, user_ids: List[str]) -> Dict:
        """计算用户列表的画像分布

        Args:
            cursor: 数据库游标
            user_ids: 用户ID列表

        Returns:
            画像分布统计
        """
        if not user_ids:
            return {}

        placeholders = ','.join('?' * len(user_ids))

        # 性别分布
        cursor.execute(
            f"""SELECT gender, COUNT(*) as count
               FROM user_profiles
               WHERE user_id IN ({placeholders}) AND gender IS NOT NULL
               GROUP BY gender""",
            user_ids
        )
        gender_dist = {row[0]: row[1] for row in cursor.fetchall()}

        # 年龄段分布
        cursor.execute(
            f"""SELECT
                   CASE
                       WHEN age >= 25 AND age < 35 THEN '25-35岁'
                       WHEN age >= 35 AND age < 45 THEN '35-45岁'
                       WHEN age >= 45 THEN '45岁以上'
                       ELSE '其他'
                   END as age_group,
                   COUNT(*) as count
               FROM user_profiles
               WHERE user_id IN ({placeholders}) AND age IS NOT NULL
               GROUP BY age_group""",
            user_ids
        )
        age_dist = {row[0]: row[1] for row in cursor.fetchall()}

        # 职业分布（只显示人数>=2的）
        cursor.execute(
            f"""SELECT occupation, COUNT(*) as count
               FROM user_profiles
               WHERE user_id IN ({placeholders}) AND occupation IS NOT NULL
               GROUP BY occupation
               HAVING count >= 2
               ORDER BY count DESC""",
            user_ids
        )
        occupation_dist = {row[0]: row[1] for row in cursor.fetchall()}

        return {
            "gender": gender_dist,
            "age": age_dist,
            "occupation": occupation_dist
        }

    def _find_significant_features(self, pattern_profile_stats: Dict, global_stats: Dict) -> List[Dict]:
        """找出显著的用户画像特征

        对比每个模式的用户群体画像分布与全局分布，找出显著差异的特征。
        显著性标准：该特征在模式用户中的占比 - 全局占比 >= 15%

        Args:
            pattern_profile_stats: 每个模式的用户画像分布
            global_stats: 全局统计数据

        Returns:
            显著特征列表，每个特征包含：
            - feature_id: 特征ID
            - feature_name: 特征名称
            - patterns: 关联的模式列表
            - significance: 显著性得分
        """
        # 计算全局画像分布
        total_users = global_stats.get('total_users', 1)

        global_gender_dist = {}
        for gender, stats in global_stats.get('gender_stats', {}).items():
            global_gender_dist[gender] = stats['total'] / total_users

        global_age_dist = {}
        for age_group, stats in global_stats.get('age_stats', {}).items():
            global_age_dist[age_group] = stats['total'] / total_users

        global_occupation_dist = {}
        for occupation, stats in global_stats.get('occupation_stats', {}).items():
            global_occupation_dist[occupation] = stats['total'] / total_users

        # 找出显著特征
        significant_features = {}  # {feature_name: {patterns: [], max_significance: float}}

        for pattern_name, pattern_stats in pattern_profile_stats.items():
            pattern_user_count = pattern_stats['user_count']
            dist = pattern_stats['profile_distribution']

            # 检查性别特征
            for gender, count in dist.get('gender', {}).items():
                pattern_ratio = count / pattern_user_count
                global_ratio = global_gender_dist.get(gender, 0)
                diff = pattern_ratio - global_ratio

                if diff >= 0.15:  # 显著性阈值：15%
                    feature_name = f"{gender}性用户"
                    if feature_name not in significant_features:
                        significant_features[feature_name] = {
                            'type': 'gender',
                            'value': gender,
                            'patterns': [],
                            'max_significance': 0
                        }
                    significant_features[feature_name]['patterns'].append({
                        'pattern': pattern_name,
                        'ratio': round(pattern_ratio * 100, 1),
                        'global_ratio': round(global_ratio * 100, 1),
                        'diff': round(diff * 100, 1)
                    })
                    significant_features[feature_name]['max_significance'] = max(
                        significant_features[feature_name]['max_significance'],
                        diff
                    )

            # 检查年龄段特征
            for age_group, count in dist.get('age', {}).items():
                pattern_ratio = count / pattern_user_count
                global_ratio = global_age_dist.get(age_group, 0)
                diff = pattern_ratio - global_ratio

                if diff >= 0.15:
                    feature_name = age_group
                    if feature_name not in significant_features:
                        significant_features[feature_name] = {
                            'type': 'age',
                            'value': age_group,
                            'patterns': [],
                            'max_significance': 0
                        }
                    significant_features[feature_name]['patterns'].append({
                        'pattern': pattern_name,
                        'ratio': round(pattern_ratio * 100, 1),
                        'global_ratio': round(global_ratio * 100, 1),
                        'diff': round(diff * 100, 1)
                    })
                    significant_features[feature_name]['max_significance'] = max(
                        significant_features[feature_name]['max_significance'],
                        diff
                    )

            # 检查职业特征
            for occupation, count in dist.get('occupation', {}).items():
                pattern_ratio = count / pattern_user_count
                global_ratio = global_occupation_dist.get(occupation, 0)
                diff = pattern_ratio - global_ratio

                if diff >= 0.15:
                    feature_name = occupation
                    if feature_name not in significant_features:
                        significant_features[feature_name] = {
                            'type': 'occupation',
                            'value': occupation,
                            'patterns': [],
                            'max_significance': 0
                        }
                    significant_features[feature_name]['patterns'].append({
                        'pattern': pattern_name,
                        'ratio': round(pattern_ratio * 100, 1),
                        'global_ratio': round(global_ratio * 100, 1),
                        'diff': round(diff * 100, 1)
                    })
                    significant_features[feature_name]['max_significance'] = max(
                        significant_features[feature_name]['max_significance'],
                        diff
                    )

        # 转换为列表并按显著性排序
        result = []
        for feature_name, data in significant_features.items():
            result.append({
                'feature_name': feature_name,
                'feature_type': data['type'],
                'feature_value': data['value'],
                'patterns': data['patterns'],
                'max_significance': data['max_significance']
            })

        result.sort(key=lambda x: x['max_significance'], reverse=True)
        return result

    def _build_prompt(
        self,
        patterns: List[Dict],
        user_examples: List[Dict],
        user_profiles: Dict[str, Dict],
        analysis_focus: str,
        statistics: Dict
    ) -> str:
        """构建LLM Prompt"""
        # 格式化高频模式（包含用户画像分布）
        patterns_text = ""
        pattern_profile_stats = statistics.get('pattern_profile_stats', {})

        for i, pattern in enumerate(patterns[:20], 1):  # 限制20个模式
            pattern_seq = json.loads(pattern['pattern_sequence'])
            pattern_key = ' → '.join(pattern_seq)

            patterns_text += f"{i}. 模式: {pattern_key}\n"
            patterns_text += f"   支持度: {pattern['support']} (用户数), "
            patterns_text += f"支持率: {pattern['support'] / statistics.get('total_users', 1) * 100:.1f}%\n"

            # 添加该模式的用户画像分布
            if pattern_key in pattern_profile_stats:
                profile_stats = pattern_profile_stats[pattern_key]
                dist = profile_stats['profile_distribution']

                if dist.get('gender'):
                    gender_str = ', '.join([f"{k}{v}人" for k, v in dist['gender'].items()])
                    patterns_text += f"   用户画像: {gender_str}"

                if dist.get('age'):
                    age_str = ', '.join([f"{k}{v}人" for k, v in dist['age'].items()])
                    patterns_text += f"; {age_str}"

                if dist.get('occupation'):
                    occ_str = ', '.join([f"{k}{v}人" for k, v in list(dist['occupation'].items())[:3]])
                    patterns_text += f"; {occ_str}"

                patterns_text += "\n"

        # 格式化用户示例
        examples_text = ""
        for i, example in enumerate(user_examples[:10], 1):  # 限制10个示例
            examples_text += f"{i}. 用户 {example['user_id']}: {example['sequence']}\n"
            if example['user_id'] in user_profiles:
                profile = user_profiles[example['user_id']]
                examples_text += f"   画像: {profile.get('age')}岁, {profile.get('gender')}, {profile.get('occupation')}\n"

        # 格式化统计数据
        stats_text = f"""
总用户数: {statistics.get('total_users', 0)}
转化用户数: {statistics.get('converted_users', 0)}
整体转化率: {statistics.get('conversion_rate', 0):.2f}%

高频事件转移（前10个）:
"""
        transition_probs = statistics.get('transition_probs', {})
        sorted_transitions = sorted(transition_probs.items(), key=lambda x: x[1]['count'], reverse=True)[:10]
        for (event_a, event_b), data in sorted_transitions:
            stats_text += f"- {event_a} → {event_b}: 概率{data['probability']:.1%}, 出现{data['count']}次\n"

        # 添加显著画像特征
        significant_features = self._find_significant_features(
            statistics.get('pattern_profile_stats', {}),
            statistics
        )

        if significant_features:
            stats_text += "\n显著用户画像特征（相比全局分布差异>=15%）:\n"
            for feature in significant_features[:8]:  # 只显示前8个
                stats_text += f"\n- {feature['feature_name']}:\n"
                for pattern_info in feature['patterns'][:3]:  # 每个特征最多显示3个关联模式
                    stats_text += f"  * 在模式「{pattern_info['pattern']}」中占比{pattern_info['ratio']}% "
                    stats_text += f"(全局{pattern_info['global_ratio']}%, 差异+{pattern_info['diff']}%)\n"

        # 分析重点描述
        focus_desc = {
            "comprehensive": "全面分析用户行为模式、转化路径和流失原因",
            "conversion": "重点分析用户转化路径和影响转化的关键因素",
            "churn": "重点分析用户流失原因和预警信号",
            "profile": "重点分析不同用户画像的行为差异"
        }.get(analysis_focus, "全面分析")

        prompt = f"""你是一个广告营销领域的事理图谱专家。请基于以下高频事件序列模式和真实统计数据，生成一个完整的事理图谱。

## 高频事件序列模式

{patterns_text}

## 真实统计数据

{stats_text}

## 用户示例数据

{examples_text}

## 分析重点

{focus_desc}

## 输出要求

请输出JSON格式的事理图谱，**必须包含三种类型的节点**：

1. **event（事件节点）**：用户的具体行为动作
   - 单次行为：如"浏览车型"、"搜索"、"点击"、"到店"
   - 行为模式：如"多次浏览"、"重复搜索"、"对比行为"（多次对比不同车型）

2. **feature（特征节点）**：用户的画像特征
   - **只能使用上述"显著用户画像特征"中列出的特征**
   - 不要创建未在显著特征列表中出现的画像节点
   - 如果没有显著特征数据，可以不创建feature节点

3. **result（结果节点）**：用户的最终状态或意向
   - 转化结果：如"已购买"、"已加购"、"高购买意向"、"低购买意向"
   - 流失状态：如"已流失"、"流失风险"
   - 注意：**行为模式（如"多次浏览"）不是结果，是event类型**

**图谱结构要求**：
- 事件节点之间用 sequential 关系连接（表示行为序列）
- 特征节点到事件节点用 causal 关系连接（表示特征影响行为）
- 事件节点到结果节点用 causal 或 conditional 关系连接（表示行为导致结果）
- **至少包含2个结果节点**，展示不同的转化路径

输出格式示例：

{{
    "nodes": [
        {{"id": "event_browse_car", "type": "event", "name": "浏览车型", "description": "用户浏览车型列表"}},
        {{"id": "event_multiple_browse", "type": "event", "name": "多次浏览", "description": "用户多次浏览同一车型"}},
        {{"id": "event_compare", "type": "event", "name": "对比车型", "description": "用户对比不同车型"}},
        {{"id": "feature_male", "type": "feature", "name": "男性用户", "description": "用户性别为男性"}},
        {{"id": "feature_age_25_35", "type": "feature", "name": "25-35岁", "description": "年龄在25-35岁之间"}},
        {{"id": "result_high_intent", "type": "result", "name": "高购买意向", "description": "表现出明确的购买意向"}},
        {{"id": "result_purchased", "type": "result", "name": "已购买", "description": "完成购买转化"}},
        {{"id": "result_churn", "type": "result", "name": "已流失", "description": "用户停止互动"}}
    ],
    "edges": [
        {{"from": "event_browse_car", "to": "event_multiple_browse", "relation_type": "sequential", "relation_desc": "浏览后重复浏览", "probability": 0.65, "confidence": 0.80, "support_count": 20}},
        {{"from": "feature_male", "to": "event_browse_car", "relation_type": "causal", "relation_desc": "男性用户更倾向浏览车型", "probability": 0.75, "confidence": 0.85, "support_count": 15}},
        {{"from": "event_compare", "to": "result_high_intent", "relation_type": "causal", "relation_desc": "对比行为表明购买意向", "probability": 0.45, "confidence": 0.70, "support_count": 10}},
        {{"from": "event_browse_car", "to": "result_churn", "relation_type": "conditional", "relation_desc": "仅浏览未深入则可能流失", "probability": 0.30, "confidence": 0.60, "support_count": 8}}
    ],
    "insights": [
        "基于实际数据的洞察示例"
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
4. **概率和置信度必须基于上述真实统计数据**，不要编造数字
5. **support_count 必须使用真实的转移次数或用户数**，不要编造
6. **insights 必须基于真实统计数据**，引用具体数字时必须来自上述统计
7. 不要创建自环边（from和to相同）
8. **不要创建双向边**：如果A→B和B→A都存在，只保留转移次数更多的方向
9. 只输出JSON，不要有其他文字

**重要提醒**：
- 如果统计数据中某个转化率为0%，不要编造成其他数字
- 如果没有某个维度的数据，不要在insights中提及
- 所有概率、百分比必须来自真实统计数据
- Sequential关系表示时间顺序，应该是单向的
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

            # 后处理：清理图谱数据
            graph_data = self._clean_graph_data(graph_data)

            logger.info(f"成功解析事理图谱: {len(graph_data['nodes'])}个节点, {len(graph_data['edges'])}条边")
            return graph_data

        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {e}, 响应: {response[:500]}", exc_info=True)
            return {"error": f"JSON解析失败: {str(e)}", "raw_response": response[:500]}
        except Exception as e:
            logger.error(f"解析事理图谱失败: {e}", exc_info=True)
            return {"error": str(e)}

    def _clean_graph_data(self, graph_data: Dict) -> Dict:
        """清理图谱数据：去除双向边和孤立节点

        Args:
            graph_data: 原始图谱数据

        Returns:
            清理后的图谱数据
        """
        nodes = graph_data.get('nodes', [])
        edges = graph_data.get('edges', [])

        # 1. 去除双向边：对于A→B和B→A，只保留support_count更大的那条
        edge_map = {}  # {(from, to): edge}
        for edge in edges:
            from_node = edge['from']
            to_node = edge['to']
            pair = (from_node, to_node)
            reverse_pair = (to_node, from_node)

            # 如果反向边已存在，比较support_count
            if reverse_pair in edge_map:
                existing_edge = edge_map[reverse_pair]
                # 保留support_count更大的边
                if edge.get('support_count', 0) > existing_edge.get('support_count', 0):
                    del edge_map[reverse_pair]
                    edge_map[pair] = edge
                    logger.info(f"去除双向边: 保留 {from_node}->{to_node} (count={edge.get('support_count')}), "
                              f"删除 {to_node}->{from_node} (count={existing_edge.get('support_count')})")
                else:
                    logger.info(f"去除双向边: 保留 {to_node}->{from_node} (count={existing_edge.get('support_count')}), "
                              f"删除 {from_node}->{to_node} (count={edge.get('support_count')})")
            else:
                edge_map[pair] = edge

        cleaned_edges = list(edge_map.values())

        # 2. 去除孤立节点：找出所有在边中出现的节点
        connected_node_ids = set()
        for edge in cleaned_edges:
            connected_node_ids.add(edge['from'])
            connected_node_ids.add(edge['to'])

        # 保留连接的节点
        cleaned_nodes = [node for node in nodes if node['id'] in connected_node_ids]

        removed_nodes = len(nodes) - len(cleaned_nodes)
        removed_edges = len(edges) - len(cleaned_edges)

        if removed_nodes > 0 or removed_edges > 0:
            logger.info(f"清理图谱: 删除{removed_edges}条边, 删除{removed_nodes}个孤立节点")

        return {
            "nodes": cleaned_nodes,
            "edges": cleaned_edges,
            "insights": graph_data.get("insights", [])
        }

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

            # 3. 计算真实统计数据
            yield {"type": "progress", "message": "正在计算统计数据..."}
            statistics = self._compute_statistics(patterns, user_examples, user_profiles)

            # 4. 构建LLM Prompt
            yield {"type": "progress", "message": "正在构建分析提示词..."}
            prompt = self._build_prompt(patterns, user_examples, user_profiles, analysis_focus, statistics)

            # 5. 流式调用LLM生成事理图谱
            yield {"type": "progress", "message": "正在调用 AI 生成事理图谱..."}

            full_response = ""
            async for chunk in self.llm.chat_completion(prompt, max_tokens=8000, temperature=0.3):
                full_response += chunk
                yield {"type": "content", "content": chunk}

            # 6. 解析JSON结果
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

