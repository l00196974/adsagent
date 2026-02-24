# behavior_text 字段修复报告

## 问题描述

用户发现行为数据中的 `behavior_text` 字段为空（NULL）。

## 问题原因

1. **数据生成脚本不生成此字段**：`generate_realistic_data.py` 只生成结构化字段（action, item_id, app_id 等），不生成 `behavior_text`
2. **需要额外转换步骤**：`behavior_text` 是通过 `convert_to_unstructured.py` 脚本从结构化数据转换而来
3. **路径配置错误**：转换脚本中的数据库路径配置错误（`backend/data/graph.db` 应为 `data/graph.db`）

## 解决方案

### 1. 修复转换脚本路径

**文件**：`backend/scripts/convert_to_unstructured.py`

```python
# 修改前
db_path = "backend/data/graph.db"

# 修改后
db_path = "data/graph.db"
```

### 2. 增强转化行为描述

为 `purchase` 和 `add_cart` 添加更清晰的中文描述：

```python
if action == "purchase" and item_id:
    parts.append(f"购买{item_id}")
    if poi_id:
        parts.append(f"在{poi_id}")
elif action == "add_cart" and item_id:
    parts.append(f"将{item_id}加入购物车")
    if app_id:
        parts.append(f"在{app_id}上")
```

### 3. 运行转换脚本

```bash
cd backend
python3 scripts/convert_to_unstructured.py
```

## 转换结果

### 统计信息
- **转换数据量**：48,437 条行为
- **转化行为更新**：120 条（purchase + add_cart）
- **处理时间**：约 30 秒

### behavior_text 格式示例

| 行为类型 | behavior_text 示例 |
|---------|-------------------|
| purchase | 购买长城_WEY VV7 在长城4S店 |
| add_cart | 将长城_哈弗H6加入购物车 在汽车之家上 |
| visit_poi | 在长城4S店停留 1小时28分钟 |
| browse | 浏览长城_WEY VV7 在汽车之家上 62秒 |
| use_app | 使用高德地图 27分钟 |
| search | 搜索长城_哈弗H6 |
| compare | 对比_长城_WEY VV7 使用汽车之家 |

### 完整转化路径示例

```
用户: user_0023 (购买用户)

转化路径（最后20条行为）:
   2025-12-25 07:56:46 | click        | click 长城_WEY VV7_详情页 在易车网上
   2025-12-25 11:56:46 | compare      | compare 对比_长城_WEY VV7 使用汽车之家
   2025-12-25 12:56:46 | compare      | compare 对比_长城_哈弗H9 使用汽车之家
   2025-12-25 16:56:46 | compare      | compare 对比_长城_WEY VV7 使用汽车之家
🎯 2025-12-25 22:56:46 | add_cart     | 将长城_哈弗H6加入购物车 在汽车之家上
🎯 2025-12-26 03:56:46 | visit_poi    | 在长城4S店停留 1小时28分钟
🎯 2025-12-27 02:56:46 | visit_poi    | 在长城4S店停留 1小时58分钟
🎯 2025-12-27 18:56:46 | visit_poi    | 在长城4S店停留 1小时43分钟
🎯 2025-12-28 15:56:46 | visit_poi    | 在长城4S店停留 1小时44分钟
   2025-12-29 00:56:46 | compare      | compare 对比_长城_哈弗H9 使用汽车之家
🎯 2025-12-29 23:56:46 | visit_poi    | 在长城4S店停留 1小时48分钟
🎯 2025-12-30 14:56:46 | add_cart     | 将长城_哈弗H6加入购物车 在汽车之家上
🎯 2025-12-31 11:56:46 | add_cart     | 将长城_WEY VV7加入购物车 在汽车之家上
🎯 2026-01-01 04:56:46 | purchase     | 购买长城_WEY VV7 在长城4S店
🎯 2026-01-01 05:56:46 | add_cart     | 将长城_哈弗H9加入购物车 在汽车之家上
🎯 2026-01-01 06:56:46 | purchase     | 购买长城_哈弗H9 在长城4S店
🎯 2026-01-01 16:56:46 | visit_poi    | 在长城4S店停留 1小时45分钟
🎯 2026-01-01 18:56:46 | visit_poi    | 在长城4S店停留 1小时9分钟
🎯 2026-01-01 22:56:46 | visit_poi    | 在长城4S店停留 1小时21分钟
🎯 2026-01-02 10:56:46 | purchase     | 购买长城_哈弗H9 在长城4S店

转化行为统计:
  add_cart: 4 次
  purchase: 3 次
  visit_poi: 20 次
```

## 验证步骤

### 1. 检查 behavior_text 是否为空

```bash
python3 -c "
import sqlite3
conn = sqlite3.connect('data/graph.db')
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM behavior_data WHERE behavior_text IS NULL OR behavior_text = \"\"')
empty_count = cursor.fetchone()[0]
print(f'空 behavior_text 数量: {empty_count}')
conn.close()
"
```

**预期结果**：0

### 2. 查看转化行为描述

```bash
python3 -c "
import sqlite3
conn = sqlite3.connect('data/graph.db')
cursor = conn.cursor()
cursor.execute('''
    SELECT action, behavior_text
    FROM behavior_data
    WHERE action IN ('purchase', 'add_cart')
    LIMIT 5
''')
for action, text in cursor.fetchall():
    print(f'{action}: {text}')
conn.close()
"
```

**预期结果**：
```
purchase: 购买长城_WEY VV7 在长城4S店
add_cart: 将长城_哈弗H6加入购物车 在汽车之家上
```

## 后续建议

### 1. 自动化转换流程

在数据生成脚本中自动调用转换：

```python
# 在 generate_realistic_data.py 的最后添加
from scripts.convert_to_unstructured import convert_behavior_data
convert_behavior_data()
```

### 2. 数据库表结构优化

考虑在 `persistence.py` 中添加 `behavior_text` 字段定义：

```python
CREATE TABLE IF NOT EXISTS behavior_data (
    ...
    behavior_text TEXT,  -- 添加此字段
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

### 3. 实时生成 behavior_text

在插入行为数据时直接生成 `behavior_text`，而不是事后转换。

## 总结

✅ **问题已解决**：所有 48,437 条行为数据的 `behavior_text` 字段已填充
✅ **转化行为优化**：purchase 和 add_cart 的描述更清晰
✅ **验证通过**：转化路径完整且易读

**下一步**：重新抽取事件数据，验证 LLM 是否能正确识别转化行为。
