# 事件抽象失败原因显示功能 - 已实现

## 需求

用户需要在页面上看到逻辑事件生成失败的原因。

## 实现方案

### 1. 数据库迁移

添加失败状态和错误信息字段到 `event_sequences` 表：

```sql
ALTER TABLE event_sequences ADD COLUMN status TEXT DEFAULT 'success';
ALTER TABLE event_sequences ADD COLUMN error_message TEXT;
```

**字段说明**：
- `status`: 状态（'success' | 'failed'）
- `error_message`: 失败原因（仅在失败时有值）

### 2. 后端修改

#### 2.1 保存失败信息

修改 `extract_events_batch()` 方法，在失败时保存失败信息：

```python
# 成功时
cursor.execute("""
    INSERT INTO event_sequences
    (user_id, sequence, start_time, end_time, status)
    VALUES (?, ?, ?, ?, ?)
""", (user_id, event_ids, start_time, end_time, "success"))

# 失败时（LLM返回空结果）
error_msg = "LLM返回空结果"
cursor.execute("""
    INSERT INTO event_sequences
    (user_id, sequence, start_time, end_time, status, error_message)
    VALUES (?, ?, ?, ?, ?, ?)
""", (user_id, [], None, None, "failed", error_msg))

# 失败时（LLM调用异常）
error_msg = f"LLM调用失败: {type(e).__name__}: {str(e)}"
cursor.execute("""
    INSERT INTO event_sequences
    (user_id, sequence, start_time, end_time, status, error_message)
    VALUES (?, ?, ?, ?, ?, ?)
""", (user_id, [], None, None, "failed", error_msg))
```

#### 2.2 返回失败信息

修改 `get_user_sequences()` 方法，查询并返回失败信息：

```python
# 批量查询失败信息
cursor.execute(f"""
    SELECT user_id, status, error_message
    FROM event_sequences
    WHERE user_id IN ({placeholders})
""", user_ids)

# 按用户分组失败信息
status_by_user = {}
for row in cursor.fetchall():
    user_id = row[0]
    status_by_user[user_id] = {
        "status": row[1],
        "error_message": row[2]
    }

# 构建结果
items.append({
    "user_id": user_id,
    "behavior_sequence": behaviors,
    "event_sequence": events,
    "behavior_count": len(behaviors),
    "event_count": len(events),
    "has_events": len(events) > 0,
    "status": status_info.get("status"),        # 新增
    "error_message": status_info.get("error_message")  # 新增
})
```

### 3. 前端修改

#### 3.1 状态列

修改状态列，显示三种状态：

```vue
<el-table-column label="状态" width="120">
  <template #default="scope">
    <el-tag v-if="scope.row.status === 'success'" type="success">已抽象</el-tag>
    <el-tag v-else-if="scope.row.status === 'failed'" type="danger">失败</el-tag>
    <el-tag v-else type="info">未抽象</el-tag>
  </template>
</el-table-column>
```

#### 3.2 失败原因列

新增失败原因列，使用 tooltip 显示完整信息：

```vue
<el-table-column label="失败原因" min-width="200">
  <template #default="scope">
    <el-tooltip v-if="scope.row.error_message" :content="scope.row.error_message" placement="top">
      <span style="color: #f56c6c; cursor: pointer;">
        {{ scope.row.error_message.substring(0, 30) }}...
      </span>
    </el-tooltip>
    <span v-else style="color: #909399">-</span>
  </template>
</el-table-column>
```

#### 3.3 操作列

修改操作列，失败的用户显示"重新生成"按钮：

```vue
<el-table-column label="操作" width="200">
  <template #default="scope">
    <!-- 成功：显示查看按钮 -->
    <el-button
      v-if="scope.row.has_events && scope.row.status === 'success'"
      size="small"
      @click="showSequenceDetail(scope.row)"
    >
      查看
    </el-button>

    <!-- 失败：显示重新生成按钮（警告色） -->
    <el-button
      v-else-if="scope.row.status === 'failed'"
      size="small"
      type="warning"
      @click="handleSingleExtract(scope.row.user_id)"
      :loading="extractingUsers[scope.row.user_id]"
    >
      重新生成
    </el-button>

    <!-- 未抽象：显示生成按钮 -->
    <el-button
      v-else
      size="small"
      type="primary"
      @click="handleSingleExtract(scope.row.user_id)"
      :loading="extractingUsers[scope.row.user_id]"
    >
      生成
    </el-button>
  </template>
</el-table-column>
```

## 失败原因类型

### 1. LLM返回空结果

**原因**：LLM调用成功，但返回的JSON中没有该用户的事件数据

**显示**：`LLM返回空结果`

**可能原因**：
- LLM理解错误，没有为该用户生成事件
- 用户行为数据质量差，LLM无法抽象
- Prompt设计问题

### 2. LLM调用失败

**原因**：LLM API调用异常

**显示**：`LLM调用失败: ReadTimeout: ...` 或 `LLM调用失败: HTTPError: ...`

**可能原因**：
- 网络超时（ReadTimeout）
- API限流（RateLimitError）
- API错误（HTTPError）
- 认证失败（AuthenticationError）

### 3. JSON解析失败

**原因**：LLM返回的内容不是有效的JSON格式

**显示**：`LLM调用失败: JSONDecodeError: ...`

**可能原因**：
- LLM返回了额外的文本（如 `<think>` 标签）
- JSON格式错误
- 返回被截断

## 用户界面效果

### 表格显示

| 用户ID | 行为序列 | 逻辑行为序列 | 状态 | 失败原因 | 操作 |
|--------|---------|-------------|------|---------|------|
| user_0001 | 55条 | 55条 | 已抽象 | - | 查看 |
| user_0002 | 75条 | - | 失败 | LLM返回空结果 | 重新生成 |
| user_0003 | 140条 | - | 失败 | LLM调用失败: ReadTimeout: ... | 重新生成 |
| user_0004 | 126条 | - | 未抽象 | - | 生成 |

### 失败原因显示

- **短文本**：表格中显示前30个字符 + "..."
- **完整文本**：鼠标悬停时通过 tooltip 显示完整错误信息
- **颜色**：红色（#f56c6c）表示错误

### 操作按钮

- **已抽象**：绿色"查看"按钮
- **失败**：橙色"重新生成"按钮
- **未抽象**：蓝色"生成"按钮

## 修改文件清单

### 后端

1. **backend/scripts/add_event_failure_fields.py**
   - 数据库迁移脚本
   - 添加 `status` 和 `error_message` 字段

2. **backend/app/services/event_extraction.py**
   - 修改 `extract_events_batch()` 方法
     - 成功时保存 `status='success'`
     - 失败时保存 `status='failed'` 和 `error_message`
   - 修改 `get_user_sequences()` 方法
     - 查询并返回 `status` 和 `error_message`

### 前端

3. **frontend/src/views/EventExtraction.vue**
   - 修改状态列：显示三种状态（已抽象/失败/未抽象）
   - 新增失败原因列：显示错误信息（带 tooltip）
   - 修改操作列：失败用户显示"重新生成"按钮

## 验证测试

### 1. 查看失败用户

```bash
# 查询失败的用户
python3 -c "
import sqlite3
from pathlib import Path

db_path = Path('data/graph.db')
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute('''
    SELECT user_id, status, error_message
    FROM event_sequences
    WHERE status = \"failed\"
    LIMIT 10
''')

print('失败的用户:')
for row in cursor.fetchall():
    print(f'  {row[0]}: {row[2][:50]}...')

conn.close()
"
```

### 2. 前端测试

1. 打开事件抽象页面
2. 查看表格中的"状态"列和"失败原因"列
3. 鼠标悬停在失败原因上，查看完整错误信息
4. 点击失败用户的"重新生成"按钮

### 3. 批量抽象测试

1. 启动批量抽象
2. 等待完成
3. 查看失败用户的错误信息
4. 尝试重新生成失败的用户

## 总结

✓ **数据库迁移**：添加 `status` 和 `error_message` 字段
✓ **后端保存**：失败时保存详细的错误信息
✓ **后端返回**：API返回失败状态和原因
✓ **前端显示**：表格中显示失败状态和原因
✓ **用户操作**：失败用户可以重新生成

**用户体验**：
- 清楚地看到哪些用户失败了
- 知道失败的具体原因
- 可以针对性地重新生成失败的用户
