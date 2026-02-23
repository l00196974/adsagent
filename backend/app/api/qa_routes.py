from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from app.services.qa_engine import QAEngine
from app.services.event_graph import EventGraphBuilder
from app.core.openai_client import OpenAIClient
from app.core.logger import app_logger

router = APIRouter()

_llm_client = None
_qa_engine = None
_event_graph_builder = None
_event_graph_data = {}

class QARequest(BaseModel):
    question: str

class BuildEventGraphFromCSVRequest(BaseModel):
    """从CSV数据构建事理图谱请求"""
    users: List[Dict] = Field(..., min_items=1, description="用户数据列表")
    analysis_focus: Optional[Dict] = Field(None, description="分析重点")

def init_services():
    global _llm_client, _qa_engine, _event_graph_builder
    try:
        _llm_client = OpenAIClient()
    except Exception:
        _llm_client = None
    _event_graph_builder = EventGraphBuilder(_llm_client)
    _qa_engine = QAEngine(_llm_client)

@router.post("/query")
async def ask_question(request: QARequest):
    global _qa_engine
    if not _qa_engine:
        init_services()
    try:
        result = await _qa_engine.answer(request.question)
        return {"code": 0, "data": result, "message": "问答成功"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Mock事理图谱生成接口已移除，请使用 /event-graph/build-from-csv 接口


@router.post("/event-graph/build-from-csv")
async def build_event_graph_from_csv(request: BuildEventGraphFromCSVRequest):
    """从CSV数据构建事理图谱"""
    global _event_graph_builder, _event_graph_data, _qa_engine
    if not _event_graph_builder:
        init_services()

    try:
        users = request.users
        analysis_focus = request.analysis_focus

        app_logger.info(f"开始从CSV数据构建事理图谱，用户数量: {len(users)}")

        result = await _event_graph_builder.build_from_real_data(
            users=users,
            analysis_focus=analysis_focus
        )

        _event_graph_data = result
        if _qa_engine:
            _qa_engine.set_event_graph(result)

        app_logger.info("事理图谱构建完成")
        return {
            "code": 0,
            "data": result,
            "message": f"成功从 {len(users)} 条数据构建事理图谱"
        }
    except Exception as e:
        app_logger.error(f"从CSV构建事理图谱失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="事理图谱构建失败，请稍后重试")
