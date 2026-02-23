"""
基础建模模块API路由
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from typing import List, Optional
from pydantic import BaseModel
import pandas as pd
import io
from app.core.logger import app_logger
from app.core.exceptions import DataValidationError, BusinessException
from app.services.base_modeling import BaseModelingService

router = APIRouter(prefix="/modeling", tags=["基础建模"])

# 服务实例
modeling_service = BaseModelingService()


# ========== 请求/响应模型 ==========

class BehaviorDataItem(BaseModel):
    user_id: str
    action: str
    timestamp: str
    item_id: Optional[str] = None
    app_id: Optional[str] = None
    media_id: Optional[str] = None
    poi_id: Optional[str] = None
    duration: Optional[int] = None
    properties: Optional[dict] = None


class AppTagItem(BaseModel):
    app_id: str
    app_name: str
    category: Optional[str] = None
    tags: Optional[List[str]] = None


class MediaTagItem(BaseModel):
    media_id: str
    media_name: str
    media_type: Optional[str] = None
    tags: Optional[List[str]] = None


class UserProfileItem(BaseModel):
    user_id: str
    age: Optional[int] = None
    gender: Optional[str] = None
    city: Optional[str] = None
    occupation: Optional[str] = None
    properties: Optional[dict] = None


# ========== 行为数据接口 ==========

@router.post("/behavior/import")
async def import_behavior_data(file: UploadFile = File(...)):
    """导入行为数据CSV"""
    try:
        app_logger.info(f"开始导入行为数据: {file.filename}")

        if not file.filename.endswith('.csv'):
            raise HTTPException(status_code=400, detail="文件格式错误，请上传CSV文件")

        try:
            content = await file.read()
            df = pd.read_csv(io.BytesIO(content))
        except Exception as e:
            app_logger.error(f"CSV文件解析失败: {e}", exc_info=True)
            raise HTTPException(status_code=400, detail=f"CSV文件解析失败: {str(e)}")

        app_logger.info(f"成功读取CSV,共 {len(df)} 条记录, 列: {list(df.columns)}")

        required_columns = ['user_id', 'action', 'timestamp']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise HTTPException(
                status_code=400, 
                detail=f"CSV文件缺少必需列: {', '.join(missing_columns)}。当前列: {', '.join(df.columns)}"
            )

        behaviors = df.to_dict('records')

        result = modeling_service.import_behavior_data(behaviors)

        if result["success"]:
            return {
                "code": 0,
                "message": f"成功导入 {result['saved_count']} 条行为数据",
                "data": {
                    "total_count": result['saved_count'],
                    "columns": list(df.columns)
                }
            }
        else:
            raise HTTPException(status_code=500, detail=result["error"])

    except HTTPException:
        raise
    except Exception as e:
        app_logger.error(f"导入行为数据失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"导入失败: {str(e)}")


@router.get("/behavior/list")
async def list_behavior_data(
    user_id: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    """查询行为数据"""
    try:
        result = modeling_service.query_behavior_data(user_id, limit, offset)
        return {
            "code": 0,
            "data": result
        }
    except Exception as e:
        app_logger.error(f"查询行为数据失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.post("/behavior/add")
async def add_behavior_data(item: BehaviorDataItem):
    """页面添加单条行为数据"""
    try:
        app_logger.info(f"添加行为数据: user_id={item.user_id}, action={item.action}")

        # TODO: 实现添加逻辑

        return {
            "code": 0,
            "message": "成功添加行为数据",
            "data": item.dict()
        }
    except Exception as e:
        app_logger.error(f"添加行为数据失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"添加失败: {str(e)}")


# ========== APP标签接口 ==========

@router.post("/app-tags/import")
async def import_app_tags(file: UploadFile = File(...)):
    """导入APP列表并自动触发LLM打标"""
    try:
        app_logger.info(f"开始导入APP列表: {file.filename}")

        # 读取CSV
        content = await file.read()
        df = pd.read_csv(io.BytesIO(content))

        app_logger.info(f"成功读取CSV,共 {len(df)} 个APP")

        # 转换为字典列表
        apps = df.to_dict('records')

        # 调用服务层导入(异步)
        result = await modeling_service.import_app_list(apps)

        if result["success"]:
            return {
                "code": 0,
                "message": f"成功导入 {result['saved_count']} 个APP，LLM正在后台生成标签",
                "data": {
                    "total_count": result['saved_count'],
                    "columns": list(df.columns),
                    "tagging_status": result.get("tagging_status", "pending")
                }
            }
        else:
            raise HTTPException(status_code=500, detail=result["error"])

    except Exception as e:
        app_logger.error(f"导入APP列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"导入失败: {str(e)}")


@router.get("/app-tags/list")
async def list_app_tags(
    limit: int = 100,
    offset: int = 0
):
    """查询APP标签"""
    try:
        result = modeling_service.query_app_tags(limit, offset)
        return {
            "code": 0,
            "data": result
        }
    except Exception as e:
        app_logger.error(f"查询APP标签失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.get("/app-tags/status")
async def get_app_tagging_status():
    """查询APP打标进度"""
    try:
        # TODO: 实现进度查询逻辑
        return {
            "code": 0,
            "data": {
                "status": "idle",  # idle, in_progress, completed, failed
                "total": 0,
                "completed": 0,
                "progress": 0.0
            }
        }
    except Exception as e:
        app_logger.error(f"查询打标进度失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


# ========== 媒体标签接口 ==========

@router.post("/media-tags/import")
async def import_media_tags(file: UploadFile = File(...)):
    """导入媒体列表并自动触发LLM打标"""
    try:
        app_logger.info(f"开始导入媒体列表: {file.filename}")

        # 读取CSV
        content = await file.read()
        df = pd.read_csv(io.BytesIO(content))

        app_logger.info(f"成功读取CSV,共 {len(df)} 个媒体")

        # 转换为字典列表
        media_list = df.to_dict('records')

        # 调用服务层导入(异步)
        result = await modeling_service.import_media_list(media_list)

        if result["success"]:
            return {
                "code": 0,
                "message": f"成功导入 {result['saved_count']} 个媒体，LLM正在后台生成标签",
                "data": {
                    "total_count": result['saved_count'],
                    "columns": list(df.columns),
                    "tagging_status": result.get("tagging_status", "pending")
                }
            }
        else:
            raise HTTPException(status_code=500, detail=result["error"])

    except Exception as e:
        app_logger.error(f"导入媒体列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"导入失败: {str(e)}")


@router.get("/media-tags/list")
async def list_media_tags(
    limit: int = 100,
    offset: int = 0
):
    """查询媒体标签"""
    try:
        result = modeling_service.query_media_tags(limit, offset)
        return {
            "code": 0,
            "data": result
        }
    except Exception as e:
        app_logger.error(f"查询媒体标签失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.get("/media-tags/status")
async def get_media_tagging_status():
    """查询媒体打标进度"""
    try:
        # TODO: 实现进度查询逻辑
        return {
            "code": 0,
            "data": {
                "status": "idle",  # idle, in_progress, completed, failed
                "total": 0,
                "completed": 0,
                "progress": 0.0
            }
        }
    except Exception as e:
        app_logger.error(f"查询打标进度失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


# ========== 用户画像接口 ==========

@router.post("/profiles/import")
async def import_user_profiles(file: UploadFile = File(...)):
    """导入用户画像数据"""
    try:
        app_logger.info(f"开始导入用户画像: {file.filename}")

        # 读取CSV
        content = await file.read()
        df = pd.read_csv(io.BytesIO(content))

        app_logger.info(f"成功读取CSV,共 {len(df)} 个用户")

        # 转换为字典列表
        profiles = df.to_dict('records')

        # 调用服务层导入
        result = modeling_service.import_user_profiles(profiles)

        if result["success"]:
            return {
                "code": 0,
                "message": f"成功导入 {result['saved_count']} 个用户画像",
                "data": {
                    "total_count": result['saved_count'],
                    "columns": list(df.columns)
                }
            }
        else:
            raise HTTPException(status_code=500, detail=result["error"])

    except Exception as e:
        app_logger.error(f"导入用户画像失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"导入失败: {str(e)}")


@router.get("/profiles/list")
async def list_user_profiles(
    limit: int = 100,
    offset: int = 0
):
    """查询用户画像"""
    try:
        result = modeling_service.query_user_profiles(limit, offset)
        return {
            "code": 0,
            "data": result
        }
    except Exception as e:
        app_logger.error(f"查询用户画像失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")
