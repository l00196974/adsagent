"""启动后端服务的辅助脚本"""
import os
import sys

# 切换到backend目录
backend_dir = r'd:\workplace\adsagent\backend'
os.chdir(backend_dir)

# 添加到Python路径
sys.path.insert(0, backend_dir)

# 启动服务
if __name__ == "__main__":
    import uvicorn
    from app.core.config import settings

    print(f"启动后端服务: {settings.app_host}:{settings.app_port}")
    uvicorn.run(
        "main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=False
    )
