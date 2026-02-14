"""
事件抽象模块API路由
"""
from fastapi import APIRouter, HTTPException
from typing import List, Optional
from pydantic import BaseModel
from app.core.logger import app_logger
from app.services.event_extraction import EventExtractionService

router = APIRouter(prefix="/events", tags=["事件抽象"])

# 服务实例
extraction_service = EventExtractionService()


# ========== 请求/响应模型 ==========

class ExtractEventsRequest(BaseModel):
    user_ids: Optional[List[str]] = None


# ========== 事件抽象接口 ==========

@router.post("/extract")
async def extract_events(request: ExtractEventsRequest = None):
    """触发事件抽象

    Args:
        user_ids: 用户ID列表,如果为空则处理所有未抽象的用户
    """
    try:
        user_ids = request.user_ids if request else None
        app_logger.info(f"开始事件抽象: user_ids={user_ids}")

        result = await extraction_service.extract_events_batch(user_ids)

        if result["success"]:
            return {
                "code": 0,
                "message": f"事件抽象完成: 成功 {result['success_count']}/{result['total_users']}",
                "data": {
                    "total_users": result["total_users"],
                    "success_count": result["success_count"],
                    "failed_count": result["failed_count"]
                }
            }
        else:
            raise HTTPException(status_code=500, detail=result.get("error", "事件抽象失败"))

    except Exception as e:
        app_logger.error(f"事件抽象失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"事件抽象失败: {str(e)}")


@router.post("/extract/{user_id}")
async def extract_events_for_user(user_id: str):
    """为单个用户触发事件抽象"""
    try:
        app_logger.info(f"开始为用户 [{user_id}] 抽象事件")

        result = await extraction_service.extract_events_for_user(user_id)

        if result["success"]:
            return {
                "code": 0,
                "message": f"用户 [{user_id}] 事件抽象完成",
                "data": {
                    "user_id": user_id,
                    "event_count": result["event_count"],
                    "events": result["events"]
                }
            }
        else:
            raise HTTPException(status_code=500, detail=result.get("error", "事件抽象失败"))

    except Exception as e:
        app_logger.error(f"用户 [{user_id}] 事件抽象失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"事件抽象失败: {str(e)}")


@router.get("/sequences")
async def list_event_sequences(limit: int = 100, offset: int = 0):
    """查询用户事件序列列表"""
    try:
        result = extraction_service.get_user_sequences(limit, offset)

        return {
            "code": 0,
            "data": result
        }

    except Exception as e:
        app_logger.error(f"查询用户序列列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.get("/sequences/{user_id}")
async def get_user_sequence(user_id: str):
    """查询单个用户的详细序列"""
    try:
        result = extraction_service.get_user_sequences(limit=1000, offset=0)

        # 查找指定用户
        user_data = None
        for item in result["items"]:
            if item["user_id"] == user_id:
                user_data = item
                break

        if not user_data:
            raise HTTPException(status_code=404, detail=f"用户 [{user_id}] 不存在")

        return {
            "code": 0,
            "data": user_data
        }

    except HTTPException:
        raise
    except Exception as e:
        app_logger.error(f"查询用户 [{user_id}] 序列失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")
