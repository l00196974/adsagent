#!/usr/bin/env python3
"""
测试批量事件抽象进度跟踪API
"""
import requests
import time
import json

BASE_URL = "http://localhost:8000/api/v1"

def test_progress_tracking():
    """测试进度跟踪功能"""
    print("=" * 60)
    print("测试批量事件抽象进度跟踪")
    print("=" * 60)

    # 1. 检查初始进度状态
    print("\n1. 检查初始进度状态...")
    response = requests.get(f"{BASE_URL}/events/extract/progress")
    print(f"状态码: {response.status_code}")
    print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")

    # 2. 启动批量抽象（后台执行）
    print("\n2. 启动批量抽象任务...")
    response = requests.post(f"{BASE_URL}/events/extract/start", json={"user_ids": None})
    print(f"状态码: {response.status_code}")
    print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")

    if response.status_code != 200:
        print("启动失败，可能已有任务在运行")
        return

    # 3. 轮询进度（最多30秒）
    print("\n3. 轮询进度...")
    for i in range(30):
        time.sleep(1)
        response = requests.get(f"{BASE_URL}/events/extract/progress")

        if response.status_code == 200:
            data = response.json()["data"]
            status = data["status"]
            progress = data.get("progress_percent", 0)
            processed = data.get("processed_users", 0)
            total = data.get("total_users", 0)

            print(f"[{i+1}s] 状态: {status}, 进度: {progress:.1f}%, 已处理: {processed}/{total}")

            if status in ["completed", "failed"]:
                print(f"\n任务完成！")
                print(f"成功: {data.get('success_count', 0)}")
                print(f"失败: {data.get('failed_count', 0)}")
                if data.get("error_message"):
                    print(f"错误: {data['error_message']}")
                break
        else:
            print(f"获取进度失败: {response.status_code}")
            break

    print("\n" + "=" * 60)

if __name__ == "__main__":
    try:
        test_progress_tracking()
    except requests.exceptions.ConnectionError:
        print("错误: 无法连接到后端服务器，请确保服务器正在运行")
    except Exception as e:
        print(f"错误: {e}")
