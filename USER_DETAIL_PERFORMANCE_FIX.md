# 用户行为序列查询性能优化 - 已解决

## 问题

用户反馈：查询用户行为序列需要 5-7 秒，数据量不大，应该 1 秒足够。

## 根本原因

**不是数据库查询慢，而是每次都调用 LLM 生成行为总结！**

### 性能分析

通过添加详细的计时日志，发现：

```
查询用户画像耗时: 0.001秒
查询行为数据耗时: 0.001秒
丰富行为数据耗时: 0.000秒
行为总结生成耗时: 10.800秒  ← 瓶颈在这里！
查询事件数据耗时: 0.001秒
总耗时: 10.805秒
```

**问题**：
- 数据库查询都很快（1-2毫秒）
- 但每次查看用户详情都调用 LLM 生成行为总结
- LLM 调用耗时 5-10 秒
- 这是不必要的，因为用户可能只是想看行为序列，不需要总结

## 解决方案

### 方案：行为总结改为可选参数

修改 API 端点，默认不生成行为总结：

```python
@router.get("/users/{user_id}/detail")
async def get_user_detail(
    user_id: str,
    include_summary: bool = False  # 默认不生成行为总结
):
    """获取用户的完整信息（画像+行为序列+事件序列+行为总结）

    Args:
        user_id: 用户ID
        include_summary: 是否生成行为总结（需要调用LLM，耗时5-10秒）
    """
    # ...

    behavior_summary = ""
    # 只有明确要求时才生成行为总结
    if include_summary and enriched_behaviors:
        behavior_summary = await extraction_service.llm_client.summarize_behavior_sequence(
            enriched_behaviors,
            user_profile=profile
        )
```

### API 使用方式

**快速查询（默认）**：
```bash
GET /api/v1/events/users/user_0001/detail
# 耗时: ~10ms
```

**包含行为总结**：
```bash
GET /api/v1/events/users/user_0001/detail?include_summary=true
# 耗时: ~10秒（需要调用LLM）
```

## 性能对比

### 优化前

| 操作 | 耗时 | 说明 |
|------|------|------|
| 查询用户详情 | 5-10秒 | 每次都调用LLM |
| 数据库查询 | 5ms | 很快 |
| LLM调用 | 5-10秒 | 瓶颈 |

### 优化后

| 操作 | 耗时 | 说明 |
|------|------|------|
| 查询用户详情（默认） | **6-26ms** | 不调用LLM |
| 查询用户详情（带总结） | 5-10秒 | 可选，明确要求时才调用 |
| 数据库查询 | 5ms | 无变化 |

**性能提升**：**200-1000 倍**（从 5-10秒 降低到 6-26毫秒）

## 验证测试

### 测试1：默认查询（不含总结）

```bash
$ time curl -s http://localhost:8000/api/v1/events/users/user_0005/detail > /dev/null

real    0m0.026s
user    0m0.004s
sys     0m0.012s
```

**结果**：26毫秒 ✓

**日志**：
```
查询用户画像耗时: 0.002秒
查询行为数据耗时: 0.002秒
丰富行为数据耗时: 0.000秒
查询事件数据耗时: 0.002秒
总耗时: 0.006秒
```

### 测试2：包含行为总结

```bash
$ time curl -s "http://localhost:8000/api/v1/events/users/user_0006/detail?include_summary=true" > /dev/null

real    0m9.903s
user    0m0.006s
sys     0m0.002s
```

**结果**：9.9秒（正常，因为需要调用LLM）

## 前端适配

前端需要更新 API 调用：

### 当前调用（需要修改）

```javascript
// frontend/src/api/index.js 或相关文件

// 默认查询（快速）
export const getUserDetail = (userId) => {
  return request({
    url: `/events/users/${userId}/detail`,
    method: 'get'
  })
}

// 包含行为总结（慢，可选）
export const getUserDetailWithSummary = (userId) => {
  return request({
    url: `/events/users/${userId}/detail`,
    method: 'get',
    params: { include_summary: true }
  })
}
```

### 前端UI建议

可以添加一个"生成行为总结"按钮：

```vue
<template>
  <div>
    <!-- 用户详情（快速加载） -->
    <div v-if="userDetail">
      <div>用户画像: {{ userDetail.profile }}</div>
      <div>行为序列: {{ userDetail.behaviors }}</div>
      <div>事件序列: {{ userDetail.events }}</div>

      <!-- 行为总结（按需加载） -->
      <div v-if="!behaviorSummary">
        <el-button @click="generateSummary" :loading="summaryLoading">
          生成行为总结（需要5-10秒）
        </el-button>
      </div>
      <div v-else>
        <h4>行为总结</h4>
        <p>{{ behaviorSummary }}</p>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  methods: {
    async loadUserDetail(userId) {
      // 快速加载基本信息
      this.userDetail = await getUserDetail(userId)
    },

    async generateSummary() {
      this.summaryLoading = true
      try {
        // 按需生成行为总结
        const result = await getUserDetailWithSummary(this.userId)
        this.behaviorSummary = result.data.behavior_summary
      } finally {
        this.summaryLoading = false
      }
    }
  }
}
</script>
```

## 其他优化建议

### 1. 缓存行为总结

如果行为总结经常被访问，可以缓存：

```python
# 伪代码
cache_key = f"behavior_summary:{user_id}"
cached = redis.get(cache_key)
if cached:
    return cached

# 生成总结
summary = await llm_client.summarize_behavior_sequence(...)

# 缓存1小时
redis.setex(cache_key, 3600, summary)
return summary
```

### 2. 预生成行为总结

在批量事件抽象时，同时生成行为总结并保存到数据库：

```python
# 在 extract_events_batch 中
for user_id in user_ids:
    # 抽象事件
    events = await extract_events(user_id)

    # 同时生成行为总结
    summary = await summarize_behavior_sequence(behaviors)

    # 保存到数据库
    save_behavior_summary(user_id, summary)
```

这样查询时直接从数据库读取，不需要调用LLM。

### 3. 异步生成

使用后台任务异步生成行为总结：

```python
@router.post("/users/{user_id}/summary/generate")
async def generate_summary_async(user_id: str):
    # 启动后台任务
    asyncio.create_task(generate_and_save_summary(user_id))
    return {"message": "行为总结生成任务已启动"}

@router.get("/users/{user_id}/summary")
async def get_summary(user_id: str):
    # 从数据库读取已生成的总结
    return get_saved_summary(user_id)
```

## 修改文件

- `backend/app/api/event_extraction_routes.py`
  - 添加 `include_summary` 参数（默认 False）
  - 只有明确要求时才调用 LLM 生成行为总结
  - 添加详细的计时日志

## 总结

✓ **根本原因**：每次查询都调用 LLM 生成行为总结（5-10秒）
✓ **解决方案**：行为总结改为可选参数，默认不生成
✓ **性能提升**：从 5-10秒 降低到 6-26毫秒（200-1000倍）
✓ **用户体验**：页面几乎瞬间加载，需要总结时可以按需生成

**现在查询用户行为序列只需要 6-26 毫秒，远低于 1 秒的目标！**
