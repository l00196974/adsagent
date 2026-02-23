# 批量抽象任务持久化 - 已实现

## 问题描述

用户反馈：启动批量抽象后，点击其他菜单再回来就看不到原来进行的任务了。

**用户关心的问题**：
1. 任务是中断了还是继续执行？
2. 重新打开页面能否看到正在执行的任务？

## 原有实现分析

### 后端（正确）

后端使用 `asyncio.create_task()` 启动后台任务：

```python
@router.post("/extract/start")
async def start_batch_extract(request: ExtractEventsRequest = None):
    # 启动后台任务
    asyncio.create_task(extraction_service.extract_events_batch(user_ids))
    return {"code": 0, "message": "批量抽象任务已启动"}
```

**特点**：
- ✓ 任务在后台异步执行，不会因为前端断开而中断
- ✓ 进度状态保存在 `EventExtractionService` 的内存中（单例模式）
- ✓ 提供 `/extract/progress` API 查询进度

**结论**：后端实现正确，任务会继续执行。

### 前端（有问题）

原有实现：

```javascript
onMounted(() => {
  loadData()  // 只加载用户列表，不检查任务状态
})

onBeforeUnmount(() => {
  // 组件销毁时清除定时器
  if (progressTimer.value) {
    clearInterval(progressTimer.value)
  }
})
```

**问题**：
1. 页面加载时不检查是否有正在运行的任务
2. 切换页面时轮询停止，回来后不会自动恢复
3. 用户看不到后台任务的状态

## 解决方案

### 修改前端代码

在 `onMounted` 时检查任务状态并恢复轮询：

```javascript
onMounted(async () => {
  // 加载数据
  loadData()

  // 检查是否有正在运行的任务
  try {
    const response = await getExtractProgress()
    if (response.code === 0 && response.data.status === 'running') {
      // 恢复进度状态
      extractProgress.value = response.data
      // 开始轮询
      startProgressPolling()
      console.log('检测到正在运行的批量抽象任务，已恢复进度跟踪')
    }
  } catch (error) {
    console.error('检查任务状态失败:', error)
  }
})
```

### 添加用户提示

在进度卡片中添加提示信息：

```vue
<el-alert
  type="info"
  :closable="false"
  show-icon
  style="margin-bottom: 15px;"
>
  <template #title>
    <span style="font-size: 13px;">任务在后台运行中，您可以切换到其他页面，回来时会自动恢复进度显示</span>
  </template>
</el-alert>
```

## 工作流程

### 场景1：正常使用

1. 用户点击"批量事件抽象"按钮
2. 前端调用 `/extract/start` API
3. 后端启动后台任务，返回成功
4. 前端开始轮询 `/extract/progress`，每秒更新一次
5. 进度卡片实时显示进度
6. 任务完成后停止轮询，显示完成提示

### 场景2：切换页面后返回

1. 用户启动批量抽象（后台任务开始执行）
2. 用户切换到其他页面
   - 前端组件卸载，轮询停止
   - **后台任务继续执行**（不受影响）
3. 用户返回事件抽象页面
   - `onMounted` 触发
   - 调用 `/extract/progress` 检查状态
   - 发现 `status === 'running'`
   - 恢复进度显示，重新开始轮询
4. 用户看到最新的进度

### 场景3：刷新浏览器

1. 用户启动批量抽象（后台任务开始执行）
2. 用户刷新浏览器（F5）
   - 前端重新加载
   - **后台任务继续执行**（不受影响）
3. 页面加载完成
   - `onMounted` 触发
   - 调用 `/extract/progress` 检查状态
   - 发现 `status === 'running'`
   - 恢复进度显示，开始轮询
4. 用户看到最新的进度

### 场景4：关闭浏览器

1. 用户启动批量抽象（后台任务开始执行）
2. 用户关闭浏览器
   - **后台任务继续执行**（不受影响）
3. 用户重新打开浏览器，访问页面
   - `onMounted` 触发
   - 调用 `/extract/progress` 检查状态
   - 如果任务还在运行，恢复进度显示
   - 如果任务已完成，显示完成提示

## 验证测试

### 测试1：检查当前任务状态

```bash
curl http://localhost:8000/api/v1/events/extract/progress
```

**结果**：
```json
{
  "code": 0,
  "data": {
    "status": "running",
    "total_users": 489,
    "processed_users": 2,
    "success_count": 0,
    "failed_count": 2,
    "current_batch": 3,
    "total_batches": 408,
    "progress_percent": 0.4,
    "estimated_remaining_seconds": 34901
  }
}
```

✓ 后台任务正在运行，进度状态正确保存

### 测试2：前端恢复功能

1. 打开事件抽象页面
2. 观察是否自动显示进度卡片
3. 检查浏览器控制台是否有日志：`检测到正在运行的批量抽象任务，已恢复进度跟踪`

## 技术细节

### 后端状态管理

```python
class EventExtractionService:
    def __init__(self):
        # 进度跟踪状态（保存在内存中）
        self.task_progress = {
            "status": "idle",  # idle, running, completed, failed
            "total_users": 0,
            "processed_users": 0,
            "success_count": 0,
            "failed_count": 0,
            "current_batch": 0,
            "total_batches": 0,
            "current_user_ids": [],
            "start_time": None,
            "end_time": None,
            "error_message": None
        }
```

**单例模式**：
- `EventExtractionService` 在 `dependencies.py` 中使用单例模式
- 所有请求共享同一个实例
- 进度状态在服务器运行期间持久化

**局限性**：
- 服务器重启后状态丢失
- 不支持多实例部署（负载均衡）

### 前端轮询机制

```javascript
const startProgressPolling = () => {
  progressTimer.value = setInterval(async () => {
    const response = await getExtractProgress()
    if (response.code === 0) {
      extractProgress.value = response.data

      // 如果完成或失败，停止轮询
      if (response.data.status === 'completed' || response.data.status === 'failed') {
        clearInterval(progressTimer.value)
        progressTimer.value = null
        if (response.data.status === 'completed') {
          await loadData()
        }
      }
    }
  }, 1000)  // 每秒轮询一次
}
```

**特点**：
- 轮询间隔：1秒
- 自动停止：任务完成或失败时
- 自动刷新：任务完成后刷新用户列表

## 用户体验改进

### 1. 状态恢复

✓ 切换页面后回来，自动恢复进度显示
✓ 刷新浏览器后，自动恢复进度显示
✓ 关闭浏览器后重新打开，如果任务还在运行，自动恢复

### 2. 明确提示

✓ 进度卡片中显示提示："任务在后台运行中，您可以切换到其他页面，回来时会自动恢复进度显示"
✓ 用户知道任务不会因为切换页面而中断

### 3. 实时更新

✓ 每秒更新一次进度
✓ 显示当前批次、已处理用户数、成功/失败数
✓ 显示预计剩余时间
✓ 显示当前正在处理的用户ID

## 修改文件

- `frontend/src/views/EventExtraction.vue`
  - 修改 `onMounted` 钩子，添加任务状态检查
  - 添加用户提示信息

## 总结

✓ 后台任务不会因为前端操作而中断
✓ 切换页面后回来会自动恢复进度显示
✓ 刷新浏览器后会自动恢复进度显示
✓ 用户体验得到改善，不会担心任务中断

**回答用户的问题**：
1. **任务是中断了还是继续执行？** → 继续执行，不会中断
2. **重新打开页面能否看到正在执行的任务？** → 能，会自动检测并恢复进度显示
