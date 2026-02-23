# 快速开始指南

## 5分钟快速验证

### 步骤 1: 启动后端服务器

```bash
cd backend
python main.py
```

等待看到:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 步骤 2: 测试后端 API（可选）

在新终端运行:
```bash
python test_progress_api.py
```

预期输出:
```
============================================================
测试批量事件抽象进度跟踪
============================================================

1. 检查初始进度状态...
状态码: 200
响应: {
  "code": 0,
  "data": {
    "status": "idle",
    ...
  }
}

2. 启动批量抽象任务...
状态码: 200
响应: {
  "code": 0,
  "message": "批量抽象任务已启动",
  ...
}

3. 轮询进度...
[1s] 状态: running, 进度: 10.0%, 已处理: 10/100
[2s] 状态: running, 进度: 20.0%, 已处理: 20/100
...
```

### 步骤 3: 启动前端开发服务器

在新终端运行:
```bash
cd frontend
npm run dev
```

等待看到:
```
  VITE v5.4.21  ready in XXX ms

  ➜  Local:   http://localhost:5173/
```

### 步骤 4: 在浏览器中测试

1. 打开浏览器访问: http://localhost:5173

2. 进入"事件抽象"页面

3. 点击"批量事件抽象"按钮

4. 在确认对话框中点击"确定"

5. 观察进度展示:
   - ✓ 进度条实时更新
   - ✓ 显示当前批次 (X/Y)
   - ✓ 显示已处理用户数
   - ✓ 显示成功/失败统计
   - ✓ 显示当前处理的用户ID
   - ✓ 显示预计剩余时间

6. 等待完成后:
   - ✓ 显示成功提示
   - ✓ 列表自动刷新

## 常见问题

### Q1: 后端启动失败

**问题**: `ModuleNotFoundError: No module named 'xxx'`

**解决**:
```bash
cd backend
pip install -r requirements.txt
```

### Q2: 前端启动失败

**问题**: `Error: Cannot find module 'xxx'`

**解决**:
```bash
cd frontend
npm install
```

### Q3: API 调用失败

**问题**: `Connection refused` 或 `404 Not Found`

**检查**:
1. 后端服务器是否正在运行？
2. 端口是否正确（后端: 8000, 前端: 5173）？
3. 防火墙是否阻止了连接？

### Q4: 进度不更新

**问题**: 点击按钮后没有进度显示

**检查**:
1. 打开浏览器开发者工具（F12）
2. 查看 Console 是否有错误
3. 查看 Network 标签，确认 API 调用成功
4. 检查后端日志是否有错误

### Q5: 任务无法启动

**问题**: 提示"已有批量抽象任务正在运行"

**解决**:
1. 等待当前任务完成
2. 或重启后端服务器

## 手动测试 API

### 测试进度查询

```bash
curl http://localhost:8000/api/v1/events/extract/progress
```

预期响应:
```json
{
  "code": 0,
  "data": {
    "status": "idle",
    "total_users": 0,
    "processed_users": 0,
    "success_count": 0,
    "failed_count": 0,
    "current_batch": 0,
    "total_batches": 0,
    "current_user_ids": [],
    "progress_percent": 0,
    "estimated_remaining_seconds": null,
    "error_message": null
  }
}
```

### 测试启动任务

```bash
curl -X POST http://localhost:8000/api/v1/events/extract/start \
  -H "Content-Type: application/json" \
  -d '{"user_ids": null}'
```

预期响应:
```json
{
  "code": 0,
  "message": "批量抽象任务已启动",
  "data": {
    "status": "started"
  }
}
```

### 测试轮询进度

```bash
# 每秒查询一次，观察进度变化
watch -n 1 'curl -s http://localhost:8000/api/v1/events/extract/progress | jq'
```

## 验证成功标志

### 后端
- [x] 服务器启动成功
- [x] API 端点响应正常
- [x] 进度状态正确更新
- [x] 日志输出正常

### 前端
- [x] 页面加载成功
- [x] 按钮点击响应
- [x] 进度卡片显示
- [x] 进度实时更新
- [x] 完成提示显示
- [x] 列表自动刷新

### 集成
- [x] 前后端通信正常
- [x] 进度数据同步
- [x] 错误处理正确
- [x] 用户体验流畅

## 下一步

验证成功后，可以:

1. 查看详细文档: `PROGRESS_TRACKING_IMPLEMENTATION.md`
2. 查看架构设计: `ARCHITECTURE_DIAGRAM.md`
3. 查看验证清单: `VERIFICATION_CHECKLIST.md`
4. 查看文件变更: `FILES_CHANGED.md`

## 需要帮助？

如果遇到问题:

1. 检查后端日志: `backend/logs/adsagent.log`
2. 检查浏览器控制台（F12）
3. 查看 `PROGRESS_TRACKING_IMPLEMENTATION.md` 的"常见问题"部分
4. 联系开发团队

## 性能测试

### 小规模测试（10-50 用户）
- 预期时间: 10-30 秒
- 批次数: 1-5 批
- 适合快速验证

### 中规模测试（100-500 用户）
- 预期时间: 1-5 分钟
- 批次数: 10-50 批
- 适合功能验证

### 大规模测试（1000+ 用户）
- 预期时间: 10+ 分钟
- 批次数: 100+ 批
- 适合性能验证

## 监控指标

在测试过程中，观察:

1. **进度更新频率**: 应该每秒更新一次
2. **预估时间准确性**: 误差应该在 ±20% 以内
3. **内存占用**: 应该保持稳定，无明显增长
4. **CPU 占用**: 主要在 LLM 调用时，其他时间应该很低
5. **网络流量**: 轮询请求应该很小（<1KB/次）

## 成功案例

预期看到的完整流程:

```
1. 用户点击"批量事件抽象"按钮
   ↓
2. 显示确认对话框
   ↓
3. 用户确认
   ↓
4. 按钮变为 loading 状态
   ↓
5. 显示"批量抽象任务已启动"消息
   ↓
6. 显示进度卡片
   ↓
7. 进度条开始更新（0% → 10% → 20% → ...）
   ↓
8. 显示当前批次信息（1/10 → 2/10 → ...）
   ↓
9. 显示当前处理的用户ID
   ↓
10. 显示预计剩余时间（递减）
    ↓
11. 进度达到 100%
    ↓
12. 显示"批量抽象完成"成功提示
    ↓
13. 列表自动刷新，显示新抽象的事件
    ↓
14. 完成！
```

恭喜！功能验证成功！🎉
