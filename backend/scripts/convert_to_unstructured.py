#!/usr/bin/env python3
"""
将旧的结构化行为数据转换为非结构化格式
"""
import sqlite3
import json

def format_behavior_text(row):
    """将结构化数据转换为非结构化文本"""
    action, item_id, app_id, media_id, poi_id, duration, properties = row

    parts = []

    if action == "visit_poi" and poi_id:
        parts.append(f"在{poi_id}停留")
        if duration:
            hours = duration // 3600
            minutes = (duration % 3600) // 60
            if hours > 0:
                parts.append(f"{hours}小时{minutes}分钟")
            else:
                parts.append(f"{minutes}分钟")
    elif action == "use_app" and app_id:
        parts.append(f"使用{app_id}")
        if duration:
            minutes = duration // 60
            parts.append(f"{minutes}分钟")
    elif action == "browse" and item_id:
        parts.append(f"浏览{item_id}")
        if media_id:
            parts.append(f"在{media_id}上")
        if duration:
            parts.append(f"{duration}秒")
    elif action == "search" and item_id:
        parts.append(f"搜索{item_id}")
    elif action == "view" and item_id:
        parts.append(f"查看{item_id}")
    else:
        # 通用格式
        parts.append(action)
        if item_id:
            parts.append(item_id)
        if app_id:
            parts.append(f"使用{app_id}")
        if media_id:
            parts.append(f"在{media_id}上")

    return " ".join(parts)

def convert_behavior_data():
    """转换行为数据"""
    db_path = "backend/data/graph.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        print("开始转换行为数据...")

        # 查询所有没有 behavior_text 的数据
        cursor.execute("""
            SELECT id, action, item_id, app_id, media_id, poi_id, duration, properties
            FROM behavior_data
            WHERE behavior_text IS NULL OR behavior_text = ''
        """)

        rows = cursor.fetchall()
        total = len(rows)
        print(f"找到 {total} 条需要转换的数据")

        if total == 0:
            print("没有需要转换的数据")
            return

        # 批量更新
        updated = 0
        for row in rows:
            behavior_id = row[0]
            behavior_text = format_behavior_text(row[1:])

            cursor.execute("""
                UPDATE behavior_data
                SET behavior_text = ?
                WHERE id = ?
            """, (behavior_text, behavior_id))

            updated += 1
            if updated % 1000 == 0:
                print(f"已转换 {updated}/{total} 条数据...")
                conn.commit()

        conn.commit()
        print(f"✓ 转换完成！共转换 {updated} 条数据")

        # 验证
        cursor.execute("SELECT COUNT(*) FROM behavior_data WHERE behavior_text IS NOT NULL AND behavior_text != ''")
        count = cursor.fetchone()[0]
        print(f"✓ 验证：现在有 {count} 条数据有 behavior_text")

        # 显示几条样例
        print("\n转换后的样例:")
        cursor.execute("""
            SELECT user_id, timestamp, behavior_text
            FROM behavior_data
            LIMIT 5
        """)
        for row in cursor.fetchall():
            print(f"  {row[0]} | {row[1]} | {row[2]}")

    except Exception as e:
        print(f"转换失败: {e}")
        conn.rollback()
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

if __name__ == "__main__":
    convert_behavior_data()
