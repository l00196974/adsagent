#!/usr/bin/env python3
"""测试 LLM API 响应格式"""
import asyncio
import sys
sys.path.insert(0, '.')

from app.core.anthropic_client import AnthropicClient

async def test_event_extraction():
    """测试事件抽象功能"""
    client = AnthropicClient()

    # 模拟用户行为数据
    user_behaviors = {
        "user_001": [
            {"action": "browse", "timestamp": "2026-01-26 10:00", "item_id": "item_014"},
            {"action": "search", "timestamp": "2026-01-30 14:00", "item_id": "item_008"},
            {"action": "purchase", "timestamp": "2026-02-10 16:00", "item_id": "item_018"},
            {"action": "purchase", "timestamp": "2026-02-13 18:00", "item_id": "item_005"}
        ]
    }

    print("=" * 80)
    print("测试事件抽象功能")
    print("=" * 80)

    try:
        result = await client.abstract_events_batch(user_behaviors)
        print("\n✓ LLM 调用成功")
        print(f"\n返回结果: {result}")

        if "user_001" in result:
            events = result["user_001"]
            print(f"\n✓ 找到 user_001 的事件: {len(events)} 个")
            for i, event in enumerate(events, 1):
                print(f"\n事件 {i}:")
                print(f"  - 类型: {event.get('event_type')}")
                print(f"  - 时间: {event.get('timestamp')}")
                print(f"  - 上下文: {event.get('context')}")
        else:
            print("\n✗ 未找到 user_001 的事件")

    except Exception as e:
        print(f"\n✗ 测试失败: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_event_extraction())
