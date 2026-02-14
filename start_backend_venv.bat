@echo off
echo 激活虚拟环境并启动后端服务...
cd /d d:\workplace\adsagent
call .venv3\Scripts\activate.bat
cd backend
python main.py
