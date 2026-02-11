@echo off
chcp 65001 >nul
echo ========================================
echo 广告知识图谱系统 - 自动化测试
echo ========================================

REM 设置工作目录
cd /d "%~dp0"

REM 检查Python
echo [1/5] 检查Python环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到Python，请先安装Python 3.11+
    exit /b 1
)
echo ✓ Python环境正常

REM 检查Node.js
echo [2/5] 检查Node.js环境...
node --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到Node.js，请先安装Node.js 20+
    exit /b 1
)
echo ✓ Node.js环境正常

REM 后端测试
echo [3/5] 运行后端测试...
cd backend
if exist requirements-test.txt (
    pip install -r requirements-test.txt -q
)
pytest tests/ -v --tb=short
if errorlevel 1 (
    echo ✗ 后端测试失败
    exit /b 1
)
echo ✓ 后端测试通过
cd ..

REM 前端测试
echo [4/5] 运行前端测试...
cd frontend
npm install --silent 2>nul
npm run test:run
if errorlevel 1 (
    echo ✗ 前端测试失败
    exit /b 1
)
echo ✓ 前端测试通过
cd ..

REM 数据验证
echo [5/5] 验证数据完整性...
python export_data.py
if errorlevel 1 (
    echo ✗ 数据生成失败
    exit /b 1
)
echo ✓ 数据生成成功

echo.
echo ========================================
echo ✓ 所有测试通过！
echo ========================================
exit /b 0
