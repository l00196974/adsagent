"""
统一异常处理
"""
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from typing import Dict
import traceback
from app.core.logger import app_logger


class BusinessException(Exception):
    """业务异常基类"""
    def __init__(self, message: str, code: int = 400):
        self.message = message
        self.code = code
        super().__init__(self.message)


class DataValidationError(BusinessException):
    """数据验证错误"""
    def __init__(self, message: str):
        super().__init__(message, 400)


class ResourceNotFoundError(BusinessException):
    """资源不存在"""
    def __init__(self, message: str):
        super().__init__(message, 404)


class DatabaseError(BusinessException):
    """数据库错误"""
    def __init__(self, message: str):
        super().__init__(message, 500)


class LLMServiceError(BusinessException):
    """LLM服务错误"""
    def __init__(self, message: str):
        super().__init__(message, 503)


async def business_exception_handler(request: Request, exc: BusinessException) -> JSONResponse:
    """业务异常处理器"""
    app_logger.warning(f"业务异常: {exc.message}", exc_info=False)
    return JSONResponse(
        status_code=exc.code,
        content={
            "code": exc.code,
            "message": exc.message,
            "detail": "请检查请求参数或联系管理员"
        }
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """通用异常处理器"""
    # 记录完整的错误堆栈到日志
    app_logger.error(f"未处理的异常: {str(exc)}", exc_info=True)

    # 返回用户友好的错误信息（不泄露内部细节）
    return JSONResponse(
        status_code=500,
        content={
            "code": 500,
            "message": "服务器内部错误",
            "detail": "操作失败，请稍后重试"
        }
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """HTTP异常处理器"""
    app_logger.warning(f"HTTP异常 {exc.status_code}: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.status_code,
            "message": exc.detail,
            "detail": "请求处理失败"
        }
    )


def safe_execute(func, *args, fallback_value=None, error_message="操作失败", **kwargs):
    """安全执行函数，捕获异常并返回fallback值"""
    try:
        return func(*args, **kwargs)
    except Exception as e:
        app_logger.error(f"{error_message}: {str(e)}", exc_info=True)
        return fallback_value
