"""
Pytest fixtures and configuration for backend tests
"""
import sys
import os
import pytest
import random

# 设置工作目录
backend_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_path)

# 设置随机种子确保测试可复现
random.seed(42)


@pytest.fixture(scope="session")
def mock_data():
    """提供Mock数据模块"""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "mock_data",
        os.path.join(backend_path, "app/data/mock_data.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def sample_users(mock_data):
    """提供测试用用户数据"""
    return mock_data.get_mock_users(100)


@pytest.fixture
def graph_db():
    """提供图数据库实例"""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "graph_db",
        os.path.join(backend_path, "app/core/graph_db.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.graph_db.clear_knowledge_graph()
    return module.graph_db


@pytest.fixture
def clean_graph(graph_db):
    """提供干净的图数据库"""
    graph_db.clear_knowledge_graph()
    yield graph_db
    graph_db.clear_knowledge_graph()


@pytest.fixture
def sample_manager():
    """提供样本管理器"""
    import importlib.util
    sys.modules['app'] = type(sys)('app')
    sys.modules['app.data'] = type(sys)('app.data')
    
    # 动态导入mock_data
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "mock_data",
        os.path.join(backend_path, "app/data/mock_data.py")
    )
    mock_data = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mock_data)
    sys.modules['app.data.mock_data'] = mock_data
    
    spec = importlib.util.spec_from_file_location(
        "sample_manager",
        os.path.join(backend_path, "app/services/sample_manager.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.SampleManager()


@pytest.fixture
def api_client():
    """提供FastAPI测试客户端"""
    try:
        from fastapi.testclient import TestClient
        from backend.main import app
        return TestClient(app)
    except ImportError:
        pytest.skip("FastAPI not installed")
