"""
Backend unit tests for the Ad Knowledge Graph System
"""
import sys
import os
import pytest
import random

# 设置路径
backend_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_path)

random.seed(42)


class TestMockData:
    """Mock数据生成测试"""
    
    def test_user_generation_count(self, mock_data):
        """测试用户生成数量"""
        for count in [10, 100, 500]:
            users = mock_data.get_mock_users(count)
            assert len(users) == count
    
    def test_user_data_structure(self, mock_data):
        """测试用户数据结构"""
        users = mock_data.get_mock_users(50)
        
        for user in users:
            # 必需字段
            assert 'user_id' in user
            assert 'demographics' in user
            assert 'interests' in user
            assert 'behaviors' in user
            assert 'brand_affinity' in user
            assert 'purchase_intent' in user
            assert 'lifecycle_stage' in user
            
            # 子字段
            assert 'age_bucket' in user['demographics']
            assert 'income_level' in user['demographics']
            assert 'city_tier' in user['demographics']
            assert 'primary_brand' in user['brand_affinity']
    
    def test_brand_coverage(self, mock_data):
        """测试品牌覆盖"""
        users = mock_data.get_mock_users(200)
        brands = set(u['brand_affinity']['primary_brand'] for u in users)
        expected = {'宝马', '奔驰', '奥迪', '特斯拉'}
        assert brands == expected
    
    def test_user_id_format(self, mock_data):
        """测试用户ID格式"""
        users = mock_data.get_mock_users(100)
        for user in users:
            assert user['user_id'].startswith('U')
        # ID唯一性
        ids = [u['user_id'] for u in users]
        assert len(ids) == len(set(ids))
    
    def test_income_distribution(self, mock_data):
        """测试收入分布"""
        users = mock_data.get_mock_users(500)
        incomes = [u['demographics']['income_level'] for u in users]
        unique_incomes = set(incomes)
        assert len(unique_incomes) >= 3
    
    def test_interests_diversity(self, mock_data):
        """测试兴趣多样性"""
        users = mock_data.get_mock_users(200)
        all_interests = []
        for user in users:
            all_interests.extend(user['interests'])
        unique = set(all_interests)
        assert len(unique) >= 5


class TestSampleManager:
    """样本管理测试"""
    
    def test_sample_generation(self, sample_manager):
        """测试样本生成"""
        samples = sample_manager.generate_samples(total_count=100)
        counts = {k: len(v) for k, v in samples.items()}
        
        assert counts['positive'] > 0
        assert counts['churn'] > 0
        assert counts['weak'] > 0
        assert counts['control'] > 0
    
    def test_sample_ratios(self, sample_manager):
        """测试样本比例"""
        samples = sample_manager.generate_samples(total_count=200)
        counts = {k: len(v) for k, v in samples.items()}
        
        churn_ratio = counts['churn'] / max(counts['positive'], 1)
        weak_ratio = counts['weak'] / max(counts['positive'], 1)
        control_ratio = counts['control'] / max(counts['positive'], 1)
        
        assert 5 < churn_ratio < 15  # 约为10倍
        assert 3 < weak_ratio < 8    # 约为5倍
        assert 2 < control_ratio < 6  # 约为5倍
    
    def test_statistics_computation(self, sample_manager):
        """测试统计计算"""
        samples = sample_manager.generate_samples(total_count=100)
        stats = sample_manager.compute_statistics(samples)
        
        for stype in ['positive', 'churn', 'weak', 'control']:
            assert 'count' in stats[stype]
            assert 'income_distribution' in stats[stype]
            assert 'top_interests' in stats[stype]
    
    def test_typical_cases(self, sample_manager):
        """测试典型案例"""
        samples = sample_manager.generate_samples(total_count=200)
        typical = sample_manager.extract_typical_cases(samples)
        
        for stype in ['positive', 'churn', 'weak', 'control']:
            assert len(typical[stype]) <= 5


class TestKnowledgeGraph:
    """知识图谱测试"""
    
    def test_entity_creation(self, clean_graph):
        """测试实体创建"""
        clean_graph.create_entity("test:user1", "User", {"name": "Test"})
        assert clean_graph.knowledge_graph.has_node("test:user1")
    
    def test_relation_creation(self, clean_graph):
        """测试关系创建"""
        clean_graph.create_entity("test:user1", "User", {})
        clean_graph.create_entity("test:brand1", "Brand", {})
        clean_graph.create_relation("test:user1", "test:brand1", "PREFERS", {"weight": 0.8})
        
        assert clean_graph.knowledge_graph.has_edge("test:user1", "test:brand1")
    
    def test_find_related(self, clean_graph):
        """测试查找关联"""
        clean_graph.create_entity("user:A", "User", {})
        clean_graph.create_entity("interest:golf", "Interest", {})
        clean_graph.create_entity("brand:bmw", "Brand", {})
        
        clean_graph.create_relation("user:A", "interest:golf", "HAS_INTEREST", {})
        clean_graph.create_relation("interest:golf", "brand:bmw", "CORRELATES_WITH", {})
        
        related = clean_graph.find_related("user:A", depth=2)
        assert len(related) == 2
    
    def test_graph_stats(self, clean_graph):
        """测试图谱统计"""
        for i in range(10):
            clean_graph.create_entity(f"user:{i}", "User", {})
        
        stats = clean_graph.get_stats()
        assert stats['total_entities'] == 10


class TestAPIRoutes:
    """API路由测试"""
    
    def test_health_endpoint(self, api_client):
        """测试健康检查"""
        response = api_client.get("/health")
        assert response.status_code == 200
        assert response.json()['status'] == 'ok'
    
    def test_root_endpoint(self, api_client):
        """测试根接口"""
        response = api_client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert 'name' in data
        assert 'version' in data
