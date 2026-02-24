"""
高频子序列挖掘服务
"""
import sqlite3
import json
import gc
from typing import List, Dict, Tuple, Optional, Iterator
from pathlib import Path
from collections import Counter
from app.core.logger import app_logger
from app.core.cache_service import SequenceCacheService
from app.core.memory_monitor import memory_monitor


class SequenceMiningService:
    """高频子序列挖掘服务 - 基于事件序列数据"""

    def __init__(self):
        self.db_path = Path("data/graph.db")
        self.cache = SequenceCacheService()  # 添加缓存服务

    def mine_frequent_subsequences(
        self,
        algorithm: str = "prefixspan",  # "prefixspan" 或 "attention"
        min_support: int = 2,
        min_length: int = 2,  # 最小序列长度
        max_length: int = 5,
        top_k: int = 20,
        target_label: Optional[str] = None,  # 目标结果标签（如"首购"、"换车"等）
        target_events: Optional[List[str]] = None,  # 目标事件列表（如["购买", "加购"]）
        use_cache: bool = True  # 是否使用缓存
    ) -> Dict:
        """挖掘高频事件子序列

        Args:
            algorithm: 算法类型 ("prefixspan" 或 "attention")
            min_support: 最小支持度(出现次数)
            min_length: 最小序列长度
            max_length: 最大序列长度
            top_k: 返回前K个模式
            target_label: 目标结果标签（如"首购"、"换车"、"观望"等），为None时挖掘所有用户
            target_events: 目标事件列表（如["购买", "加购"]），为None时挖掘所有序列
            use_cache: 是否使用缓存

        Returns:
            {
                "algorithm": "prefixspan",
                "frequent_patterns": [...],
                "statistics": {...}
            }
        """
        try:
            # 尝试从缓存获取
            if use_cache:
                # 将target_events转为字符串用于缓存键
                target_events_str = ','.join(sorted(target_events)) if target_events else None
                cached_result = self.cache.get_patterns(
                    min_support,
                    max_length,
                    target_label,
                    target_events_str,
                    None  # 不再使用 target_category
                )
                if cached_result:
                    app_logger.info(f"从缓存获取模式: min_support={min_support}, max_length={max_length}, target_label={target_label}, target_events={target_events}")
                    # 过滤缓存结果中的模式长度
                    cached_result["frequent_patterns"] = [
                        p for p in cached_result["frequent_patterns"]
                        if min_length <= p["length"] <= max_length
                    ]
                    cached_result["statistics"]["patterns_found"] = len(cached_result["frequent_patterns"])
                    return cached_result

            app_logger.info(f"开始挖掘高频子序列: algorithm={algorithm}, min_support={min_support}, min_length={min_length}, max_length={max_length}, target_label={target_label}, target_events={target_events}")
            memory_monitor.log_memory_usage("挖掘开始")

            # 1. 从数据库加载所有用户的事件序列 (限制50,000条)
            sequences, stats = self._load_event_sequences(
                limit=50000,
                target_label=target_label,
                target_events=target_events
            )

            if not sequences:
                app_logger.warning("没有找到事件序列数据")
                return {
                    "algorithm": algorithm,
                    "frequent_patterns": [],
                    "statistics": {
                        "total_users": 0,
                        "total_sequences": 0,
                        "unique_event_types": 0
                    }
                }

            app_logger.info(f"加载了 {len(sequences)} 个用户的事件序列")
            memory_monitor.log_memory_usage("序列加载完成")

            # 2. 根据算法类型选择挖掘方法
            if algorithm == "prefixspan":
                frequent_patterns = self._mine_with_prefixspan(sequences, min_support, max_length)
            elif algorithm == "attention":
                frequent_patterns = self._mine_with_attention(sequences, min_support, max_length)
            else:
                raise ValueError(f"不支持的算法类型: {algorithm}")

            memory_monitor.log_memory_usage("模式挖掘完成")

            # 3. 格式化结果并过滤长度，然后取前K个
            formatted_patterns = self._format_patterns(frequent_patterns, len(sequences))

            # 过滤最小长度
            formatted_patterns = [p for p in formatted_patterns if p["length"] >= min_length]

            # 如果指定了目标事件，只保留以目标事件结尾的模式
            if target_events:
                formatted_patterns = [
                    p for p in formatted_patterns
                    if p["pattern"][-1] in target_events
                ]
                app_logger.info(f"过滤后保留以{target_events}结尾的模式: {len(formatted_patterns)}个")

            formatted_patterns = formatted_patterns[:top_k]

            # 4. 计算统计信息
            all_events = [event for seq in sequences for event in seq]
            unique_events = set(all_events)

            statistics = {
                "total_users": len(sequences),
                "total_sequences": len(sequences),
                "unique_event_types": len(unique_events),
                "avg_sequence_length": round(sum(len(seq) for seq in sequences) / len(sequences), 2) if sequences else 0,
                "min_support": min_support,
                "min_length": min_length,
                "max_length": max_length,
                "patterns_found": len(formatted_patterns),
                "target_label": target_label,  # 添加目标标签信息
                "target_events": target_events,  # 添加目标事件信息
                **stats  # 合并加载序列时的统计信息
            }

            result = {
                "algorithm": algorithm,
                "frequent_patterns": formatted_patterns,
                "statistics": statistics
            }

            # 缓存结果
            if use_cache:
                target_events_str = ','.join(sorted(target_events)) if target_events else None
                self.cache.set_patterns(
                    result,
                    min_support,
                    max_length,
                    target_label,
                    target_events_str,
                    None,  # 不再使用 target_category
                    ttl=600
                )

            app_logger.info(f"✓ 高频子序列挖掘完成: 找到 {len(formatted_patterns)} 个模式")

            return result

        except Exception as e:
            app_logger.error(f"高频子序列挖掘失败: {type(e).__name__}: {str(e)}", exc_info=True)
            raise

    def _mine_with_prefixspan(
        self,
        sequences: List[List[str]],
        min_support: int,
        max_length: int
    ) -> List[Tuple[int, List[str]]]:
        """使用 PrefixSpan 算法挖掘频繁模式"""
        try:
            from prefixspan import PrefixSpan
            ps = PrefixSpan(sequences)
            # PrefixSpan库不支持maxlen参数,需要手动过滤
            frequent_patterns = ps.frequent(minsup=min_support)
            # 过滤掉超过最大长度的模式
            filtered_patterns = [
                (support, pattern)
                for support, pattern in frequent_patterns
                if len(pattern) <= max_length
            ]
            app_logger.info(f"PrefixSpan 挖掘完成: 找到 {len(filtered_patterns)} 个频繁模式")
            return filtered_patterns
        except ImportError:
            app_logger.warning("PrefixSpan 库未安装,使用简单频繁项集挖掘")
            return self._simple_frequent_mining(sequences, min_support, max_length)

    def _mine_with_attention(
        self,
        sequences: List[List[str]],
        min_support: int,
        max_length: int
    ) -> List[Tuple[int, List[str]]]:
        """使用 Attention 权重挖掘频繁模式 - 流式处理版本

        注: 这是一个简化实现,真正的 Attention 需要训练 Transformer 模型
        这里使用共现频率作为 Attention 权重的近似
        """
        app_logger.info("使用 Attention 权重方法挖掘频繁模式")

        batch_size = 2000
        total_batches = (len(sequences) + batch_size - 1) // batch_size

        # 第一阶段: 分批计算事件对的共现频率
        cooccurrence = Counter()
        for batch_idx in range(total_batches):
            start_idx = batch_idx * batch_size
            end_idx = min(start_idx + batch_size, len(sequences))
            batch = sequences[start_idx:end_idx]

            for seq in batch:
                for i in range(len(seq)):
                    for j in range(i + 1, min(i + max_length, len(seq))):
                        cooccurrence[(seq[i], seq[j])] += 1

            # 定期检查内存
            if (batch_idx + 1) % 5 == 0:
                memory_monitor.check_memory()
                if memory_monitor.is_memory_critical():
                    app_logger.error("内存使用达到严重阈值,提前终止共现计算")
                    break

        app_logger.info(f"共现矩阵计算完成: {len(cooccurrence)} 个事件对")

        # 第二阶段: 分批构建频繁模式
        pattern_counts = Counter()
        for batch_idx in range(total_batches):
            start_idx = batch_idx * batch_size
            end_idx = min(start_idx + batch_size, len(sequences))
            batch = sequences[start_idx:end_idx]

            for seq in batch:
                # 生成所有可能的子序列
                for length in range(2, min(len(seq) + 1, max_length + 1)):
                    for i in range(len(seq) - length + 1):
                        subseq = tuple(seq[i:i + length])

                        # 计算子序列的 Attention 权重(基于共现频率)
                        attention_weight = 0
                        for k in range(len(subseq) - 1):
                            attention_weight += cooccurrence.get((subseq[k], subseq[k + 1]), 0)

                        # 只保留高权重的子序列
                        if attention_weight >= min_support:
                            pattern_counts[subseq] += 1

            # 每处理5批后,过滤低频模式
            if (batch_idx + 1) % 5 == 0:
                before_count = len(pattern_counts)
                pattern_counts = Counter({
                    pattern: count
                    for pattern, count in pattern_counts.items()
                    if count >= min_support or count >= (batch_idx + 1) * batch_size * 0.001
                })
                after_count = len(pattern_counts)
                app_logger.info(f"批次 {batch_idx + 1}/{total_batches}: 过滤模式 {before_count} -> {after_count}")

                gc.collect()
                memory_monitor.check_memory()
                if memory_monitor.is_memory_critical():
                    app_logger.error("内存使用达到严重阈值,提前终止模式挖掘")
                    break

        # 过滤出频繁模式
        frequent = [
            (count, list(pattern))
            for pattern, count in pattern_counts.items()
            if count >= min_support
        ]

        # 按支持度降序排序
        frequent.sort(reverse=True, key=lambda x: x[0])

        app_logger.info(f"Attention 方法挖掘完成: 找到 {len(frequent)} 个频繁模式")
        return frequent

    def _normalize_event_type(self, event_type: str) -> str:
        """标准化事件类型名称

        Args:
            event_type: 原始事件类型

        Returns:
            标准化后的事件类型
        """
        normalized = event_type.strip()

        # 同义词映射
        synonyms = {
            '使用app': '使用APP',
            '使用': '使用APP',
            'app活跃': '活跃',
            '使用App': '使用APP',
            '打开app': '打开APP',
            '打开App': '打开APP',
            '使用app': '使用APP'
        }

        return synonyms.get(normalized, normalized)

    def _load_event_sequences(
        self,
        limit: Optional[int] = None,
        offset: int = 0,
        target_label: Optional[str] = None,  # 目标结果标签
        target_events: Optional[List[str]] = None,  # 目标事件列表
        use_cache: bool = True
    ) -> Tuple[List[List[str]], Dict]:
        """从数据库加载所有用户的事件序列 - 优化版本

        使用分批加载事件详情来减少内存占用

        Args:
            limit: 限制返回数量
            offset: 偏移量
            target_label: 目标结果标签（如"首购"、"换车"等），为None时加载所有用户
            target_events: 目标事件列表（如["购买", "加购"]），为None时挖掘所有序列
            use_cache: 是否使用缓存

        Returns:
            (sequences, statistics)
            - sequences: [[event_type1, event_type2, ...], ...]
            - statistics: {
                "label_distribution": {"首购": 10, "换车": 5, ...},
                "target_users": 50  # 包含目标事件的用户数
              }
        """
        # 尝试从缓存获取
        if use_cache and limit and offset == 0:
            cached_sequences = self.cache.get_sequences(limit)
            if cached_sequences:
                app_logger.info(f"从缓存获取序列: limit={limit}")
                return cached_sequences

        sequences = []
        label_distribution = {}
        target_users = 0

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # 构建查询 - 只加载成功状态且非空的序列，并关联用户标签
            if target_label:
                # 过滤特定标签的用户
                query = """
                    SELECT es.user_id, es.sequence, up.properties
                    FROM event_sequences es
                    JOIN user_profiles up ON es.user_id = up.user_id
                    WHERE es.status = 'success' AND es.sequence != '[]'
                    ORDER BY es.user_id
                """
            else:
                # 加载所有用户，但仍然获取标签信息用于统计
                query = """
                    SELECT es.user_id, es.sequence, up.properties
                    FROM event_sequences es
                    LEFT JOIN user_profiles up ON es.user_id = up.user_id
                    WHERE es.status = 'success' AND es.sequence != '[]'
                    ORDER BY es.user_id
                """

            if limit:
                query += f" LIMIT {limit}"
            if offset:
                query += f" OFFSET {offset}"

            cursor.execute(query)
            all_rows = cursor.fetchall()

            # 第一遍：过滤用户并统计标签分布
            filtered_rows = []
            for row in all_rows:
                user_id = row[0]
                sequence_json = row[1]
                properties_json = row[2]

                # 解析用户标签
                user_label = None
                if properties_json:
                    try:
                        properties = json.loads(properties_json)
                        user_label = properties.get('purchase_intent', 'unknown')
                    except:
                        user_label = 'unknown'
                else:
                    user_label = 'unknown'

                # 统计标签分布
                label_distribution[user_label] = label_distribution.get(user_label, 0) + 1

                # 如果指定了目标标签，只保留匹配的用户
                if target_label is None or user_label == target_label:
                    filtered_rows.append((user_id, sequence_json))

            app_logger.info(f"标签过滤: 总用户数={len(all_rows)}, 目标标签={target_label}, 过滤后={len(filtered_rows)}")
            app_logger.info(f"标签分布: {label_distribution}")

            # 收集所有需要查询的event_id
            all_event_ids = []
            for row in filtered_rows:
                event_ids = json.loads(row[1])

                # 类型检查：确保 event_ids 是字符串列表
                if isinstance(event_ids, list):
                    # 过滤出字符串类型的 event_id
                    valid_event_ids = [
                        eid for eid in event_ids
                        if isinstance(eid, str)
                    ]

                    # 如果列表中包含字典（错误格式），记录警告
                    if len(valid_event_ids) < len(event_ids):
                        app_logger.warning(
                            f"用户 {row[0]} 的 sequence 字段包含非字符串元素，"
                            f"已过滤 {len(event_ids) - len(valid_event_ids)} 个无效元素"
                        )

                    all_event_ids.extend(valid_event_ids)
                else:
                    app_logger.error(f"用户 {row[0]} 的 sequence 字段格式错误: {type(event_ids)}")

            # 分批查询事件详情 (每批10000个ID)
            event_map = {}
            if all_event_ids:
                batch_size = 10000
                total_ids = len(all_event_ids)
                app_logger.info(f"分批加载 {total_ids} 个事件详情")

                for i in range(0, total_ids, batch_size):
                    batch_ids = all_event_ids[i:i + batch_size]
                    placeholders = ','.join('?' * len(batch_ids))
                    cursor.execute(f"""
                        SELECT event_id, event_type, event_category
                        FROM extracted_events
                        WHERE event_id IN ({placeholders})
                    """, batch_ids)

                    # 更新event_map - 现在包含事件类型和分类
                    for row in cursor.fetchall():
                        event_map[row[0]] = (row[1], row[2] or 'engagement')

                    # 定期检查内存
                    if (i // batch_size + 1) % 5 == 0:
                        memory_monitor.check_memory()

                app_logger.info(f"事件详情加载完成: {len(event_map)} 个事件")

            # 构建序列并截取到目标事件
            for row in filtered_rows:
                user_id = row[0]
                event_ids = json.loads(row[1])

                # 类型检查：确保 event_ids 是字符串列表
                if not isinstance(event_ids, list):
                    app_logger.error(f"用户 {user_id} 的 sequence 字段格式错误: {type(event_ids)}")
                    continue

                # 过滤出字符串类型的 event_id
                valid_event_ids = [eid for eid in event_ids if isinstance(eid, str)]

                # 从字典中查找事件类型
                full_sequence = []
                target_index = -1

                for idx, event_id in enumerate(valid_event_ids):
                    event_info = event_map.get(event_id)
                    if not event_info:
                        continue

                    event_type, category = event_info

                    # 事件标准化
                    event_type = self._normalize_event_type(event_type)
                    full_sequence.append(event_type)

                    # 检查是否匹配目标事件列表
                    if target_events and event_type in target_events and target_index == -1:
                        # 记录在 full_sequence 中的索引位置
                        target_index = len(full_sequence) - 1

                # 过滤和截取
                if target_events:
                    if target_index >= 0:
                        # 截取到目标事件（包含目标）
                        truncated_sequence = full_sequence[:target_index + 1]
                        sequences.append(truncated_sequence)
                        target_users += 1
                else:
                    if full_sequence:
                        sequences.append(full_sequence)

        # 缓存结果（注意：缓存时不包含标签信息，避免缓存失效）
        if use_cache and limit and offset == 0 and target_label is None and target_events is None:
            self.cache.set_sequences(sequences, limit, ttl=300)

        statistics = {
            "label_distribution": label_distribution,
            "target_users": target_users
        }

        return sequences, statistics

    def _simple_frequent_mining(
        self,
        sequences: List[List[str]],
        min_support: int,
        max_length: int
    ) -> List[Tuple[int, List[str]]]:
        """简单的频繁子序列挖掘(当 PrefixSpan 不可用时) - 流式处理版本

        使用批处理和增量过滤来控制内存使用

        注意：支持度 = 包含该模式的用户数（每个用户最多计数一次）

        Returns:
            [(support, pattern), ...]
        """
        pattern_counts = Counter()
        batch_size = 2000  # 每批处理2000个序列
        total_batches = (len(sequences) + batch_size - 1) // batch_size

        app_logger.info(f"开始流式挖掘: {len(sequences)}个序列, 分{total_batches}批处理")

        # 分批处理序列
        for batch_idx in range(total_batches):
            start_idx = batch_idx * batch_size
            end_idx = min(start_idx + batch_size, len(sequences))
            batch = sequences[start_idx:end_idx]

            # 处理当前批次
            for seq in batch:
                # 对于每个序列，记录其包含的所有唯一子序列
                seen_patterns = set()

                # 生成长度为 1 到 max_length 的所有子序列
                for length in range(1, min(len(seq) + 1, max_length + 1)):
                    for i in range(len(seq) - length + 1):
                        subseq = tuple(seq[i:i + length])
                        seen_patterns.add(subseq)

                # 对该用户包含的每个模式计数一次
                for pattern in seen_patterns:
                    pattern_counts[pattern] += 1

            # 每处理5批后,过滤掉低频模式以释放内存
            if (batch_idx + 1) % 5 == 0:
                before_count = len(pattern_counts)
                pattern_counts = Counter({
                    pattern: count
                    for pattern, count in pattern_counts.items()
                    if count >= min_support or count >= (batch_idx + 1) * batch_size * 0.001  # 保留有潜力的模式
                })
                after_count = len(pattern_counts)
                app_logger.info(f"批次 {batch_idx + 1}/{total_batches}: 过滤模式 {before_count} -> {after_count}")

                # 触发垃圾回收
                gc.collect()

                # 检查内存
                memory_monitor.check_memory()
                if memory_monitor.is_memory_critical():
                    app_logger.error("内存使用达到严重阈值,提前终止挖掘")
                    break

        # 最终过滤出频繁模式
        frequent = [
            (count, list(pattern))
            for pattern, count in pattern_counts.items()
            if count >= min_support
        ]

        # 按支持度降序排序
        frequent.sort(reverse=True, key=lambda x: x[0])

        app_logger.info(f"挖掘完成: 找到 {len(frequent)} 个频繁模式")
        return frequent

    def _format_patterns(
        self,
        patterns: List[Tuple[int, List[str]]],
        total_sequences: int
    ) -> List[Dict]:
        """格式化频繁模式结果

        Args:
            patterns: [(support, pattern), ...]
            total_sequences: 总序列数

        Returns:
            格式化后的模式列表
        """
        formatted = []

        for support, pattern in patterns:
            # 跳过单个事件的模式(长度为1)
            if len(pattern) <= 1:
                continue

            # 支持率 = 支持度 / 总用户数 * 100
            support_rate = (support / total_sequences * 100) if total_sequences > 0 else 0

            formatted.append({
                "pattern": pattern,
                "support": support,  # 支持度 = 包含该模式的用户数
                "support_rate": round(support_rate, 2),  # 支持率（百分比）
                "length": len(pattern),
                "description": self._generate_pattern_description(pattern)
            })

        # 按支持度降序排序
        formatted.sort(key=lambda x: x["support"], reverse=True)

        return formatted

    def _generate_pattern_description(self, pattern: List[str]) -> str:
        """生成模式的自然语言描述

        Args:
            pattern: 事件类型列表

        Returns:
            描述文本
        """
        if len(pattern) == 2:
            return f"用户在{pattern[0]}后,通常会{pattern[1]}"
        elif len(pattern) == 3:
            return f"用户{pattern[0]} → {pattern[1]} → {pattern[2]}的行为路径"
        else:
            return f"{' → '.join(pattern[:3])}...的{len(pattern)}步行为序列"

    def save_patterns(
        self,
        patterns: List[Dict],
        algorithm: str,
        min_support: int
    ) -> Dict:
        """保存用户确认的高频模式到数据库

        Args:
            patterns: 要保存的模式列表
            algorithm: 使用的算法
            min_support: 最小支持度

        Returns:
            保存结果
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 表由 persistence.py 统一管理，这里不再重复创建
                # 使用与 persistence.py 一致的列名 pattern_sequence

                saved_count = 0
                for pattern_data in patterns:
                    pattern = pattern_data.get("pattern", [])
                    pattern_str = json.dumps(pattern, ensure_ascii=False)

                    cursor.execute("""
                        SELECT id FROM frequent_patterns
                        WHERE pattern_sequence = ?
                    """, (pattern_str,))

                    if cursor.fetchone():
                        app_logger.info(f"模式 {pattern} 已存在,跳过")
                        continue

                    frequency = pattern_data.get("frequency") or pattern_data.get("support_rate", 0.0)

                    cursor.execute("""
                        INSERT INTO frequent_patterns
                        (pattern_sequence, support, confidence, occurrence_count, user_count, pattern_id)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        pattern_str,
                        pattern_data.get("support", 0),
                        frequency,
                        pattern_data.get("support", 0),  # occurrence_count
                        pattern_data.get("support", 0),  # user_count
                        f"pattern_{hash(pattern_str)}"  # pattern_id
                    ))
                    saved_count += 1

                conn.commit()

            app_logger.info(f"✓ 成功保存 {saved_count} 个高频模式")

            return {
                "saved_count": saved_count,
                "total_patterns": len(patterns)
            }

        except Exception as e:
            app_logger.error(f"保存模式失败: {e}", exc_info=True)
            raise

    def get_saved_patterns(self, limit: int = 100, offset: int = 0) -> Dict:
        """查询已保存的高频模式

        Args:
            limit: 返回数量
            offset: 偏移量

        Returns:
            模式列表和统计信息
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 查询总数
                cursor.execute("SELECT COUNT(*) FROM frequent_patterns")
                total = cursor.fetchone()[0]

                # 查询模式列表
                cursor.execute("""
                    SELECT id, pattern_sequence, support, confidence, occurrence_count, user_count, pattern_id, created_at
                    FROM frequent_patterns
                    ORDER BY support DESC, created_at DESC
                    LIMIT ? OFFSET ?
                """, (limit, offset))

                patterns = []
                for row in cursor.fetchall():
                    pattern_data = {
                        "id": row[0],
                        "pattern": json.loads(row[1]),
                        "support": row[2],
                        "frequency": row[3],  # confidence 映射为 frequency
                        "length": len(json.loads(row[1])),
                        "description": "",  # 旧字段，保留兼容性
                        "algorithm": "PrefixSpan",  # 默认算法
                        "min_support": row[2],  # 使用 support 作为 min_support
                        "created_at": row[7],
                        "user_count": row[5]
                    }
                    patterns.append(pattern_data)

            return {
                "patterns": patterns,
                "total": total,
                "limit": limit,
                "offset": offset
            }

        except Exception as e:
            app_logger.error(f"查询保存的模式失败: {e}", exc_info=True)
            raise

    def delete_pattern(self, pattern_id: int):
        """删除已保存的模式

        Args:
            pattern_id: 模式ID
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM frequent_patterns WHERE id = ?", (pattern_id,))
                conn.commit()

            app_logger.info(f"✓ 删除模式 {pattern_id}")

        except Exception as e:
            app_logger.error(f"删除模式失败: {e}", exc_info=True)
            raise

    def get_event_types(self) -> List[Dict]:
        """获取所有事件类型列表

        Returns:
            事件类型列表，按出现频率降序排序
            [
                {"event_type": "浏览车型", "count": 1306},
                {"event_type": "搜索", "count": 629},
                ...
            ]
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT event_type, COUNT(*) as count
                    FROM extracted_events
                    GROUP BY event_type
                    ORDER BY count DESC
                """)

                event_types = []
                for row in cursor.fetchall():
                    event_types.append({
                        "event_type": row[0],
                        "count": row[1]
                    })

                app_logger.info(f"✓ 查询到 {len(event_types)} 种事件类型")
                return event_types

        except Exception as e:
            app_logger.error(f"查询事件类型失败: {e}", exc_info=True)
            raise

    def get_pattern_examples(
        self,
        pattern: List[str],
        limit: int = 5,
        max_scan: int = 1000
    ) -> List[Dict]:
        """获取某个模式的具体用户示例

        Args:
            pattern: 事件类型序列
            limit: 返回示例数量
            max_scan: 最大扫描序列数（默认1000，最大10000）

        Returns:
            用户示例列表
        """
        # 限制最大扫描数，防止性能问题
        if max_scan > 10000:
            max_scan = 10000

        examples = []

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # 查询事件序列（使用可配置的限制）
            cursor.execute("""
                SELECT user_id, sequence
                FROM event_sequences
                LIMIT ?
            """, (max_scan,))

            all_rows = cursor.fetchall()

            # 收集所有需要查询的event_id
            all_event_ids = []
            for row in all_rows:
                event_ids = json.loads(row[1])
                all_event_ids.extend(event_ids)

            # 批量查询所有事件（一次查询，避免N+1问题）
            event_map = {}
            if all_event_ids:
                placeholders = ','.join('?' * len(all_event_ids))
                cursor.execute(f"""
                    SELECT event_id, event_type, timestamp, context
                    FROM extracted_events
                    WHERE event_id IN ({placeholders})
                """, all_event_ids)

                for row in cursor.fetchall():
                    event_map[row[0]] = {
                        "event_type": row[1],
                        "timestamp": row[2],
                        "context": json.loads(row[3]) if row[3] else {}
                    }

            # 构建示例
            for row in all_rows:
                if len(examples) >= limit:
                    break

                user_id = row[0]
                event_ids = json.loads(row[1])

                # 从字典中查找事件信息（O(1)查找）
                event_types = []
                event_details = []

                for event_id in event_ids:
                    event_info = event_map.get(event_id)
                    if event_info:
                        event_types.append(event_info["event_type"])
                        event_details.append({
                            "event_type": event_info["event_type"],
                            "timestamp": event_info["timestamp"],
                            "context": event_info["context"]
                        })

                # 检查是否包含目标模式
                if self._contains_pattern(event_types, pattern):
                    examples.append({
                        "user_id": user_id,
                        "sequence": event_types,  # 添加完整的事件类型序列
                        "events": event_details   # 保留详细信息
                    })

        return examples

    def _contains_pattern(self, sequence: List[str], pattern: List[str]) -> bool:
        """检查序列是否包含指定模式(子序列)

        Args:
            sequence: 完整序列
            pattern: 要查找的模式

        Returns:
            是否包含
        """
        pattern_len = len(pattern)
        for i in range(len(sequence) - pattern_len + 1):
            if sequence[i:i + pattern_len] == pattern:
                return True
        return False
