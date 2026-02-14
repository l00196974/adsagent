"""真正的端到端验证脚本"""
import subprocess
import time
import requests
import sys
import os

print("=" * 60)
print("知识图谱系统 - 真实启动验证")
print("=" * 60)

# 1. 启动后端
print("\n[1/3] 启动后端服务...")
backend_dir = r'd:\workplace\adsagent\backend'
backend_process = subprocess.Popen(
    [sys.executable, 'main.py'],
    cwd=backend_dir,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)

# 等待后端启动
print("等待后端启动...")
for i in range(10):
    time.sleep(1)
    try:
        response = requests.get('http://localhost:8000/health', timeout=2)
        if response.status_code == 200:
            print(f"✓ 后端启动成功! 响应: {response.json()}")
            break
    except:
        print(f"  等待中... ({i+1}/10)")
else:
    print("✗ 后端启动失败!")
    backend_process.kill()
    sys.exit(1)

# 2. 启动前端
print("\n[2/3] 启动前端服务...")
frontend_dir = r'd:\workplace\adsagent\frontend'
frontend_process = subprocess.Popen(
    ['npm', 'run', 'dev'],
    cwd=frontend_dir,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)

# 等待前端启动
print("等待前端启动...")
for i in range(15):
    time.sleep(1)
    try:
        response = requests.get('http://localhost:5173', timeout=2)
        if response.status_code == 200:
            print(f"✓ 前端启动成功!")
            break
    except:
        print(f"  等待中... ({i+1}/15)")
else:
    print("✗ 前端启动失败!")
    backend_process.kill()
    frontend_process.kill()
    sys.exit(1)

# 3. 验证完整性
print("\n[3/3] 验证系统完整性...")
try:
    # 测试后端API
    response = requests.get('http://localhost:8000/api/v1/graphs/knowledge/stats')
    print(f"✓ 后端API正常: {response.json()}")

    print("\n" + "=" * 60)
    print("✓ 系统启动成功!")
    print("=" * 60)
    print("\n访问地址:")
    print("  前端: http://localhost:5173")
    print("  后端: http://localhost:8000")
    print("  API文档: http://localhost:8000/docs")
    print("\n测试CSV文件位置:")
    print("  d:\\workplace\\adsagent\\backend\\data\\test_data.csv")
    print("\n按Ctrl+C停止服务...")

    # 保持运行
    while True:
        time.sleep(1)

except KeyboardInterrupt:
    print("\n\n停止服务...")
    backend_process.kill()
    frontend_process.kill()
    print("服务已停止")
except Exception as e:
    print(f"\n✗ 验证失败: {e}")
    backend_process.kill()
    frontend_process.kill()
    sys.exit(1)
