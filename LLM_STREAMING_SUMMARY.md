# LLM流式响应实时显示 - 实施总结

## 目标

在前端实时显示LLM返回的内容，而不是等到最后才显示结果。

## 已完成的工作

### 1. 后端实现 ✅

#### 1.1 流式抽象方法
文件: `backend/app/core/openai_client.py`

添加了 `abstract_events_batch_stream()` 方法，实时yield LLM的每个chunk。

#### 1.2 流式API端点
文件: `backend/app/api/event_extraction_routes.py`

添加了 `/extract/{user_id}/llm-stream` 端点，使用Server-Sent Events返回流式数据。

### 2. 前端实现 ✅

#### 2.1 流式API调用
文件: `frontend/src/api/index.js`

添加了 `extractEventsForUserStream()` 函数，使用fetch API读取SSE流。

#### 2.2 UI集成
文件: `frontend/src/views/EventExtraction.vue`

修改了 `handleSingleExtract()` 方法，实时显示LLM响应到日志面板。

## 使用方法

1. 启动后端: `cd backend && python main.py`
2. 启动前端: `cd frontend && npm run dev`
3. 打开事件抽象页面
4. 点击任意用户的"重新生成"按钮
5. 在右侧LLM日志面板中查看实时响应

## 效果演示

```
--- LLM实时响应 ---
[进度] 正在调用LLM分析 125 条行为...
user_0007|看车|2026-01-15 10:00|4S店,宝马,停留2小时
user_0007|浏览车型|2026-01-15 12:30|汽车之家,宝马7系,奔驰S级
user_0007|搜索|2026-01-16 09:00|海岛游,三亚
...
--- 响应结束 ---
✓ 事件抽象完成
```

## 技术实现

### 后端流式生成器

```python
async def abstract_events_batch_stream(self, user_behaviors, user_profiles=None):
    stream_generator = await self.chat_completion(prompt, max_tokens=8000, stream=True)

    full_response = ""
    async for chunk in stream_generator:
        full_response += chunk
        yield chunk  # 实时返回每个chunk
```

### SSE端点

```python
@router.post("/extract/{user_id}/llm-stream")
async def extract_events_for_user_llm_stream(user_id: str):
    async def event_generator():
        async for chunk in llm_client.abstract_events_batch_stream(...):
            yield f"data: {json.dumps({'type': 'llm_chunk', 'content': chunk})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

### 前端SSE消费

```javascript
fetch(url, { method: 'POST' }).then(response => {
  const reader = response.body.getReader()
  const decoder = new TextDecoder()

  const readStream = () => {
    reader.read().then(({ done, value }) => {
      const chunk = decoder.decode(value)
      // 解析SSE数据
      if (line.startsWith('data: ')) {
        const data = JSON.parse(line.substring(6))
        if (data.type === 'llm_chunk') {
          callbacks.onLLMChunk(data.content)  // 实时显示
        }
      }
      readStream()
    })
  }
  readStream()
})
```

## 待解决问题

1. **后端启动问题** - 需要检查并修复后端启动错误
2. **数据库查询** - 确保正确查询用户行为和画像数据
3. **错误处理** - 完善网络中断、超时等异常处理

## 下一步

1. 修复后端启动问题
2. 测试流式端点是否正常工作
3. 在前端验证实时显示效果
4. 优化用户体验（进度条、取消功能等）

## 相关文件

- `backend/app/core/openai_client.py` - 流式方法实现
- `backend/app/api/event_extraction_routes.py` - 流式API端点
- `frontend/src/api/index.js` - 前端API调用
- `frontend/src/views/EventExtraction.vue` - UI集成
- `backend/LLM_STREAMING_GUIDE.md` - 详细实施指南

## 测试命令

```bash
# 测试流式端点
curl -N -X POST http://localhost:8000/api/v1/events/extract/user_0007/llm-stream

# 预期输出
data: {"type": "start", "message": "开始为用户 user_0007 抽象事件..."}
data: {"type": "progress", "message": "正在调用LLM分析 125 条行为..."}
data: {"type": "llm_chunk", "content": "user_0007|"}
data: {"type": "llm_chunk", "content": "看车|"}
...
data: {"type": "done", "message": "抽象完成"}
```

---

**状态**: 代码已完成，等待后端启动问题解决后测试
**最后更新**: 2026-02-23
