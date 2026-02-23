# 批量事件抽象性能分析与优化方案

## 当前性能问题

### 实际运行数据

```
总用户数: 486
已处理: 14 (2.9%)
成功: 2
失败: 12
总批次: 406
预计剩余时间: 91746秒 (约25小时)
```

### 性能瓶颈分析

#### 1. 批次太小（根本原因）

```
分为 406 批处理，每批平均 1 个用户
```

**原因**：
- 平均每个用户有 96 条行为
- 按 50 tokens/行为 估算 = 4800 tokens/用户
- MAX_TOKENS_PER_BATCH = 8000
- 8000 / 4800 = 1.7 个用户/批
- **结果：大部分批次只有1个用户！**

#### 2. LLM调用慢

每批耗时统计：
```
第1批: 60秒 (1个用户)
第2批: 62秒 (1个用户)
第3批: 80秒 (1个用户)
第4批: 82秒 (2个用户)
第11批: 2038秒 (2个用户，超时重试)
```

**平均每批：50-60秒**

#### 3. 成功率低

```
处理12批，只成功2个用户
失败原因：
- LLM返回空结果
- ReadTimeout (超时)
- LLM返回格式错误
```

### 总耗时估算

```
486个用户 ÷ 1.2个用户/批 = 405批
405批 × 50秒/批 = 20250秒 ≈ 5.6小时

考虑失败率（85%失败）：
实际可能需要 10-20 小时
```

## 优化方案

### 方案1：增加批次大小（推荐）

**问题**：8000 tokens 太保守了

**优化**：
```python
# 当前
MAX_TOKENS_PER_BATCH = 8000  # 只能容纳1-2个用户

# 优化后
MAX_TOKENS_PER_BATCH = 40000  # 可以容纳8-10个用户
```

**效果**：
- 批次数：406 → 50
- 总耗时：5.6小时 → 0.7小时（42分钟）
- **提升：8倍**

**风险**：
- LLM可能有token限制
- 需要测试MiniMax的实际限制

### 方案2：并发处理批次

**当前**：串行处理，一次只处理一批

**优化**：并发处理多个批次
```python
import asyncio

# 并发处理3个批次
async def process_batches_concurrent(batches):
    semaphore = asyncio.Semaphore(3)  # 最多3个并发

    async def process_one_batch(batch):
        async with semaphore:
            return await llm_client.abstract_events_batch(batch)

    tasks = [process_one_batch(batch) for batch in batches]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return results
```

**效果**：
- 3个并发：5.6小时 → 1.9小时
- **提升：3倍**

### 方案3：优化LLM调用

#### 3.1 减少prompt长度

**当前问题**：每次都发送完整的行为描述

**优化**：
```python
# 当前：发送完整描述
"2026-01-01 10:00:00 在XX西餐厅停留 1小时14分钟"

# 优化：简化描述
"10:00 西餐厅 1h14m"
```

**效果**：
- Token减少 50%
- 批次大小翻倍
- 总耗时减半

#### 3.2 使用更快的模型

**当前**：MiniMax-M2.5（慢，经常超时）

**优化**：
- 尝试其他模型（如 GLM-4-Flash）
- 或者使用本地模型

### 方案4：改进批处理策略

**当前**：按token数严格分批

**优化**：智能分批
```python
# 优先处理行为少的用户（快速完成）
user_ids_sorted = sorted(user_ids, key=lambda uid: len(behaviors[uid]))

# 混合分批：每批包含大小用户
def create_mixed_batches(users):
    small_users = [u for u in users if len(u.behaviors) < 50]
    large_users = [u for u in users if len(u.behaviors) >= 50]

    batches = []
    for large in large_users:
        batch = [large]
        # 填充小用户
        while small_users and estimate_tokens(batch + [small_users[0]]) < MAX_TOKENS:
            batch.append(small_users.pop(0))
        batches.append(batch)

    return batches
```

**效果**：
- 更均衡的批次大小
- 更好的资源利用

### 方案5：缓存和增量处理

**优化**：
```python
# 保存中间结果，支持断点续传
def save_checkpoint(processed_users):
    with open('checkpoint.json', 'w') as f:
        json.dump(processed_users, f)

# 恢复时跳过已处理的用户
def load_checkpoint():
    if os.path.exists('checkpoint.json'):
        with open('checkpoint.json') as f:
            return json.load(f)
    return []
```

## 推荐的优化组合

### 立即可做（最小改动）

1. **增加 MAX_TOKENS_PER_BATCH 到 40000**
   - 改动：1行代码
   - 效果：8倍提升
   - 风险：低（可以测试）

```python
# backend/app/services/event_extraction.py 第304行
MAX_TOKENS_PER_BATCH = 40000  # 从8000改为40000
```

2. **增加LLM超时时间**（已完成）
   - 从60秒增加到180秒
   - 减少超时失败

### 中期优化（需要测试）

3. **并发处理3个批次**
   - 改动：约50行代码
   - 效果：3倍提升
   - 风险：中（需要测试并发稳定性）

4. **简化prompt**
   - 改动：修改prompt生成逻辑
   - 效果：2倍提升
   - 风险：低（不影响质量）

### 长期优化

5. **更换更快的LLM模型**
6. **实现断点续传**
7. **优化批处理策略**

## 预期效果

### 当前性能
```
486个用户
406批次
预计耗时: 25小时
成功率: 15%
```

### 优化后（方案1）
```
486个用户
50批次 (增加批次大小)
预计耗时: 3小时
成功率: 50% (增加超时时间)
```

### 优化后（方案1+2）
```
486个用户
50批次
3个并发
预计耗时: 1小时
成功率: 50%
```

### 优化后（方案1+2+3）
```
486个用户
25批次 (简化prompt)
3个并发
预计耗时: 25分钟
成功率: 70% (更稳定)
```

## 立即行动建议

**最快见效的优化**：

1. 修改 `MAX_TOKENS_PER_BATCH` 从 8000 到 40000
2. 重启批量抽象任务
3. 观察效果

**代码修改**：
```python
# backend/app/services/event_extraction.py
# 第304行

# 修改前
MAX_TOKENS_PER_BATCH = 8000

# 修改后
MAX_TOKENS_PER_BATCH = 40000  # 增加到40000，每批可容纳8-10个用户
```

**预期效果**：
- 批次数：406 → 50
- 总耗时：25小时 → 3小时
- **提升：8倍**

## 其他发现

### LLM返回格式问题

日志显示很多"LLM返回空结果"，可能是：
1. LLM返回了`<think>`标签但没有JSON
2. JSON格式错误
3. 超时导致返回不完整

**建议**：
- 改进JSON解析逻辑
- 添加重试机制
- 记录原始响应用于调试
