from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import graph_routes, sample_routes, qa_routes
from app.core.config import settings

app = FastAPI(
    title="广告知识图谱系统",
    description="知识图谱+事理图谱生成与智能问答",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(graph_routes.router, prefix="/api/v1/graphs")
app.include_router(sample_routes.router, prefix="/api/v1/samples")
app.include_router(qa_routes.router, prefix="/api/v1/qa")

@app.get("/health")
async def health():
    return {"status": "ok", "message": "广告知识图谱系统运行中"}

@app.get("/")
async def root():
    return {
        "name": "广告知识图谱系统",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "knowledge_graph": "/api/v1/graphs/knowledge",
            "samples": "/api/v1/samples",
            "qa": "/api/v1/qa"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.app_host, port=settings.app_port)
