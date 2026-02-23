#!/usr/bin/env python3
"""
添加事件抽象失败信息字段
"""
import sqlite3
from pathlib import Path

def migrate():
    """添加失败信息字段"""
    db_path = Path("data/graph.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        print("开始迁移...")

        # 检查字段是否已存在
        cursor.execute("PRAGMA table_info(event_sequences)")
        columns = [row[1] for row in cursor.fetchall()]

        if "status" not in columns:
            print("添加 status 字段...")
            cursor.execute("""
                ALTER TABLE event_sequences
                ADD COLUMN status TEXT DEFAULT 'success'
            """)
            print("✓ status 字段添加成功")
        else:
            print("status 字段已存在")

        if "error_message" not in columns:
            print("添加 error_message 字段...")
            cursor.execute("""
                ALTER TABLE event_sequences
                ADD COLUMN error_message TEXT
            """)
            print("✓ error_message 字段添加成功")
        else:
            print("error_message 字段已存在")

        conn.commit()
        print("✓ 迁移完成")

        # 验证
        cursor.execute("PRAGMA table_info(event_sequences)")
        print("\n当前表结构:")
        for row in cursor.fetchall():
            print(f"  {row[1]} ({row[2]})")

    except Exception as e:
        print(f"迁移失败: {e}")
        conn.rollback()
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
