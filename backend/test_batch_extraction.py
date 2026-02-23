#!/usr/bin/env python3
"""
测试批量事件抽象功能
"""
import asyncio
import sys
sys.path.insert(0, '.')

from app.services.event_extraction import EventExtractionService

async def test_batch_extraction():
    """测试批量事件抽象"""
    service = EventExtractionService()

    # 测试只处理2个用户
    test_user_ids = ['user_0002', 'user_0003']

    print(f"开始测试批量事件抽象...")
    print(f"测试用户: {test_user_ids}")

    try:
        result = await service.extract_events_batch(user_ids=test_user_ids)

        print(f"\n✓ 批量抽象完成!")
        print(f"  总用户数: {result['total_users']}")
        print(f"  成功: {result['success_count']}")
        print(f"  失败: {result['failed_count']}")

        if result['results']:
            print(f"\n前3个结果:")
            for i, r in enumerate(result['results'][:3], 1):
                print(f"  {i}. {r['user_id']}: {r['success']}")
                if r['success'] and 'events' in r:
                    print(f"     抽象了 {len(r['events'])} 个事件")

        # 检查进度
        progress = service.get_progress()
        print(f"\n进度状态: {progress['status']}")
        print(f"进度百分比: {progress['progress_percent']}%")

    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_batch_extraction())
