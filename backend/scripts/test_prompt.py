#!/usr/bin/env python3
"""
测试事件抽取prompt的独立脚本
用于快速测试prompt效果，无需重启服务
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import sqlite3
import asyncio
from app.core.openai_client import OpenAIClient

async def test_prompt_with_user(user_id: str, limit: int = 20):
    """测试指定用户的事件抽取

    Args:
        user_id: 用户ID
        limit: 限制行为数量（用于快速测试）
    """
    print(f"\n{'='*60}")
    print(f"测试用户: {user_id} (限制{limit}条行为)")
    print(f"{'='*60}\n")

    # 1. 从数据库加载行为数据
    db_path = "data/graph.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute(f"""
        SELECT timestamp, behavior_text, action
        FROM behavior_data
        WHERE user_id = ?
        ORDER BY timestamp
        LIMIT {limit}
    """, (user_id,))

    behaviors = []
    conversion_count = 0
    for row in cursor.fetchall():
        behaviors.append({
            "timestamp": row[0],
            "behavior_text": row[1]
        })
        if row[2] in ('purchase', 'add_cart'):
            conversion_count += 1
        elif row[2] == 'visit_poi' and '4S店' in row[1]:
            conversion_count += 1

    conn.close()

    if not behaviors:
        print(f"❌ 用户 {user_id} 没有行为数据")
        return

    print(f"加载了 {len(behaviors)} 条行为")
    print(f"预期转化事件数: {conversion_count}")
    print(f"\n前3条行为:")
    for i, b in enumerate(behaviors[:3], 1):
        print(f"  {i}. {b['timestamp']} {b['behavior_text']}")

    # 2. 调用LLM
    print(f"\n调用LLM抽取事件...")
    client = OpenAIClient()
    result = await client.abstract_events_batch(
        user_behaviors={user_id: behaviors},
        batch_size=20  # 每批20条
    )

    # 3. 分析结果
    events = result.get("events", {}).get(user_id, [])
    print(f"\n{'='*60}")
    print(f"抽取结果")
    print(f"{'='*60}\n")
    print(f"总事件数: {len(events)}")

    # 统计事件分类
    category_stats = {}
    for event in events:
        category = event.get("category", "unknown")
        category_stats[category] = category_stats.get(category, 0) + 1

    print(f"\n事件分类统计:")
    for category, count in category_stats.items():
        print(f"  {category}: {count} 个")

    # 显示转化事件
    conversion_events = [e for e in events if e.get("category") == "conversion"]
    if conversion_events:
        print(f"\n✓ 发现 {len(conversion_events)} 个转化事件:")
        for event in conversion_events[:10]:
            print(f"  - {event['timestamp']} | {event['event_type']} | {event.get('context', {})}")

        # 计算识别率
        if conversion_count > 0:
            recognition_rate = len(conversion_events) / conversion_count * 100
            print(f"\n转化事件识别率: {recognition_rate:.1f}% ({len(conversion_events)}/{conversion_count})")
    else:
        print(f"\n❌ 未发现转化事件（预期{conversion_count}个）")

    # 显示LLM响应片段
    llm_response = result.get("llm_response", "")
    print(f"\nLLM响应长度: {len(llm_response)} 字符")
    print(f"LLM响应前500字符:\n{llm_response[:500]}")

async def main():
    """主函数"""
    import argparse
    parser = argparse.ArgumentParser(description='测试事件抽取prompt')
    parser.add_argument('--user', default='user_0216', help='用户ID（默认user_0216）')
    parser.add_argument('--limit', type=int, default=20, help='限制行为数量（默认20）')
    args = parser.parse_args()

    await test_prompt_with_user(args.user, args.limit)

if __name__ == "__main__":
    asyncio.run(main())
