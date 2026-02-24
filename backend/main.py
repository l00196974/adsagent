from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import qa_routes, base_modeling_routes, event_extraction_routes, sequence_mining_routes, causal_graph_routes, logical_behavior_routes
from app.core.config import settings
from app.core.exceptions import (
    BusinessException,
    business_exception_handler,
    general_exception_handler,
    http_exception_handler
)
from app.core.logger import app_logger
from app.core.database import init_db
from fastapi import HTTPException

app = FastAPI(
    title="广告知识图谱系统",
    description="知识图谱+事理图谱生成与智能问答",
    version="1.0.0"
)

# 初始化数据库
@app.on_event("startup")
async def startup_event():
    """应用启动时初始化数据库"""
    app_logger.info("初始化数据库...")
    init_db()
    app_logger.info("数据库初始化完成")

# 注册异常处理器
app.add_exception_handler(BusinessException, business_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(qa_routes.router, prefix="/api/v1/qa")
app.include_router(base_modeling_routes.router, prefix="/api/v1")
app.include_router(event_extraction_routes.router, prefix="/api/v1")
app.include_router(sequence_mining_routes.router, prefix="/api/v1")
app.include_router(causal_graph_routes.router, prefix="/api/v1")
app.include_router(logical_behavior_routes.router, prefix="/api/v1")

@app.get("/health")
async def health():
    app_logger.info("健康检查请求")
    return {"status": "ok", "message": "广告知识图谱系统运行中"}

@app.get("/")
async def root():
    return {
        "name": "广告知识图谱系统",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "base_modeling": "/api/v1/modeling",
            "event_extraction": "/api/v1/events",
            "qa": "/api/v1/qa",
            "sequence_mining": "/api/v1/mining",
            "causal_graph": "/api/v1/causal-graph",
            "logical_behaviors": "/api/v1/logical-behaviors"
        }
    }

if __name__ == "__main__":
    import uvicorn
    app_logger.info(f"启动广告知识图谱系统 - {settings.app_host}:{settings.app_port}")
    uvicorn.run(app, host=settings.app_host, port=settings.app_port)
