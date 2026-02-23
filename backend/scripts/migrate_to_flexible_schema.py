#!/usr/bin/env python3
"""
数据迁移脚本 - 从旧结构迁移到新的灵活结构

执行方式:
    cd backend
    python scripts/migrate_to_flexible_schema.py
"""

import sqlite3
import json
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.flexible_persistence import FlexiblePersistence
from app.core.logger import app_logger


def migrate_behavior_data(db_path: str = "data/graph.db"):
    """迁移行为数据到新结构"""

    app_logger.info("开始迁移行为数据...")

    persistence = FlexiblePersistence(db_path)

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()

        # 检查旧表是否存在
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='behavior_data'
        """)
        if not cursor.fetchone():
            app_logger.warning("旧表 behavior_data 不存在，跳过迁移")
            return 0

        # 读取旧数据（分批）
        batch_size = 10000
        offset = 0
        total_migrated = 0

        while True:
            cursor.execute(f"""
                SELECT user_id, action, timestamp, item_id, app_id, media_id, poi_id, duration, properties
                FROM behavior_data
                LIMIT {batch_size} OFFSET {offset}
            """)

            rows = cursor.fetchall()
            if not rows:
                break

            # 转换为新格式
            new_events = []
            for row in rows:
                user_id, action, timestamp, item_id, app_id, media_id, poi_id, duration, properties = row

                # 构建event_data（包含所有属性，包括action）
                event_data = {}

                # action也放入event_data中（不再是结构化字段）
                if action:
                    event_data['action'] = action

                if item_id:
                    event_data['item_id'] = item_id
                if app_id:
                    event_data['app_id'] = app_id
                if media_id:
                    event_data['media_id'] = media_id
                if poi_id:
                    event_data['poi_id'] = poi_id
                if duration:
                    event_data['duration'] = duration

                # 合并properties
                if properties:
                    try:
                        props = json.loads(properties)
                        event_data.update(props)
                    except:
                        pass

                new_events.append({
                    "user_id": user_id,
                    "event_time": timestamp,
                    "event_data": json.dumps(event_data, ensure_ascii=False)
                })

            # 批量插入新表
            inserted = persistence.batch_insert_behavior_events(new_events)
            total_migrated += inserted

            app_logger.info(f"已迁移 {total_migrated} 条行为数据")

            offset += batch_size

    app_logger.info(f"✓ 行为数据迁移完成: {total_migrated} 条")
    return total_migrated


def migrate_user_profiles(db_path: str = "data/graph.db"):
    """迁移用户画像到新结构"""

    app_logger.info("开始迁移用户画像...")

    persistence = FlexiblePersistence(db_path)

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()

        # 检查旧表是否存在
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='user_profiles'
        """)
        if not cursor.fetchone():
            app_logger.warning("旧表 user_profiles 不存在，跳过迁移")
            return 0

        # 读取旧数据
        cursor.execute("""
            SELECT user_id, age, gender, income, occupation, city, interests, budget, has_car, purchase_intent
            FROM user_profiles
        """)

        rows = cursor.fetchall()
        if not rows:
            app_logger.warning("没有用户画像数据需要迁移")
            return 0

        # 转换为新格式
        new_profiles = []
        for row in rows:
            user_id, age, gender, income, occupation, city, interests, budget, has_car, purchase_intent = row

            # 构建profile_data
            profile_data = {}
            if age:
                profile_data['age'] = age
            if gender:
                profile_data['gender'] = gender
            if income:
                profile_data['income'] = income
            if occupation:
                profile_data['occupation'] = occupation
            if city:
                profile_data['city'] = city
            if interests:
                profile_data['interests'] = interests
            if budget:
                profile_data['budget'] = budget
            if has_car:
                profile_data['has_car'] = has_car
            if purchase_intent:
                profile_data['purchase_intent'] = purchase_intent

            new_profiles.append({
                "user_id": user_id,
                "profile_data": json.dumps(profile_data, ensure_ascii=False),
                "profile_version": 1
            })

        # 批量插入新表
        inserted = persistence.batch_upsert_user_profiles(new_profiles)

        app_logger.info(f"✓ 用户画像迁移完成: {inserted} 个")
        return inserted


def verify_migration(db_path: str = "data/graph.db"):
    """验证迁移结果"""

    app_logger.info("验证迁移结果...")

    persistence = FlexiblePersistence(db_path)

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()

        # 统计旧表数据
        cursor.execute("SELECT COUNT(*) FROM behavior_data")
        old_behavior_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM user_profiles")
        old_profile_count = cursor.fetchone()[0]

    # 统计新表数据
    stats = persistence.get_statistics()

    print("\n=== 迁移验证 ===")
    print(f"旧表 behavior_data: {old_behavior_count} 条")
    print(f"新表 behavior_events: {stats['behavior_events_count']} 条")
    print(f"旧表 user_profiles: {old_profile_count} 个")
    print(f"新表 user_profiles_v2: {stats['user_profiles_count']} 个")

    if stats['behavior_events_count'] >= old_behavior_count:
        print("✓ 行为数据迁移验证通过")
    else:
        print("✗ 行为数据迁移不完整")

    if stats['user_profiles_count'] >= old_profile_count:
        print("✓ 用户画像迁移验证通过")
    else:
        print("✗ 用户画像迁移不完整")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="数据迁移工具")
    parser.add_argument("--db", default="data/graph.db", help="数据库路径")
    parser.add_argument("--verify-only", action="store_true", help="仅验证，不迁移")

    args = parser.parse_args()

    if args.verify_only:
        verify_migration(args.db)
    else:
        print("开始数据迁移...")
        print("=" * 50)

        # 迁移行为数据
        behavior_count = migrate_behavior_data(args.db)

        # 迁移用户画像
        profile_count = migrate_user_profiles(args.db)

        print("\n" + "=" * 50)
        print(f"迁移完成:")
        print(f"  - 行为数据: {behavior_count} 条")
        print(f"  - 用户画像: {profile_count} 个")

        # 验证
        verify_migration(args.db)


if __name__ == "__main__":
    main()
