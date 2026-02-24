#!/usr/bin/env python3
"""
清理 event_sequences 表中的错误数据

该脚本会：
1. 查找 sequence 字段中存储事件对象（而非 event_id）的记录
2. 删除这些错误格式的记录
3. 输出清理统计信息
"""

import sqlite3
import json
import os

def cleanup_event_sequences():
    """清理 event_sequences 表中的错误数据"""
    # 使用相对路径，与其他服务保持一致
    db_path = "data/graph.db"

    if not os.path.exists(db_path):
        print(f"数据库文件不存在: {db_path}")
        return

    print(f"连接数据库: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # 查找所有记录
        cursor.execute("SELECT user_id, sequence FROM event_sequences")
        rows = cursor.fetchall()

        total_count = len(rows)
        error_count = 0
        deleted_users = []

        print(f"\n总记录数: {total_count}")
        print("开始检查数据格式...\n")

        for user_id, sequence_json in rows:
            try:
                sequence = json.loads(sequence_json)

                # 检查是否是列表
                if not isinstance(sequence, list):
                    print(f"✗ {user_id}: sequence 不是列表类型 ({type(sequence).__name__})")
                    deleted_users.append(user_id)
                    error_count += 1
                    continue

                # 检查列表是否为空
                if len(sequence) == 0:
                    continue

                # 检查第一个元素的类型
                first_element = sequence[0]

                if isinstance(first_element, dict):
                    print(f"✗ {user_id}: sequence 存储的是事件对象（字典），而非 event_id")
                    deleted_users.append(user_id)
                    error_count += 1
                elif not isinstance(first_element, str):
                    print(f"✗ {user_id}: sequence 元素类型错误 ({type(first_element).__name__})")
                    deleted_users.append(user_id)
                    error_count += 1

            except json.JSONDecodeError as e:
                print(f"✗ {user_id}: JSON 解析失败 - {e}")
                deleted_users.append(user_id)
                error_count += 1
            except Exception as e:
                print(f"✗ {user_id}: 处理失败 - {e}")
                deleted_users.append(user_id)
                error_count += 1

        # 删除错误记录
        if deleted_users:
            print(f"\n发现 {error_count} 条错误记录，开始删除...")

            for user_id in deleted_users:
                cursor.execute("DELETE FROM event_sequences WHERE user_id = ?", (user_id,))
                print(f"  已删除: {user_id}")

            conn.commit()
            print(f"\n✓ 成功删除 {error_count} 条错误记录")
        else:
            print("\n✓ 未发现错误数据，数据格式正确")

        # 输出统计信息
        print("\n" + "="*60)
        print("清理统计:")
        print(f"  总记录数: {total_count}")
        print(f"  错误记录数: {error_count}")
        print(f"  剩余记录数: {total_count - error_count}")
        print("="*60)

    except Exception as e:
        print(f"\n清理过程出错: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    print("="*60)
    print("event_sequences 表数据清理工具")
    print("="*60)
    cleanup_event_sequences()
