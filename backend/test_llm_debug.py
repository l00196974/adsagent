"""
调试 LLM 响应 - 打印完整响应
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.core.openai_client import OpenAIClient
import json
import logging

# 设置详细日志
logging.basicConfig(level=logging.DEBUG)


async def test_raw_llm_response():
    """直接测试 LLM 响应"""
    print("=" * 80)
    print("测试: 直接查看 LLM 原始响应")
    print("=" * 80)

    client = OpenAIClient()

    # 简单的 prompt
    prompt = """你是一个用户行为分析专家。请将以下用户的原始行为数据抽象为高层次的事件。

用户 user_001 (年龄35岁, 男, 收入高):
  - 2026-02-13 10:00:00 在宝马4S店(汽车4S店)停留2小时
  - 2026-02-13 15:00:00 在汽车之家搜索:宝马7系价格

要求:
1. 将细粒度的行为抽象为有业务意义的事件
2. 事件类型要简洁(2-6个中文字)
3. 保留时间信息
4. 提取关键上下文信息
5. 必须返回JSON对象格式

输出格式示例:
{
  "user_001": [
    {
      "event_type": "看车",
      "timestamp": "2026-02-13 10:00:00",
      "context": {"brand": "宝马", "poi_type": "4S店", "duration": "2小时"}
    },
    {
      "event_type": "关注豪华轿车",
      "timestamp": "2026-02-13 15:00:00",
      "context": {"brand": "宝马", "model": "7系"}
    }
  ]
}

请严格按照上述JSON格式输出,不要添加任何其他说明文字:"""

    print("\n发送 Prompt:")
    print("-" * 80)
    print(prompt)
    print("-" * 80)

    try:
        response = await client.chat_completion(prompt, max_tokens=1000)

        print("\n原始响应:")
        print("=" * 80)
        print(response)
        print("=" * 80)

        # 尝试解析
        print("\n尝试解析 JSON...")

        # 移除 <think> 标签
        if '<think>' in response:
            response = response.split('</think>')[-1].strip()
            print(f"\n移除 <think> 后:")
            print(response)

        # 提取 JSON
        import re
        json_match = re.search(r'\{(?:[^{}]|(?:\{[^{}]*\}))*\}', response, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            print(f"\n提取的 JSON 字符串:")
            print(json_str)

            data = json.loads(json_str)
            print(f"\n解析后的数据:")
            print(json.dumps(data, ensure_ascii=False, indent=2))

            if "user_001" in data:
                print(f"\n✓ 成功找到 user_001 的数据")
                return True
            else:
                print(f"\n✗ JSON 中没有 user_001 键")
                print(f"实际的键: {list(data.keys())}")
                return False
        else:
            print("\n✗ 未找到 JSON 对象")
            return False

    except Exception as e:
        print(f"\n✗ 异常: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_raw_llm_response())
    sys.exit(0 if success else 1)
