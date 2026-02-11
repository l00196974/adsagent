from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from app.services.qa_engine import QAEngine
from app.services.event_graph import EventGraphBuilder
from app.core.anthropic_client import AnthropicClient

router = APIRouter()

_llm_client = None
_qa_engine = None
_event_graph_builder = None
_event_graph_data = {}

class QARequest(BaseModel):
    question: str

def init_services():
    global _llm_client, _qa_engine, _event_graph_builder
    try:
        _llm_client = AnthropicClient()
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

@router.post("/event-graph/generate")
async def generate_event_graph(
    industry: str = "汽车",
    total_samples: int = 1000
):
    global _event_graph_builder, _event_graph_data, _qa_engine
    if not _event_graph_builder:
        init_services()
    try:
        result = await _event_graph_builder.build(
            industry=industry,
            total_samples=total_samples
        )
        _event_graph_data = result
        if _qa_engine:
            _qa_engine.set_event_graph(result)
        return {"code": 0, "data": result, "message": "事理图谱生成成功"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
