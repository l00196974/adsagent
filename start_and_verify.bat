@echo off
echo ========================================
echo 启动并验证知识图谱系统
echo ========================================

echo.
echo [1/4] 检查Python环境...
python --version
if %errorlevel% neq 0 (
    echo 错误: Python未安装或不在PATH中
    pause
    exit /b 1
)

echo.
echo [2/4] 启动后端服务...
cd /d d:\workplace\adsagent\backend
start "后端服务" cmd /k "python main.py"
timeout /t 5 /nobreak >nul

echo.
echo [3/4] 验证后端服务...
curl -s http://localhost:8000/health
if %errorlevel% neq 0 (
    echo 警告: 后端服务可能未成功启动
    echo 请检查后端服务窗口的错误信息
) else (
    echo 后端服务启动成功!
)

echo.
echo [4/4] 启动前端服务...
cd /d d:\workplace\adsagent\frontend
start "前端服务" cmd /k "npm run dev"

echo.
echo ========================================
echo 服务启动完成
echo ========================================
echo.
echo 后端地址: http://localhost:8000
echo 前端地址: http://localhost:5173
echo.
echo 请等待10秒后访问前端页面
echo 如果页面无法访问,请检查两个命令行窗口的错误信息
echo.
pause
