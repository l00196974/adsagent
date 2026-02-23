#!/bin/bash
# 清除旧的环境变量
unset ANTHROPIC_BASE_URL
unset OPENAI_BASE_URL

# 启动后端服务
cd /home/linxiankun/adsagent/backend
python3 main.py
