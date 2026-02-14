import asyncio
from openai import AsyncOpenAI
import json
import re

async def test_improved_prompt():
    client = AsyncOpenAI(
        api_key='sk-cp-JR9Eu_CKlkUfY0S0eS32mTx39wLJ744mtaGTKKLpKfJyUiyyagPVNySKdWwMLsBA43Sh9L_6fxisX07gOy_5L2UJeNw-fv5TS0auu6b85t8OCEbMxxQhRMk',
        base_url='https://api.minimaxi.com/v1'
    )
    
    # 改进的prompt - 更明确要求输出格式
    prompt = """请为以下APP生成3-5个标签。

APP名称: 微信
分类: 社交通讯

要求:
1. 标签描述APP的核心功能、用户群体、使用场景
2. 标签要简洁(2-4个字)
3. 直接输出JSON数组,格式: ["标签1", "标签2", "标签3"]

请直接输出JSON数组:"""
    
    response = await client.chat.completions.create(
        model='MiniMax-M2.1',
        max_tokens=300,
        temperature=0.3,
        messages=[{"role": "user", "content": prompt}]
    )
    
    result = response.choices[0].message.content
    print(f"原始响应:\n{result}\n")
    print("=" * 60)
    
    # 处理响应
    if '<think>' in result:
        result = result.split('</think>')[-1].strip()
        print(f"移除<think>后:\n{result}\n")
        print("=" * 60)
    
    # 提取JSON
    json_match = re.search(r'\[.*?\]', result, re.DOTALL)
    if json_match:
        json_str = json_match.group(0)
        tags = json.loads(json_str)
        print(f"✓ 成功解析标签: {tags}")
        print(f"标签数量: {len(tags)}")
    else:
        print(f"✗ 未找到JSON数组")
        print(f"响应内容: [{result}]")

asyncio.run(test_improved_prompt())
