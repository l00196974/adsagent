"""
Backend API integration tests
"""
import sys
import os
import pytest

backend_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_path)


class TestGraphAPI:
    """图谱API测试"""
    
    def test_load_data_endpoint(self, api_client):
        """测试数据加载接口"""
        response = api_client.post("/api/v1/graphs/data/load", json={"count": 100})
        assert response.status_code == 200
        data = response.json()
        assert data['code'] == 0
    
    def test_build_knowledge_graph(self, api_client):
        """测试构建知识图谱"""
        # 先加载数据
        api_client.post("/api/v1/graphs/data/load", json={"count": 50})
        
        # 构建图谱
        response = api_client.post("/api/v1/graphs/knowledge/build")
        assert response.status_code == 200
        data = response.json()
        assert data['code'] == 0
        assert 'stats' in data['data']
    
    def test_get_progress(self, api_client):
        """测试获取进度"""
        response = api_client.get("/api/v1/graphs/knowledge/progress")
        assert response.status_code == 200
        data = response.json()
        assert 'current_step' in data['data']


class TestSampleAPI:
    """样本API测试"""
    
    def test_generate_samples(self, api_client):
        """测试生成样本"""
        response = api_client.post("/api/v1/samples/generate", json={
            "industry": "汽车",
            "total_count": 100
        })
        assert response.status_code == 200
        data = response.json()
        assert data['code'] == 0
        assert 'samples' in data['data']
    
    def test_sample_statistics(self, api_client):
        """测试样本统计"""
        response = api_client.post("/api/v1/samples/generate", json={
            "industry": "汽车",
            "total_count": 200
        })
        
        # 检查统计信息
        data = response.json()
        assert 'samples' in data['data']
        samples = data['data']['samples']
        
        assert len(samples['positive']) > 0
        assert len(samples['churn']) > 0


class TestQAAPI:
    """问答API测试"""
    
    def test_event_graph_generation(self, api_client):
        """测试事理图谱生成"""
        response = api_client.post("/api/v1/qa/event-graph/generate", json={
            "industry": "汽车",
            "n_samples": 100
        })
        assert response.status_code == 200
        data = response.json()
        assert data['code'] == 0
    
    def test_qa_query(self, api_client):
        """测试问答查询"""
        response = api_client.post("/api/v1/qa/query", json={
            "question": "喜欢打高尔夫的用户是宝马7系高潜还是奔驰S系高潜？"
        })
        assert response.status_code == 200
        data = response.json()
        assert data['code'] == 0
        assert 'answer' in data['data']
