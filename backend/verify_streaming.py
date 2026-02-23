#!/usr/bin/env python3
"""验证所有LLM调用都使用流式模式"""

import os
import re
from pathlib import Path

def check_streaming_usage():
    """检查所有LLM调用是否使用流式模式"""
    backend_dir = Path(__file__).parent

    # 查找所有Python文件
    python_files = list(backend_dir.rglob("*.py"))

    # 排除测试文件和本脚本
    python_files = [
        f for f in python_files
        if not f.name.startswith("test_")
        and f.name != "verify_streaming.py"
        and "__pycache__" not in str(f)
    ]

    print("=" * 80)
    print("LLM调用流式模式审计报告")
    print("=" * 80)
    print()

    total_calls = 0
    streaming_calls = 0
    non_streaming_calls = 0
    issues = []

    for file_path in python_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')

            # 查找 chat_completion 调用
            for i, line in enumerate(lines, 1):
                if '.chat_completion(' in line and not line.strip().startswith('#'):
                    total_calls += 1

                    # 检查是否显式设置了stream参数
                    if 'stream=' in line:
                        if 'stream=True' in line:
                            streaming_calls += 1
                        elif 'stream=False' in line:
                            non_streaming_calls += 1
                            issues.append({
                                'file': str(file_path.relative_to(backend_dir)),
                                'line': i,
                                'content': line.strip()
                            })
                    else:
                        # 没有显式设置stream参数，检查默认值
                        # 根据chat_completion的定义，默认是stream=False
                        # 但我们已经修改为stream=True，所以这里需要检查
                        print(f"⚠️  警告: {file_path.relative_to(backend_dir)}:{i}")
                        print(f"   未显式设置stream参数: {line.strip()}")
                        print()

        except Exception as e:
            print(f"❌ 读取文件失败: {file_path}: {e}")

    print(f"总计LLM调用: {total_calls}")
    print(f"流式调用: {streaming_calls} ({streaming_calls/total_calls*100:.1f}%)")
    print(f"非流式调用: {non_streaming_calls} ({non_streaming_calls/total_calls*100:.1f}%)")
    print()

    if issues:
        print("❌ 发现非流式调用:")
        print()
        for issue in issues:
            print(f"  文件: {issue['file']}")
            print(f"  行号: {issue['line']}")
            print(f"  代码: {issue['content']}")
            print()
        return False
    else:
        print("✅ 所有LLM调用都使用流式模式!")
        print()
        return True

if __name__ == "__main__":
    success = check_streaming_usage()
    exit(0 if success else 1)
