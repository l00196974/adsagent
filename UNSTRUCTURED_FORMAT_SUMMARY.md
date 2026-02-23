# 非结构化格式改造总结

## 改造完成 ✓

已成功将行为数据和用户画像改造为非结构化格式，同时保持向后兼容。

## 改动内容

### 1. 数据库迁移

**脚本**: `backend/scripts/migrate_to_unstructured.py`

添加了两个新字段：
- `behavior_data.behavior_text` - 非结构化行为描述
- `user_profiles.profile_text` - 非结构化用户画像

**执行结果**:
```
✓ behavior_data.behavior_text 字段添加成功
✓ user_profiles.profile_text 字段添加成功
```

### 2. 后端服务修改

#### BaseModelingService (backend/app/services/base_modeling.py)

**import_behavior_data()** - 兼容两种格式：
- 非结构化：`{user_id, timestamp, behavior_text}`
- 结构化：`{user_id, action, timestamp, item_id, app_id, ...}`（向后兼容）

**query_behavior_data()** - 查询时优先返回非结构化格式：
- 如果有 `behavior_text`，返回非结构化格式
- 否则返回结构化格式（向后兼容）

**import_user_profiles()** - 兼容两种格式：
- 非结构化：`{user_id, profile_text}`
- 结构化：`{user_id, age, gender, city, ...}`（向后兼容）

**query_user_profiles()** - 查询时优先返回非结构化格式：
- 如果有 `profile_text`，返回非结构化格式
- 否则返回结构化格式（向后兼容）

#### EventExtractionService (backend/app/services/event_extraction.py)

**_enrich_behaviors_with_entities()** - 智能处理：
- 检测到非结构化格式（有 `behavior_text`）时，直接返回，不做实体关联
- 结构化格式继续执行原有的实体关联逻辑

**_get_user_profile()** - 兼容两种格式：
- 优先从 `user_profiles.profile_text` 读取非结构化画像
- 否则读取结构化字段（向后兼容）

**extract_events_for_user()** 和 **extract_events_batch()** - 查询时包含新字段：
- SQL 查询包含 `behavior_text` 字段
- 根据是否有 `behavior_text` 决定返回格式

### 3. 前端修改

#### BaseModeling.vue (frontend/src/views/BaseModeling.vue)

**行为数据**:
- 表格简化为 3 列：用户ID、时间戳、行为描述
- 模板改为非结构化格式：
  ```csv
  user_id,timestamp,behavior_text
  user_001,2026-01-01 10:00:00,在微信上浏览了BMW 7系的广告，停留了5分钟
  ```

**用户画像**:
- 表格简化为 2 列：用户ID、用户画像
- 模板改为非结构化格式：
  ```csv
  user_id,profile_text
  user_001,28岁男性，北京工程师，年收入50万，本科学历，喜欢高尔夫和科技产品
  ```

## 兼容性保证

### 向后兼容

✓ **旧数据继续可用**：
- 已有的结构化数据（没有 `behavior_text` 或 `profile_text`）继续正常工作
- 查询时自动识别格式并返回相应字段

✓ **旧格式导入继续支持**：
- 可以继续导入结构化格式的 CSV
- 系统自动识别并存储到对应字段

✓ **事件抽象功能兼容**：
- 自动检测数据格式
- 非结构化数据直接传给 LLM
- 结构化数据继续执行实体关联后传给 LLM

### 新旧格式对比

#### 行为数据

**旧格式（结构化）**:
```csv
user_id,action,timestamp,item_id,app_id,media_id,poi_id,duration,properties
user_001,view,2026-01-01 10:00:00,item_001,app_001,,,300,{}
```

**新格式（非结构化）**:
```csv
user_id,timestamp,behavior_text
user_001,2026-01-01 10:00:00,在微信上浏览了BMW 7系的广告，停留了5分钟
```

#### 用户画像

**旧格式（结构化）**:
```csv
user_id,age,gender,city,occupation,properties
user_001,28,男,北京,工程师,{"income_level":"高","education":"本科"}
```

**新格式（非结构化）**:
```csv
user_id,profile_text
user_001,28岁男性，北京工程师，年收入50万，本科学历，喜欢高尔夫和科技产品
```

## 测试验证

### 测试脚本

**test_unstructured_format.py** - 测试非结构化格式的导入和查询

**测试结果**:
```
✓ 导入非结构化行为数据成功
✓ 查询行为数据返回正确格式
✓ 导入非结构化用户画像成功
✓ 查询用户画像返回正确格式
```

### 手动测试步骤

1. 启动后端：`cd backend && python main.py`
2. 启动前端：`cd frontend && npm run dev`
3. 访问 http://localhost:5173
4. 进入"基础建模"页面
5. 点击"下载模板"按钮，下载新格式模板
6. 编辑模板，填入数据
7. 点击"导入CSV"上传
8. 查看表格显示是否正确
9. 进入"事件抽象"页面，测试事件抽象功能

## 优势

### 1. 更灵活的数据表达

非结构化文本可以包含任意信息，不受字段限制：
- 行为：可以描述复杂的用户行为场景
- 画像：可以用自然语言描述用户特征

### 2. 更适合 LLM 处理

LLM 更擅长理解自然语言文本，而不是结构化字段：
- 减少了字段映射和转换的复杂度
- LLM 可以直接理解上下文和语义

### 3. 更简单的数据准备

用户只需要用自然语言描述，不需要：
- 理解复杂的字段定义
- 填写多个结构化字段
- 处理 JSON 格式的 properties

### 4. 向后兼容

保留了结构化格式的支持：
- 已有数据不受影响
- 可以混合使用两种格式
- 逐步迁移到新格式

## 注意事项

### 1. 数据质量

非结构化文本的质量直接影响 LLM 的理解：
- 建议提供清晰、完整的描述
- 避免过于简略或模糊的表达
- 包含关键信息（时间、地点、动作、对象等）

### 2. 性能考虑

非结构化文本可能更长：
- Token 消耗可能增加
- 需要注意 LLM 的 token 限制
- 批处理时注意批次大小

### 3. 迁移建议

如果有大量旧数据：
- 可以保持旧格式继续使用
- 新数据使用新格式
- 不需要强制迁移旧数据

## 文件清单

### 新增文件
- `backend/scripts/migrate_to_unstructured.py` - 数据库迁移脚本
- `test_unstructured_format.py` - 测试脚本
- `UNSTRUCTURED_FORMAT_SUMMARY.md` - 本文档

### 修改文件
- `backend/app/services/base_modeling.py` - 导入和查询逻辑
- `backend/app/services/event_extraction.py` - 事件抽象兼容性
- `frontend/src/views/BaseModeling.vue` - 模板和显示

## 总结

✓ 数据库迁移完成
✓ 后端服务兼容两种格式
✓ 前端模板和显示更新
✓ 事件抽象功能兼容
✓ 测试验证通过
✓ 向后兼容保证

用户现在可以使用更简单、更灵活的非结构化格式导入数据，同时旧数据继续正常工作。
