# 基于目标行为的序列挖掘实现总结

## 实现日期
2026-02-24

## 实现内容

本次实现为广告知识图谱系统添加了**基于目标行为的序列挖掘**功能，解决了原有序列挖掘缺乏目标导向的问题。

## 核心改进

### 1. 事件分类系统

**数据库层面**：
- 为 `extracted_events` 表添加 `event_category` 字段
- 支持三种事件分类：
  - `conversion`（转化）：购买、加购、到店、留资等
  - `engagement`（互动）：浏览、搜索、查看、收藏等
  - `churn`（流失）：卸载、取消关注、长期不活跃等

**LLM 提示词增强**：
- 更新事件抽取 prompt，要求 LLM 识别并标注事件类型
- 强调保留原始数据中的转化行为（purchase、add_cart、visit_poi）
- 输出格式从 4 字段扩展到 5 字段：`用户ID|事件类型|时间戳|上下文信息|事件分类`

### 2. 目标导向的序列挖掘

**新增参数**：
- `target_event`：指定目标事件（如"购买"、"留资"）
- `target_category`：指定目标事件分类（如"conversion"）

**挖掘逻辑**：
- 只保留包含目标事件/分类的用户序列
- 截取序列到目标事件第一次出现（包含目标）
- 所有挖掘出的模式都以目标事件结束

### 3. 事件标准化

**问题**：现有数据中存在事件名称变体（如"使用APP"、"使用App"、"使用app"）

**解决方案**：
- 添加 `_normalize_event_type()` 方法
- 统一同义词映射
- 在加载序列时自动应用标准化

## 修改文件清单

### 后端文件

1. **backend/scripts/add_event_category_column.py** (新建)
2. **backend/app/core/openai_client.py**
3. **backend/app/services/event_extraction.py**
4. **backend/app/api/event_extraction_routes.py**
5. **backend/app/services/sequence_mining.py**
6. **backend/app/api/sequence_mining_routes.py**

### 前端文件

7. **frontend/src/views/SequenceMining.vue**

## 验证步骤

### 1. 验证数据库迁移

```bash
cd /home/linxiankun/adsagent/backend
python3 scripts/add_event_category_column.py
```

### 2. 验证事件抽取（需要重新抽取）

```bash
# 清空现有数据
python3 -c "
import sqlite3
conn = sqlite3.connect('data/graph.db')
cursor = conn.cursor()
cursor.execute('DELETE FROM extracted_events')
cursor.execute('DELETE FROM event_sequences')
conn.commit()
conn.close()
print('✓ 已清空事件数据')
"

# 启动后端服务后，重新抽取事件
curl -X POST http://localhost:8000/api/v1/events/extract/user_0001
```

### 3. 验证序列挖掘

```bash
# 目标事件挖掘
curl -X POST http://localhost:8000/api/v1/mining/mine \
  -H "Content-Type: application/json" \
  -d '{
    "target_event": "购买",
    "min_support": 2,
    "min_length": 2,
    "max_length": 5
  }'
```

## 预期效果

挖掘结果将显示导向目标事件的行为路径，例如：
- ["浏览车型", "查看详情", "对比价格", "购买"]
- ["搜索车型", "查看评测", "购买"]

所有模式都以目标事件结束，具有明确的业务意义。
