# 前端导入路径问题修复

## 问题描述

前端报错：
```
[plugin:vite:import-analysis] Failed to resolve import "@/api" from "src/views/CausalGraphView.vue". Does the file exist?
```

## 问题原因

Vite配置中缺少路径别名`@`的配置，导致无法解析`@/api`这样的导入路径。

## 修复方案

### 1. 更新vite.config.ts

**文件**: `frontend/vite.config.ts`

**修改前**:
```typescript
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  }
})
```

**修改后**:
```typescript
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  }
})
```

### 2. 重启开发服务器

修改配置后，需要重启Vite开发服务器：

```bash
cd frontend

# 停止当前服务器（Ctrl+C）

# 重新启动
npm run dev
```

## 验证修复

### 1. 检查导入是否正常

前端应该能够正常导入API函数：
```javascript
import { listCausalGraphs, getCausalGraph } from '@/api'
```

### 2. 检查API端点

确认后端API端点正常工作：

```bash
# 测试事理图谱列表
curl http://localhost:8000/api/v1/causal-graph/list

# 测试健康检查
curl http://localhost:8000/health
```

### 3. 检查前端页面

访问前端页面，确认没有导入错误：
- http://localhost:5173/causal-graph

## 相关文件

### 前端文件
- `frontend/vite.config.ts` - Vite配置（已修复）
- `frontend/src/api/index.js` - API函数定义
- `frontend/src/views/CausalGraphView.vue` - 事理图谱视图

### 后端文件
- `backend/main.py` - 主应用，注册路由
- `backend/app/api/causal_graph_routes.py` - 事理图谱API路由

## 路径别名说明

配置路径别名后，可以使用以下方式导入：

```javascript
// 使用别名（推荐）
import { listCausalGraphs } from '@/api'
import MyComponent from '@/components/MyComponent.vue'

// 相对路径（不推荐，路径长且容易出错）
import { listCausalGraphs } from '../../api/index.js'
import MyComponent from '../../components/MyComponent.vue'
```

## 常见问题

### Q1: 修改配置后仍然报错？
A: 需要重启Vite开发服务器。配置文件的修改不会热更新。

### Q2: 其他路径别名不工作？
A: 确保在`vite.config.ts`的`resolve.alias`中添加了对应的别名配置。

### Q3: TypeScript报错找不到模块？
A: 如果使用TypeScript，还需要在`tsconfig.json`中配置路径映射：
```json
{
  "compilerOptions": {
    "paths": {
      "@/*": ["./src/*"]
    }
  }
}
```

## 后端API端点

事理图谱相关的API端点：

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/v1/causal-graph/generate | 生成事理图谱 |
| GET | /api/v1/causal-graph/list | 获取图谱列表 |
| GET | /api/v1/causal-graph/{graph_id} | 获取单个图谱 |
| DELETE | /api/v1/causal-graph/{graph_id} | 删除图谱 |
| POST | /api/v1/causal-graph/{graph_id}/query | 图谱问答 |

## 测试步骤

### 1. 启动后端
```bash
cd backend
python main.py
```

### 2. 启动前端
```bash
cd frontend
npm run dev
```

### 3. 访问页面
打开浏览器访问：http://localhost:5173

### 4. 测试功能
- 查看事理图谱列表
- 生成新的事理图谱
- 查看图谱详情
- 进行图谱问答

## 修复状态

✅ **已修复**
- Vite配置已更新，添加了`@`路径别名
- 使用`fileURLToPath`和`import.meta.url`，无需安装额外依赖
- 兼容ES模块规范

## 注意事项

1. **重启服务器**: 修改配置文件后必须重启Vite开发服务器
2. **清除缓存**: 如果仍有问题，尝试清除浏览器缓存或使用无痕模式
3. **检查端口**: 确保前端(5173)和后端(8000)端口没有被占用
4. **检查代理**: Vite配置中的proxy设置确保前端可以访问后端API
