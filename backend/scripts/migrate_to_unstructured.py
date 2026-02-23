#!/usr/bin/env python3
"""
迁移到非结构化格式
- behavior_data: 添加 behavior_text 字段
- user_profiles: 添加 profile_text 字段
"""
import sqlite3
from pathlib import Path

def migrate():
    db_path = Path("data/graph.db")

    if not db_path.exists():
        print(f"数据库文件不存在: {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # 1. 检查 behavior_data 表是否已有 behavior_text 字段
        cursor.execute("PRAGMA table_info(behavior_data)")
        columns = [row[1] for row in cursor.fetchall()]

        if 'behavior_text' not in columns:
            print("添加 behavior_data.behavior_text 字段...")
            cursor.execute("ALTER TABLE behavior_data ADD COLUMN behavior_text TEXT")
            print("✓ behavior_data.behavior_text 字段添加成功")
        else:
            print("✓ behavior_data.behavior_text 字段已存在")

        # 2. 检查 user_profiles 表是否已有 profile_text 字段
        cursor.execute("PRAGMA table_info(user_profiles)")
        columns = [row[1] for row in cursor.fetchall()]

        if 'profile_text' not in columns:
            print("添加 user_profiles.profile_text 字段...")
            cursor.execute("ALTER TABLE user_profiles ADD COLUMN profile_text TEXT")
            print("✓ user_profiles.profile_text 字段添加成功")
        else:
            print("✓ user_profiles.profile_text 字段已存在")

        conn.commit()
        print("\n迁移完成！")

        # 显示表结构
        print("\n=== behavior_data 表结构 ===")
        cursor.execute("PRAGMA table_info(behavior_data)")
        for row in cursor.fetchall():
            print(f"  {row[1]}: {row[2]}")

        print("\n=== user_profiles 表结构 ===")
        cursor.execute("PRAGMA table_info(user_profiles)")
        for row in cursor.fetchall():
            print(f"  {row[1]}: {row[2]}")

    except Exception as e:
        print(f"迁移失败: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
