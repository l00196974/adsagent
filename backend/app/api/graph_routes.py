from fastapi import APIRouter, HTTPException
from typing import Dict
from app.services.knowledge_graph import KnowledgeGraphBuilder, GraphQueryEngine
from app.data.mock_data import get_mock_users

router = APIRouter()

_kg_builder = KnowledgeGraphBuilder()
_kg_data = None
_loaded_users = 0  # 已加载的用户数量

@router.post("/data/load")
async def load_user_data(count: int = 50000):
    """加载用户数据"""
    global _loaded_users
    try:
        # 预加载用户数据
        users = get_mock_users(count)
        _loaded_users = len(users)
        return {
            "code": 0, 
            "data": {
                "loaded_count": _loaded_users,
                "message": f"成功加载 {count} 用户数据"
            },
            "message": "用户数据加载成功"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/data/status")
async def get_data_status():
    """获取数据加载状态"""
    return {
        "code": 0,
        "data": {
            "loaded_count": _loaded_users,
            "status": "已加载" if _loaded_users > 0 else "未加载"
        }
    }

@router.post("/knowledge/build")
async def build_knowledge_graph(user_count: int = None):
    """构建知识图谱"""
    global _kg_data
    try:
        # 如果未指定数量，使用已加载的用户数量
        if user_count is None or user_count <= 0:
            if _loaded_users > 0:
                user_count = _loaded_users
            else:
                user_count = 50000  # 默认5万
        
        _kg_data = _kg_builder.build(user_count=user_count)
        return {"code": 0, "data": _kg_data, "message": "知识图谱构建成功"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/knowledge/progress")
async def get_build_progress():
    """获取知识图谱构建进度"""
    try:
        progress = _kg_builder.get_progress()
        return {"code": 0, "data": progress}
    except Exception as e:
        return {"code": 0, "data": {"current_step": "未开始", "step_progress": 0, "total_batches": 0}}

@router.get("/knowledge/query")
async def query_graph(entity_name: str = None, entity_type: str = None, depth: int = 2):
    if not _kg_data:
        raise HTTPException(status_code=400, detail="请先构建知识图谱")
    try:
        engine = GraphQueryEngine()
        if entity_name:
            result = engine.query_by_entity(entity_name, depth)
        else:
            result = {
                "entities": _kg_data["entities"][:100],
                "relations": _kg_data["relations"][:200]
            }
        return {"code": 0, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/brand-correlation")
async def query_brand_correlation(brand: str):
    if not _kg_data:
        raise HTTPException(status_code=400, detail="请先构建知识图谱")
    try:
        engine = GraphQueryEngine()
        result = engine.query_brand_interest_correlation(brand)
        return {"code": 0, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
