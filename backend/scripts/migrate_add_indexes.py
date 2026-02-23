#!/usr/bin/env python3
"""
数据库迁移脚本：添加性能优化索引

为现有数据库添加复合索引以提升查询性能
"""
import sqlite3
import sys
from pathlib import Path

def migrate_add_indexes(db_path: str):
    """为现有数据库添加索引"""
    print(f"开始迁移数据库: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    indexes = [
        ("idx_behavior_user_timestamp", "behavior_data(user_id, timestamp)", "行为数据复合索引"),
        ("idx_extracted_events_timestamp", "extracted_events(timestamp)", "事件时间戳索引"),
    ]

    for idx_name, idx_def, description in indexes:
        try:
            cursor.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {idx_def}")
            print(f"✓ 创建索引: {idx_name} ({description})")
        except Exception as e:
            print(f"✗ 创建索引失败 {idx_name}: {e}")

    conn.commit()
    conn.close()

    print("迁移完成!")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    else:
        # 默认路径
        db_path = Path(__file__).parent.parent.parent / "data" / "graph.db"

    if not Path(db_path).exists():
        print(f"错误: 数据库文件不存在: {db_path}")
        sys.exit(1)

    migrate_add_indexes(str(db_path))
