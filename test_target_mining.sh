#!/bin/bash

echo "=========================================="
echo "测试基于目标行为的序列挖掘"
echo "=========================================="
echo ""

cd /home/linxiankun/adsagent/backend

# 1. 验证原始数据中的转化行为
echo "1. 验证原始数据中的转化行为..."
python3 -c "
import sqlite3
conn = sqlite3.connect('data/graph.db')
cursor = conn.cursor()

cursor.execute('''
    SELECT action, COUNT(*) as count
    FROM behavior_data
    WHERE action IN ('purchase', 'add_cart', 'visit_poi')
    GROUP BY action
''')
results = cursor.fetchall()

if results:
    print('✓ 原始数据包含转化行为:')
    for action, count in results:
        print(f'  - {action}: {count} 条')
else:
    print('✗ 原始数据缺少转化行为')
    exit(1)

conn.close()
"
echo ""

# 2. 检查数据库 event_category 字段
echo "2. 检查数据库 event_category 字段..."
python3 -c "
import sqlite3
conn = sqlite3.connect('data/graph.db')
cursor = conn.cursor()
cursor.execute('PRAGMA table_info(extracted_events)')
columns = [col[1] for col in cursor.fetchall()]
if 'event_category' in columns:
    print('✓ event_category 字段已添加')
else:
    print('✗ event_category 字段缺失')
    exit(1)
conn.close()
"
echo ""

# 3. 提示用户启动后端服务
echo "3. 后端服务检查..."
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✓ 后端服务正在运行"
else
    echo "✗ 后端服务未运行"
    echo ""
    echo "请先启动后端服务："
    echo "  cd backend && python main.py"
    exit 1
fi
echo ""

# 4. 清空旧的事件数据
echo "4. 清空旧的事件数据..."
python3 -c "
import sqlite3
conn = sqlite3.connect('data/graph.db')
cursor = conn.cursor()
cursor.execute('DELETE FROM extracted_events')
cursor.execute('DELETE FROM event_sequences')
conn.commit()
print(f'✓ 已清空事件数据')
conn.close()
"
echo ""

# 5. 抽取一个购买用户的事件
echo "5. 抽取一个购买用户的事件（测试事件分类）..."
PURCHASE_USER=$(python3 -c "
import sqlite3
conn = sqlite3.connect('data/graph.db')
cursor = conn.cursor()
cursor.execute('SELECT user_id FROM behavior_data WHERE action = \"purchase\" LIMIT 1')
user_id = cursor.fetchone()[0]
print(user_id)
conn.close()
")

echo "  购买用户: $PURCHASE_USER"
curl -s -X POST "http://localhost:8000/api/v1/events/extract/$PURCHASE_USER" > /tmp/extract_result.json

if [ $? -eq 0 ]; then
    echo "✓ 事件抽取成功"

    # 检查是否有 conversion 分类的事件
    python3 -c "
import sqlite3
conn = sqlite3.connect('data/graph.db')
cursor = conn.cursor()
cursor.execute('''
    SELECT event_type, event_category
    FROM extracted_events
    WHERE user_id = '$PURCHASE_USER' AND event_category = 'conversion'
''')
conversion_events = cursor.fetchall()

if conversion_events:
    print('✓ 发现转化事件:')
    for event_type, category in conversion_events:
        print(f'  - {event_type} ({category})')
else:
    print('✗ 未发现转化事件（可能 LLM 未正确标注）')

conn.close()
"
else
    echo "✗ 事件抽取失败"
fi
echo ""

# 6. 测试目标导向挖掘
echo "6. 测试目标导向挖掘..."
echo "  注意：需要先抽取更多用户的事件才能进行有效挖掘"
echo ""
echo "  手动测试命令："
echo "  curl -X POST http://localhost:8000/api/v1/mining/mine \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"target_event\": \"购买\", \"min_support\": 2}'"
echo ""

echo "=========================================="
echo "测试完成！"
echo "=========================================="
echo ""
echo "下一步："
echo "1. 批量抽取所有用户的事件（在前端或通过 API）"
echo "2. 在前端界面测试目标导向挖掘"
echo "3. 选择目标事件（如'购买'）或目标分类（如'conversion'）"
echo ""
