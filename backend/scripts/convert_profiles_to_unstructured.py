#!/usr/bin/env python3
"""
将旧的结构化用户画像转换为非结构化格式
"""
import sqlite3
import json

def format_profile_text(row):
    """将结构化数据转换为非结构化文本"""
    user_id, age, gender, city, occupation, properties_json = row

    parts = []

    # 基本信息
    if age:
        parts.append(f"{age}岁")
    if gender:
        parts.append(gender)
    if city:
        parts.append(f"{city}")
    if occupation:
        parts.append(occupation)

    # 解析 properties
    if properties_json:
        try:
            properties = json.loads(properties_json)

            # 收入
            if "income" in properties and properties["income"]:
                income = properties["income"]
                if income >= 10000:
                    parts.append(f"年收入{income//10000}万")
                else:
                    parts.append(f"年收入{income}元")

            # 兴趣爱好
            if "interests" in properties and properties["interests"]:
                interests = properties["interests"]
                if isinstance(interests, list) and interests:
                    parts.append(f"喜欢{', '.join(interests)}")

            # 购车预算
            if "budget" in properties and properties["budget"]:
                budget = properties["budget"]
                parts.append(f"购车预算{budget}万")

            # 是否有车
            if "has_car" in properties:
                has_car = properties["has_car"]
                if has_car:
                    parts.append("已有车")
                else:
                    parts.append("无车")

            # 购车意向
            if "purchase_intent" in properties and properties["purchase_intent"]:
                intent = properties["purchase_intent"]
                if intent != "无":
                    parts.append(f"购车意向: {intent}")

        except json.JSONDecodeError:
            pass

    return "，".join(parts) if parts else f"{user_id}用户"

def convert_profile_data():
    """转换用户画像数据"""
    db_path = "data/graph.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        print("开始转换用户画像数据...")

        # 查询所有没有 profile_text 的数据
        cursor.execute("""
            SELECT user_id, age, gender, city, occupation, properties
            FROM user_profiles
            WHERE profile_text IS NULL OR profile_text = ''
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
            user_id = row[0]
            profile_text = format_profile_text(row)

            cursor.execute("""
                UPDATE user_profiles
                SET profile_text = ?
                WHERE user_id = ?
            """, (profile_text, user_id))

            updated += 1
            if updated % 100 == 0:
                print(f"已转换 {updated}/{total} 条数据...")
                conn.commit()

        conn.commit()
        print(f"✓ 转换完成！共转换 {updated} 条数据")

        # 验证
        cursor.execute("SELECT COUNT(*) FROM user_profiles WHERE profile_text IS NOT NULL AND profile_text != ''")
        count = cursor.fetchone()[0]
        print(f"✓ 验证：现在有 {count} 条数据有 profile_text")

        # 显示几条样例
        print("\n转换后的样例:")
        cursor.execute("""
            SELECT user_id, profile_text
            FROM user_profiles
            LIMIT 5
        """)
        for row in cursor.fetchall():
            print(f"  {row[0]} | {row[1]}")

    except Exception as e:
        print(f"转换失败: {e}")
        conn.rollback()
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

if __name__ == "__main__":
    convert_profile_data()
