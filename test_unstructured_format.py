#!/usr/bin/env python3
"""
测试非结构化格式兼容性
"""
import sys
sys.path.insert(0, '/home/linxiankun/adsagent/backend')

from app.services.base_modeling import BaseModelingService

def test_unstructured_format():
    """测试非结构化格式导入和查询"""
    service = BaseModelingService()

    print("=" * 60)
    print("测试非结构化格式兼容性")
    print("=" * 60)

    # 1. 测试导入非结构化行为数据
    print("\n1. 导入非结构化行为数据...")
    behaviors = [
        {
            "user_id": "test_user_001",
            "timestamp": "2026-01-01 10:00:00",
            "behavior_text": "在微信上浏览了BMW 7系的广告，停留了5分钟"
        },
        {
            "user_id": "test_user_001",
            "timestamp": "2026-01-01 10:30:00",
            "behavior_text": "在汽车之家APP搜索\"豪华轿车\""
        }
    ]
    result = service.import_behavior_data(behaviors)
    print(f"导入结果: {result}")

    # 2. 测试查询行为数据
    print("\n2. 查询行为数据...")
    result = service.query_behavior_data(user_id="test_user_001", limit=10)
    print(f"查询到 {len(result['items'])} 条数据")
    for item in result['items']:
        print(f"  - {item.get('timestamp')}: {item.get('behavior_text', item.get('action'))}")

    # 3. 测试导入非结构化用户画像
    print("\n3. 导入非结构化用户画像...")
    profiles = [
        {
            "user_id": "test_user_001",
            "profile_text": "28岁男性，北京工程师，年收入50万，本科学历，喜欢高尔夫和科技产品"
        }
    ]
    result = service.import_user_profiles(profiles)
    print(f"导入结果: {result}")

    # 4. 测试查询用户画像
    print("\n4. 查询用户画像...")
    result = service.query_user_profiles(limit=10)
    print(f"查询到 {len(result['items'])} 个用户")
    for item in result['items']:
        if 'profile_text' in item:
            print(f"  - {item['user_id']}: {item['profile_text'][:50]}...")
        else:
            print(f"  - {item['user_id']}: {item.get('age')}岁 {item.get('gender')} {item.get('city')}")

    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)

if __name__ == "__main__":
    try:
        test_unstructured_format()
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
