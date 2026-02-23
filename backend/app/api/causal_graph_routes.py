"""
事理图谱API路由
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
import logging
import json

from app.services.causal_graph_service import CausalGraphService
from app.core.openai_client import OpenAIClient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/causal-graph", tags=["事理图谱"])


# ========== 请求模型 ==========

class GenerateCausalGraphRequest(BaseModel):
    """生成事理图谱请求"""
    pattern_ids: Optional[List[int]] = Field(None, description="高频模式ID列表，None表示使用所有模式")
    analysis_focus: str = Field("comprehensive", description="分析重点：comprehensive/conversion/churn/profile")
    graph_name: Optional[str] = Field(None, description="图谱名称")


class QueryRequest(BaseModel):
    """问答请求"""
    question: str = Field(..., description="用户问题")
    user_context: Optional[Dict] = Field(None, description="用户上下文（画像和行为序列）")


# ========== 依赖注入 ==========

def get_causal_graph_service() -> CausalGraphService:
    """获取事理图谱服务实例"""
    llm_client = OpenAIClient()
    return CausalGraphService(llm_client)


# ========== API端点 ==========

@router.post("/generate")
async def generate_causal_graph(
    request: GenerateCausalGraphRequest,
    service: CausalGraphService = Depends(get_causal_graph_service)
):
    """生成事理图谱（非流式）

    基于高频模式生成事理图谱，支持选择特定模式或使用所有模式。
    """
    try:
        logger.info(f"收到生成事理图谱请求: {request.dict()}")

        result = await service.generate_from_patterns(
            pattern_ids=request.pattern_ids,
            analysis_focus=request.analysis_focus,
            graph_name=request.graph_name
        )

        return {
            "success": True,
            "data": result,
            "message": "事理图谱生成成功"
        }

    except ValueError as e:
        logger.error(f"生成事理图谱失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"生成事理图谱异常: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"生成事理图谱失败: {str(e)}")


@router.post("/generate/stream")
async def generate_causal_graph_stream(
    request: GenerateCausalGraphRequest,
    service: CausalGraphService = Depends(get_causal_graph_service)
):
    """生成事理图谱（流式）

    使用 Server-Sent Events (SSE) 流式返回生成进度和结果。
    """
    async def event_generator():
        try:
            logger.info(f"收到流式生成事理图谱请求: {request.dict()}")

            # 发送开始事件
            yield f"data: {json.dumps({'type': 'start', 'message': '开始生成事理图谱...'}, ensure_ascii=False)}\n\n"

            # 调用流式生成
            async for chunk in service.generate_from_patterns_stream(
                pattern_ids=request.pattern_ids,
                analysis_focus=request.analysis_focus,
                graph_name=request.graph_name
            ):
                yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"

            # 发送完成事件
            yield f"data: {json.dumps({'type': 'done', 'message': '生成完成'}, ensure_ascii=False)}\n\n"

        except Exception as e:
            logger.error(f"流式生成事理图谱异常: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # 禁用 nginx 缓冲
        }
    )


@router.get("/list")
async def list_causal_graphs(
    limit: int = 20,
    offset: int = 0,
    service: CausalGraphService = Depends(get_causal_graph_service)
):
    """获取事理图谱列表

    返回所有已生成的事理图谱，支持分页。
    """
    try:
        result = await service.list_graphs(limit=limit, offset=offset)

        return {
            "success": True,
            "data": result,
            "message": "获取事理图谱列表成功"
        }

    except Exception as e:
        logger.error(f"获取事理图谱列表异常: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取事理图谱列表失败: {str(e)}")


@router.get("/{graph_id}")
async def get_causal_graph(
    graph_id: int,
    service: CausalGraphService = Depends(get_causal_graph_service)
):
    """获取指定的事理图谱

    返回完整的事理图谱数据，包括节点、边和洞察。
    """
    try:
        result = await service.get_graph_by_id(graph_id)

        return {
            "success": True,
            "data": result,
            "message": "获取事理图谱成功"
        }

    except ValueError as e:
        logger.error(f"获取事理图谱失败: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"获取事理图谱异常: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取事理图谱失败: {str(e)}")


@router.delete("/{graph_id}")
async def delete_causal_graph(
    graph_id: int,
    service: CausalGraphService = Depends(get_causal_graph_service)
):
    """删除事理图谱

    删除指定的事理图谱及其所有关联数据。
    """
    try:
        await service.delete_graph(graph_id)

        return {
            "success": True,
            "message": "删除事理图谱成功"
        }

    except ValueError as e:
        logger.error(f"删除事理图谱失败: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"删除事理图谱异常: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"删除事理图谱失败: {str(e)}")


@router.post("/{graph_id}/query")
async def query_with_graph(
    graph_id: int,
    request: QueryRequest,
    service: CausalGraphService = Depends(get_causal_graph_service)
):
    """基于事理图谱回答问题

    使用事理图谱数据回答用户问题，支持提供用户上下文。
    """
    try:
        logger.info(f"收到问答请求: graph_id={graph_id}, question={request.question}")

        result = await service.answer_question_with_graph(
            graph_id=graph_id,
            question=request.question,
            user_context=request.user_context
        )

        return {
            "success": True,
            "data": result,
            "message": "问答成功"
        }

    except ValueError as e:
        logger.error(f"问答失败: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"问答异常: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"问答失败: {str(e)}")
