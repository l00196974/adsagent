#!/usr/bin/env python3
"""
数据库迁移脚本：为 extracted_events 表添加 event_category 字段
"""
import sqlite3
import os

def main():
    # 数据库路径
    db_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'graph.db')

    if not os.path.exists(db_path):
        print(f"✗ 数据库文件不存在: {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # 检查列是否存在
        cursor.execute("PRAGMA table_info(extracted_events)")
        columns = [col[1] for col in cursor.fetchall()]

        if 'event_category' not in columns:
            # 添加列
            cursor.execute("""
                ALTER TABLE extracted_events
                ADD COLUMN event_category TEXT DEFAULT 'engagement'
            """)
            conn.commit()
            print("✓ 已添加 event_category 字段到 extracted_events 表")
        else:
            print("✓ event_category 字段已存在")

        # 显示表结构
        cursor.execute("PRAGMA table_info(extracted_events)")
        print("\n当前表结构:")
        for col in cursor.fetchall():
            print(f"  {col[1]} ({col[2]})")

    except Exception as e:
        print(f"✗ 迁移失败: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    main()
