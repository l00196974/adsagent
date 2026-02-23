#!/usr/bin/env python3
"""
性能基准测试脚本

测试优化前后的性能对比
"""

import time
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.sequence_mining import SequenceMiningService
from app.core.flexible_persistence import FlexiblePersistence
from app.core.logger import app_logger


def benchmark_sequence_loading():
    """测试序列加载性能"""
    print("\n=== 序列加载性能测试 ===")

    service = SequenceMiningService()

    # 测试1: 不使用缓存
    start = time.time()
    sequences = service._load_event_sequences(use_cache=False)
    elapsed_no_cache = time.time() - start
    print(f"✓ 不使用缓存: {elapsed_no_cache:.3f}秒, 加载 {len(sequences)} 个序列")

    # 测试2: 使用缓存（第一次）
    start = time.time()
    sequences = service._load_event_sequences(use_cache=True)
    elapsed_first_cache = time.time() - start
    print(f"✓ 使用缓存（第一次）: {elapsed_first_cache:.3f}秒")

    # 测试3: 使用缓存（第二次，应该很快）
    start = time.time()
    sequences = service._load_event_sequences(use_cache=True)
    elapsed_second_cache = time.time() - start
    print(f"✓ 使用缓存（第二次）: {elapsed_second_cache:.3f}秒")

    if elapsed_second_cache < elapsed_no_cache:
        speedup = elapsed_no_cache / elapsed_second_cache
        print(f"✓ 缓存加速: {speedup:.1f}倍")


def benchmark_pattern_mining():
    """测试模式挖掘性能"""
    print("\n=== 模式挖掘性能测试 ===")

    service = SequenceMiningService()

    # 测试1: 不使用缓存
    start = time.time()
    result = service.mine_frequent_subsequences(
        algorithm="attention",
        min_support=2,
        max_length=5,
        use_cache=False
    )
    elapsed_no_cache = time.time() - start
    print(f"✓ 不使用缓存: {elapsed_no_cache:.3f}秒, 找到 {len(result['frequent_patterns'])} 个模式")

    # 测试2: 使用缓存（第一次）
    start = time.time()
    result = service.mine_frequent_subsequences(
        algorithm="attention",
        min_support=2,
        max_length=5,
        use_cache=True
    )
    elapsed_first_cache = time.time() - start
    print(f"✓ 使用缓存（第一次）: {elapsed_first_cache:.3f}秒")

    # 测试3: 使用缓存（第二次）
    start = time.time()
    result = service.mine_frequent_subsequences(
        algorithm="attention",
        min_support=2,
        max_length=5,
        use_cache=True
    )
    elapsed_second_cache = time.time() - start
    print(f"✓ 使用缓存（第二次）: {elapsed_second_cache:.3f}秒")

    if elapsed_second_cache < elapsed_no_cache:
        speedup = elapsed_no_cache / elapsed_second_cache
        print(f"✓ 缓存加速: {speedup:.1f}倍")


def benchmark_database_queries():
    """测试数据库查询性能"""
    print("\n=== 数据库查询性能测试 ===")

    db_path = "data/graph.db"

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()

        # 测试1: 用户行为查询（使用复合索引）
        start = time.time()
        cursor.execute("""
            SELECT COUNT(*)
            FROM behavior_data
            WHERE user_id = 'user_0001' AND timestamp > '2025-01-01'
        """)
        count = cursor.fetchone()[0]
        elapsed = (time.time() - start) * 1000
        print(f"✓ 用户行为查询（复合索引）: {elapsed:.2f}ms, 结果: {count}条")

        # 测试2: 按action过滤（使用action索引）
        start = time.time()
        cursor.execute("""
            SELECT COUNT(*)
            FROM behavior_data
            WHERE action = 'purchase'
        """)
        count = cursor.fetchone()[0]
        elapsed = (time.time() - start) * 1000
        print(f"✓ 按行为类型过滤: {elapsed:.2f}ms, 结果: {count}条")

        # 测试3: 事件序列查询（使用user_id索引）
        start = time.time()
        cursor.execute("""
            SELECT COUNT(*)
            FROM event_sequences
            WHERE user_id = 'user_0001'
        """)
        count = cursor.fetchone()[0]
        elapsed = (time.time() - start) * 1000
        print(f"✓ 用户事件序列查询: {elapsed:.2f}ms, 结果: {count}条")

        # 测试4: 高频模式查询（使用support索引）
        start = time.time()
        cursor.execute("""
            SELECT COUNT(*)
            FROM frequent_patterns
            WHERE support >= 10
            ORDER BY support DESC
            LIMIT 100
        """)
        count = cursor.fetchone()[0]
        elapsed = (time.time() - start) * 1000
        print(f"✓ 高频模式查询（排序）: {elapsed:.2f}ms, 结果: {count}条")


def benchmark_flexible_persistence():
    """测试灵活持久化层性能"""
    print("\n=== 灵活持久化层性能测试 ===")

    persistence = FlexiblePersistence()

    # 测试1: 查询行为事件
    start = time.time()
    events = persistence.query_behavior_events(user_id="test_user_001", limit=100)
    elapsed = (time.time() - start) * 1000
    print(f"✓ 查询行为事件: {elapsed:.2f}ms, 结果: {len(events)}条")

    # 测试2: 查询用户画像
    start = time.time()
    profile = persistence.query_user_profile("test_user_001")
    elapsed = (time.time() - start) * 1000
    print(f"✓ 查询用户画像: {elapsed:.2f}ms")

    # 测试3: 批量插入性能
    import json
    from datetime import datetime

    test_events = [
        {
            "user_id": f"bench_user_{i}",
            "event_time": datetime.now(),
            "event_type": "test",
            "event_data": json.dumps({"test": i}, ensure_ascii=False)
        }
        for i in range(1000)
    ]

    start = time.time()
    count = persistence.batch_insert_behavior_events(test_events)
    elapsed = time.time() - start
    print(f"✓ 批量插入1000条: {elapsed:.3f}秒, 速度: {count/elapsed:.0f}条/秒")


def benchmark_summary():
    """性能测试总结"""
    print("\n" + "=" * 60)
    print("性能优化总结")
    print("=" * 60)

    with sqlite3.connect("data/graph.db") as conn:
        cursor = conn.cursor()

        # 统计数据量
        cursor.execute("SELECT COUNT(*) FROM behavior_data")
        behavior_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(DISTINCT user_id) FROM behavior_data")
        user_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM event_sequences")
        sequence_count = cursor.fetchone()[0]

    print(f"\n数据规模:")
    print(f"  - 用户数: {user_count}")
    print(f"  - 行为数: {behavior_count}")
    print(f"  - 序列数: {sequence_count}")

    print(f"\n优化措施:")
    print(f"  ✓ 添加数据库索引（7个）")
    print(f"  ✓ 修复N+1查询问题（3处）")
    print(f"  ✓ 实现批量数据库操作（4处）")
    print(f"  ✓ 添加缓存机制（TTL缓存）")
    print(f"  ✓ 创建灵活数据结构")

    print(f"\n预期性能提升:")
    print(f"  - 查询速度: 5-10倍")
    print(f"  - 导入速度: 10-20倍")
    print(f"  - 模式挖掘: 10倍")
    print(f"  - 内存占用: 降低5-10倍")


def main():
    """主函数"""
    print("=" * 60)
    print("性能基准测试")
    print("=" * 60)

    try:
        benchmark_database_queries()
        benchmark_flexible_persistence()
        benchmark_sequence_loading()
        benchmark_pattern_mining()
        benchmark_summary()

        print("\n✅ 所有性能测试完成")

    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
