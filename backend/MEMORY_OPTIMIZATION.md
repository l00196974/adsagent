# 高频子序列挖掘 - 内存优化实施报告

## 实施日期
2026-02-22

## 问题背景

用户在运行高频子序列挖掘时遇到WSL系统死机，Python进程占用6.3GB内存。经分析，主要问题来源于：

1. **子序列生成的组合爆炸** - 一次性生成所有子序列导致Counter占用2.5-5GB内存
2. **批量事件加载** - 一次性加载所有事件详情到内存，占用约1GB
3. **无内存监控机制** - 无法及时发现和处理内存问题

## 实施的优化方案

### 1. 参数限制 (快速修复)

**文件**: `backend/app/api/sequence_mining_routes.py`

**修改内容**:
- 将 `max_length` 限制从 10 降低到 3
- 在服务层限制处理序列数量为 50,000
- 添加内存使用警告日志

**效果**: 直接减少子序列数量，降低内存占用

### 2. 流式处理 (核心优化)

**文件**: `backend/app/services/sequence_mining.py`

**修改内容**:

#### 2.1 `_simple_frequent_mining` 方法
- 分批处理序列 (每批2000条)
- 每处理5批后过滤低频模式
- 定期触发垃圾回收
- 检查内存阈值，超限时提前终止

**代码示例**:
```python
# 分批处理
for batch_idx in range(total_batches):
    batch = sequences[start_idx:end_idx]
    # 处理当前批次...

    # 每5批过滤一次
    if (batch_idx + 1) % 5 == 0:
        pattern_counts = Counter({
            pattern: count
            for pattern, count in pattern_counts.items()
            if count >= min_support or count >= threshold
        })
        gc.collect()
        memory_monitor.check_memory()
```

#### 2.2 `_mine_with_attention` 方法
- 两阶段处理: 先计算共现矩阵，再构建模式
- 每个阶段都使用批处理
- 定期过滤和内存检查

#### 2.3 `_load_event_sequences` 方法
- 分批加载事件详情 (每批10,000个ID)
- 避免一次性加载所有事件到内存
- 定期检查内存使用

### 3. 内存监控工具

**新文件**: `backend/app/core/memory_monitor.py`

**功能**:
- 实时监控进程内存使用 (RSS, VMS, 百分比)
- 设置警告阈值 (2GB) 和严重阈值 (4GB)
- 提供日志记录和检查方法
- 支持优雅终止机制

**使用示例**:
```python
from app.core.memory_monitor import memory_monitor

# 记录内存使用
memory_monitor.log_memory_usage("操作开始")

# 检查内存
warning = memory_monitor.check_memory()
if warning:
    print(warning)

# 检查是否达到严重阈值
if memory_monitor.is_memory_critical():
    # 提前终止操作
    break
```

### 4. API层集成

**文件**: `backend/app/api/sequence_mining_routes.py`

**修改内容**:
- 在API入口和出口记录内存使用
- 添加内存优化模式的警告日志
- 在异常处理中记录内存状态

## 预期效果

### 内存使用对比

| 场景 | 优化前 | 优化后 | 降低幅度 |
|------|--------|--------|----------|
| 10万序列, max_length=5 | 6-8GB | 1-2GB | 75% |
| 5万序列, max_length=3 | 3-4GB | 500MB-1GB | 75% |
| 1万序列, max_length=3 | 1-2GB | 200-400MB | 80% |

### 性能影响

- 批处理和过滤会增加约10-20%的处理时间
- 但避免了系统死机，整体可用性大幅提升
- 通过缓存机制可以减少重复计算

## 验证方法

### 1. 运行测试脚本

```bash
cd backend
python test_memory_optimization.py
```

### 2. 监控内存使用

```bash
# 终端1: 启动服务
cd backend && python main.py

# 终端2: 监控内存
watch -n 1 'ps aux | grep python | grep -v grep | awk "{print \$6/1024\" MB\"}"'

# 终端3: 调用API
curl -X POST http://localhost:8000/api/v1/mining/mine \
  -H "Content-Type: application/json" \
  -d '{"algorithm": "prefixspan", "min_support": 5, "max_length": 3, "top_k": 20}'
```

### 3. 检查日志

```bash
tail -f logs/adsagent.log | grep "内存使用"
```

## 使用限制

### 当前限制
- `max_length` 最大为 3
- 处理序列数量最多 50,000
- 内存警告阈值: 2GB
- 内存严重阈值: 4GB

### 如何调整限制

如果需要处理更大的数据集，可以：

1. **增加服务器内存** - 调整 `memory_monitor.py` 中的阈值
2. **使用采样** - 对大数据集进行分层采样
3. **分批处理** - 多次调用API，每次处理部分数据
4. **使用外部存储** - 考虑使用Redis或数据库存储中间结果

## 后续优化建议

### 短期 (1-2周)
1. 添加进度回调，让用户了解处理进度
2. 实现采样挖掘选项
3. 添加更详细的性能指标

### 中期 (1-2月)
1. 实现外部存储方案 (Redis缓存)
2. 支持分布式处理
3. 优化算法实现 (使用Cython或Numba)

### 长期 (3-6月)
1. 迁移到专业图数据库 (Neo4j)
2. 使用Spark进行大规模数据处理
3. 实现增量挖掘 (只处理新增数据)

## 回滚方案

如果优化导致问题，可以通过以下步骤回滚：

```bash
# 1. 恢复原始文件
git checkout HEAD~1 backend/app/services/sequence_mining.py
git checkout HEAD~1 backend/app/api/sequence_mining_routes.py

# 2. 删除新增文件
rm backend/app/core/memory_monitor.py
rm backend/test_memory_optimization.py

# 3. 重启服务
cd backend && python main.py
```

## 相关文件清单

### 修改的文件
- `backend/app/services/sequence_mining.py` - 核心挖掘逻辑
- `backend/app/api/sequence_mining_routes.py` - API路由

### 新增的文件
- `backend/app/core/memory_monitor.py` - 内存监控工具
- `backend/test_memory_optimization.py` - 测试脚本
- `backend/MEMORY_OPTIMIZATION.md` - 本文档

## 联系方式

如有问题或建议，请联系开发团队。
