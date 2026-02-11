#!/bin/bash
# 广告知识图谱系统 - 自动化测试脚本

set -e  # 遇到错误立即退出

echo "========================================"
echo "广告知识图谱系统 - 自动化测试"
echo "========================================"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查函数
check_command() {
    if command -v $1 &> /dev/null; then
        echo -e "${GREEN}✓${NC} $2"
    else
        echo -e "${RED}✗${NC} $2 未安装"
        exit 1
    fi
}

# 检查环境
echo ""
echo "检查运行环境..."
check_command python "Python 3.11+"
check_command node "Node.js 20+"
check_command npm "npm"

# 后端测试
echo ""
echo "========================================"
echo "后端测试"
echo "========================================"

cd backend

# 安装依赖
if [ -f requirements.txt ]; then
    echo "安装后端依赖..."
    pip install -q -r requirements.txt
fi

if [ -f requirements-test.txt ]; then
    echo "安装测试依赖..."
    pip install -q -r requirements-test.txt
fi

# 运行测试
echo "运行后端单元测试..."
pytest tests/ -v --tb=short --cov=app --cov-report=term-missing

if [ $? -ne 0 ]; then
    echo -e "${RED}✗ 后端测试失败${NC}"
    exit 1
fi

echo -e "${GREEN}✓ 后端测试通过${NC}"
cd ..

# 前端测试
echo ""
echo "========================================"
echo "前端测试"
echo "========================================"

cd frontend

# 安装依赖
echo "安装前端依赖..."
npm install --silent

# 运行测试
echo "运行前端测试..."
npm run test:run

if [ $? -ne 0 ]; then
    echo -e "${RED}✗ 前端测试失败${NC}"
    exit 1
fi

echo -e "${GREEN}✓ 前端测试通过${NC}"

# 代码检查
echo ""
echo "========================================"
echo "代码质量检查"
echo "========================================"

echo "运行ESLint..."
npm run lint -- --max-warnings=0 || true

echo "运行Prettier检查..."
npm run format -- --check || true

cd ..

# 数据验证
echo ""
echo "========================================"
echo "数据验证"
echo "========================================"

echo "生成测试数据..."
cd backend
python ../export_data.py

if [ $? -ne 0 ]; then
    echo -e "${RED}✗ 数据生成失败${NC}"
    exit 1
fi

echo -e "${GREEN}✓ 数据生成成功${NC}"
cd ..

echo ""
echo "========================================"
echo -e "${GREEN}✓ 所有测试通过！${NC}"
echo "========================================"
