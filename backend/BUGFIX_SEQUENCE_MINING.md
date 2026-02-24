# 高频子序列挖掘功能错误修复报告

**修复日期**: 2026-02-23
**问题**: `sqlite3.ProgrammingError: Error binding parameter 131: type 'dict' is not supported`

## 问题根因

`event_sequences` 表的 `sequence` 字段存储格式不一致：

- **正确格式**: `["event_id_1", "event_id_2", ...]` - event_id 字符串数组
- **错误格式**: `[{"event_type": "看车", "timestamp": "...", ...}, ...]` - 事件对象数组

当 `sequence` 字段存储事件对象数组时，`sequence_mining.py` 中的 `_load_event_sequences()` 方法会将字典对象添加到 SQL 查询参数列表，导致 SQLite 参数绑定失败。

## 修复内容

### 1. 修复数据写入错误

**文件**: [backend/app/api/event_extraction_routes.py](backend/app/api/event_extraction_routes.py)

**位置1**: 第190-217行（批量抽取流式接口）

修复前：
```python
for event in user_events:
    event_id = f"{user_id}_{uuid.uuid4().hex[:8]}"
    # ... 插入 extracted_events ...

# 错误：存储事件对象数组
cursor.execute("""
    INSERT OR REPLACE INTO event_sequences (user_id, sequence)
    VALUES (?, ?)
""", (user_id, json.dumps(user_events, ensure_ascii=False)))
```

修复后：
```python
event_ids = []
for event in user_events:
    event_id = f"{user_id}_{uuid.uuid4().hex[:8]}"
    event_ids.append(event_id)
    # ... 插入 extracted_events ...

# 正确：存储 event_id 数组
cursor.execute("""
    INSERT OR REPLACE INTO event_sequences (user_id, sequence, start_time, end_time, status)
    VALUES (?, ?, ?, ?, ?)
""", (
    user_id,
    json.dumps(event_ids, ensure_ascii=False),
    user_events[0].get("timestamp") if user_events else None,
    user_events[-1].get("timestamp") if user_events else None,
    "success"
))
```

**位置2**: 第432-450行（单用户LLM流式抽象接口）

应用了相同的修复逻辑。

### 2. 增强容错性

**文件**: [backend/app/services/sequence_mining.py](backend/app/services/sequence_mining.py)

**位置1**: 第279-303行（`_load_event_sequences` 方法）

添加类型检查和过滤：
```python
# 收集所有需要查询的event_id
all_event_ids = []
for row in all_rows:
    event_ids = json.loads(row[1])

    # 类型检查：确保 event_ids 是字符串列表
    if isinstance(event_ids, list):
        # 过滤出字符串类型的 event_id
        valid_event_ids = [
            eid for eid in event_ids
            if isinstance(eid, str)
        ]

        # 如果列表中包含字典（错误格式），记录警告
        if len(valid_event_ids) < len(event_ids):
            app_logger.warning(
                f"用户 {row[0]} 的 sequence 字段包含非字符串元素，"
                f"已过滤 {len(event_ids) - len(valid_event_ids)} 个无效元素"
            )

        all_event_ids.extend(valid_event_ids)
    else:
        app_logger.error(f"用户 {row[0]} 的 sequence 字段格式错误: {type(event_ids)}")
```

**位置2**: 第311-319行（构建序列部分）

添加类型检查：
```python
# 构建序列
for row in all_rows:
    user_id = row[0]
    event_ids = json.loads(row[1])

    # 类型检查：确保 event_ids 是字符串列表
    if not isinstance(event_ids, list):
        app_logger.error(f"用户 {user_id} 的 sequence 字段格式错误: {type(event_ids)}")
        continue

    # 过滤出字符串类型的 event_id
    valid_event_ids = [eid for eid in event_ids if isinstance(eid, str)]
```

### 3. 数据清理工具

**文件**: [backend/scripts/cleanup_event_sequences.py](backend/scripts/cleanup_event_sequences.py)

创建了数据清理脚本，用于：
- 检测 `event_sequences` 表中的错误格式记录
- 删除错误记录
- 输出清理统计信息

## 验证结果

### 1. 数据清理结果

```
总记录数: 504
错误记录数: 4
剩余记录数: 500
```

清理了4条存储事件对象的错误记录。

### 2. 数据格式验证

```
✓ 正确 | user_0006 | 长度: 49 | 元素类型: str
✓ 正确 | user_0013 | 长度: 52 | 元素类型: str
✓ 正确 | user_0030 | 长度: 48 | 元素类型: str
✓ 正确 | user_0034 | 长度: 60 | 元素类型: str
✓ 正确 | user_0041 | 长度: 49 | 元素类型: str
```

所有记录现在都存储正确的 event_id 字符串数组。

### 3. 功能测试

高频子序列挖掘功能测试成功：

```bash
curl -X POST http://localhost:8000/api/v1/mining/mine \
  -H "Content-Type: application/json" \
  -d '{"algorithm": "prefixspan", "min_support": 2, "max_length": 3, "top_k": 20}'
```

返回结果：
```json
{
  "code": 0,
  "message": "挖掘完成",
  "data": {
    "algorithm": "prefixspan",
    "frequent_patterns": [...],
    "statistics": {
      "total_users": 341,
      "total_sequences": 341,
      "unique_event_types": 150,
      "patterns_found": 20
    }
  }
}
```

### 4. 日志验证

修复后的日志显示：
```
2026-02-23 22:12:25 - INFO - 分批加载 27649 个事件详情
2026-02-23 22:12:25 - INFO - 事件详情加载完成: 27649 个事件
2026-02-23 22:12:25 - INFO - 加载了 341 个用户的事件序列
2026-02-23 22:12:25 - INFO - 挖掘完成: 找到 561 个频繁模式
2026-02-23 22:12:25 - INFO - ✓ 高频子序列挖掘完成: 找到 20 个模式
```

无任何错误信息。

## 影响范围

### 修复的功能
- 高频子序列挖掘（`/api/v1/mining/mine`）
- 事件抽取功能（`/api/v1/events/extract/*`）

### 未受影响的功能
- [backend/app/services/event_extraction.py](backend/app/services/event_extraction.py) 中的批量抽取功能已经使用正确格式，无需修改

## 预防措施

1. **数据格式规范**: `event_sequences.sequence` 字段必须存储 event_id 字符串数组
2. **类型检查**: 在读取 `sequence` 字段时添加类型检查和过滤
3. **日志记录**: 发现错误格式时记录警告日志
4. **定期清理**: 可使用 `cleanup_event_sequences.py` 脚本定期检查和清理错误数据

## 相关文件

- [backend/app/api/event_extraction_routes.py](backend/app/api/event_extraction_routes.py) - 修复数据写入
- [backend/app/services/sequence_mining.py](backend/app/services/sequence_mining.py) - 增强容错性
- [backend/scripts/cleanup_event_sequences.py](backend/scripts/cleanup_event_sequences.py) - 数据清理工具
- [backend/app/services/event_extraction.py](backend/app/services/event_extraction.py) - 已使用正确格式（无需修改）
