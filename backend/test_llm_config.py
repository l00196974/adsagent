"""
测试LLM配置和API调用
"""
import asyncio
import sys
import os
from pathlib import Path

# 添加backend目录到Python路径
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app.core.config import settings
from app.core.anthropic_client import AnthropicClient
from openai import AsyncOpenAI

async def test_config_loading():
    """测试配置加载"""
    print("=" * 60)
    print("1. 配置加载测试")
    print("=" * 60)

    print(f"ANTHROPIC_API_KEY: {settings.anthropic_api_key[:20]}...")
    print(f"ANTHROPIC_BASE_URL: {settings.anthropic_base_url}")
    print(f"PRIMARY_MODEL: {settings.primary_model}")
    print(f"REASONING_MODEL: {settings.reasoning_model}")
    print(f"MAX_TOKENS_PER_REQUEST: {settings.max_tokens_per_request}")

    # 检查环境变量
    print("\n环境变量:")
    print(f"os.getenv('ANTHROPIC_BASE_URL'): {os.getenv('ANTHROPIC_BASE_URL')}")
    print(f"os.getenv('PRIMARY_MODEL'): {os.getenv('PRIMARY_MODEL')}")

    # 检查.env文件
    env_file = backend_dir / ".env"
    print(f"\n.env文件路径: {env_file}")
    print(f".env文件存在: {env_file.exists()}")

    if env_file.exists():
        print("\n.env文件内容:")
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                if 'ANTHROPIC' in line or 'MODEL' in line:
                    print(f"  {line.strip()}")

async def test_anthropic_client():
    """测试AnthropicClient初始化"""
    print("\n" + "=" * 60)
    print("2. AnthropicClient初始化测试")
    print("=" * 60)

    client = AnthropicClient()
    print(f"Client类型: {type(client.client)}")
    print(f"Client base_url: {client.client.base_url}")
    print(f"Primary model: {client.primary_model}")
    print(f"Reasoning model: {client.reasoning_model}")

async def test_direct_api_call():
    """测试直接API调用"""
    print("\n" + "=" * 60)
    print("3. 直接API调用测试")
    print("=" * 60)

    # 使用配置中的值
    client = AsyncOpenAI(
        api_key=settings.anthropic_api_key,
        base_url=settings.anthropic_base_url
    )

    print(f"使用base_url: {client.base_url}")
    print(f"使用model: {settings.primary_model}")

    try:
        response = await client.chat.completions.create(
            model=settings.primary_model,
            max_tokens=200,
            temperature=0.3,
            messages=[{"role": "user", "content": "请说'测试成功'"}]
        )

        result = response.choices[0].message.content if response.choices else ""
        print(f"✓ API调用成功!")
        print(f"响应: {result}")
        return True
    except Exception as e:
        print(f"✗ API调用失败: {e}")
        return False

async def test_generate_app_tags():
    """测试generate_app_tags方法"""
    print("\n" + "=" * 60)
    print("4. generate_app_tags方法测试")
    print("=" * 60)

    client = AnthropicClient()

    try:
        tags = await client.generate_app_tags("微信", "社交通讯")
        print(f"✓ 标签生成成功!")
        print(f"生成的标签: {tags}")
        return True
    except Exception as e:
        print(f"✗ 标签生成失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("LLM配置和API调用诊断测试")
    print("=" * 60)

    # 测试1: 配置加载
    await test_config_loading()

    # 测试2: AnthropicClient初始化
    await test_anthropic_client()

    # 测试3: 直接API调用
    api_success = await test_direct_api_call()

    # 测试4: generate_app_tags
    if api_success:
        await test_generate_app_tags()
    else:
        print("\n跳过generate_app_tags测试(因为直接API调用失败)")

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
