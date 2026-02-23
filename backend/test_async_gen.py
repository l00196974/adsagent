import asyncio
import httpx

async def test_stream():
    """测试async generator"""
    client = httpx.AsyncClient(timeout=30.0)
    try:
        async with client.stream(
            "POST",
            "https://httpbin.org/post",
            json={"test": "data"}
        ) as response:
            async for line in response.aiter_lines():
                print(f"Line: {line[:50]}")
                yield line
    finally:
        await client.aclose()

async def main():
    print("Testing async generator...")
    gen = test_stream()
    print(f"Generator type: {type(gen)}")

    count = 0
    async for item in gen:
        count += 1
        if count >= 3:
            break

    print(f"Success! Received {count} items")

if __name__ == "__main__":
    asyncio.run(main())
