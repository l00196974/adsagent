"""
端到端验证脚本 - 测试知识图谱模型重构
"""
import sys
import os

# 添加backend到路径
backend_dir = r'd:\workplace\adsagent\backend'
sys.path.insert(0, backend_dir)
os.chdir(backend_dir)

print("=" * 60)
print("知识图谱模型重构 - 端到端验证")
print("=" * 60)

# 1. 测试模块导入
print("\n[1/5] 测试模块导入...")
try:
    from app.core.llm_client import llm_relation_identifier
    print("✓ LLM客户端导入成功")

    from app.services.knowledge_graph import KnowledgeGraphBuilder
    print("✓ 知识图谱服务导入成功")

    from app.services.field_detector import field_detector
    print("✓ 字段识别器导入成功")

    from app.core.graph_db import graph_db
    print("✓ 图数据库导入成功")
except Exception as e:
    print(f"✗ 模块导入失败: {e}")
    sys.exit(1)

# 2. 测试字段识别器
print("\n[2/5] 测试字段识别器...")
try:
    test_columns = ["user_id", "age", "owned_items", "poi_id", "app_id", "purchase_history"]
    mapping = field_detector.auto_detect_fields(test_columns)

    expected_fields = ["user_id", "age", "owned_items", "poi_id", "app_id", "purchase_history"]
    for field in expected_fields:
        if field in mapping.values():
            print(f"✓ 识别字段: {field}")
        else:
            print(f"✗ 未识别字段: {field}")
except Exception as e:
    print(f"✗ 字段识别测试失败: {e}")

# 3. 测试商品索引构建
print("\n[3/5] 测试商品索引构建...")
try:
    test_users = [
        {
            "user_id": "user_001",
            "owned_items": [
                {"item_id": "item_001", "name": "宝马730Li", "brand": "宝马", "series": "7系"}
            ]
        },
        {
            "user_id": "user_002",
            "primary_brand": "奔驰",
            "primary_model": "S400L"
        }
    ]

    item_index = llm_relation_identifier.build_item_index(test_users)
    print(f"✓ 商品索引构建成功: {len(item_index)} 个商品")
    for name, item_id in list(item_index.items())[:3]:
        print(f"  - {name} -> {item_id}")
except Exception as e:
    print(f"✗ 商品索引构建失败: {e}")

# 4. 测试CSV数据读取
print("\n[4/5] 测试CSV数据读取...")
try:
    import pandas as pd
    csv_path = r'd:\workplace\adsagent\backend\data\test_data.csv'

    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
        print(f"✓ CSV文件读取成功: {len(df)} 行数据")
        print(f"  列: {', '.join(df.columns[:5])}...")
    else:
        print(f"✗ CSV文件不存在: {csv_path}")
except Exception as e:
    print(f"✗ CSV读取失败: {e}")

# 5. 测试图数据库
print("\n[5/5] 测试图数据库...")
try:
    stats = {
        "实体数量": graph_db.knowledge_graph.number_of_nodes(),
        "关系数量": graph_db.knowledge_graph.number_of_edges()
    }
    print(f"✓ 图数据库状态:")
    for key, value in stats.items():
        print(f"  - {key}: {value}")
except Exception as e:
    print(f"✗ 图数据库测试失败: {e}")

print("\n" + "=" * 60)
print("验证完成!")
print("=" * 60)
print("\n下一步:")
print("1. 手动启动后端: cd d:\\workplace\\adsagent\\backend && python main.py")
print("2. 手动启动前端: cd d:\\workplace\\adsagent\\frontend && npm run dev")
print("3. 访问 http://localhost:5173/import 上传测试CSV")
