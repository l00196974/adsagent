"""
测试 MiniMax-M2.5 模型调用
"""
import asyncio
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from app.core.openai_client import OpenAIClient
from app.core.config import settings


async def test_basic_chat():
    """测试基础对话功能"""
    print("=" * 60)
    print("测试 1: 基础对话")
    print("=" * 60)

    client = OpenAIClient()

    prompt = "请用一句话介绍你自己。"
    print(f"\n提问: {prompt}")

    try:
        response = await client.chat_completion(prompt, max_tokens=200)
        print(f"\n回答: {response}")
        print("\n✓ 基础对话测试通过")
        return True
    except Exception as e:
        print(f"\n✗ 基础对话测试失败: {e}")
        return False


async def test_json_output():
    """测试 JSON 格式输出"""
    print("\n" + "=" * 60)
    print("测试 2: JSON 格式输出")
    print("=" * 60)

    client = OpenAIClient()

    prompt = """请为以下3个APP生成标签，返回JSON格式：
1. 微信
2. 抖音
3. 淘宝

要求：
- 每个APP生成3-5个标签
- 返回格式: {"微信": ["标签1", "标签2"], ...}
- 只返回JSON，不要其他文字"""

    print(f"\n提问: {prompt}")

    try:
        response = await client.chat_completion(prompt, max_tokens=500)
        print(f"\n回答: {response}")

        # 尝试解析 JSON
        import json
        import re
        json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            data = json.loads(json_str)
            print(f"\n解析后的JSON: {json.dumps(data, ensure_ascii=False, indent=2)}")
            print("\n✓ JSON输出测试通过")
            return True
        else:
            print("\n✗ 未找到有效的JSON格式")
            return False
    except Exception as e:
        print(f"\n✗ JSON输出测试失败: {e}")
        return False


async def test_reasoning():
    """测试推理能力"""
    print("\n" + "=" * 60)
    print("测试 3: 推理能力")
    print("=" * 60)

    client = OpenAIClient()

    prompt = """分析以下用户行为，推断用户的购车意向：

用户A:
- 在宝马4S店停留2小时
- 搜索"宝马7系价格"
- 浏览宝马官网配置页面
- 经常使用高尔夫APP

请分析：
1. 用户的购车意向强度（高/中/低）
2. 推荐的广告投放策略

用简洁的语言回答（3-5句话）。"""

    print(f"\n提问: {prompt}")

    try:
        response = await client.chat_completion(prompt, max_tokens=500, temperature=0.3)
        print(f"\n回答: {response}")
        print("\n✓ 推理能力测试通过")
        return True
    except Exception as e:
        print(f"\n✗ 推理能力测试失败: {e}")
        return False


async def test_batch_tagging():
    """测试批量打标功能"""
    print("\n" + "=" * 60)
    print("测试 4: 批量APP打标")
    print("=" * 60)

    client = OpenAIClient()

    apps = [
        {"app_id": "app_001", "app_name": "微信", "category": "社交"},
        {"app_id": "app_002", "app_name": "抖音", "category": "娱乐"},
        {"app_id": "app_003", "app_name": "淘宝", "category": "购物"}
    ]

    print(f"\n待打标APP: {[app['app_name'] for app in apps]}")

    try:
        result = await client.generate_app_tags_batch(apps)
        print(f"\n打标结果:")
        for app_id, tags in result.items():
            app_name = next(app['app_name'] for app in apps if app['app_id'] == app_id)
            print(f"  {app_name}: {tags}")

        success_count = len([v for v in result.values() if v])
        if success_count == len(apps):
            print(f"\n✓ 批量打标测试通过 ({success_count}/{len(apps)})")
            return True
        else:
            print(f"\n⚠ 批量打标部分成功 ({success_count}/{len(apps)})")
            return False
    except Exception as e:
        print(f"\n✗ 批量打标测试失败: {e}")
        return False


async def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("MiniMax-M2.5 模型测试")
    print("=" * 60)
    print(f"\n配置信息:")
    print(f"  API Key: {settings.openai_api_key[:20]}...")
    print(f"  Base URL: {settings.openai_base_url}")
    print(f"  Primary Model: {settings.primary_model}")
    print(f"  Reasoning Model: {settings.reasoning_model}")
    print()

    results = []

    # 运行测试
    results.append(await test_basic_chat())
    results.append(await test_json_output())
    results.append(await test_reasoning())
    results.append(await test_batch_tagging())

    # 汇总结果
    print("\n" + "=" * 60)
    print("测试汇总")
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"\n通过: {passed}/{total}")

    if passed == total:
        print("\n✓ 所有测试通过！MiniMax-M2.5 模型工作正常。")
    else:
        print(f"\n⚠ {total - passed} 个测试失败，请检查配置或模型响应。")

    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
