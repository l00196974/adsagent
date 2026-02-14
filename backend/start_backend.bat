@echo off
REM 清除可能存在的旧环境变量
set ANTHROPIC_BASE_URL=
set ANTHROPIC_API_KEY=

REM 启动后端服务
echo 正在启动后端服务...
python main.py
