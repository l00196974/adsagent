# 事件抽象功能验证指南

## 已完成的修改

### 1. 前端菜单 ✅
- **文件**: `frontend/src/App.vue`
- **修改**: 在"基础建模"后添加了"事件抽象"菜单项
- **路由**: `/events`

### 2. 后端API ✅
- **文件**: `backend/app/api/event_extraction_routes.py`
- **新增接口**: `GET /api/v1/events/users/{user_id}/detail`
- **功能**: 返回用户画像、行为数据和事件序列的完整信息

### 3. 前端API客户端 ✅
- **文件**: `frontend/src/api/index.js`
- **新增方法**:
  - `extractEvents(userIds)` - 批量事件抽象
  - `extractEventsForUser(userId)` - 单用户事件抽象
  - `listEventSequences(limit, offset)` - 查询事件序列列表
  - `getUserSequence(userId)` - 查询单个用户序列
  - `getUserDetail(userId)` - 获取用户完整信息

### 4. 事件抽象页面优化 ✅
- **文件**: `frontend/src/views/EventExtraction.vue`
- **新增功能**:
  - 用户画像展示区域（年龄、性别、城市、职业等）
  - 优化的行为序列展示（带颜色标签、时间格式化）
  - 改进的视觉样式

## 验证步骤

### 前置条件

1. **安装后端依赖**
```bash
cd backend
pip install -r requirements.txt
```

2. **配置环境变量**
```bash
cd backend
cp .env.example .env
# 编辑 .env 文件，添加 ANTHROPIC_API_KEY
```

3. **安装前端依赖**
```bash
cd frontend
npm install
```

### 启动服务

1. **启动后端服务**
```bash
cd backend
python3 main.py
# 服务运行在 http://localhost:8000
# API文档: http://localhost:8000/docs
```

2. **启动前端服务**（新终端窗口）
```bash
cd frontend
npm run dev
# 服务运行在 http://localhost:5173
```

### 功能验证

#### 步骤1: 验证菜单显示
1. 打开浏览器访问 `http://localhost:5173`
2. 检查顶部菜单栏
3. 确认"事件抽象"菜单项显示在"基础建模"和"数据导入"之间

#### 步骤2: 导入测试数据
在验证事件抽象功能前，需要先导入基础数据：

1. 点击"基础建模"菜单
2. 导入以下数据：
   - **用户画像数据** (CSV格式，包含: user_id, age, gender, city, occupation)
   - **行为数据** (CSV格式，包含: user_id, action, timestamp, item_id, app_id等)

示例CSV格式：

**用户画像 (user_profiles.csv)**:
```csv
user_id,age,gender,city,occupation
user_001,28,男,北京,工程师
user_002,35,女,上海,设计师
user_003,42,男,深圳,产品经理
```

**行为数据 (behavior_data.csv)**:
```csv
user_id,action,timestamp,item_id,app_id,duration
user_001,view,2024-01-01 10:00:00,item_123,app_001,30
user_001,click,2024-01-01 10:05:00,item_456,app_001,5
user_002,search,2024-01-01 11:00:00,keyword_abc,app_002,10
```

#### 步骤3: 验证事件抽象页面
1. 点击"事件抽象"菜单
2. 验证页面显示：
   - ✅ 用户列表表格
   - ✅ 行为序列列数
   - ✅ 事理序列列数
   - ✅ 状态标签（已抽象/未抽象）
   - ✅ 操作按钮（查看/生成）

#### 步骤4: 验证单用户事件抽象
1. 选择一个"未抽象"状态的用户
2. 点击"生成"按钮
3. 等待LLM处理完成（需要配置有效的ANTHROPIC_API_KEY）
4. 验证：
   - ✅ 状态变为"已抽象"
   - ✅ 事理序列列显示事件数量

#### 步骤5: 验证用户详情展示
1. 点击任意用户的"查看"按钮或行为序列链接
2. 验证详情弹窗显示：
   - ✅ **用户画像区域**
     - 用户ID、年龄、性别、城市、职业
     - 扩展属性（如果有）
   - ✅ **原始行为序列**
     - 行为类型标签（带颜色）
     - 格式化的时间戳
     - 详细信息（内容ID、APP ID、时长等）
   - ✅ **抽象事理序列**
     - 事件列表（如果已抽象）
     - 或"暂无事理序列"提示

#### 步骤6: 验证批量事件抽象
1. 点击"批量事件抽象"按钮
2. 确认操作提示
3. 等待处理完成
4. 验证：
   - ✅ 显示成功/失败统计
   - ✅ 所有用户状态更新
   - ✅ 数据持久化保存

#### 步骤7: 验证数据持久化
1. 刷新页面
2. 验证：
   - ✅ 用户列表数据仍然存在
   - ✅ 事件抽象结果保持不变
   - ✅ 再次查看详情，数据完整

### API验证（可选）

使用curl或Postman测试新增的API接口：

```bash
# 获取用户完整信息
curl http://localhost:8000/api/v1/events/users/user_001/detail

# 预期响应格式：
{
  "code": 0,
  "data": {
    "user_id": "user_001",
    "profile": {
      "user_id": "user_001",
      "age": 28,
      "gender": "男",
      "city": "北京",
      "occupation": "工程师",
      "properties": {},
      "created_at": "2024-01-01 00:00:00"
    },
    "behaviors": [
      {
        "id": 1,
        "user_id": "user_001",
        "action": "view",
        "timestamp": "2024-01-01 10:00:00",
        "item_id": "item_123",
        "app_id": "app_001",
        "duration": 30,
        "properties": {}
      }
    ],
    "events": [
      "用户浏览商品",
      "用户点击详情"
    ]
  }
}
```

### 数据库验证（可选）

检查数据库中的数据：

```bash
# 使用Python检查数据库
python3 -c "
import sqlite3
conn = sqlite3.connect('data/graph.db')
cursor = conn.cursor()

# 检查用户画像
cursor.execute('SELECT COUNT(*) FROM user_profiles')
print(f'用户画像: {cursor.fetchone()[0]} 条')

# 检查行为数据
cursor.execute('SELECT COUNT(*) FROM behavior_data')
print(f'行为数据: {cursor.fetchone()[0]} 条')

# 检查抽象事件
cursor.execute('SELECT COUNT(*) FROM extracted_events')
print(f'抽象事件: {cursor.fetchone()[0]} 条')

# 检查事件序列
cursor.execute('SELECT COUNT(*) FROM event_sequences')
print(f'事件序列: {cursor.fetchone()[0]} 条')

conn.close()
"
```

## 预期结果

### 成功标志
- ✅ 菜单中显示"事件抽象"入口
- ✅ 页面正常加载用户列表
- ✅ 详情弹窗显示完整的用户画像信息
- ✅ 行为序列展示格式优化（标签、时间、详情）
- ✅ 事件抽象功能正常工作
- ✅ 数据持久化保存，刷新后不丢失

### 可能的问题

1. **LLM API调用失败**
   - 检查 `.env` 文件中的 `ANTHROPIC_API_KEY` 是否配置正确
   - 查看后端日志: `backend/logs/adsagent.log`

2. **数据库表不存在**
   - 确保后端服务至少启动过一次（会自动创建表）
   - 检查 `data/graph.db` 文件是否存在

3. **前端API调用失败**
   - 检查浏览器控制台错误信息
   - 确认后端服务正常运行
   - 检查CORS配置

## 技术细节

### 数据流
```
用户点击"查看"
  → 前端调用 getUserDetail(userId)
  → 后端 GET /api/v1/events/users/{user_id}/detail
  → 查询 user_profiles 表（用户画像）
  → 查询 behavior_data 表（行为数据）
  → 查询 extracted_events 表（事件数据）
  → 返回合并后的完整数据
  → 前端展示在详情弹窗中
```

### 持久化机制
- 所有数据存储在 `data/graph.db` SQLite数据库中
- 事件抽象结果保存在 `extracted_events` 和 `event_sequences` 表
- 每次抽象会先删除旧数据，再插入新数据
- 使用事务确保数据一致性

## 总结

本次优化实现了以下目标：
1. ✅ 在前端菜单中添加"事件抽象"入口
2. ✅ 展示用户画像信息和行为序列
3. ✅ 基于基础建模的数据进行事件抽象
4. ✅ 持久化保存抽象结果

所有功能已完整实现，数据持久化逻辑已验证正确。
