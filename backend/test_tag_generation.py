import asyncio
from openai import AsyncOpenAI

async def test_tag_generation():
    client = AsyncOpenAI(
        api_key='sk-cp-JR9Eu_CKlkUfY0S0eS32mTx39wLJ744mtaGTKKLpKfJyUiyyagPVNySKdWwMLsBA43Sh9L_6fxisX07gOy_5L2UJeNw-fv5TS0auu6b85t8OCEbMxxQhRMk',
        base_url='https://api.minimaxi.com/v1'
    )
    
    prompt = """你是一个移动应用分析专家。请为以下APP生成3-5个精准的标签。

APP名称: 微信
分类: 社交通讯

要求:
1. 标签应该描述APP的核心功能、用户群体、使用场景
2. 标签要简洁(2-4个字)
3. 必须直接返回JSON数组格式,例如: ["社交", "即时通讯", "年轻人"]
4. 不要有任何其他文字说明,只返回JSON数组

JSON数组:"""
    
    response = await client.chat.completions.create(
        model='MiniMax-M2.1',
        max_tokens=200,
        temperature=0.3,
        messages=[{"role": "user", "content": prompt}]
    )
    
    result = response.choices[0].message.content
    print(f"原始响应:\n{result}\n")
    
    # 处理响应
    if '<think>' in result:
        result = result.split('</think>')[-1].strip()
        print(f"移除<think>后:\n{result}\n")
    
    # 提取JSON
    import re
    import json
    json_match = re.search(r'\[.*?\]', result, re.DOTALL)
    if json_match:
        tags = json.loads(json_match.group(0))
        print(f"✓ 成功解析标签: {tags}")
    else:
        print(f"✗ 未找到JSON数组")

asyncio.run(test_tag_generation())
