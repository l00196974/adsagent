import asyncio
import sys
sys.path.insert(0, '/home/linxiankun/adsagent/backend')

from app.core.openai_client import OpenAIClient

async def test():
    client = OpenAIClient()
    gen = client.chat_completion("test", stream=True)
    print(f"Type: {type(gen)}")
    print(f"Is coroutine: {asyncio.iscoroutine(gen)}")
    print(f"Is async generator: {hasattr(gen, '__anext__')}")

asyncio.run(test())
