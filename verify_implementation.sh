#!/bin/bash

echo "=========================================="
echo "验证基于目标行为的序列挖掘实现"
echo "=========================================="
echo ""

# 1. 验证数据库迁移
echo "1. 验证数据库迁移..."
cd /home/linxiankun/adsagent/backend
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
conn.close()
"
echo ""

# 2. 验证 Python 语法
echo "2. 验证 Python 语法..."
cd /home/linxiankun/adsagent/backend
python3 -m py_compile \
    app/core/openai_client.py \
    app/services/event_extraction.py \
    app/api/event_extraction_routes.py \
    app/services/sequence_mining.py \
    app/api/sequence_mining_routes.py \
    scripts/add_event_category_column.py

if [ $? -eq 0 ]; then
    echo "✓ 所有 Python 文件语法正确"
else
    echo "✗ Python 语法检查失败"
    exit 1
fi
echo ""

# 3. 检查修改的文件
echo "3. 检查修改的文件..."
files=(
    "backend/scripts/add_event_category_column.py"
    "backend/app/core/openai_client.py"
    "backend/app/services/event_extraction.py"
    "backend/app/api/event_extraction_routes.py"
    "backend/app/services/sequence_mining.py"
    "backend/app/api/sequence_mining_routes.py"
    "frontend/src/views/SequenceMining.vue"
)

for file in "${files[@]}"; do
    if [ -f "/home/linxiankun/adsagent/$file" ]; then
        echo "✓ $file"
    else
        echo "✗ $file 不存在"
    fi
done
echo ""

# 4. 检查关键代码片段
echo "4. 检查关键代码片段..."

# 检查 event_category 字段是否在 INSERT 语句中
if grep -q "event_category" backend/app/services/event_extraction.py; then
    echo "✓ event_extraction.py 包含 event_category"
else
    echo "✗ event_extraction.py 缺少 event_category"
fi

if grep -q "target_event" backend/app/services/sequence_mining.py; then
    echo "✓ sequence_mining.py 包含 target_event 参数"
else
    echo "✗ sequence_mining.py 缺少 target_event 参数"
fi

if grep -q "_normalize_event_type" backend/app/services/sequence_mining.py; then
    echo "✓ sequence_mining.py 包含事件标准化方法"
else
    echo "✗ sequence_mining.py 缺少事件标准化方法"
fi

if grep -q "target_event" frontend/src/views/SequenceMining.vue; then
    echo "✓ SequenceMining.vue 包含 target_event 字段"
else
    echo "✗ SequenceMining.vue 缺少 target_event 字段"
fi

echo ""
echo "=========================================="
echo "验证完成！"
echo "=========================================="
echo ""
echo "下一步："
echo "1. 启动后端服务: cd backend && python main.py"
echo "2. 清空并重新抽取事件数据"
echo "3. 测试目标导向的序列挖掘"
echo ""
