"""
简化测试 - 调试 LLM 响应格式问题
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.core.openai_client import OpenAIClient
import json


async def test_simple_event_extraction():
    """测试简单的事件抽取"""
    print("=" * 80)
    print("测试: 简单事件抽取 (调试模式)")
    print("=" * 80)

    client = OpenAIClient()

    # 非常简单的测试数据
    user_behaviors = {
        "user_001": [
            {
                "action": "visit_poi",
                "timestamp": "2026-02-13 10:00:00",
                "poi_info": {
                    "poi_name": "宝马4S店",
                    "poi_type": "汽车4S店"
                },
                "duration": 7200
            },
            {
                "action": "search",
                "timestamp": "2026-02-13 15:00:00",
                "item_id": "宝马7系价格",
                "app_info": {
                    "app_name": "汽车之家"
                }
            }
        ]
    }

    user_profiles = {
        "user_001": {
            "age": 35,
            "gender": "男",
            "income_level": "高"
        }
    }

    print("\n调用 LLM...")
    try:
        result = await client.abstract_events_batch(user_behaviors, user_profiles)

        print("\n返回结果:")
        print(json.dumps(result, ensure_ascii=False, indent=2))

        if "user_001" in result and result["user_001"]:
            print(f"\n✓ 成功抽取 {len(result['user_001'])} 个事件")
            return True
        else:
            print("\n✗ 未能抽取事件")
            return False

    except Exception as e:
        print(f"\n✗ 异常: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_simple_event_extraction())
    sys.exit(0 if success else 1)
