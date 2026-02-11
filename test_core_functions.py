#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
核心功能测试套件 - 广告知识图谱系统
测试所有核心模块：Mock数据、样本管理、知识图谱、事理图谱、智能问答

运行方式: 
  cd backend && python ../test_core_functions.py
  或者
  python test_core_functions.py (从项目根目录)
"""
import sys
import os
import json
import random
import unittest

# 设置工作目录
WORK_DIR = os.path.dirname(os.path.abspath(__file__))
if WORK_DIR not in sys.path:
    sys.path.insert(0, WORK_DIR)

# 设置随机种子确保测试可复现
random.seed(42)

# 尝试添加backend路径
backend_path = os.path.join(WORK_DIR, 'backend')
backend_app_path = os.path.join(backend_path, 'app')
if os.path.exists(backend_app_path) and backend_app_path not in sys.path:
    sys.path.insert(0, backend_app_path)


class TestMockData(unittest.TestCase):
    """Mock数据生成模块测试"""
    
    def setUp(self):
        """设置测试环境"""
        # 使用动态导入避免路径问题
        if 'backend.app.data.mock_data' in sys.modules:
            self.mock_data = sys.modules['backend.app.data.mock_data']
        else:
            try:
                import importlib.util
                spec = importlib.util.spec_from_file_location(
                    "mock_data", 
                    os.path.join(backend_path, "app/data/mock_data.py")
                )
                self.mock_data = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(self.mock_data)
                sys.modules['backend.app.data.mock_data'] = self.mock_data
            except FileNotFoundError:
                # 如果backend不存在，使用根目录的export_data
                self.mock_data = None
    
    def test_user_generation_count(self):
        """测试用户生成数量"""
        if not self.mock_data:
            self.skipTest("Mock数据模块不可用")
        
        for count in [10, 100, 500]:
            users = self.mock_data.get_mock_users(count)
            self.assertEqual(len(users), count, f"期望生成{count}个用户，实际{len(users)}")
    
    def test_user_data_structure(self):
        """测试用户数据结构完整性"""
        if not self.mock_data:
            self.skipTest("Mock数据模块不可用")
        
        users = self.mock_data.get_mock_users(100)
        
        for user in users:
            # 必需字段
            self.assertIn('user_id', user)
            self.assertIn('demographics', user)
            self.assertIn('interests', user)
            self.assertIn('behaviors', user)
            self.assertIn('brand_affinity', user)
            self.assertIn('purchase_intent', user)
            self.assertIn('lifecycle_stage', user)
            
            # demographics子字段
            self.assertIn('age_bucket', user['demographics'])
            self.assertIn('income_level', user['demographics'])
            self.assertIn('city_tier', user['demographics'])
    
    def test_brand_preferences_coverage(self):
        """测试品牌偏好覆盖"""
        if not self.mock_data:
            self.skipTest("Mock数据模块不可用")
        
        users = self.mock_data.get_mock_users(500)
        brands_found = set()
        
        for user in users:
            brand = user['brand_affinity']['primary_brand']
            brands_found.add(brand)
        
        # 应该覆盖所有定义的品牌
        expected_brands = {'宝马', '奔驰', '奥迪', '特斯拉'}
        self.assertEqual(brands_found, expected_brands)
    
    def test_income_distribution(self):
        """测试收入分布合理性"""
        if not self.mock_data:
            self.skipTest("Mock数据模块不可用")
        
        users = self.mock_data.get_mock_users(1000)
        incomes = [u['demographics']['income_level'] for u in users]
        
        # 统计各收入水平占比
        income_counts = {}
        for inc in incomes:
            income_counts[inc] = income_counts.get(inc, 0) + 1
        
        # 验证各收入水平都有数据
        self.assertGreater(len(income_counts), 2)


class TestExportedData(unittest.TestCase):
    """导出数据验证测试"""
    
    def setUp(self):
        """设置数据路径"""
        self.data_dir = os.path.join(WORK_DIR, 'data')
        if not os.path.exists(self.data_dir):
            # 尝试从backend上级目录查找
            self.data_dir = os.path.join(WORK_DIR, 'backend', '..', 'data')
        if not os.path.exists(self.data_dir):
            self.data_dir = os.path.join(WORK_DIR, '..', 'data')
    
    def test_mock_users_export(self):
        """测试Mock用户数据导出"""
        file_path = os.path.join(self.data_dir, 'mock_users.json')
        self.assertTrue(os.path.exists(file_path), f"文件不存在: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
            self.assertIn('metadata', data)
            self.assertIn('users', data)
            
            metadata = data['metadata']
            self.assertIn('count', metadata)
            self.assertIn('generated_at', metadata)
            self.assertEqual(metadata['industry'], '汽车')
            
            # 用户数量应>=1000
            self.assertGreaterEqual(metadata['count'], 1000)
            
            # 验证数据结构
            if len(data['users']) > 0:
                user = data['users'][0]
                required_fields = ['user_id', 'demographics', 'interests', 'brand_affinity']
                for field in required_fields:
                    self.assertIn(field, user)
    
    def test_samples_export(self):
        """测试样本数据导出"""
        file_path = os.path.join(self.data_dir, 'samples.json')
        self.assertTrue(os.path.exists(file_path))
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
            self.assertIn('metadata', data)
            self.assertIn('samples', data)
            
            metadata = data['metadata']
            self.assertIn('ratios', metadata)
            
            # 验证1:10:5:5比例
            ratios = metadata['ratios']
            self.assertEqual(ratios['positive'], 1)
            self.assertEqual(ratios['churn'], 10)
            self.assertEqual(ratios['weak'], 5)
            self.assertEqual(ratios['control'], 5)
            
            # 验证样本类型
            for sample_type in ['positive', 'churn', 'weak', 'control']:
                self.assertIn(sample_type, data['samples'])
                self.assertIsInstance(data['samples'][sample_type], list)
    
    def test_knowledge_graph_export(self):
        """测试知识图谱数据导出"""
        file_path = os.path.join(self.data_dir, 'knowledge_graph.json')
        self.assertTrue(os.path.exists(file_path))
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
            self.assertIn('metadata', data)
            self.assertIn('knowledge_graph', data)
            
            kg = data['knowledge_graph']
            self.assertIn('entities', kg)
            self.assertIn('relations', kg)
            self.assertIn('stats', kg)
            
            stats = kg['stats']
            self.assertGreater(stats['total_entities'], 0)
            self.assertGreater(stats['total_relations'], 0)
            
            # 验证实体类型
            entity_types = set(e['type'] for e in kg['entities'])
            self.assertIn('User', entity_types)
            self.assertIn('Brand', entity_types)
    
    def test_event_graph_export(self):
        """测试事理图谱数据导出"""
        file_path = os.path.join(self.data_dir, 'event_graph.json')
        self.assertTrue(os.path.exists(file_path))
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
            self.assertIn('metadata', data)
            self.assertIn('event_graph', data)
            
            eg = data['event_graph']
            self.assertIn('events', eg)
            self.assertIn('causal_chains', eg)
            self.assertIn('rules', eg)
            self.assertIn('insights', eg)
            
            # 验证因果链概率
            for chain in eg['causal_chains']:
                self.assertIn('probability', chain)
                self.assertIn('confidence', chain)
                self.assertGreaterEqual(chain['probability'], 0)
                self.assertLessEqual(chain['probability'], 1)


class TestSampleRatios(unittest.TestCase):
    """样本比例验证测试"""
    
    def test_sample_ratios_1_10_5_5(self):
        """测试样本比例1:10:5:5"""
        file_path = os.path.join(WORK_DIR, 'data', 'samples.json')
        if not os.path.exists(file_path):
            file_path = os.path.join(WORK_DIR, 'backend', '..', 'data', 'samples.json')
        
        self.assertTrue(os.path.exists(file_path))
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
            counts = data['metadata']['sample_counts']
            
            # 计算比例
            positive = counts['positive']
            churn = counts['churn']
            weak = counts['weak']
            control = counts['control']
            
            # 验证各类型都有数据
            self.assertGreater(positive, 0)
            self.assertGreater(churn, 0)
            self.assertGreater(weak, 0)
            self.assertGreater(control, 0)
            
            # 验证比例大致正确
            churn_ratio = churn / positive
            weak_ratio = weak / positive
            control_ratio = control / positive
            
            self.assertGreater(churn_ratio, 5)
            self.assertLess(churn_ratio, 15)
            
            self.assertGreater(weak_ratio, 3)
            self.assertLess(weak_ratio, 8)
            
            self.assertGreaterEqual(control_ratio, 2.5)
            self.assertLess(control_ratio, 8)
            
            print(f"样本比例: 正{positive}:流失{churn}:弱{weak}:对照{control}")
            print(f"实际比例: 1:{churn_ratio:.1f}:{weak_ratio:.1f}:{control_ratio:.1f}")


class TestKnowledgeGraphStructure(unittest.TestCase):
    """知识图谱结构测试"""
    
    def test_entity_types(self):
        """测试实体类型"""
        file_path = os.path.join(WORK_DIR, 'data', 'knowledge_graph.json')
        if not os.path.exists(file_path):
            file_path = os.path.join(WORK_DIR, 'backend', '..', 'data', 'knowledge_graph.json')
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
            kg = data['knowledge_graph']
            entities = kg['entities']
            relations = kg['relations']
            
            # 收集实体类型
            entity_types = {}
            for entity in entities:
                e_type = entity['type']
                entity_types[e_type] = entity_types.get(e_type, 0) + 1
            
            print(f"实体类型分布: {entity_types}")
            
            # 应该包含User, Brand, Model, Interest
            self.assertIn('User', entity_types)
            self.assertIn('Brand', entity_types)
            self.assertGreater(entity_types.get('User', 0), 10)
            self.assertGreater(entity_types.get('Brand', 0), 0)
    
    def test_relation_types(self):
        """测试关系类型"""
        file_path = os.path.join(WORK_DIR, 'data', 'knowledge_graph.json')
        if not os.path.exists(file_path):
            file_path = os.path.join(WORK_DIR, 'backend', '..', 'data', 'knowledge_graph.json')
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
            kg = data['knowledge_graph']
            relations = kg['relations']
            
            # 收集关系类型
            relation_types = {}
            for relation in relations:
                r_type = relation['type']
                relation_types[r_type] = relation_types.get(r_type, 0) + 1
            
            print(f"关系类型分布: {relation_types}")
            
            # 应该包含HAS_INTEREST, PREFERS, INTERESTED_IN
            self.assertGreater(len(relation_types), 0)
    
    def test_user_brand_relations(self):
        """测试用户-品牌关系"""
        file_path = os.path.join(WORK_DIR, 'data', 'knowledge_graph.json')
        if not os.path.exists(file_path):
            file_path = os.path.join(WORK_DIR, 'backend', '..', 'data', 'knowledge_graph.json')
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
            kg = data['knowledge_graph']
            relations = kg['relations']
            
            # 统计PREFERS关系
            prefers = [r for r in relations if r['type'] == 'PREFERS']
            self.assertGreater(len(prefers), 0)
            
            # 验证关系包含权重
            for r in prefers[:10]:
                self.assertIn('weight', r)


class TestEventGraphStructure(unittest.TestCase):
    """事理图谱结构测试"""
    
    def test_causal_chains(self):
        """测试因果链"""
        file_path = os.path.join(WORK_DIR, 'data', 'event_graph.json')
        if not os.path.exists(file_path):
            file_path = os.path.join(WORK_DIR, 'backend', '..', 'data', 'event_graph.json')
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
            eg = data['event_graph']
            chains = eg['causal_chains']
            
            # 应该有因果链
            self.assertGreater(len(chains), 0)
            
            for chain in chains:
                self.assertIn('events', chain)
                self.assertIn('probability', chain)
                self.assertIn('confidence', chain)
                self.assertIn('description', chain)
                
                # 概率应在0-1之间
                self.assertGreaterEqual(chain['probability'], 0)
                self.assertLessEqual(chain['probability'], 1)
    
    def test_rules(self):
        """测试规则"""
        file_path = os.path.join(WORK_DIR, 'data', 'event_graph.json')
        if not os.path.exists(file_path):
            file_path = os.path.join(WORK_DIR, 'backend', '..', 'data', 'event_graph.json')
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
            eg = data['event_graph']
            rules = eg['rules']
            
            # 应该有规则
            self.assertGreater(len(rules), 0)
            
            for rule in rules:
                self.assertIn('condition', rule)
                self.assertIn('action', rule)
                self.assertIn('weight', rule)
                
                # 权重应在0-1之间
                self.assertGreaterEqual(rule['weight'], 0)
                self.assertLessEqual(rule['weight'], 1)
    
    def test_insights(self):
        """测试洞察"""
        file_path = os.path.join(WORK_DIR, 'data', 'event_graph.json')
        if not os.path.exists(file_path):
            file_path = os.path.join(WORK_DIR, 'backend', '..', 'data', 'event_graph.json')
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
            eg = data['event_graph']
            insights = eg['insights']
            
            # 应该有洞察
            self.assertGreater(len(insights), 0)
            
            for insight in insights:
                self.assertIn('title', insight)
                self.assertIn('description', insight)
                self.assertIn('supporting_data', insight)
                self.assertIn('recommendation', insight)
                
                supporting = insight['supporting_data']
                self.assertIn('sample_size', supporting)
                self.assertIn('conversion_rate', supporting)


class TestDataQuality(unittest.TestCase):
    """数据质量测试"""
    
    def test_user_data_quality(self):
        """测试用户数据质量"""
        file_path = os.path.join(WORK_DIR, 'data', 'mock_users.json')
        if not os.path.exists(file_path):
            file_path = os.path.join(WORK_DIR, 'backend', '..', 'data', 'mock_users.json')
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
            users = data['users']
            
            # 检查前100个用户的数据质量
            for user in users[:100]:
                # 验证必需字段
                self.assertIsNotNone(user.get('user_id'))
                self.assertIsNotNone(user.get('demographics'))
                self.assertIsNotNone(user.get('brand_affinity'))
                
                # 验证品牌分数
                brand_score = user['brand_affinity']['brand_score']
                self.assertGreaterEqual(brand_score, 0)
                self.assertLessEqual(brand_score, 1)
    
    def test_no_duplicate_users(self):
        """测试无重复用户"""
        file_path = os.path.join(WORK_DIR, 'data', 'mock_users.json')
        if not os.path.exists(file_path):
            file_path = os.path.join(WORK_DIR, 'backend', '..', 'data', 'mock_users.json')
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
            users = data['users']
            user_ids = [u['user_id'] for u in users]
            
            # 验证ID唯一性
            self.assertEqual(len(user_ids), len(set(user_ids)))
    
    def test_graph_connectivity(self):
        """测试图谱连通性"""
        file_path = os.path.join(WORK_DIR, 'data', 'knowledge_graph.json')
        if not os.path.exists(file_path):
            file_path = os.path.join(WORK_DIR, 'backend', '..', 'data', 'knowledge_graph.json')
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
            kg = data['knowledge_graph']
            relations = kg['relations']
            
            # 创建实体集合
            entities = {e['id'] for e in kg['entities']}
            
            # 验证所有关系都连接有效的实体
            for rel in relations:
                self.assertIn(rel['from'], entities, f"关系引用了不存在的实体: {rel['from']}")
                self.assertIn(rel['to'], entities, f"关系引用了不存在的实体: {rel['to']}")


def run_tests():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("广告知识图谱系统 - 核心功能测试套件")
    print("=" * 60 + "\n")
    
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加所有测试类
    test_classes = [
        TestMockData,
        TestExportedData,
        TestSampleRatios,
        TestKnowledgeGraphStructure,
        TestEventGraphStructure,
        TestDataQuality
    ]
    
    for test_class in test_classes:
        suite.addTests(loader.loadTestsFromTestCase(test_class))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 输出总结
    print("\n" + "=" * 60)
    print("测试结果总结")
    print("=" * 60)
    print(f"运行测试数: {result.testsRun}")
    print(f"成功测试: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失败测试: {len(result.failures)}")
    print(f"错误测试: {len(result.errors)}")
    print(f"跳过测试: {len(result.skipped)}")
    
    if result.failures:
        print("\n失败测试详情:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback.split('AssertionError')[0].strip()}")
    
    if result.errors:
        print("\n错误测试详情:")
        for test, traceback in result.errors:
            error_msg = str(traceback).split('\n')[-2] if '\n' in str(traceback) else str(traceback)
            print(f"  - {test}: {error_msg}")
    
    # 计算成功率
    success_rate = (result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100
    print(f"\n成功率: {success_rate:.1f}%")
    
    # 返回结果
    success = len(result.failures) == 0 and len(result.errors) == 0
    print("\n" + "=" * 60)
    if success:
        print("✓ 所有测试通过！")
    else:
        print("✗ 存在失败的测试")
    print("=" * 60 + "\n")
    
    return success


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
