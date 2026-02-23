# CSV导入模板使用说明

## 核心设计理念

**最小结构化原则**：只有必需的字段是结构化的，其他所有信息都以非结构化文本形式存储。

---

## 1. 行为数据模板（behavior_data_template.csv）

### 必需列（结构化字段）

| 列名 | 类型 | 说明 | 示例 |
|------|------|------|------|
| user_id | 文本 | 用户ID | user_001 |
| event_time | 日期时间 | 事件发生时间 | 2026-02-22 10:00:00 |

**时间格式**：`YYYY-MM-DD HH:MM:SS`

### 可选列（非结构化字段）

以下列都会被打包到`event_data`中，可以根据需要添加或删除：

| 列名 | 类型 | 说明 | 示例 |
|------|------|------|------|
| action | 文本 | 行为类型 | browse, search, click, purchase |
| item | 文本 | 物品/车型 | 宝马5系 |
| duration | 整数 | 持续时间（秒） | 120 |
| app | 文本 | APP名称 | 汽车之家 |
| media | 文本 | 媒体名称 | 易车网 |
| poi | 文本 | 地点名称 | 宝马4S店 |
| price | 整数 | 价格 | 450000 |
| page_url | 文本 | 页面URL | https://... |

**重要提示**：
- 可以添加任意自定义列，无需修改数据库结构
- 空值可以留空或不填
- 所有可选列都会被打包到`event_data`中

### 行为类型说明

| 行为类型 | 说明 | 常用字段 |
|---------|------|---------|
| browse | 浏览内容 | item, duration, media |
| search | 搜索 | item(搜索词), app |
| click | 点击 | item, media |
| compare | 对比 | item(多个，逗号分隔), app |
| use_app | 使用APP | app, duration |
| visit_poi | 访问地点 | poi, duration |
| add_cart | 加购 | item, app, price |
| purchase | 购买 | item, poi, price |

---

## 2. 用户画像模板（user_profiles_template.csv）

### 必需列（结构化字段）

| 列名 | 类型 | 说明 | 示例 |
|------|------|------|------|
| user_id | 文本 | 用户ID | user_001 |

### 可选列（非结构化字段）

以下列都会被打包到`profile_data`中：

| 列名 | 类型 | 说明 | 示例 |
|------|------|------|------|
| age | 整数 | 年龄 | 35 |
| gender | 文本 | 性别 | 男/女 |
| income | 整数 | 月收入（元） | 25000 |
| occupation | 文本 | 职业 | 互联网从业者 |
| city | 文本 | 城市 | 上海 |
| interests | 文本 | 兴趣爱好（逗号分隔） | 高尔夫,旅游,科技 |
| education | 文本 | 学历 | 本科/硕士/博士 |
| marital_status | 文本 | 婚姻状况 | 已婚/未婚 |
| has_car | 文本 | 是否有车 | 是/否 |
| purchase_intent | 文本 | 购车意向 | 首购/换车/增购/观望 |
| budget | 文本 | 购车预算 | 40-50万 |

**重要提示**：
- 可以添加任意自定义列
- 所有可选列都会被打包到`profile_data`中

---

## 3. 导入方式

### 方式1：通过API导入

```bash
# 导入行为数据
curl -X POST http://localhost:8000/api/v1/flexible-import/behavior-data \
  -F "file=@behavior_data.csv"

# 导入用户画像
curl -X POST http://localhost:8000/api/v1/flexible-import/user-profiles \
  -F "file=@user_profiles.csv"
```

### 方式2：通过Python脚本导入

```python
from app.services.flexible_csv_importer import FlexibleCSVImporter

importer = FlexibleCSVImporter()

# 导入行为数据
result = importer.import_behavior_data('behavior_data.csv')
print(f"成功: {result['success']}, 失败: {result['error']}")

# 导入用户画像
result = importer.import_user_profiles('user_profiles.csv')
print(f"成功: {result['success']}, 失败: {result['error']}")
```

---

## 4. 数据格式示例

### 导入前（CSV格式）

```csv
user_id,event_time,action,item,duration,app
user_001,2026-02-22 10:00:00,browse,宝马5系,120,汽车之家
```

### 导入后（数据库存储）

```json
{
  "user_id": "user_001",
  "event_time": "2026-02-22 10:00:00",
  "event_data": "{\"action\": \"browse\", \"item\": \"宝马5系\", \"duration\": 120, \"app\": \"汽车之家\"}"
}
```

### 查询时（自动解析）

```python
events = persistence.query_behavior_events(user_id='user_001', parse=True)
# event['event_data'] = {'action': 'browse', 'item': '宝马5系', 'duration': 120, 'app': '汽车之家'}
```

---

## 5. 常见问题

### Q: 可以添加自定义列吗？
A: 可以！除了必需列外，可以添加任意自定义列，它们会自动打包到`event_data`或`profile_data`中。

### Q: 空值如何处理？
A: 空值可以留空或不填，导入时会自动忽略。

### Q: 文件编码要求？
A: 建议使用UTF-8或UTF-8-BOM编码，确保中文正常显示。

### Q: 可以导入多少数据？
A: 系统支持10W+用户规模，批量导入速度约77,519条/秒。

### Q: 如何验证导入结果？
A: 导入后会返回成功和失败的数量，也可以通过查询API验证数据。

---

## 6. 下载模板

### 通过API下载

```bash
# 下载行为数据模板
curl -O http://localhost:8000/api/v1/flexible-import/template/behavior-data

# 下载用户画像模板
curl -O http://localhost:8000/api/v1/flexible-import/template/user-profiles
```

### 通过脚本生成

```bash
cd backend
python scripts/generate_csv_templates.py
```

模板文件会生成在 `data/templates/` 目录下。

---

## 7. 最佳实践

1. **保持字段命名一致**：统一使用`action`而不是混用`action`和`event_type`
2. **使用标准时间格式**：`YYYY-MM-DD HH:MM:SS`
3. **批量导入**：一次导入大量数据比多次导入小批量数据更高效
4. **验证数据**：导入后验证数据完整性和正确性
5. **备份数据**：导入前备份现有数据

---

## 8. 技术支持

如有问题，请查看：
- 完整文档：`FLEXIBLE_DATA_STRUCTURE_GUIDE.md`
- 性能优化报告：`PERFORMANCE_OPTIMIZATION_REPORT.md`
