# 序列挖掘功能修复报告

**修复日期**: 2026-02-24
**问题**: 序列挖掘结果的用户数、支持率、支持度指标不正确，超过实际用户数

## 问题分析

### 原始问题

1. **用户数统计错误**: 挖掘结果显示的 `total_users` 包含了失败状态的用户
2. **缺少最小长度参数**: 无法过滤掉过短的序列模式

### 数据库状态

```
总用户数: 496
├─ 成功状态 (status='success', sequence!='[]'): 341
└─ 失败状态 (status='failed' 或 sequence='[]'): 155
```

### 根本原因

在 [backend/app/services/sequence_mining.py](backend/app/services/sequence_mining.py) 的 `_load_event_sequences()` 方法中：

```python
# 原始查询（错误）
query = """
    SELECT user_id, sequence
    FROM event_sequences
    ORDER BY user_id
"""
```

这个查询加载了所有用户记录，包括：
- 失败状态的用户（155个）
- 空序列的用户

导致统计信息不准确。

## 修复内容

### 1. 修复用户数统计

**文件**: [backend/app/services/sequence_mining.py](backend/app/services/sequence_mining.py)

**位置**: 第261-269行

修复前：
```python
query = """
    SELECT user_id, sequence
    FROM event_sequences
    ORDER BY user_id
"""
```

修复后：
```python
query = """
    SELECT user_id, sequence
    FROM event_sequences
    WHERE status = 'success' AND sequence != '[]'
    ORDER BY user_id
"""
```

**效果**: 只加载成功状态且非空的序列，确保统计准确。

### 2. 添加最小序列长度参数

#### 后端修改

**文件**: [backend/app/services/sequence_mining.py](backend/app/services/sequence_mining.py)

**位置1**: 第21-28行（方法签名）

```python
def mine_frequent_subsequences(
    self,
    algorithm: str = "prefixspan",
    min_support: int = 2,
    min_length: int = 2,  # 新增：最小序列长度
    max_length: int = 5,
    top_k: int = 20,
    use_cache: bool = True
) -> Dict:
```

**位置2**: 第46-51行（缓存过滤）

```python
if use_cache:
    cached_result = self.cache.get_patterns(min_support, max_length)
    if cached_result:
        # 过滤缓存结果中的模式长度
        cached_result["frequent_patterns"] = [
            p for p in cached_result["frequent_patterns"]
            if min_length <= p["length"] <= max_length
        ]
        cached_result["statistics"]["patterns_found"] = len(cached_result["frequent_patterns"])
        return cached_result
```

**位置3**: 第85-88行（结果过滤）

```python
# 格式化结果并过滤长度，然后取前K个
formatted_patterns = self._format_patterns(frequent_patterns, len(sequences))
# 过滤最小长度
formatted_patterns = [p for p in formatted_patterns if p["length"] >= min_length]
formatted_patterns = formatted_patterns[:top_k]
```

**位置4**: 第93-100行（统计信息）

```python
statistics = {
    "total_users": len(sequences),
    "total_sequences": len(sequences),
    "unique_event_types": len(unique_events),
    "avg_sequence_length": round(sum(len(seq) for seq in sequences) / len(sequences), 2) if sequences else 0,
    "min_support": min_support,
    "min_length": min_length,  # 新增
    "max_length": max_length,
    "patterns_found": len(formatted_patterns)
}
```

#### API 路由修改

**文件**: [backend/app/api/sequence_mining_routes.py](backend/app/api/sequence_mining_routes.py)

**位置1**: 第18-23行（请求模型）

```python
class MiningRequest(BaseModel):
    algorithm: str = Field("prefixspan", description="算法类型: prefixspan 或 attention")
    min_support: int = Field(2, ge=1, le=100, description="最小支持度")
    min_length: int = Field(2, ge=1, le=10, description="最小序列长度")  # 新增
    max_length: int = Field(3, ge=2, le=5, description="最大序列长度 (限制为5以控制内存使用)")
    top_k: int = Field(20, ge=1, le=100, description="返回前K个模式")
```

**位置2**: 第48-53行（服务调用）

```python
result = mining_service.mine_frequent_subsequences(
    algorithm=request.algorithm,
    min_support=request.min_support,
    min_length=request.min_length,  # 新增
    max_length=request.max_length,
    top_k=request.top_k
)
```

#### 前端修改

**文件**: [frontend/src/views/SequenceMining.vue](frontend/src/views/SequenceMining.vue)

**位置1**: 第71-99行（表单布局）

添加了"最小序列长度"输入框：

```vue
<el-col :span="12">
  <el-form-item label="最小序列长度">
    <el-input-number
      v-model="miningForm.min_length"
      :min="1"
      :max="10"
      placeholder="最小序列长度"
    />
    <el-tooltip content="挖掘的子序列的最小长度" placement="top">
      <el-icon style="margin-left: 10px; cursor: help"><QuestionFilled /></el-icon>
    </el-tooltip>
  </el-form-item>
</el-col>
```

**位置2**: 第407-412行（表单数据）

```javascript
const miningForm = ref({
  algorithm: 'prefixspan',
  min_support: 2,
  min_length: 2,  // 新增
  max_length: 5,
  top_k: 20
})
```

## 验证结果

### 1. 用户数统计验证

```bash
# 数据库查询
总用户数: 496
成功状态且非空序列的用户数: 341
失败或空序列的用户数: 155

# 挖掘结果
挖掘结果显示的用户数: 341
数据库中成功用户数: 341
✓ 数据一致
```

### 2. 最小长度参数验证

**测试1**: `min_length=2, max_length=3`

```json
{
  "frequent_patterns": [
    {"pattern": ["使用APP", "使用APP", "使用APP"], "length": 3},
    {"pattern": ["使用APP", "使用APP"], "length": 2},
    {"pattern": ["活跃", "活跃"], "length": 2}
  ],
  "statistics": {
    "total_users": 341,
    "min_length": 2,
    "max_length": 3
  }
}
```

✓ 所有模式长度在 [2, 3] 范围内

**测试2**: `min_length=3, max_length=5`

```json
{
  "frequent_patterns": [
    {"pattern": ["使用APP", "使用APP", "使用APP", "使用APP", "使用APP"], "length": 5},
    {"pattern": ["使用APP", "使用APP", "使用APP"], "length": 3},
    {"pattern": ["使用APP", "使用APP", "使用APP", "使用APP"], "length": 4}
  ],
  "statistics": {
    "total_users": 341,
    "min_length": 3,
    "max_length": 5
  }
}
```

✓ 所有模式长度在 [3, 5] 范围内，长度为2的模式被过滤

### 3. 支持度和支持率验证

```
模式: ["使用APP", "使用APP"]
支持度 (support): 118
支持率 (support_rate): 34.6%
计算验证: 118 / 341 ≈ 34.6% ✓

总用户数: 341
包含该模式的用户数: 118
比例: 34.6% ✓
```

## 功能改进

### 1. 更准确的统计信息

- `total_users`: 只统计成功状态的用户
- `support`: 包含该模式的用户数（准确）
- `support_rate`: 支持度 / 总用户数 * 100（准确）

### 2. 更灵活的模式过滤

用户可以通过 `min_length` 和 `max_length` 参数精确控制挖掘的序列长度范围：

- `min_length=2, max_length=3`: 只挖掘2-3步的短序列
- `min_length=3, max_length=5`: 只挖掘3-5步的中长序列
- `min_length=1, max_length=10`: 挖掘所有长度的序列

### 3. 性能优化

通过过滤失败状态的用户，减少了不必要的数据加载和处理：

- 原始: 加载 496 个用户记录（包含155个空序列）
- 优化后: 只加载 341 个有效用户记录
- 性能提升: 减少 31% 的数据加载量

## API 使用示例

### 请求

```bash
curl -X POST http://localhost:8000/api/v1/mining/mine \
  -H "Content-Type: application/json" \
  -d '{
    "algorithm": "prefixspan",
    "min_support": 2,
    "min_length": 2,
    "max_length": 3,
    "top_k": 10
  }'
```

### 响应

```json
{
  "code": 0,
  "message": "挖掘完成",
  "data": {
    "algorithm": "prefixspan",
    "frequent_patterns": [
      {
        "pattern": ["使用APP", "使用APP", "使用APP"],
        "support": 118,
        "support_rate": 34.6,
        "length": 3,
        "description": "用户使用APP → 使用APP → 使用APP的行为路径"
      }
    ],
    "statistics": {
      "total_users": 341,
      "total_sequences": 341,
      "unique_event_types": 150,
      "avg_sequence_length": 81.08,
      "min_support": 2,
      "min_length": 2,
      "max_length": 3,
      "patterns_found": 10
    }
  }
}
```

## 相关文件

- [backend/app/services/sequence_mining.py](backend/app/services/sequence_mining.py) - 核心挖掘服务
- [backend/app/api/sequence_mining_routes.py](backend/app/api/sequence_mining_routes.py) - API 路由
- [frontend/src/views/SequenceMining.vue](frontend/src/views/SequenceMining.vue) - 前端界面
- [frontend/src/api/index.js](frontend/src/api/index.js) - API 客户端

## 总结

本次修复解决了两个关键问题：

1. **统计准确性**: 通过过滤失败状态的用户，确保统计信息准确反映实际情况
2. **功能完善性**: 添加 `min_length` 参数，让用户可以更灵活地控制挖掘结果

修复后的系统能够准确统计用户数、支持度和支持率，并提供更灵活的序列长度过滤功能。
