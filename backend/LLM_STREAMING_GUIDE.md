# LLM流式响应实时显示实施指南

## 目标

在前端实时显示LLM返回的内容，而不是等到最后才显示结果。

## 已完成的工作

### 1. 后端实现

#### 1.1 添加流式抽象方法

在 `backend/app/core/openai_client.py` 中添加了 `abstract_events_batch_stream()` 方法：

```python
async def abstract_events_batch_stream(
    self,
    user_behaviors: Dict[str, List[Dict]],
    user_profiles: Dict[str, Dict] = None,
    stream_callback=None
):
    """批量抽象用户行为为事件（流式版本，实时返回LLM响应）"""
    # 使用流式调用
    stream_generator = await self.chat_completion(prompt, max_tokens=8000, stream=True)

    # 实时yield每个chunk
    full_response = ""
    async for chunk in stream_generator:
        full_response += chunk
        if stream_callback:
            await stream_callback(chunk)
        yield chunk  # 实时返回给调用者
```

#### 1.2 添加流式API端点

在 `backend/app/api/event_extraction_routes.py` 中添加了 `/extract/{user_id}/llm-stream` 端点：

```python
@router.post("/extract/{user_id}/llm-stream")
async def extract_events_for_user_llm_stream(user_id: str):
    """返回Server-Sent Events格式的流式数据"""
    async def event_generator():
        # 实时yield LLM的每个chunk
        async for chunk in llm_client.abstract_events_batch_stream(...):
            yield f"data: {json.dumps({'type': 'llm_chunk', 'content': chunk}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
```

### 2. 前端实现

#### 2.1 添加流式API调用

在 `frontend/src/api/index.js` 中添加了 `extractEventsForUserStream()` 函数：

```javascript
export const extractEventsForUserStream = (userId, callbacks = {}) => {
  const url = `${BASE_URL}/events/extract/${userId}/llm-stream`

  return new Promise((resolve, reject) => {
    fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    }).then(response => {
      const reader = response.body.getReader()
      const decoder = new TextDecoder()

      const readStream = () => {
        reader.read().then(({ done, value }) => {
          if (done) return

          const chunk = decoder.decode(value, { stream: true })
          const lines = chunk.split('\n')

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const data = JSON.parse(line.substring(6))

              switch (data.type) {
                case 'llm_chunk':
                  if (callbacks.onLLMChunk) callbacks.onLLMChunk(data.content)
                  break
                case 'done':
                  if (callbacks.onDone) callbacks.onDone(data)
                  resolve(data)
                  return
                case 'error':
                  if (callbacks.onError) callbacks.onError(data.message)
                  reject(new Error(data.message))
                  return
              }
            }
          }

          readStream()
        })
      }

      readStream()
    })
  })
}
```

#### 2.2 修改前端调用

在 `frontend/src/views/EventExtraction.vue` 中修改了 `handleSingleExtract()` 方法：

```javascript
const handleSingleExtract = async (userId) => {
  try {
    extractingUsers[userId] = true

    startLLMLog(`事件抽象 - ${userId}`)
    appendLLMLog(`\n--- LLM实时响应 ---\n`)

    await extractEventsForUserStream(userId, {
      onProgress: (message) => {
        appendLLMLog(`[进度] ${message}\n`)
      },
      onLLMChunk: (chunk) => {
        // 实时显示LLM返回的每个chunk
        appendLLMLog(chunk)
      },
      onDone: (data) => {
        appendLLMLog(`\n--- 响应结束 ---\n`)
        completeLLMLog()
        ElMessage.success(`用户 [${userId}] 事件抽象完成`)
        loadData()
      },
      onError: (error) => {
        errorLLMLog(error)
        ElMessage.error(`用户 [${userId}] 事件抽象失败: ${error}`)
      }
    })

  } finally {
    extractingUsers[userId] = false
  }
}
```

## 使用方法

1. 启动后端服务
2. 启动前端服务
3. 在事件抽象页面点击"重新生成"按钮
4. 在右侧的LLM日志面板中可以看到实时的LLM响应内容

## 效果

- ✅ LLM响应内容实时显示在日志面板中
- ✅ 用户可以看到LLM正在生成的内容
- ✅ 不需要等待整个响应完成才能看到结果
- ✅ 提供更好的用户体验和透明度

## 注意事项

1. **Server-Sent Events (SSE)** - 使用SSE协议进行流式传输
2. **nginx缓冲** - 如果使用nginx，需要禁用缓冲 (`X-Accel-Buffering: no`)
3. **超时设置** - 确保前端和后端的超时时间足够长
4. **错误处理** - 需要处理网络中断、超时等异常情况

## 后续优化建议

1. **添加重连机制** - 网络中断时自动重连
2. **进度百分比** - 根据已生成的内容估算进度
3. **取消功能** - 允许用户中途取消LLM调用
4. **批量流式** - 支持批量用户的流式抽象

## 相关文件

- `backend/app/core/openai_client.py` - LLM客户端，包含流式方法
- `backend/app/api/event_extraction_routes.py` - API路由，包含流式端点
- `frontend/src/api/index.js` - 前端API调用
- `frontend/src/views/EventExtraction.vue` - 事件抽象页面
- `frontend/src/stores/llmLog.js` - LLM日志管理

## 测试命令

```bash
# 测试流式端点
curl -N -X POST http://localhost:8000/api/v1/events/extract/user_0007/llm-stream

# 应该看到实时的SSE数据流
data: {"type": "start", "message": "开始为用户 user_0007 抽象事件..."}
data: {"type": "progress", "message": "正在调用LLM分析..."}
data: {"type": "llm_chunk", "content": "user_0007|"}
data: {"type": "llm_chunk", "content": "看车|"}
data: {"type": "llm_chunk", "content": "2026-01-15 10:00|"}
...
data: {"type": "done", "message": "抽象完成"}
```

---

**实施状态**: 代码已完成，需要解决后端启动问题后进行测试
**最后更新**: 2026-02-23
