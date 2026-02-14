# CSV数据导入使用说明

## 概述

广告知识图谱系统现在支持通过CSV文件导入真实用户行为数据。系统会自动识别字段并构建知识图谱和事理图谱。

## 系统架构

**新的工作流程：**
1. **数据导入** (`/import`) - 上传CSV文件作为主入口
2. **数据概览** (`/`) - 查看统计信息
3. **图谱可视化** (`/graph`) - 查看知识图谱
4. **样本管理** (`/samples`) - 管理训练样本
5. **智能问答** (`/qa`) - 基于图谱的智能问答

## 测试数据文件

系统提供了4个测试CSV文件，位于 `test_data/` 目录：

### 1. 基础用户信息 (`01_user_basic_info.csv`)
包含用户的基本人口统计信息：
- `user_id` - 用户ID
- `age` - 年龄
- `gender` - 性别
- `education` - 学历
- `income_level` - 收入水平
- `city` - 城市
- `occupation` - 职业
- `marital_status` - 婚姻状况
- `has_children` - 是否有孩子
- `has_house` - 是否有房
- `has_car` - 是否有车
- `phone_price` - 手机价格区间

### 2. 用户行为数据 (`02_user_behavior.csv`)
包含用户的行为数据：
- `user_id` - 用户ID
- `commute_distance` - 通勤距离（公里）
- `interests` - 兴趣爱好（逗号分隔）
- `app_open_count` - APP打开次数
- `app_usage_duration` - APP使用时长（秒）
- `miniprogram_open_count` - 小程序打开次数
- `car_search_count` - 汽车搜索次数
- `car_browse_count` - 汽车浏览次数
- `car_compare_count` - 汽车比价次数
- `car_app_payment` - 是否在汽车APP付费
- `consumption_frequency` - 消费频率（每月）

### 3. 品牌偏好数据 (`03_brand_preference.csv`)
包含用户的品牌偏好信息：
- `user_id` - 用户ID
- `primary_brand` - 主要关注品牌
- `primary_model` - 主要关注车型
- `brand_score` - 品牌偏好分数（0-1）
- `purchase_intent` - 购买意向（高/中/低/弱）
- `lifecycle_stage` - 生命周期阶段（转化/意向/考虑/认知）

### 4. 广告与位置数据 (`04_ad_location_data.csv`)
包含广告曝光和位置信息：
- `user_id` - 用户ID
- `push_exposure` - PUSH消息曝光次数
- `push_click` - PUSH消息点击次数
- `ad_exposure` - 广告曝光次数
- `ad_click` - 广告点击次数
- `near_4s_store` - 是否在4S店附近
- `weather_info` - 天气信息

## 使用步骤

### 1. 启动服务

**后端服务：**
```bash
cd backend
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**前端服务：**
```bash
cd frontend
npm run dev
```

### 2. 导入CSV数据

1. 访问 http://localhost:5173/import
2. 拖拽或点击上传CSV文件（可以上传多个文件）
3. 点击"开始导入"按钮
4. 系统会自动识别字段并显示识别结果

### 3. 构建知识图谱

导入成功后：
1. 点击"构建知识图谱"按钮
2. 系统会基于真实数据构建知识图谱
3. 构建完成后可以查看统计信息

### 4. 生成事理图谱

1. 点击"生成事理图谱"按钮
2. 系统会分析用户行为并生成事理图谱
3. 查看关键洞察和投放建议

### 5. 查看结果

- **数据概览** (`/`) - 查看用户数、实体数、关系数等统计信息
- **图谱可视化** (`/graph`) - 可视化查看知识图谱
- **智能问答** (`/qa`) - 基于图谱进行智能问答

## 支持的字段（40+）

系统支持自动识别以下字段类型：

### 基础信息
- user_id, age, gender, education, income_level, city, occupation

### 资产信息
- has_house, has_car, phone_price

### 家庭信息
- marital_status, has_children, commute_distance

### 兴趣行为
- interests, behaviors

### 品牌车型
- primary_brand, primary_model, brand_score

### 购买意向
- purchase_intent, intent_score, lifecycle_stage

### APP行为
- app_open_count, app_usage_duration, miniprogram_open_count

### 汽车行为
- car_search_count, car_browse_count, car_compare_count, car_app_payment

### 广告数据
- push_exposure, push_click, ad_exposure, ad_click

### 位置天气
- near_4s_store, location_history, weather_info

### 消费行为
- consumption_frequency

## 字段识别规则

系统使用智能字段识别器，支持：
1. **精确匹配** - 标准字段名直接识别
2. **模糊匹配** - 相似字段名自动映射
3. **中英文识别** - 支持中文和英文字段名
4. **同义词识别** - 自动识别常见同义词

例如：
- `年龄` → `age`
- `性别` → `gender`
- `收入` → `income_level`
- `兴趣爱好` → `interests`

## 数据要求

1. **文件格式**：CSV格式，UTF-8编码
2. **文件大小**：单个文件最大10MB
3. **文件数量**：单次最多上传20个文件
4. **必需字段**：至少包含 `user_id` 字段
5. **数据去重**：系统会自动根据 `user_id` 去重合并

## 注意事项

1. **后端服务重启**：如果API返回404错误，请重启后端服务
2. **字段命名**：建议使用标准字段名以提高识别准确率
3. **数据质量**：确保CSV文件格式正确，避免特殊字符
4. **浏览器兼容**：建议使用Chrome或Edge浏览器

## 示例问答

导入数据并构建图谱后，可以尝试以下问题：

1. "喜欢打高尔夫的用户是宝马7系高潜还是奔驰S系高潜？"
2. "高收入人群对豪华轿车的品牌偏好是什么？"
3. "什么样的用户容易流失？"
4. "针对商务人士应该投放哪些素材？"

## 故障排除

### 问题1：API返回404错误
**解决方案**：重启后端服务
```bash
# 停止当前后端进程
# 重新启动
cd backend
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 问题2：字段识别不准确
**解决方案**：
1. 检查CSV文件的字段名是否规范
2. 使用标准字段名（参考上面的支持字段列表）
3. 确保CSV文件使用UTF-8编码

### 问题3：前端页面无法加载
**解决方案**：
1. 检查前端服务是否正常运行
2. 清除浏览器缓存
3. 检查浏览器控制台是否有错误信息

## 技术架构

- **后端**：FastAPI + Python 3.14
- **前端**：Vue 3 + Element Plus + Vite
- **数据库**：SQLite (data/graph.db)
- **图谱引擎**：NetworkX
- **字段识别**：自定义字段检测器（支持40+字段）

## 更新日志

### 2026-02-12
- ✅ 修复前端导入错误（`doGenerateSamples` → `generateSamples`）
- ✅ 添加 `onUnmounted` 导入到 GraphVisual.vue
- ✅ 调整系统架构：DataImport 作为主入口
- ✅ 重写 Dashboard 为纯统计展示页面
- ✅ 创建测试CSV文件和使用文档
