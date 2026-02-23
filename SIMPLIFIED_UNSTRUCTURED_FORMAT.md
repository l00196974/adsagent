# 简化为纯非结构化格式 - 总结

## 修改完成 ✓

已移除所有向后兼容逻辑，只保留非结构化格式。

## 修改内容

### 1. 后端服务简化

#### BaseModelingService (backend/app/services/base_modeling.py)

**import_behavior_data()** - 只接受非结构化格式：
```python
# 只接受: {user_id, timestamp, behavior_text}
cursor.execute("""
    INSERT INTO behavior_data
    (user_id, timestamp, behavior_text, action)
    VALUES (?, ?, ?, ?)
""", (user_id, timestamp, behavior_text, "unstructured"))
```

**query_behavior_data()** - 只返回非结构化格式：
```python
# 只查询: id, user_id, timestamp, behavior_text
SELECT id, user_id, timestamp, behavior_text
FROM behavior_data
```

**import_user_profiles()** - 只接受非结构化格式：
```python
# 只接受: {user_id, profile_text}
INSERT OR REPLACE INTO user_profiles
(user_id, profile_text)
VALUES (?, ?)
```

**query_user_profiles()** - 只返回非结构化格式：
```python
# 只查询: id, user_id, profile_text, created_at
SELECT id, user_id, profile_text, created_at
FROM user_profiles
```

#### EventExtractionService (backend/app/services/event_extraction.py)

**_enrich_behaviors_with_entities()** - 简化为直接返回：
```python
def _enrich_behaviors_with_entities(self, behaviors: List[Dict]) -> List[Dict]:
    # 非结构化格式，直接返回
    return behaviors
```

**_get_user_profile()** - 只查询非结构化格式：
```python
SELECT user_id, profile_text
FROM user_profiles
WHERE user_id = ?
```

**extract_events_for_user()** - 只查询非结构化字段：
```python
SELECT id, timestamp, behavior_text
FROM behavior_data
WHERE user_id = ?
```

**extract_events_batch()** - 只查询非结构化字段：
```python
SELECT id, timestamp, behavior_text
FROM behavior_data
WHERE user_id = ?
```

**get_user_sequences()** - 只查询非结构化字段：
```python
SELECT user_id, timestamp, behavior_text
FROM behavior_data
WHERE user_id IN (...)
```

### 2. 前端简化

#### BaseModeling.vue

**行为数据表格** - 直接绑定字段：
```vue
<el-table-column prop="behavior_text" label="行为描述" />
```

**用户画像表格** - 直接绑定字段：
```vue
<el-table-column prop="profile_text" label="用户画像" />
```

#### EventExtraction.vue

**用户画像显示** - 直接显示文本：
```vue
<div>{{ userProfile.profile_text }}</div>
```

**行为序列显示** - 直接显示文本：
```vue
<span class="behavior-time">{{ formatTimestamp(behavior.timestamp) }}</span>
<span class="behavior-detail">{{ behavior.behavior_text }}</span>
```

## 数据格式

### 行为数据

**CSV 格式**:
```csv
user_id,timestamp,behavior_text
user_001,2026-01-01 10:00:00,在微信上浏览了BMW 7系的广告，停留了5分钟
```

**数据库存储**:
- `user_id`: TEXT
- `timestamp`: DATETIME
- `behavior_text`: TEXT
- `action`: TEXT (固定为 "unstructured")

**API 返回**:
```json
{
  "id": 1,
  "user_id": "user_001",
  "timestamp": "2026-01-01 10:00:00",
  "behavior_text": "在微信上浏览了BMW 7系的广告，停留了5分钟"
}
```

### 用户画像

**CSV 格式**:
```csv
user_id,profile_text
user_001,28岁男性，北京工程师，年收入50万，本科学历，喜欢高尔夫和科技产品
```

**数据库存储**:
- `user_id`: TEXT
- `profile_text`: TEXT

**API 返回**:
```json
{
  "id": 1,
  "user_id": "user_001",
  "profile_text": "28岁男性，北京工程师，年收入50万，本科学历，喜欢高尔夫和科技产品",
  "created_at": "2026-02-22 12:00:00"
}
```

## 移除的代码

### 后端
- ✓ 移除结构化字段的查询逻辑
- ✓ 移除格式判断逻辑（`if "behavior_text" in behavior`）
- ✓ 移除实体关联逻辑（APP、媒体、POI、Item）
- ✓ 移除 `_format_behavior()` 的调用
- ✓ 简化 `_enrich_behaviors_with_entities()` 为直接返回

### 前端
- ✓ 移除 `v-if/v-else` 格式判断
- ✓ 移除结构化字段显示（action, item_id, app_id, duration）
- ✓ 移除用户画像的 el-descriptions 组件
- ✓ 移除 `getBehaviorTagType()` 方法的使用

## 优势

### 1. 代码更简洁
- 后端查询只需要 3-4 个字段
- 前端显示直接绑定字段
- 无需复杂的格式判断逻辑

### 2. 性能更好
- 查询字段更少，SQL 更快
- 无需实体关联查询
- 无需格式转换

### 3. 维护更容易
- 代码逻辑清晰
- 无需考虑兼容性
- 易于理解和修改

## 测试验证

### 测试脚本
- `test_unstructured_format.py` - 测试通过 ✓

### 测试结果
```
✓ 导入非结构化行为数据成功
✓ 查询行为数据返回正确格式
✓ 导入非结构化用户画像成功
✓ 查询用户画像返回正确格式
```

## 注意事项

### 旧数据处理

如果数据库中有旧的结构化数据：
1. 可以手动清空表：`DELETE FROM behavior_data; DELETE FROM user_profiles;`
2. 或者运行迁移脚本转换数据（如果需要）
3. 重新导入非结构化格式的数据

### 数据库字段

虽然简化了代码，但数据库表仍保留旧字段：
- `behavior_data` 表仍有 `action`, `item_id`, `app_id` 等字段
- `user_profiles` 表仍有 `age`, `gender`, `city` 等字段
- 这些字段不再使用，但保留以避免数据库迁移问题

## 修改文件清单

### 后端
- `backend/app/services/base_modeling.py` - 简化导入和查询逻辑
- `backend/app/services/event_extraction.py` - 简化所有查询和处理逻辑

### 前端
- `frontend/src/views/BaseModeling.vue` - 简化表格显示
- `frontend/src/views/EventExtraction.vue` - 简化用户详情显示

## 总结

✓ 移除所有向后兼容逻辑
✓ 只保留非结构化格式
✓ 代码更简洁、性能更好
✓ 测试验证通过

现在系统完全使用非结构化格式，代码更加简洁易维护！
