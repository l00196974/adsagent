# 广告知识图谱系统

基于用户行为和画像数据构建知识图谱与事理图谱，支撑智能问答和投放策略生成的完整解决方案。

## 📋 目录

- [系统概述](#系统概述)
- [核心功能](#核心功能)
- [系统架构](#系统架构)
- [快速启动](#快速启动)
- [技术栈](#技术栈)
- [目录结构](#目录结构)
- [核心服务](#核心服务)
- [数据模型](#数据模型)
- [API接口](#api接口)
- [配置说明](#配置说明)
- [已知问题](#已知问题)
- [扩展点](#扩展点)
- [贡献指南](#贡献指南)

---

## 系统概述

### 项目背景

广告知识图谱系统是一个基于用户行为数据的智能分析平台，通过构建知识图谱和事理图谱，为广告投放决策提供数据支持和智能洞察。

### 核心价值

- **数据驱动**：支持CSV文件导入，自动识别40+字段类型
- **智能分析**：基于LLM的因果推理和自然语言问答
- **可视化展示**：D3.js驱动的交互式图谱可视化
- **批次管理**：完整的数据导入批次追溯和管理

### 适用场景

- 汽车行业用户画像分析
- 品牌偏好和购买意向预测
- 用户流失分析和挽回策略
- 精准广告投放决策支持

---

## 核心功能

### 1. CSV数据导入

- **多文件上传**：支持同时上传多个CSV文件（最多20个）
- **智能字段识别**：自动识别40+字段类型（中英文、同义词）
- **数据标准化**：自动去重、字段映射、数据清洗
- **批次管理**：完整的导入批次追溯和管理

### 2. 知识图谱构建

- **实体抽取**：User、Interest、Brand、Model四类实体
- **关系建立**：HAS_INTEREST、PREFERS、INTERESTED_IN三类关系
- **权重计算**：基于数据统计的真实权重（非硬编码）
- **批处理模式**：5000实体/批次，10x+性能提升

### 3. 事理图谱生成

- **样本生成**：1:10:5:5比例（正样本:高潜:弱兴趣:对照）
- **因果推理**：基于LLM的因果关系分析
- **置信度评估**：Wilson score interval置信度计算
- **洞察生成**：自动生成关键发现和投放建议

### 4. 智能问答

- **意图识别**：comparison、recommendation、churn_analysis、segment_analysis
- **图谱查询**：基于知识图谱的推理回答
- **自然语言**：LLM驱动的自然语言总结（待实现）

### 5. 图谱可视化

- **交互式展示**：D3.js力导向图
- **实体搜索**：支持按类型和关键词搜索
- **关系扩展**：点击节点展开关联实体
- **AI查询**：自然语言查询图谱

---

## 系统架构

### 整体架构

```
┌─────────────────────────────────────────────────────┐
│              前端 (Vue3 + Element Plus)              │
│  数据导入 | 数据概览 | 图谱可视化 | 智能问答          │
└─────────────────────────────────────────────────────┘
                          │
                          ▼ HTTP/REST API
┌─────────────────────────────────────────────────────┐
│                 后端 (FastAPI)                       │
│  知识图谱服务 | 事理图谱 | 问答引擎 | 批次管理        │
└─────────────────────────────────────────────────────┘
                          │
        ┌─────────────────┴─────────────────┐
        ▼                                   ▼
┌───────────────┐               ┌───────────────────┐
│ 双层数据架构   │               │ LLM API           │
│ NetworkX+SQLite│               │ (OpenAI/Anthropic)│
└───────────────┘               └───────────────────┘
```

### 双层数据架构

**内存层（NetworkX）**
- 知识图谱：MultiDiGraph（支持多重边）
- 事理图谱：DiGraph（有向图）
- 优势：快速查询、图算法支持

**持久层（SQLite）**
- 知识图谱数据：`data/graph.db`
- 导入批次数据：`data/import_data.db`
- 优势：数据持久化、批次追溯

### 请求流模式

```
Frontend → Router → Dependency Injection → Service Layer → GraphDB → Persistence
```

**关键特性**：
- FastAPI依赖注入确保并发安全
- 批处理模式提升性能
- 统一异常处理和日志记录

---

## 快速启动

### 环境要求

- Python 3.8+
- Node.js 16+
- SQLite 3

### 后端启动

```bash
# 1. 安装依赖
cd backend
pip install -r requirements.txt

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入 LLM API Key

# 3. 启动服务
python main.py
# 服务运行在 http://localhost:8000
# API文档: http://localhost:8000/docs
```

### 前端启动

```bash
# 1. 安装依赖
cd frontend
npm install

# 2. 启动开发服务器
npm run dev
# 前端运行在 http://localhost:5173
```

### 验证流程

1. **数据导入**：访问 http://localhost:5173/import
   - 上传 `test_data/` 目录下的CSV文件（必须先上传数据）
   - 查看字段识别结果
   - 点击"构建知识图谱"

2. **图谱可视化**：访问 http://localhost:5173/graph
   - 查看基于CSV数据构建的品牌-兴趣关联图谱
   - 搜索实体并展开关系

3. **智能问答**：访问 http://localhost:5173/qa
   - 输入问题："喜欢打高尔夫的用户是宝马7系高潜还是奔驰S系高潜？"

**注意**：系统完全基于CSV上传的数据,必须先在数据导入页面上传CSV文件后才能使用其他功能。

---

## 技术栈

### 后端技术

| 技术 | 版本 | 用途 |
|------|------|------|
| FastAPI | 0.104+ | Web框架 |
| Pydantic | 2.0+ | 数据验证 |
| NetworkX | 3.0+ | 图数据结构 |
| SQLite | 3.x | 数据持久化 |
| Pandas | 2.0+ | 数据处理 |
| SQLAlchemy | 2.0+ | ORM（待添加） |

### 前端技术

| 技术 | 版本 | 用途 |
|------|------|------|
| Vue 3 | 3.3+ | 前端框架 |
| Element Plus | 2.4+ | UI组件库 |
| D3.js | 7.8+ | 图可视化 |
| Axios | 1.6+ | HTTP客户端 |
| Vue Router | 4.2+ | 路由管理 |
| Pinia | 2.1+ | 状态管理（已安装未使用） |

### LLM集成

- 支持 OpenAI API
- 支持 Anthropic Claude API
- 支持自定义兼容OpenAI格式的API

---

## 目录结构

```
adsagent/
├── backend/                    # 后端代码
│   ├── app/
│   │   ├── api/               # API路由
│   │   │   ├── graph_routes.py      # 知识图谱API
│   │   │   ├── sample_routes.py     # 样本和批次管理API
│   │   │   └── qa_routes.py         # 问答API
│   │   ├── core/              # 核心模块
│   │   │   ├── config.py            # 配置管理
│   │   │   ├── database.py          # 数据库连接
│   │   │   ├── dependencies.py      # 依赖注入
│   │   │   ├── exceptions.py        # 异常定义
│   │   │   ├── logger.py            # 日志系统
│   │   │   ├── graph_db.py          # 图数据库
│   │   │   └── persistence.py       # 持久化层
│   │   ├── services/          # 业务逻辑
│   │   │   ├── knowledge_graph.py   # 知识图谱构建
│   │   │   ├── event_graph.py       # 事理图谱生成
│   │   │   ├── qa_engine.py         # 问答引擎
│   │   │   ├── sample_manager.py    # 样本管理
│   │   │   ├── field_detector.py    # 字段识别
│   │   │   └── import_batch_service.py # 批次管理
│   │   ├── models/            # 数据模型
│   │   │   └── import_data.py       # 导入批次模型
│   │   └── data/              # Mock数据
│   │       └── mock_data.py         # Mock数据生成
│   ├── data/                  # 数据文件
│   │   ├── graph.db                 # 知识图谱数据库
│   │   └── import_data.db           # 批次管理数据库
│   ├── logs/                  # 日志文件
│   │   ├── adsagent.log             # 应用日志
│   │   └── adsagent_error.log       # 错误日志
│   ├── main.py                # 应用入口
│   ├── requirements.txt       # Python依赖
│   ├── llm_config.yaml        # LLM配置
│   └── LLM_CONFIG_README.md   # LLM配置说明
├── frontend/                  # 前端代码
│   ├── src/
│   │   ├── views/            # 页面组件
│   │   │   ├── DataImport.vue      # 数据导入（主入口）
│   │   │   ├── Dashboard.vue       # 数据概览
│   │   │   ├── GraphVisual.vue     # 图谱可视化
│   │   │   ├── Samples.vue         # 样本管理
│   │   │   └── QAChat.vue          # 智能问答
│   │   ├── api/              # API封装
│   │   │   └── index.js            # API客户端
│   │   ├── router/           # 路由配置
│   │   │   └── index.js
│   │   ├── App.vue           # 根组件
│   │   └── main.js           # 应用入口
│   └── package.json          # Node依赖
├── test_data/                # 测试数据
│   ├── 01_user_basic_info.csv
│   ├── 02_user_behavior.csv
│   ├── 03_brand_preference.csv
│   └── 04_ad_location_data.csv
├── CLAUDE.md                 # Claude Code项目指南
├── CSV_IMPORT_GUIDE.md       # CSV导入使用指南
└── README.md                 # 本文档
```

---

## 核心服务

### KnowledgeGraphBuilder

**功能**：从CSV上传的用户行为数据构建知识图谱

**关键方法**：
- `build_from_csv_data(users)`: 从CSV数据构建图谱（主要方法）
- `get_progress()`: 获取构建进度

**批处理模式**：
```python
BATCH_SIZE = 5000  # 每批处理5000个用户
# 使用 batch_create_entities() 和 batch_create_relations()
# 性能提升10x+
```

**数据来源**：完全基于CSV上传的真实数据,不再使用Mock数据

**文件位置**：[backend/app/services/knowledge_graph.py](backend/app/services/knowledge_graph.py)

### EventGraphBuilder

**功能**：从CSV数据生成事理图谱（因果关系图）

**关键方法**：
- `build_from_real_data(users)`: 从CSV数据生成事理图谱（主要方法）

**样本比例**：1:10:5:5（正样本:高潜:弱兴趣:对照）

**数据来源**：完全基于CSV上传的真实数据

**文件位置**：[backend/app/services/event_graph.py](backend/app/services/event_graph.py)

### QAEngine

**功能**：自然语言问答引擎

**意图类型**：
- `comparison`: 品牌/车型对比
- `recommendation`: 投放策略推荐
- `churn_analysis`: 流失分析
- `segment_analysis`: 用户分群分析

**文件位置**：[backend/app/services/qa_engine.py](backend/app/services/qa_engine.py)

### FieldDetector

**功能**：智能字段识别器

**支持字段**：40+字段类型
- 基础信息：user_id, age, gender, education, income_level
- 资产信息：has_house, has_car, phone_price
- 家庭信息：marital_status, has_children, commute_distance
- 兴趣行为：interests, behaviors
- 品牌偏好：primary_brand, primary_model, brand_score
- APP行为：app_open_count, app_usage_duration
- 汽车行为：car_search_count, car_browse_count, car_compare_count
- 广告数据：push_exposure, push_click, ad_exposure, ad_click

**文件位置**：[backend/app/services/field_detector.py](backend/app/services/field_detector.py)

### ImportBatchService

**功能**：导入批次管理服务

**关键方法**：
- `create_batch()`: 创建导入批次
- `list_batches()`: 获取批次列表
- `get_batch()`: 获取批次详情
- `get_batch_users()`: 获取批次用户数据
- `delete_batch()`: 删除批次

**文件位置**：[backend/app/services/import_batch_service.py](backend/app/services/import_batch_service.py)

---

## 数据模型

### 知识图谱模型

**实体类型**：
- `User`: 用户实体（user_id, age, gender, income_level等）
- `Interest`: 兴趣实体（name）
- `Brand`: 品牌实体（name）
- `Model`: 车型实体（name, brand）

**关系类型**：
- `HAS_INTEREST`: User → Interest（权重：0.9）
- `PREFERS`: User → Brand（权重：基于brand_score）
- `INTERESTED_IN`: User → Model（权重：brand_score * 0.9）

**权重计算**：
```python
# 基于数据统计的真实权重
interest_weight = min(0.9, 0.3 + (count/total_users)*2)
brand_weight = brand_score
model_weight = brand_score * 0.9
```

### 事理图谱模型

**节点类型**：
- 偏好特征：用户兴趣、品牌偏好
- 行为特征：APP使用、汽车搜索
- 转化结果：高购买意向、低购买意向
- 流失原因：缺乏触发点、价格敏感

**边属性**：
- `relation`: 关系描述
- `probability`: 转化概率
- `confidence`: 置信度（Wilson score interval）

### 导入批次模型

**ImportBatch表**：
```python
id: Integer (主键)
batch_name: String (批次名称)
batch_time: DateTime (导入时间)
file_count: Integer (文件数量)
record_count: Integer (记录数量)
unique_record_count: Integer (去重后记录数量)
file_info: JSON (文件信息列表)
status: String (completed/failed)
```

**ImportedUser表**：
```python
id: Integer (主键)
batch_id: Integer (外键)
user_id: String (用户ID)
# ... 40+字段
raw_data: JSON (原始完整数据)
```

---

## API接口

### 知识图谱API

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/v1/graphs/knowledge/build-from-csv` | POST | 构建知识图谱（CSV数据） |
| `/api/v1/graphs/knowledge/query` | GET | 查询图谱 |
| `/api/v1/graphs/knowledge/search` | GET | 搜索实体 |
| `/api/v1/graphs/knowledge/expand/{entity_id}` | GET | 展开实体关系 |
| `/api/v1/graphs/knowledge/ai-query` | POST | AI智能查询 |
| `/api/v1/graphs/knowledge/types` | GET | 获取实体类型 |
| `/api/v1/graphs/knowledge/stats` | GET | 获取图谱统计 |

### 样本和批次管理API

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/v1/samples/import-csv` | POST | 导入单个CSV |
| `/api/v1/samples/import-batch` | POST | 批量导入CSV |
| `/api/v1/samples/list` | GET | 获取样本列表 |
| `/api/v1/samples/batches` | GET | 获取批次列表 |
| `/api/v1/samples/batches/{batch_id}` | GET | 获取批次详情 |
| `/api/v1/samples/batches/{batch_id}/users` | GET | 获取批次用户数据 |
| `/api/v1/samples/batches/{batch_id}` | DELETE | 删除批次 |

### 问答和事理图谱API

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/v1/qa/query` | POST | 智能问答 |
| `/api/v1/qa/event-graph/build-from-csv` | POST | 生成事理图谱（CSV数据） |

### 统一响应格式

```json
{
  "code": 0,
  "data": { ... },
  "message": "操作成功"
}
```

---

## 配置说明

### 环境变量配置

创建 `backend/.env` 文件：

```bash
# LLM API配置
LLM_PROVIDER=openai
LLM_API_KEY=your-api-key-here
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4

# 应用配置
APP_HOST=0.0.0.0
APP_PORT=8000

# 日志配置
LOG_LEVEL=INFO
```

### LLM配置

详见 [backend/LLM_CONFIG_README.md](backend/LLM_CONFIG_README.md)

支持的提供商：
- OpenAI
- Anthropic Claude
- Azure OpenAI
- 自定义兼容OpenAI格式的API

---

## 已知问题

### 🔴 高危问题（P0）

1. **CSV上传安全漏洞**
   - 位置：[backend/app/api/sample_routes.py](backend/app/api/sample_routes.py)
   - 问题：仅检查文件扩展名，无文件大小限制
   - 影响：可能导致内存溢出或恶意代码执行

2. **错误信息泄露**
   - 位置：多个API路由
   - 问题：返回完整异常堆栈给客户端
   - 影响：可能泄露系统结构和敏感信息

3. **URL参数注入**
   - 位置：[frontend/src/api/index.js](frontend/src/api/index.js)
   - 问题：直接拼接用户输入到URL
   - 影响：可能导致URL注入攻击

### 🟡 中等问题（P1）

1. **N+1查询问题**
   - 位置：[backend/app/services/knowledge_graph.py](backend/app/services/knowledge_graph.py)
   - 问题：内层循环重复查询所有实体
   - 影响：性能随数据量指数级下降

2. **前端状态管理缺失**
   - 位置：前端所有页面
   - 问题：页面间数据不共享，导入数据切换页面后丢失
   - 影响：用户体验差，需要重新导入数据

3. **事件监听器内存泄漏**
   - 位置：[frontend/src/views/GraphVisual.vue](frontend/src/views/GraphVisual.vue)
   - 问题：resize监听器未在组件卸载时移除
   - 影响：长时间使用可能导致内存泄漏

### 🟢 低优先级问题（P2）

1. **代码重复**：关键字提取逻辑重复
2. **过长函数**：ai_graph_query函数77行
3. **魔法数字**：硬编码的权重值

详细问题清单见：[C:\Users\HUAWEI\.claude\plans\glittery-meandering-eclipse.md](C:\Users\HUAWEI\.claude\plans\glittery-meandering-eclipse.md)

---

## 扩展点

### 1. 图数据库集成

**当前**：NetworkX + SQLite
**扩展**：Neo4j / NebulaGraph

**优势**：
- 更强大的图查询能力（Cypher查询语言）
- 更好的性能（大规模图数据）
- 原生图算法支持

**实施步骤**：
1. 更新 [backend/app/core/graph_db.py](backend/app/core/graph_db.py)
2. 添加Neo4j驱动依赖
3. 实现Neo4j适配器

### 2. 数据源扩展

**当前**：Mock数据 + CSV导入
**扩展**：ClickHouse / MySQL / PostgreSQL

**优势**：
- 实时数据接入
- 大规模数据处理
- 数据仓库集成

**实施步骤**：
1. 修改 [backend/app/data/mock_data.py](backend/app/data/mock_data.py)
2. 添加数据源客户端
3. 实现数据同步逻辑

### 3. LLM提供商切换

**当前**：配置文件支持，但未实现客户端
**扩展**：完整的LLM客户端实现

**实施步骤**：
1. 创建 [backend/app/core/llm_client.py](backend/app/core/llm_client.py)
2. 实现统一的LLM接口
3. 支持多提供商切换

### 4. 缓存层添加

**当前**：无缓存
**扩展**：Redis缓存

**优势**：
- 查询结果缓存
- 会话状态管理
- 分布式锁

**实施步骤**：
1. 创建 `backend/app/core/cache.py`
2. 添加Redis客户端
3. 包装频繁访问的查询

---

## 贡献指南

### 开发流程

1. Fork本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启Pull Request

### 代码规范

**Python**：
- 遵循PEP 8规范
- 使用类型注解
- 编写文档字符串

**JavaScript**：
- 遵循ESLint规则
- 使用Vue 3 Composition API
- 组件命名使用PascalCase

### 测试要求

- 单元测试覆盖率 > 80%
- 所有API端点需要集成测试
- 前端组件需要单元测试

---

## 许可证

本项目采用 MIT 许可证。详见 LICENSE 文件。

---

## 联系方式

如有问题或建议，请通过以下方式联系：

- 提交 Issue
- 发送 Pull Request
- 邮件联系：[your-email@example.com]

---

## 致谢

感谢以下开源项目：

- [FastAPI](https://fastapi.tiangolo.com/)
- [Vue.js](https://vuejs.org/)
- [NetworkX](https://networkx.org/)
- [D3.js](https://d3js.org/)
- [Element Plus](https://element-plus.org/)

---

**最后更新**：2026-02-13
