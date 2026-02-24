#!/usr/bin/env python3
"""
测试用户画像导入和查询功能
"""
import sys
sys.path.insert(0, '/home/linxiankun/adsagent/backend')

from app.services.base_modeling import BaseModelingService
import pandas as pd

def test_import_and_query():
    """测试导入和查询功能"""
    service = BaseModelingService()

    print("=" * 60)
    print("测试用户画像功能")
    print("=" * 60)

    # 测试1: 导入结构化数据
    print("\n1. 测试导入结构化CSV数据")
    df = pd.read_csv('data/user_profiles.csv')
    print(f"   CSV文件包含 {len(df)} 条记录")
    print(f"   列: {df.columns.tolist()}")

    profiles = df.head(10).to_dict('records')
    result = service.import_user_profiles(profiles)
    print(f"   导入结果: {result}")

    # 测试2: 导入富结构化数据
    print("\n2. 测试导入富结构化数据（包含income, interests等）")
    rich_profiles = [
        {
            "user_id": "rich_test_001",
            "age": 40,
            "gender": "男",
            "city": "深圳",
            "occupation": "企业高管",
            "income": 500000,
            "interests": ["高尔夫", "商务旅行", "红酒"],
            "budget": 80,
            "has_car": True,
            "purchase_intent": "换车"
        }
    ]
    result = service.import_user_profiles(rich_profiles)
    print(f"   导入结果: {result}")

    # 测试3: 导入非结构化数据
    print("\n3. 测试导入非结构化数据（纯文本）")
    unstructured_profiles = [
        {
            "user_id": "unstructured_test_001",
            "profile_text": "50岁男性，北京企业家，年收入200万，喜欢收藏和艺术，购车预算150万，考虑购买豪华SUV"
        }
    ]
    result = service.import_user_profiles(unstructured_profiles)
    print(f"   导入结果: {result}")

    # 测试4: 查询所有数据
    print("\n4. 测试查询功能")
    result = service.query_user_profiles(limit=5)
    print(f"   总记录数: {result['total']}")
    print(f"   返回记录数: {len(result['items'])}")

    print("\n   前3条记录:")
    for item in result['items'][:3]:
        print(f"   - {item['user_id']}:")
        print(f"     年龄: {item['age']}, 性别: {item['gender']}, 城市: {item['city']}")
        print(f"     画像: {item['profile_text'][:80]}...")

    # 测试5: 查询特定用户
    print("\n5. 测试查询特定用户")
    result = service.query_user_profiles(user_id="rich_test_001")
    if result['items']:
        item = result['items'][0]
        print(f"   用户ID: {item['user_id']}")
        print(f"   基本信息: {item['age']}岁, {item['gender']}, {item['city']}, {item['occupation']}")
        print(f"   扩展属性: {item['properties']}")
        print(f"   画像文本: {item['profile_text']}")

    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)

if __name__ == "__main__":
    test_import_and_query()
