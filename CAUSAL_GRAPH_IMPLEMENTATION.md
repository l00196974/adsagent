# 事理图谱功能实现说明

## 概述

本次实现了完整的事理图谱生成和查看功能，包括后端服务、API接口和前端页面。

## 已实现的功能

### 后端实现

#### 1. 数据库表结构 (`backend/app/core/persistence.py`)

新增了三个表：

- **causal_graphs**: 存储事理图谱的元数据和完整数据
  - 字段：id, graph_name, analysis_focus, source_pattern_ids, total_users, total_patterns, graph_data, insights, created_at, updated_at

- **causal_graph_nodes**: 存储事理图谱的节点
  - 字段：id, graph_id, node_id, node_type, node_name, description, properties

- **causal_graph_edges**: 存储事理图谱的边
  - 字段：id, graph_id, from_node_id, to_node_id, relation_type, relation_desc, probability, confidence, condition, support_count, properties

#### 2. 事理图谱服务 (`backend/app/services/causal_graph_service.py`)

核心方法：

- `generate_from_patterns()`: 基于高频模式生成事理图谱
  - 加载高频模式数据
  - 提取用户示例和画像
  - 构建LLM Prompt
  - 调用LLM生成图谱
  - 解析JSON结果
  - 保存到数据库

- `get_graph_by_id()`: 获取指定的事理图谱
- `list_graphs()`: 获取事理图谱列表（支持分页）
- `delete_graph()`: 删除事理图谱
- `answer_question_with_graph()`: 基于事理图谱回答问题

#### 3. API路由 (`backend/app/api/causal_graph_routes.py`)

端点：

- `POST /api/v1/causal-graph/generate`: 生成事理图谱
- `GET /api/v1/causal-graph/list`: 获取图谱列表
- `GET /api/v1/causal-graph/{graph_id}`: 获取指定图谱
- `DELETE /api/v1/causal-graph/{graph_id}`: 删除图谱
- `POST /api/v1/causal-graph/{graph_id}/query`: 基于图谱问答

### 前端实现

#### 1. API客户端 (`frontend/src/api/index.js`)

新增方法：

- `generateCausalGraph()`: 生成事理图谱
- `listCausalGraphs()`: 获取图谱列表
- `getCausalGraph()`: 获取指定图谱
- `deleteCausalGraph()`: 删除图谱
- `queryCausalGraph()`: 基于图谱问答
- `listFrequentPatterns()`: 获取高频模式列表

#### 2. 事理图谱生成页面 (`frontend/src/views/CausalGraphGeneration.vue`)

功能模块：

- **模式选择区域**: 显示所有高频模式，支持多选、全选、清空
- **生成配置区域**: 配置图谱名称、分析重点、使用模式
- **生成进度区域**: 显示生成进度和当前步骤
- **生成结果预览**: 显示节点数、边数、关键洞察

#### 3. 事理图谱查看页面 (`frontend/src/views/CausalGraphView.vue`)

功能模块：

- **左侧边栏**: 图谱列表，支持选择和删除
- **中间主区域**: 使用D3.js绘制力导向图
  - 节点样式：事件（蓝色圆形）、特征（绿色圆形）、结果（红色圆形）
  - 边样式：顺承（灰色实线）、因果（蓝色粗实线）、条件（橙色虚线）
  - 支持缩放、拖拽、节点拖动
- **右侧边栏**: 显示图谱基本信息和关键洞察
- **底部抽屉**: AI问答功能，支持示例问题

#### 4. 路由和导航 (`frontend/src/router/index.js`, `frontend/src/App.vue`)

新增路由：

- `/causal-graph/generate`: 事理图谱生成页面
- `/causal-graph/view/:graphId?`: 事理图谱查看页面

导航菜单新增"事理图谱"子菜单。

## 使用流程

### 1. 生成事理图谱

1. 访问"事理图谱 > 生成图谱"页面
2. 选择要使用的高频模式（或选择"使用所有模式"）
3. 配置图谱名称和分析重点
4. 点击"生成事理图谱"按钮
5. 等待生成完成，查看结果预览
6. 点击"查看详情"跳转到查看页面

### 2. 查看事理图谱

1. 访问"事理图谱 > 查看图谱"页面
2. 从左侧列表选择一个图谱
3. 在中间区域查看图谱可视化
4. 在右侧查看图谱信息和洞察
5. 点击右下角浮动按钮打开AI问答

### 3. AI问答

1. 在查看页面点击右下角浮动按钮
2. 输入问题或点击示例问题
3. 查看AI基于图谱数据的回答

## 技术要点

### LLM Prompt设计

Prompt包含以下部分：

1. **高频模式数据**: 模式序列、支持度、用户数
2. **用户示例**: 用户ID、行为序列、用户画像
3. **分析重点**: 综合分析/转化分析/流失分析/画像分析
4. **输出格式**: JSON格式，包含nodes、edges、insights
5. **关系类型说明**: sequential/causal/conditional

### JSON解析鲁棒性

- 移除MiniMax的`<think>`标签
- 移除markdown代码块标记
- 提取最大的完整JSON对象
- 验证必需字段

### 图谱可视化

- 使用D3.js力导向布局算法
- 节点颜色区分类型
- 边的粗细表示概率
- 边的样式区分关系类型
- 支持缩放、拖拽、节点拖动

## 待优化项

1. **性能优化**
   - 大规模图谱（100+节点）的渲染性能
   - 节点聚合功能
   - 局部展开/收起

2. **功能增强**
   - 图谱编辑功能
   - 导出为图片/PDF
   - 多版本对比
   - 实时更新

3. **用户体验**
   - 加载动画优化
   - 错误提示优化
   - 操作引导

## 测试建议

### 后端测试

```bash
# 测试数据库初始化
python -c "from backend.app.core.persistence import persistence; print('OK')"

# 启动后端服务
cd backend
python main.py

# 测试API端点
curl http://localhost:8000/api/v1/causal-graph/list
```

### 前端测试

```bash
# 安装依赖
cd frontend
npm install

# 启动开发服务器
npm run dev

# 访问页面
# http://localhost:5173/causal-graph/generate
# http://localhost:5173/causal-graph/view
```

### 集成测试

1. 确保有高频模式数据（通过"高频子序列挖掘"页面生成）
2. 生成事理图谱
3. 查看图谱可视化
4. 测试AI问答功能

## 注意事项

1. **LLM API配置**: 确保`.env`文件中配置了正确的`OPENAI_API_KEY`和`OPENAI_BASE_URL`
2. **数据依赖**: 需要先有高频模式数据才能生成事理图谱
3. **超时设置**: 生成事理图谱的API调用超时设置为120秒
4. **浏览器兼容性**: 图谱可视化需要现代浏览器支持（Chrome/Firefox/Edge）

## 文件清单

### 后端文件

- `backend/app/core/persistence.py`: 数据库表结构和持久化方法
- `backend/app/services/causal_graph_service.py`: 事理图谱服务
- `backend/app/api/causal_graph_routes.py`: API路由
- `backend/main.py`: 注册路由

### 前端文件

- `frontend/src/api/index.js`: API客户端方法
- `frontend/src/views/CausalGraphGeneration.vue`: 生成页面
- `frontend/src/views/CausalGraphView.vue`: 查看页面
- `frontend/src/router/index.js`: 路由配置
- `frontend/src/App.vue`: 导航菜单

## 总结

本次实现完成了事理图谱功能的核心流程，包括：

1. ✅ 数据库表结构设计和实现
2. ✅ 后端服务和API接口
3. ✅ 前端生成和查看页面
4. ✅ 图谱可视化（D3.js）
5. ✅ AI问答功能
6. ✅ 路由和导航集成

系统已经可以正常使用，后续可以根据实际使用情况进行优化和功能增强。
