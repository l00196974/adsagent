# 批量事件抽象进度跟踪功能实现

## 概述

本次实现为批量事件抽象功能添加了实时进度跟踪，解决了用户在执行长时间任务时无法看到进度的问题。

## 实现方案

采用**内存进度跟踪 + 轮询**方案：
- 后端：在 `EventExtractionService` 中维护进度状态，提供进度查询API
- 前端：定时轮询进度并实时更新UI
- 架构：使用 `asyncio.create_task` 实现后台任务执行

## 修改的文件

### 后端

1. **backend/app/services/event_extraction.py**
   - 添加 `task_progress` 状态字典
   - 添加 `get_progress()` 方法：返回当前进度和预估剩余时间
   - 添加 `_update_progress()` 方法：更新进度状态
   - 修改 `extract_events_batch()` 方法：在批处理循环中更新进度

2. **backend/app/api/event_extraction_routes.py**
   - 添加 `POST /events/extract/start` 端点：启动后台任务
   - 添加 `GET /events/extract/progress` 端点：查询进度
   - 保留原有 `POST /events/extract` 端点（同步版本，向后兼容）

### 前端

3. **frontend/src/api/index.js**
   - 添加 `startBatchExtract()` 函数
   - 添加 `getExtractProgress()` 函数

4. **frontend/src/views/EventExtraction.vue**
   - 添加进度展示UI组件（进度条、统计信息、当前处理用户）
   - 添加 `extractProgress` 响应式状态
   - 添加 `startProgressPolling()` 方法：每秒轮询进度
   - 添加 `formatProgress()` 和 `formatTime()` 辅助方法
   - 添加完成/失败提示组件
   - 添加进度卡片样式

## 进度状态结构

```python
{
    "status": "idle",  # idle, running, completed, failed
    "total_users": 0,
    "processed_users": 0,
    "success_count": 0,
    "failed_count": 0,
    "current_batch": 0,
    "total_batches": 0,
    "current_user_ids": [],  # 当前批次正在处理的用户ID
    "start_time": None,
    "end_time": None,
    "error_message": None,
    "progress_percent": 0,  # 计算得出
    "estimated_remaining_seconds": None  # 计算得出
}
```

## API端点

### 启动批量抽象（后台执行）

```bash
POST /api/v1/events/extract/start
Content-Type: application/json

{
  "user_ids": null  # null表示处理所有未抽象的用户
}

# 响应
{
  "code": 0,
  "message": "批量抽象任务已启动",
  "data": {
    "status": "started"
  }
}
```

### 查询进度

```bash
GET /api/v1/events/extract/progress

# 响应
{
  "code": 0,
  "data": {
    "status": "running",
    "total_users": 100,
    "processed_users": 45,
    "success_count": 42,
    "failed_count": 3,
    "current_batch": 5,
    "total_batches": 10,
    "current_user_ids": ["user_0045", "user_0046", "user_0047"],
    "progress_percent": 45.0,
    "estimated_remaining_seconds": 120
  }
}
```

## 使用方法

### 后端测试

1. 启动后端服务器：
```bash
cd backend
python main.py
```

2. 运行测试脚本：
```bash
python test_progress_api.py
```

3. 手动测试API：
```bash
# 启动批量抽象
curl -X POST http://localhost:8000/api/v1/events/extract/start \
  -H "Content-Type: application/json" \
  -d '{"user_ids": null}'

# 查询进度（多次调用观察变化）
curl http://localhost:8000/api/v1/events/extract/progress
```

### 前端测试

1. 启动前端开发服务器：
```bash
cd frontend
npm run dev
```

2. 访问 http://localhost:5173

3. 进入"事件抽象"页面

4. 点击"批量事件抽象"按钮

5. 观察进度展示：
   - 进度条实时更新
   - 显示当前批次和总批次
   - 显示已处理/成功/失败用户数
   - 显示当前正在处理的用户ID
   - 显示预计剩余时间

## 功能特性

### 实时进度展示
- 进度百分比
- 已处理/总用户数
- 成功/失败统计
- 当前批次信息
- 预计剩余时间

### 用户体验优化
- 按钮禁用（任务运行时）
- 完成/失败提示
- 自动刷新列表
- 组件销毁时清理定时器

### 错误处理
- 重复启动检测
- 网络错误处理
- 任务失败提示

## 性能考虑

- **轮询频率**：1秒/次，适合长时间任务
- **内存占用**：进度状态 <1KB
- **并发限制**：单任务模式（可扩展为多任务队列）

## 局限性

1. **进度状态在内存中**：服务器重启会丢失
2. **轮询延迟**：1-2秒延迟
3. **单实例部署**：不支持多实例负载均衡

## 后续优化方向

1. **持久化进度**：保存到数据库，支持服务器重启后恢复
2. **WebSocket推送**：替换轮询为WebSocket，实现真正的实时更新
3. **任务队列**：使用Celery或RQ，支持多任务并发和分布式部署
4. **取消任务**：添加取消按钮，允许用户中止正在运行的任务
5. **历史记录**：保存每次批量抽象的历史记录和统计信息

## 验证清单

- [x] 后端进度状态管理
- [x] 后端API端点实现
- [x] 前端进度展示UI
- [x] 前端轮询逻辑
- [x] 错误处理
- [x] 完成/失败提示
- [x] 组件生命周期管理
- [x] 测试脚本
- [x] 文档

## 测试场景

### 正常流程
1. 点击"批量事件抽象"按钮
2. 确认对话框
3. 任务启动，显示进度卡片
4. 进度实时更新
5. 任务完成，显示成功提示
6. 列表自动刷新

### 边界情况
- 重复点击按钮（应提示已有任务在运行）
- 中途刷新页面（进度状态丢失，但任务继续执行）
- 服务器重启（任务中断，需要重新启动）
- 网络错误（轮询失败，前端显示错误）
- 空用户列表（正常处理，显示0/0）

## 技术栈

- **后端**：FastAPI + asyncio + SQLite
- **前端**：Vue 3 + Element Plus + Axios
- **架构**：REST API + 轮询

## 总结

本实现通过最小改动解决了批量事件抽象无进度反馈的问题，提供了良好的用户体验。采用的内存进度跟踪+轮询方案简单可靠，适合当前规模和需求。
