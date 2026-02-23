# CSV测试数据说明

## 文件位置

生成的CSV文件位于：`backend/data/csv_export/`

- **用户画像**: `user_profiles.csv` (501行，包含表头)
- **行为数据**: `behavior_data.csv` (46,037行，包含表头)

## 数据统计

- **用户数**: 500
- **总行为数**: 46,036
- **平均行为数**: 92.1条/用户
- **购买用户数**: 15 (3.0%)
- **购买行为数**: 55

## 文件格式

### 1. user_profiles.csv（用户画像）

**字段说明**:

| 字段名 | 类型 | 说明 | 示例 |
|--------|------|------|------|
| user_id | 字符串 | 用户ID | user_0001 |
| age | 整数 | 年龄 | 40 |
| gender | 字符串 | 性别 | 男/女 |
| income | 整数 | 月收入（元） | 37068 |
| occupation | 字符串 | 职业 | 企业管理者 |
| city | 字符串 | 城市 | 上海 |
| interests | 字符串 | 兴趣（逗号分隔） | 高尔夫,健身,美食,阅读 |
| budget | 整数 | 购车预算（万元） | 23 |
| has_car | 字符串 | 是否有车 | 是/否 |
| purchase_intent | 字符串 | 购车意向 | 首购/换车/增购/观望/无 |

**示例数据**:
```csv
user_id,age,gender,income,occupation,city,interests,budget,has_car,purchase_intent
user_0001,40,男,37068,企业管理者,上海,"高尔夫,健身,美食,阅读",23,是,无
user_0002,25,女,13410,企业管理者,上海,"美食,科技",12,是,无
user_0003,37,男,34487,教师,南京,"阅读,音乐,旅游,摄影,高尔夫",32,否,首购
```

### 2. behavior_data.csv（行为数据）

**字段说明**:

| 字段名 | 类型 | 说明 | 示例 |
|--------|------|------|------|
| user_id | 字符串 | 用户ID | user_0001 |
| action | 字符串 | 行为类型 | browse/search/click/compare/use_app/visit_poi/add_cart/purchase |
| timestamp | 字符串 | 时间戳 | 2025-11-24 10:42:47 |
| item_id | 字符串 | 物品ID（车型、搜索词等） | 大众_迈腾 |
| app_id | 字符串 | APP名称 | 汽车之家 |
| media_id | 字符串 | 媒体名称 | 易车网 |
| poi_id | 字符串 | POI名称 | 宝马4S店 |
| duration | 整数 | 持续时间（秒） | 129 |

**行为类型说明**:

- **browse**: 浏览内容（需要media_id和item_id）
- **search**: 搜索（需要app_id和item_id）
- **click**: 点击（需要media_id和item_id）
- **compare**: 对比（需要app_id和item_id）
- **use_app**: 使用APP（需要app_id）
- **visit_poi**: 访问POI（需要poi_id）
- **add_cart**: 加购（需要app_id和item_id）
- **purchase**: 购买（需要item_id和poi_id）

**示例数据**:
```csv
user_id,action,timestamp,item_id,app_id,media_id,poi_id,duration
user_0001,browse,2025-11-24 10:42:47,大众_迈腾,,易车网,,129
user_0001,search,2025-11-24 21:42:47,大众迈腾,汽车之家,,,
user_0001,visit_poi,2025-11-25 07:42:47,,,,XX高尔夫俱乐部,3689
user_0001,purchase,2025-12-15 18:30:00,宝马_5系,,,宝马4S店,
```

## 数据特点

### 1. 真实的用户画像分布

- **年龄**: 25-50岁，集中在30-40岁（60%）
- **收入**: 8,000-50,000元/月，根据年龄段分布
- **职业**: 互联网、金融、企业管理、医生、教师、工程师等
- **城市**: 一二线城市（北上广深杭等）
- **兴趣**: 高尔夫、旅游、科技、健身、摄影等

### 2. 符合逻辑的行为序列

行为序列模拟了真实的汽车购买决策过程：

**兴趣萌芽阶段** (25-35%):
- 浏览汽车资讯
- 使用相关APP
- 访问高尔夫球场、商务会所等

**信息收集阶段** (35-45%):
- 搜索车型信息
- 浏览评测文章
- 点击车型详情

**对比评估阶段** (20-30%):
- 对比不同品牌和车型
- 访问4S店
- 深度浏览配置和价格

**决策购买阶段** (0-10%，仅转化用户):
- 多次访问4S店
- 加购车型
- 最终购买

### 3. 品牌选择逻辑

根据用户收入和预算匹配品牌：

- **高收入（≥20,000元/月）**: 宝马、奔驰、奥迪、雷克萨斯
- **中等收入（≥12,000元/月）**: 大众、丰田、本田
- **一般收入（≥8,000元/月）**: 吉利、比亚迪、长城

### 4. 真实的转化率

- **首购/换车**: 12%转化率
- **增购**: 8%转化率
- **观望**: 3%转化率
- **无意向**: 0.5%转化率
- **总体转化率**: 约3%

## 导入测试

### 方式1：通过前端导入

1. 启动后端服务：
```bash
cd backend
python main.py
```

2. 启动前端服务：
```bash
cd frontend
npm run dev
```

3. 访问前端页面，使用CSV导入功能

### 方式2：通过API导入

```bash
# 导入用户画像
curl -X POST http://localhost:8000/api/v1/samples/import-csv \
  -F "file=@data/csv_export/user_profiles.csv" \
  -F "data_type=user_profile"

# 导入行为数据
curl -X POST http://localhost:8000/api/v1/samples/import-csv \
  -F "file=@data/csv_export/behavior_data.csv" \
  -F "data_type=behavior"
```

### 方式3：直接运行Python脚本导入数据库

如果CSV导入功能有问题，可以直接运行：
```bash
cd backend
python scripts/generate_realistic_data.py
```

这会直接将数据写入数据库，跳过CSV导入步骤。

## 验证数据

导入后可以验证数据：

```bash
# 查看用户数
sqlite3 data/graph.db "SELECT COUNT(DISTINCT user_id) FROM behavior_data"

# 查看行为数
sqlite3 data/graph.db "SELECT COUNT(*) FROM behavior_data"

# 查看购买用户数
sqlite3 data/graph.db "SELECT COUNT(DISTINCT user_id) FROM behavior_data WHERE action='purchase'"

# 查看各行为类型分布
sqlite3 data/graph.db "SELECT action, COUNT(*) FROM behavior_data GROUP BY action"
```

## 后续使用

导入数据后，可以进行：

1. **事件抽象**: 使用LLM将原始行为抽象为高层次事件
2. **高频子序列挖掘**: 挖掘用户行为的高频模式
3. **事理图谱生成**: 基于高频模式生成因果关系图谱
4. **智能问答**: 基于图谱回答业务问题

## 注意事项

1. **编码格式**: CSV文件使用UTF-8-BOM编码，确保中文正常显示
2. **空字段**: 某些字段可能为空（如browse行为没有app_id）
3. **时间范围**: 行为数据时间跨度为90天（从当前时间往前推）
4. **数据一致性**: 用户画像和行为数据通过user_id关联

## 生成脚本

如需重新生成CSV文件：

```bash
cd backend
python scripts/generate_csv_data.py
```

可以修改脚本中的`num_users`参数来生成不同数量的用户数据。
