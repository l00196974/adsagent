"""
逻辑行为生成API路由
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional

from app.services.logical_behavior import LogicalBehaviorGenerator
from app.core.dependencies import get_logical_behavior_generator
from app.core.logger import app_logger
from app.core.exceptions import BusinessException, DatabaseError, LLMServiceError


router = APIRouter(prefix="/logical-behaviors", tags=["逻辑行为生成"])


class GenerateBatchRequest(BaseModel):
    """批量生成请求"""
    user_ids: List[str] = Field(..., description="用户ID列表")
    max_workers: int = Field(4, ge=1, le=10, description="并发数")


@router.post("/generate/batch")
async def generate_batch(
    request: GenerateBatchRequest,
    generator: LogicalBehaviorGenerator = Depends(get_logical_behavior_generator)
):
    """批量生成逻辑行为序列"""
    try:
        result = await generator.generate_batch(request.user_ids, request.max_workers)
        return {
            "code": 200,
            "message": "批量生成完成",
            "data": result
        }
    except Exception as e:
        app_logger.error(f"批量生成失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"批量生成失败: {str(e)}")


@router.post("/generate/{user_id}")
async def generate_for_user(
    user_id: str,
    generator: LogicalBehaviorGenerator = Depends(get_logical_behavior_generator)
):
    """为单个用户生成逻辑行为序列"""
    try:
        result = await generator.generate_for_user(user_id)
        return {
            "code": 200,
            "message": "生成成功",
            "data": result
        }
    except DatabaseError as e:
        app_logger.error(f"数据库错误: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except LLMServiceError as e:
        app_logger.error(f"LLM服务错误: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        app_logger.error(f"生成逻辑行为失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"生成失败: {str(e)}")


@router.get("/progress")
async def get_progress(
    generator: LogicalBehaviorGenerator = Depends(get_logical_behavior_generator)
):
    """获取生成进度"""
    try:
        progress = generator.get_progress()
        return {
            "code": 200,
            "message": "获取进度成功",
            "data": progress
        }
    except Exception as e:
        app_logger.error(f"获取进度失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取进度失败: {str(e)}")


@router.get("/query/{user_id}")
async def query_logical_behaviors(
    user_id: str,
    generator: LogicalBehaviorGenerator = Depends(get_logical_behavior_generator)
):
    """查询用户的逻辑行为序列"""
    try:
        behaviors = generator.query_logical_behaviors(user_id)
        return {
            "code": 200,
            "message": "查询成功",
            "data": {
                "user_id": user_id,
                "logical_behaviors": behaviors,
                "count": len(behaviors)
            }
        }
    except DatabaseError as e:
        app_logger.error(f"数据库错误: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        app_logger.error(f"查询逻辑行为失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")
