# 批量事件抽象进度跟踪 - 架构图

## 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend (Vue 3)                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  EventExtraction.vue                                             │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  [批量事件抽象] 按钮                                      │    │
│  │         ↓                                                │    │
│  │  handleBatchExtract()                                    │    │
│  │         ↓                                                │    │
│  │  startBatchExtract(null) ──────────────────────┐       │    │
│  │         ↓                                       │       │    │
│  │  startProgressPolling()                        │       │    │
│  │         ↓                                       │       │    │
│  │  setInterval(1000ms)                           │       │    │
│  │         ↓                                       │       │    │
│  │  getExtractProgress() ─────────────────┐      │       │    │
│  │         ↓                               │      │       │    │
│  │  更新 extractProgress 状态              │      │       │    │
│  │         ↓                               │      │       │    │
│  │  渲染进度 UI                            │      │       │    │
│  └────────────────────────────────────────┼──────┼───────┘    │
│                                            │      │             │
└────────────────────────────────────────────┼──────┼─────────────┘
                                             │      │
                                             │      │
                    ┌────────────────────────┘      └────────────────────────┐
                    │                                                         │
                    ▼ HTTP GET                                    HTTP POST   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Backend (FastAPI)                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  event_extraction_routes.py                                                  │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                                                                       │   │
│  │  GET /events/extract/progress        POST /events/extract/start     │   │
│  │         ↓                                      ↓                     │   │
│  │  extraction_service.get_progress()   asyncio.create_task(...)       │   │
│  │         ↓                                      ↓                     │   │
│  │  返回进度状态                          启动后台任务                   │   │
│  │                                                                       │   │
│  └───────────────────────────────────────┬───────────────────────────────┘   │
│                                          │                                   │
│  EventExtractionService                  │                                   │
│  ┌───────────────────────────────────────▼─────────────────────────────┐   │
│  │                                                                       │   │
│  │  task_progress = {                                                   │   │
│  │    status: "idle/running/completed/failed",                         │   │
│  │    total_users: 0,                                                   │   │
│  │    processed_users: 0,                                               │   │
│  │    success_count: 0,                                                 │   │
│  │    failed_count: 0,                                                  │   │
│  │    current_batch: 0,                                                 │   │
│  │    total_batches: 0,                                                 │   │
│  │    current_user_ids: [],                                             │   │
│  │    start_time: None,                                                 │   │
│  │    end_time: None,                                                   │   │
│  │    error_message: None                                               │   │
│  │  }                                                                   │   │
│  │                                                                       │   │
│  │  extract_events_batch(user_ids)                                     │   │
│  │    ↓                                                                 │   │
│  │    _update_progress(status="running", ...)                          │   │
│  │    ↓                                                                 │   │
│  │    加载用户数据                                                       │   │
│  │    ↓                                                                 │   │
│  │    动态分批（按 token 数）                                            │   │
│  │    ↓                                                                 │   │
│  │    for batch in batches:                                            │   │
│  │      _update_progress(current_batch=i, current_user_ids=[...])     │   │
│  │      ↓                                                               │   │
│  │      调用 LLM 批量抽象                                                │   │
│  │      ↓                                                               │   │
│  │      保存结果到数据库                                                 │   │
│  │      ↓                                                               │   │
│  │      _update_progress(processed_users=..., success_count=...)      │   │
│  │    ↓                                                                 │   │
│  │    _update_progress(status="completed", end_time=...)              │   │
│  │                                                                       │   │
│  │  get_progress()                                                      │   │
│  │    ↓                                                                 │   │
│  │    计算 progress_percent                                             │   │
│  │    ↓                                                                 │   │
│  │    计算 estimated_remaining_seconds                                  │   │
│  │    ↓                                                                 │   │
│  │    返回完整进度状态                                                   │   │
│  │                                                                       │   │
│  └───────────────────────────────────────────────────────────────────┘   │
│                                                                               │
└───────────────────────────────────────────────────────────────────────────────┘
```

## 数据流

### 启动流程

```
用户点击按钮
    ↓
前端: handleBatchExtract()
    ↓
前端: startBatchExtract(null)
    ↓
后端: POST /events/extract/start
    ↓
后端: asyncio.create_task(extract_events_batch())
    ↓
后端: 返回 {"status": "started"}
    ↓
前端: startProgressPolling()
    ↓
前端: 每秒调用 getExtractProgress()
```

### 进度更新流程

```
后端: extract_events_batch() 执行中
    ↓
后端: _update_progress(status="running", total_users=100, ...)
    ↓
后端: for batch in batches:
    ↓
后端:   _update_progress(current_batch=i, current_user_ids=[...])
    ↓
后端:   调用 LLM
    ↓
后端:   保存结果
    ↓
后端:   _update_progress(processed_users=..., success_count=...)
    ↓
前端: getExtractProgress() (每秒轮询)
    ↓
前端: 更新 extractProgress 状态
    ↓
前端: Vue 响应式更新 UI
```

### 完成流程

```
后端: 所有批次处理完成
    ↓
后端: _update_progress(status="completed", end_time=...)
    ↓
前端: getExtractProgress() 检测到 status="completed"
    ↓
前端: clearInterval(progressTimer)
    ↓
前端: 显示完成提示
    ↓
前端: loadData() 刷新列表
```

## 关键设计决策

### 1. 为什么使用轮询而不是 WebSocket？

**优点**:
- 实现简单，无需额外依赖
- 符合现有架构（REST API）
- 适合当前规模（100-1000 用户）

**缺点**:
- 1-2 秒延迟
- 额外的 HTTP 请求开销

**结论**: 对于长时间任务（几分钟），1秒轮询延迟可接受

### 2. 为什么使用内存存储而不是数据库？

**优点**:
- 实现简单，无需修改数据库 schema
- 读写速度快
- 适合临时状态

**缺点**:
- 服务器重启会丢失进度
- 不支持多实例部署

**结论**: 对于单实例部署，内存存储足够

### 3. 为什么使用 asyncio.create_task 而不是 Celery？

**优点**:
- 无需引入新依赖
- 配置简单
- 适合单任务场景

**缺点**:
- 不支持任务队列
- 不支持分布式执行

**结论**: 对于当前需求（单任务批量处理），asyncio 足够

## 性能指标

- **轮询频率**: 1 次/秒
- **进度状态大小**: <1KB
- **网络开销**: ~100 bytes/秒
- **内存占用**: 可忽略
- **CPU 占用**: 可忽略

## 扩展性

### 短期优化（无需架构变更）
- 调整轮询频率（0.5-2 秒）
- 添加进度持久化（SQLite）
- 添加取消任务功能

### 长期优化（需要架构变更）
- 使用 WebSocket 推送
- 使用 Celery 任务队列
- 支持多实例部署
- 添加任务历史记录
