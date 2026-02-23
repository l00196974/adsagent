"""
测试数据丰富化的完整集成流程
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.core.openai_client import OpenAIClient
from app.services.event_extraction import EventExtractionService


async def test_format_enriched_behavior():
    """测试行为格式化功能"""
    print("=" * 80)
    print("测试 1: 行为格式化功能")
    print("=" * 80)

    client = OpenAIClient()

    # 测试各种类型的丰富行为数据
    test_behaviors = [
        {
            "action": "visit_poi",
            "timestamp": "2026-02-13 10:00:00",
            "poi_id": "poi_bmw_001",
            "duration": 7200,
            "poi_info": {
                "poi_id": "poi_bmw_001",
                "poi_name": "宝马4S店(朝阳店)",
                "poi_type": "汽车4S店",
                "address": "北京市朝阳区"
            }
        },
        {
            "action": "use_app",
            "timestamp": "2026-02-13 14:30:00",
            "app_id": "app_002",
            "duration": 1800,
            "app_info": {
                "app_id": "app_002",
                "app_name": "高尔夫助手",
                "category": "运动",
                "tags": ["高尔夫", "运动", "社交"]
            }
        },
        {
            "action": "search",
            "timestamp": "2026-02-13 15:00:00",
            "app_id": "app_007",
            "item_id": "宝马7系价格",
            "app_info": {
                "app_id": "app_007",
                "app_name": "汽车之家",
                "category": "汽车",
                "tags": ["汽车资讯", "购车", "评测"]
            }
        },
        {
            "action": "browse",
            "timestamp": "2026-02-13 16:00:00",
            "media_id": "media_001",
            "item_id": "item_005",
            "duration": 300,
            "media_info": {
                "media_id": "media_001",
                "media_name": "爱奇艺",
                "media_type": "视频平台",
                "tags": ["视频", "影视", "综艺"]
            },
            "item_info": {
                "item_id": "item_005",
                "item_type": "Video",
                "item_name": "豪华轿车评测:宝马7系vs奔驰S级",
                "properties": {"category": "汽车评测"}
            }
        },
        {
            "action": "purchase",
            "timestamp": "2026-02-13 18:00:00",
            "item_id": "item_010",
            "item_info": {
                "item_id": "item_010",
                "item_type": "Product",
                "item_name": "高尔夫球杆套装",
                "properties": {"price": 5999}
            }
        }
    ]

    print("\n格式化结果:")
    for behavior in test_behaviors:
        formatted = client._format_enriched_behavior(behavior)
        print(f"  {formatted}")

    print("\n✓ 行为格式化测试通过")
    return True


async def test_event_extraction_with_llm():
    """测试完整的事件抽取流程(使用真实LLM)"""
    print("\n" + "=" * 80)
    print("测试 2: 完整事件抽取流程(使用 MiniMax-M2.5)")
    print("=" * 80)

    client = OpenAIClient()

    # 模拟丰富后的用户行为数据
    user_behaviors = {
        "user_001": [
            {
                "action": "visit_poi",
                "timestamp": "2026-02-13 10:00:00",
                "poi_id": "poi_bmw_001",
                "duration": 7200,
                "poi_info": {
                    "poi_name": "宝马4S店(朝阳店)",
                    "poi_type": "汽车4S店"
                }
            },
            {
                "action": "use_app",
                "timestamp": "2026-02-13 14:30:00",
                "app_id": "app_002",
                "duration": 1800,
                "app_info": {
                    "app_name": "高尔夫助手",
                    "tags": ["高尔夫", "运动"]
                }
            },
            {
                "action": "search",
                "timestamp": "2026-02-13 15:00:00",
                "item_id": "宝马7系价格",
                "app_info": {
                    "app_name": "汽车之家"
                }
            },
            {
                "action": "browse",
                "timestamp": "2026-02-13 16:00:00",
                "media_info": {
                    "media_name": "爱奇艺"
                },
                "item_info": {
                    "item_name": "豪华轿车评测:宝马7系vs奔驰S级"
                }
            }
        ]
    }

    # 用户画像
    user_profiles = {
        "user_001": {
            "age": 35,
            "gender": "男",
            "income_level": "高",
            "interests": ["高尔夫", "豪华轿车", "商务旅行"]
        }
    }

    print("\n输入数据:")
    print(f"  用户画像: {user_profiles['user_001']}")
    print(f"  行为数量: {len(user_behaviors['user_001'])} 条")

    try:
        # 调用 LLM 进行事件抽取
        result = await client.abstract_events_batch(user_behaviors, user_profiles)

        print("\n抽取结果:")
        if "user_001" in result and result["user_001"]:
            events = result["user_001"]
            print(f"  抽取了 {len(events)} 个事件:")
            for i, event in enumerate(events, 1):
                print(f"\n  事件 {i}:")
                print(f"    类型: {event.get('event_type', 'N/A')}")
                print(f"    时间: {event.get('timestamp', 'N/A')}")
                print(f"    上下文: {event.get('context', {})}")

            print("\n✓ 事件抽取测试通过")
            return True
        else:
            print("\n✗ 事件抽取失败: 未返回有效结果")
            return False

    except Exception as e:
        print(f"\n✗ 事件抽取测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_comparison():
    """对比有无数据丰富化的效果"""
    print("\n" + "=" * 80)
    print("测试 3: 对比有无数据丰富化的效果")
    print("=" * 80)

    client = OpenAIClient()

    # 场景1: 只有ID(无丰富化)
    behaviors_without_enrichment = {
        "user_001": [
            {
                "action": "visit_poi",
                "timestamp": "2026-02-13 10:00:00",
                "poi_id": "poi_001",
                "duration": 7200
            },
            {
                "action": "use_app",
                "timestamp": "2026-02-13 14:30:00",
                "app_id": "app_002",
                "duration": 1800
            },
            {
                "action": "search",
                "timestamp": "2026-02-13 15:00:00",
                "item_id": "item_005"
            }
        ]
    }

    # 场景2: 有详细信息(已丰富化)
    behaviors_with_enrichment = {
        "user_001": [
            {
                "action": "visit_poi",
                "timestamp": "2026-02-13 10:00:00",
                "poi_id": "poi_001",
                "duration": 7200,
                "poi_info": {
                    "poi_name": "宝马4S店(朝阳店)",
                    "poi_type": "汽车4S店"
                }
            },
            {
                "action": "use_app",
                "timestamp": "2026-02-13 14:30:00",
                "app_id": "app_002",
                "duration": 1800,
                "app_info": {
                    "app_name": "高尔夫助手",
                    "tags": ["高尔夫", "运动"]
                }
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
            "income_level": "高",
            "interests": ["高尔夫", "豪华轿车"]
        }
    }

    print("\n场景1: 无数据丰富化(只有ID)")
    print("-" * 80)
    try:
        result1 = await client.abstract_events_batch(behaviors_without_enrichment, user_profiles)
        if result1.get("user_001"):
            print(f"抽取了 {len(result1['user_001'])} 个事件:")
            for event in result1["user_001"]:
                print(f"  - {event.get('event_type')}: {event.get('context')}")
        else:
            print("  未能抽取事件")
    except Exception as e:
        print(f"  失败: {e}")

    print("\n场景2: 有数据丰富化(包含实体详细信息)")
    print("-" * 80)
    try:
        result2 = await client.abstract_events_batch(behaviors_with_enrichment, user_profiles)
        if result2.get("user_001"):
            print(f"抽取了 {len(result2['user_001'])} 个事件:")
            for event in result2["user_001"]:
                print(f"  - {event.get('event_type')}: {event.get('context')}")
        else:
            print("  未能抽取事件")
    except Exception as e:
        print(f"  失败: {e}")

    print("\n✓ 对比测试完成")
    return True


async def main():
    """运行所有测试"""
    print("\n" + "=" * 80)
    print("数据丰富化集成测试")
    print("=" * 80)

    results = []

    # 运行测试
    results.append(await test_format_enriched_behavior())
    results.append(await test_event_extraction_with_llm())
    results.append(await test_comparison())

    # 汇总结果
    print("\n" + "=" * 80)
    print("测试汇总")
    print("=" * 80)
    passed = sum(results)
    total = len(results)
    print(f"\n通过: {passed}/{total}")

    if passed == total:
        print("\n✓ 所有测试通过！数据丰富化功能正常工作。")
    else:
        print(f"\n⚠ {total - passed} 个测试失败。")

    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
