"""
内存优化测试脚本

测试高频子序列挖掘的内存使用情况
"""
import sys
import time
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from app.services.sequence_mining import SequenceMiningService
from app.core.memory_monitor import memory_monitor
from app.core.logger import app_logger


def test_mining_with_memory_monitoring():
    """测试挖掘功能并监控内存使用"""

    print("=" * 60)
    print("高频子序列挖掘 - 内存优化测试")
    print("=" * 60)

    service = SequenceMiningService()

    # 测试场景1: 小数据集
    print("\n[测试1] 小数据集 (使用现有数据)")
    memory_monitor.log_memory_usage("测试开始")

    start_time = time.time()

    try:
        result = service.mine_frequent_subsequences(
            algorithm="prefixspan",
            min_support=2,
            max_length=3,
            top_k=20,
            use_cache=False  # 禁用缓存以测试真实性能
        )

        elapsed = time.time() - start_time

        print(f"\n✓ 挖掘完成")
        print(f"  - 处理序列数: {result['statistics']['total_sequences']}")
        print(f"  - 找到模式数: {result['statistics']['patterns_found']}")
        print(f"  - 耗时: {elapsed:.2f}秒")

        memory_monitor.log_memory_usage("测试完成")

        # 显示前5个模式
        print(f"\n前5个高频模式:")
        for i, pattern in enumerate(result['frequent_patterns'][:5], 1):
            print(f"  {i}. {' -> '.join(pattern['pattern'])} (支持度: {pattern['support']})")

    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()

    # 测试场景2: Attention算法
    print("\n" + "=" * 60)
    print("[测试2] Attention算法")
    memory_monitor.log_memory_usage("测试开始")

    start_time = time.time()

    try:
        result = service.mine_frequent_subsequences(
            algorithm="attention",
            min_support=2,
            max_length=3,
            top_k=20,
            use_cache=False
        )

        elapsed = time.time() - start_time

        print(f"\n✓ 挖掘完成")
        print(f"  - 处理序列数: {result['statistics']['total_sequences']}")
        print(f"  - 找到模式数: {result['statistics']['patterns_found']}")
        print(f"  - 耗时: {elapsed:.2f}秒")

        memory_monitor.log_memory_usage("测试完成")

    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()

    # 最终内存报告
    print("\n" + "=" * 60)
    print("最终内存使用报告")
    print("=" * 60)
    usage = memory_monitor.get_memory_usage()
    print(f"物理内存 (RSS): {usage['rss_mb']:.1f} MB")
    print(f"虚拟内存 (VMS): {usage['vms_mb']:.1f} MB")
    print(f"内存占用率: {usage['percent']:.1f}%")

    if usage['rss_mb'] < 2048:
        print("\n✓ 内存使用正常 (< 2GB)")
    elif usage['rss_mb'] < 4096:
        print("\n⚠ 内存使用偏高 (2-4GB)")
    else:
        print("\n✗ 内存使用过高 (> 4GB)")


if __name__ == "__main__":
    test_mining_with_memory_monitoring()
