# 事件抽象页面数据兼容性修复

## 问题描述

事件抽象页面显示的行为数据和用户画像仍然是旧的结构化格式，没有切换到基础建模的非结构化数据。

## 根本原因

1. **后端查询未包含新字段**: `get_user_sequences` 方法查询行为数据时没有包含 `behavior_text` 字段
2. **前端显示硬编码结构化格式**: EventExtraction.vue 组件只显示结构化字段（action, item_id, app_id 等）

## 修复内容

### 1. 后端修改

#### EventExtractionService.get_user_sequences()

**文件**: `backend/app/services/event_extraction.py`

**修改前**:
```python
cursor.execute(f"""
    SELECT user_id, action, timestamp, item_id, app_id, media_id, poi_id, duration
    FROM behavior_data
    WHERE user_id IN ({placeholders})
    ORDER BY user_id, timestamp ASC
""", user_ids)

# 按用户分组行为数据
behaviors_by_user = {}
for row in cursor.fetchall():
    user_id = row[0]
    if user_id not in behaviors_by_user:
        behaviors_by_user[user_id] = []
    action_desc = self._format_behavior(row[1:])  # 跳过user_id
    behaviors_by_user[user_id].append(action_desc)
```

**修改后**:
```python
cursor.execute(f"""
    SELECT user_id, action, timestamp, item_id, app_id, media_id, poi_id, duration, behavior_text
    FROM behavior_data
    WHERE user_id IN ({placeholders})
    ORDER BY user_id, timestamp ASC
""", user_ids)

# 按用户分组行为数据
behaviors_by_user = {}
for row in cursor.fetchall():
    user_id = row[0]
    if user_id not in behaviors_by_user:
        behaviors_by_user[user_id] = []

    # 如果有 behavior_text，使用非结构化格式
    if row[8]:  # behavior_text
        action_desc = f"{row[2]} {row[8]}"  # timestamp + behavior_text
    else:
        # 结构化格式（向后兼容）
        action_desc = self._format_behavior(row[1:8])  # 跳过user_id和behavior_text

    behaviors_by_user[user_id].append(action_desc)
```

**效果**:
- 非结构化数据显示为: `2026-01-01 10:00:00 在微信上浏览了BMW 7系的广告，停留了5分钟`
- 结构化数据显示为: `2026-01-01 10:00:00 浏览item_001`

### 2. 前端修改

#### EventExtraction.vue - 用户画像显示

**文件**: `frontend/src/views/EventExtraction.vue`

**修改前**:
```vue
<el-descriptions :column="2" border>
  <el-descriptions-item label="用户ID">{{ userProfile.user_id }}</el-descriptions-item>
  <el-descriptions-item label="年龄">{{ userProfile.age || '-' }}</el-descriptions-item>
  <el-descriptions-item label="性别">{{ userProfile.gender || '-' }}</el-descriptions-item>
  ...
</el-descriptions>
```

**修改后**:
```vue
<!-- 非结构化格式 -->
<div v-if="userProfile.profile_text" style="padding: 15px; background: #f5f7fa; border-radius: 4px;">
  {{ userProfile.profile_text }}
</div>
<!-- 结构化格式（向后兼容） -->
<el-descriptions v-else :column="2" border>
  <el-descriptions-item label="用户ID">{{ userProfile.user_id }}</el-descriptions-item>
  <el-descriptions-item label="年龄">{{ userProfile.age || '-' }}</el-descriptions-item>
  ...
</el-descriptions>
```

#### EventExtraction.vue - 行为序列显示

**修改前**:
```vue
<div v-for="(behavior, index) in userBehaviors" :key="index" class="behavior-item">
  <el-tag :type="getBehaviorTagType(behavior.action)" size="small">
    {{ behavior.action }}
  </el-tag>
  <span class="behavior-time">{{ formatTimestamp(behavior.timestamp) }}</span>
  <span class="behavior-detail">
    <span v-if="behavior.item_id">内容: {{ behavior.item_id }}</span>
    <span v-if="behavior.app_id">APP: {{ behavior.app_id }}</span>
    <span v-if="behavior.duration">时长: {{ behavior.duration }}s</span>
  </span>
</div>
```

**修改后**:
```vue
<div v-for="(behavior, index) in userBehaviors" :key="index" class="behavior-item">
  <!-- 非结构化格式 -->
  <template v-if="behavior.behavior_text">
    <span class="behavior-time">{{ formatTimestamp(behavior.timestamp) }}</span>
    <span class="behavior-detail">{{ behavior.behavior_text }}</span>
  </template>
  <!-- 结构化格式（向后兼容） -->
  <template v-else>
    <el-tag :type="getBehaviorTagType(behavior.action)" size="small">
      {{ behavior.action }}
    </el-tag>
    <span class="behavior-time">{{ formatTimestamp(behavior.timestamp) }}</span>
    <span class="behavior-detail">
      <span v-if="behavior.item_id">内容: {{ behavior.item_id }}</span>
      <span v-if="behavior.app_id">APP: {{ behavior.app_id }}</span>
      <span v-if="behavior.duration">时长: {{ behavior.duration }}s</span>
    </span>
  </template>
</div>
```

## 数据流

### 事件抽象页面数据来源

```
用户点击"查看"
    ↓
前端: getUserDetail(user_id)
    ↓
后端: GET /api/v1/events/users/{user_id}/detail
    ↓
后端: modeling_service.query_user_profiles()  ← 从 user_profiles 表查询
    ↓
后端: modeling_service.query_behavior_data()  ← 从 behavior_data 表查询
    ↓
后端: extraction_service._enrich_behaviors_with_entities()  ← 兼容非结构化
    ↓
前端: 显示用户画像和行为序列  ← 智能判断格式
```

### 用户列表数据来源

```
页面加载
    ↓
前端: GET /api/v1/events/sequences
    ↓
后端: extraction_service.get_user_sequences()
    ↓
后端: 查询 behavior_data 表（包含 behavior_text）
    ↓
后端: 智能格式化行为描述
    ↓
前端: 显示用户列表
```

## 兼容性保证

### 向后兼容

✓ **旧数据继续可用**:
- 没有 `behavior_text` 的数据显示为结构化格式
- 没有 `profile_text` 的数据显示为结构化字段

✓ **智能判断格式**:
- 后端查询时包含新旧字段
- 前端显示时使用 `v-if` 判断

✓ **混合使用**:
- 可以同时存在新旧格式的数据
- 每条数据独立判断格式

## 测试验证

### 测试脚本

**test_event_extraction_data.py** - 测试事件抽象页面数据

**测试结果**:
```
✓ get_user_sequences 返回数据
✓ behavior_sequence 包含行为描述
✓ 非结构化数据显示为 'timestamp behavior_text'
✓ 结构化数据显示为格式化字符串
```

### 手动测试步骤

1. 启动服务（后端 + 前端）
2. 访问"基础建模"页面
3. 导入非结构化格式的行为数据和用户画像
4. 访问"事件抽象"页面
5. 查看用户列表，行为序列应该显示完整文本
6. 点击"查看"按钮，查看用户详情
7. 用户画像应该显示完整文本
8. 原始行为序列应该显示完整文本

### 预期结果

**用户列表 - 行为序列**:
```
2026-01-01 10:00:00 在微信上浏览了BMW 7系的广告，停留了5分钟
2026-01-01 10:30:00 在汽车之家APP搜索"豪华轿车"
```

**用户详情 - 用户画像**:
```
28岁男性，北京工程师，年收入50万，本科学历，喜欢高尔夫和科技产品
```

**用户详情 - 原始行为序列**:
```
2026-01-01 10:00:00
在微信上浏览了BMW 7系的广告，停留了5分钟

2026-01-01 10:30:00
在汽车之家APP搜索"豪华轿车"
```

## 修改文件清单

### 后端
- `backend/app/services/event_extraction.py` - 修改 `get_user_sequences()` 方法

### 前端
- `frontend/src/views/EventExtraction.vue` - 修改用户画像和行为序列显示

### 测试
- `test_event_extraction_data.py` - 新增测试脚本

## 总结

✓ 后端查询包含非结构化字段
✓ 后端智能格式化行为描述
✓ 前端智能判断显示格式
✓ 向后兼容结构化数据
✓ 测试验证通过

现在事件抽象页面已经完全切换到基础建模的数据，并且兼容新旧两种格式。
