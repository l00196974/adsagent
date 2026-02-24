"""
FastAPI依赖注入 - 解决并发安全问题
"""
from typing import Generator
from fastapi import Depends
from app.core.graph_db import GraphDatabase
from app.services.knowledge_graph import KnowledgeGraphBuilder
from app.services.sample_manager import SampleManager
from app.services.qa_engine import QAEngine
from app.services.event_graph import EventGraphBuilder
from app.services.logical_behavior import LogicalBehaviorGenerator
from app.core.openai_client import OpenAIClient
from app.core.config import settings
from app.core.logger import app_logger


# ========== 图数据库依赖 ==========

def get_graph_db() -> GraphDatabase:
    """获取图数据库实例（单例）"""
    from app.core.graph_db import graph_db
    return graph_db


# ========== 知识图谱构建器依赖 ==========

def get_kg_builder() -> Generator[KnowledgeGraphBuilder, None, None]:
    """获取知识图谱构建器（每个请求独立实例）"""
    builder = KnowledgeGraphBuilder()
    try:
        yield builder
    finally:
        # 清理资源
        pass


# ========== 样本管理器依赖 ==========

def get_sample_manager() -> Generator[SampleManager, None, None]:
    """获取样本管理器（每个请求独立实例）"""
    manager = SampleManager()
    try:
        yield manager
    finally:
        pass


# ========== LLM客户端依赖 ==========

def get_llm_client() -> Generator[OpenAIClient, None, None]:
    """获取LLM客户端（每个请求独立实例）"""
    if not settings.openai_api_key:
        app_logger.warning("未配置OpenAI API Key，LLM功能将降级")
        yield None
    else:
        try:
            client = OpenAIClient()
            yield client
        except Exception as e:
            app_logger.error(f"初始化LLM客户端失败: {e}")
            yield None


# ========== QA引擎依赖 ==========

def get_qa_engine(
    llm_client: OpenAIClient = None
) -> Generator[QAEngine, None, None]:
    """获取QA引擎（每个请求独立实例）"""
    engine = QAEngine(llm_client=llm_client)
    try:
        yield engine
    finally:
        pass


# ========== 事理图谱构建器依赖 ==========

def get_event_graph_builder(
    llm_client: OpenAIClient = None
) -> Generator[EventGraphBuilder, None, None]:
    """获取事理图谱构建器（每个请求独立实例）"""
    builder = EventGraphBuilder(llm_client=llm_client)
    try:
        yield builder
    finally:
        pass


# ========== 逻辑行为生成器依赖 ==========

def get_logical_behavior_generator(
    llm_client: OpenAIClient = Depends(get_llm_client)
) -> Generator[LogicalBehaviorGenerator, None, None]:
    """获取逻辑行为生成器（每个请求独立实例）"""
    if not llm_client:
        # 如果没有传入llm_client，创建一个新的
        llm_client = OpenAIClient() if settings.openai_api_key else None
    generator = LogicalBehaviorGenerator(llm_client=llm_client)
    try:
        yield generator
    finally:
        pass
