#!/bin/bash
# 监控批量事件抽取进度

echo "开始监控批量事件抽取进度..."
echo "按 Ctrl+C 停止监控"
echo ""

while true; do
    clear
    echo "=== 批量事件抽取进度 ($(date '+%Y-%m-%d %H:%M:%S')) ==="
    echo ""

    curl -s http://localhost:8000/api/v1/events/extract/progress | python3 -c "
import json
import sys
try:
    data = json.load(sys.stdin)
    if 'data' in data:
        d = data['data']
        status = d['status']

        # 状态图标
        if status == 'running':
            icon = '🔄'
        elif status == 'completed':
            icon = '✅'
        elif status == 'failed':
            icon = '❌'
        else:
            icon = '⏸️'

        print(f'{icon} 状态: {status}')
        print(f'📊 进度: {d[\"progress_percent\"]}%')
        print(f'👥 用户: {d[\"processed_users\"]}/{d[\"total_users\"]}')
        print(f'✓ 成功: {d[\"success_count\"]}')
        print(f'✗ 失败: {d[\"failed_count\"]}')
        print(f'📦 批次: {d[\"current_batch\"]}/{d[\"total_batches\"]}')

        if d.get('estimated_remaining_seconds'):
            mins = d['estimated_remaining_seconds'] // 60
            secs = d['estimated_remaining_seconds'] % 60
            print(f'⏱️  预计剩余: {mins}分{secs}秒')

        # 如果完成了就退出
        if status == 'completed':
            print('')
            print('🎉 批量抽取已完成！')
            exit(0)
        elif status == 'failed':
            print('')
            print(f'❌ 批量抽取失败: {d.get(\"error_message\", \"未知错误\")}')
            exit(1)
except Exception as e:
    print(f'❌ 无法获取进度: {e}')
"

    echo ""
    echo "下次更新: 30秒后..."
    sleep 30
done
