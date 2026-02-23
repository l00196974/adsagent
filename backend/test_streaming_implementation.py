#!/usr/bin/env python3
"""测试LLM流式调用和重试机制"""

import asyncio
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.openai_client import OpenAIClient
from app.core.logger import app_logger as logger

async def test_streaming_mode():
    """测试流式调用模式"""
    print("=" * 80)
    print("测试1: 流式调用模式")
    print("=" * 80)

    client = OpenAIClient()

    # 测试简单的流式调用
    prompt = "请用一句话介绍汽车广告投放的重要性。"

    try:
        print(f"\n发送提示词: {prompt}")
        print("\n开始流式调用...")

        stream_generator = client.chat_completion(prompt, max_tokens=200)
        response = await client._collect_stream_response(stream_generator)

        print(f"\n✅ 流式调用成功")
        print(f"响应长度: {len(response)} 字符")
        print(f"响应内容: {response[:200]}...")

        return True
    except Exception as e:
        print(f"\n❌ 流式调用失败: {e}")
        return False

async def test_retry_mechanism():
    """测试重试机制（模拟失败场景）"""
    print("\n" + "=" * 80)
    print("测试2: 重试机制")
    print("=" * 80)

    # 注意: 这个测试需要模拟失败场景，实际环境中可能无法触发重试
    # 这里只是验证重试参数可以正常传递

    client = OpenAIClient()
    prompt = "测试重试机制"

    try:
        print(f"\n发送提示词: {prompt}")
        print("调用LLM（max_retries=1）...")

        stream_generator = client.chat_completion(
            prompt,
            max_tokens=100,
            stream=True,
            max_retries=1
        )
        response = await client._collect_stream_response(stream_generator)

        print(f"\n✅ 调用成功（未触发重试）")
        print(f"响应长度: {len(response)} 字符")

        return True
    except Exception as e:
        print(f"\n⚠️  调用失败: {e}")
        print("注意: 如果是网络错误，重试机制应该已经生效")
        return False

async def test_batch_event_abstraction():
    """测试批量事件抽象（最关键的流式调用场景）"""
    print("\n" + "=" * 80)
    print("测试3: 批量事件抽象流式调用")
    print("=" * 80)

    client = OpenAIClient()

    # 模拟用户行为数据
    user_behaviors = {
        "user_001": [
            {
                "timestamp": "2026-01-15 10:00:00",
                "action": "browse",
                "item_info": {"item_name": "宝马7系"},
                "app_info": {"app_name": "汽车之家"}
            },
            {
                "timestamp": "2026-01-15 12:00:00",
                "action": "search",
                "item_id": "豪华轿车",
                "app_info": {"app_name": "汽车之家"}
            }
        ]
    }

    user_profiles = {
        "user_001": {
            "age": 35,
            "gender": "男",
            "occupation": "企业高管",
            "city": "北京"
        }
    }

    try:
        print("\n开始批量事件抽象...")
        print(f"用户数量: {len(user_behaviors)}")

        result = await client.abstract_events_batch(user_behaviors, user_profiles)

        print(f"\n✅ 批量事件抽象成功")
        print(f"提取的事件数量: {sum(len(events) for events in result['events'].values())}")
        print(f"原始响应长度: {len(result.get('raw_response', ''))}")

        if result['events']:
            print("\n示例事件:")
            for user_id, events in list(result['events'].items())[:1]:
                for event in events[:3]:
                    print(f"  - {event}")

        return True
    except Exception as e:
        print(f"\n❌ 批量事件抽象失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """运行所有测试"""
    print("\n" + "=" * 80)
    print("LLM流式调用和重试机制测试")
    print("=" * 80)

    results = []

    # 测试1: 基础流式调用
    results.append(await test_streaming_mode())

    # 测试2: 重试机制
    results.append(await test_retry_mechanism())

    # 测试3: 批量事件抽象（最关键的场景）
    results.append(await test_batch_event_abstraction())

    # 总结
    print("\n" + "=" * 80)
    print("测试总结")
    print("=" * 80)
    print(f"\n总计测试: {len(results)}")
    print(f"通过: {sum(results)}")
    print(f"失败: {len(results) - sum(results)}")

    if all(results):
        print("\n✅ 所有测试通过!")
        return 0
    else:
        print("\n❌ 部分测试失败")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
