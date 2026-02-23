# 事理图谱功能问题诊断与修复

## 问题现象

1. **前端报错**: 无法解析`@/api`导入
2. **查看图谱报错**: API调用失败
3. **生成图谱报错**: API调用失败

## 问题诊断

### 问题1: 前端路径别名未配置

**症状**:
```
[plugin:vite:import-analysis] Failed to resolve import "@/api" from "src/views/CausalGraphView.vue"
```

**原因**: Vite配置缺少`@`路径别名

**修复**: ✅ 已修复 `frontend/vite.config.ts`

### 问题2: 后端服务器未重启

**症状**: API返回404或旧版本响应

**原因**: 代码更新后未重启后端服务器

**修复**: 需要重启后端

## 完整修复步骤

### 步骤1: 停止后端服务器

```bash
# 查找后端进程
ps aux | grep "python.*main.py" | grep -v grep

# 停止进程（替换PID）
kill <PID>

# 或者如果在终端运行，直接Ctrl+C
```

### 步骤2: 重启后端服务器

```bash
cd /home/linxiankun/adsagent/backend
python main.py
```

**预期输出**:
```
2026-02-22 XX:XX:XX - adsagent - INFO - 初始化数据库...
2026-02-22 XX:XX:XX - adsagent - INFO - 数据库初始化完成
2026-02-22 XX:XX:XX - adsagent - INFO - 启动广告知识图谱系统 - 0.0.0.0:8000
INFO:     Started server process [XXXXX]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

### 步骤3: 验证后端API

```bash
# 测试健康检查
curl http://localhost:8000/health

# 预期输出: {"status":"ok","message":"广告知识图谱系统运行中"}

# 测试根路径
curl http://localhost:8000/

# 预期输出应包含: "causal_graph": "/api/v1/causal-graph"

# 测试事理图谱列表
curl http://localhost:8000/api/v1/causal-graph/list

# 预期输出: {"graphs": [...], "total": ...}
```

### 步骤4: 重启前端服务器

```bash
cd /home/linxiankun/adsagent/frontend

# 停止当前服务器（Ctrl+C）

# 重新启动
npm run dev
```

**预期输出**:
```
VITE v5.x.x  ready in XXX ms

➜  Local:   http://localhost:5173/
➜  Network: use --host to expose
➜  press h + enter to show help
```

### 步骤5: 验证前端

打开浏览器访问：http://localhost:5173

1. 打开浏览器开发者工具（F12）
2. 查看Console，确认没有导入错误
3. 访问事理图谱页面
4. 测试查看图谱和生成图谱功能

## 验证清单

### 后端验证

- [ ] 后端服务器成功启动
- [ ] 健康检查API正常: `curl http://localhost:8000/health`
- [ ] 根路径包含causal_graph端点
- [ ] 事理图谱列表API正常: `curl http://localhost:8000/api/v1/causal-graph/list`
- [ ] API文档可访问: http://localhost:8000/docs

### 前端验证

- [ ] 前端服务器成功启动
- [ ] 浏览器Console无导入错误
- [ ] 可以访问事理图谱页面
- [ ] 可以查看图谱列表
- [ ] 可以生成新图谱
- [ ] 可以查看图谱详情
- [ ] 可以进行图谱问答

## 常见问题

### Q1: 后端启动失败

**可能原因**:
- 端口8000被占用
- 数据库文件损坏
- 依赖包未安装

**解决方案**:
```bash
# 检查端口占用
lsof -i :8000

# 重新安装依赖
cd backend
pip install -r requirements.txt

# 检查数据库
ls -lh data/graph.db
```

### Q2: 前端启动失败

**可能原因**:
- 端口5173被占用
- node_modules损坏
- 依赖包未安装

**解决方案**:
```bash
# 检查端口占用
lsof -i :5173

# 重新安装依赖
cd frontend
rm -rf node_modules
npm install
```

### Q3: API调用404

**可能原因**:
- 后端未重启
- 路由未正确注册
- URL路径错误

**解决方案**:
1. 重启后端服务器
2. 检查main.py中的路由注册
3. 检查API URL是否正确

### Q4: 前端导入错误

**可能原因**:
- Vite配置未更新
- 前端未重启
- 缓存问题

**解决方案**:
1. 确认vite.config.ts已更新
2. 重启前端服务器
3. 清除浏览器缓存或使用无痕模式

## 文件修改记录

### 已修改文件

1. **frontend/vite.config.ts**
   - 添加了`@`路径别名配置
   - 使用`fileURLToPath`和`import.meta.url`

### 未修改文件（已验证正确）

1. **backend/main.py**
   - 路由注册正确
   - 包含causal_graph_routes

2. **backend/app/api/causal_graph_routes.py**
   - API端点定义正确
   - 路由前缀为`/causal-graph`

3. **frontend/src/api/index.js**
   - API函数定义正确
   - 包含所有事理图谱相关函数

4. **frontend/src/views/CausalGraphView.vue**
   - 导入语句正确
   - 使用`@/api`路径

## 快速修复命令

```bash
# 1. 停止所有服务
pkill -f "python.*main.py"
pkill -f "vite"

# 2. 启动后端（在新终端）
cd /home/linxiankun/adsagent/backend
python main.py

# 3. 启动前端（在新终端）
cd /home/linxiankun/adsagent/frontend
npm run dev

# 4. 验证
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/causal-graph/list
```

## 预期结果

修复完成后：

1. ✅ 前端无导入错误
2. ✅ 后端API正常响应
3. ✅ 可以查看事理图谱列表
4. ✅ 可以生成新的事理图谱
5. ✅ 可以查看图谱详情
6. ✅ 可以进行图谱问答

## 技术支持

如果问题仍然存在，请检查：

1. **日志文件**:
   - 后端日志: `backend/logs/adsagent.log`
   - 后端错误日志: `backend/logs/adsagent_error.log`

2. **浏览器Console**: 查看详细错误信息

3. **网络请求**: 使用浏览器开发者工具的Network标签查看API请求

4. **数据库**: 确认数据库文件存在且可访问
   ```bash
   ls -lh /home/linxiankun/adsagent/backend/data/graph.db
   ```
