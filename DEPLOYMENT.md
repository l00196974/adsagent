# 部署指南

## 系统要求

### 必需软件
- Python 3.11+
- Node.js 18+
- npm 或 yarn

### Linux系统依赖

Ubuntu/Debian:
```bash
sudo apt update
sudo apt install python3-venv python3-pip
```

CentOS/RHEL:
```bash
sudo yum install python3-venv python3-pip
```

### macOS系统依赖
```bash
# 使用Homebrew
brew install python@3.11 node
```

### Windows系统依赖
- 从 python.org 下载安装Python 3.11+（确保勾选"Add Python to PATH"）
- 从 nodejs.org 下载安装Node.js 18+

## 开发环境部署

### 后端

```bash
cd backend

# 创建虚拟环境（首次部署）
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate  # Linux/macOS
# 或 venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑.env文件，设置OPENAI_API_KEY（必需）

# 验证配置
python -c "from app.core.config import settings; print(f'配置成功: {settings.primary_model}')"

# 启动服务
python main.py
```

访问 http://localhost:8000 查看API文档

**注意**:
- 首次启动会自动创建数据库文件 `data/graph.db`
- 如果看到 "ValueError: OPENAI_API_KEY environment variable is required"，说明需要在 `.env` 文件中设置有效的API密钥

### 前端

```bash
cd frontend
npm install
npm run dev
```

访问 http://localhost:5173

## 生产环境部署

### 使用Docker Compose (推荐)

1. 配置环境变量

```bash
cp .env.example .env
# 编辑.env设置生产配置
```

2. 启动服务

```bash
docker-compose up -d
```

3. 查看日志

```bash
docker-compose logs -f
```

4. 停止服务

```bash
docker-compose down
```

### 手动部署

#### 后端

```bash
cd backend

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# 或 venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 安装生产服务器（gunicorn）
pip install gunicorn

# 配置环境变量
cp .env.example .env
# 编辑.env设置生产配置

# 使用gunicorn启动生产服务器
gunicorn main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

#### 前端

```bash
cd frontend
npm run build
# 将dist目录部署到nginx/apache
```

Nginx配置示例:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    root /path/to/frontend/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## 环境变量配置

### 必需配置

- `OPENAI_API_KEY`: LLM API密钥 (必需)
- `OPENAI_BASE_URL`: API地址 (默认: https://api.minimaxi.com/v1)

### 可选配置

- `PRIMARY_MODEL`: 主模型 (默认: MiniMax-M2.1)
- `REASONING_MODEL`: 推理模型 (默认: MiniMax-M2.1)
- `MAX_LLM_WORKERS`: 并发数 (默认: 4，可根据API限制调整)
- `MAX_TOKENS_PER_REQUEST`: Token限制 (默认: 30000，生产环境可配置为204800)
- `APP_HOST`: 服务器绑定地址 (默认: 0.0.0.0)
- `APP_PORT`: 服务器端口 (默认: 8000)

## 数据备份

### 备份数据库

```bash
# 备份
cp backend/data/graph.db backup/graph_$(date +%Y%m%d).db

# 恢复
cp backup/graph_20260301.db backend/data/graph.db
```

### 自动备份脚本

```bash
#!/bin/bash
# backup.sh
BACKUP_DIR="/path/to/backup"
DATE=$(date +%Y%m%d_%H%M%S)
cp /home/linxiankun/adsagent/backend/data/graph.db "$BACKUP_DIR/graph_$DATE.db"

# 保留最近7天的备份
find "$BACKUP_DIR" -name "graph_*.db" -mtime +7 -delete
```

添加到crontab (每天凌晨2点备份):

```bash
0 2 * * * /path/to/backup.sh
```

## 监控与日志

### 日志位置

- 应用日志: `backend/logs/adsagent.log`
- 错误日志: `backend/logs/adsagent_error.log`

### 日志查看

```bash
# 实时查看日志
tail -f backend/logs/adsagent.log

# 查看错误日志
tail -f backend/logs/adsagent_error.log

# 搜索特定错误
grep "ERROR" backend/logs/adsagent.log
```

### 监控指标

建议监控以下指标:

- API响应时间
- LLM调用成功率
- 数据库查询性能
- 内存使用情况
- 磁盘空间使用

## 性能调优

### 数据库优化

启用WAL模式提升并发性能:

```bash
sqlite3 backend/data/graph.db "PRAGMA journal_mode=WAL;"
```

### 并发配置

根据API限制调整 `MAX_LLM_WORKERS`:

- 免费API: 2-4
- 付费API: 4-8
- 企业API: 8-16

### 缓存优化

系统已实现内存缓存，无需额外配置。如需分布式缓存，可考虑引入Redis。

## 安全检查清单

- [ ] API密钥使用环境变量，不提交到代码库
- [ ] 生产环境禁用调试模式
- [ ] 配置防火墙规则，只开放必要端口
- [ ] 定期备份数据库
- [ ] 监控日志异常
- [ ] 使用HTTPS加密传输
- [ ] 限制文件上传大小 (已配置100MB)
- [ ] 定期更新依赖包

## 故障排查

### 后端无法启动

1. 检查环境变量是否正确配置
2. 检查端口是否被占用: `lsof -i :8000`
3. 检查日志: `tail -f backend/logs/adsagent.log`

### LLM调用失败

1. 检查API密钥是否有效
2. 检查API配额是否用尽
3. 检查网络连接
4. 查看错误日志获取详细信息

### 数据库锁定

如果遇到数据库锁定错误:

```bash
# 检查是否有其他进程在使用数据库
lsof backend/data/graph.db

# 如果确认没有其他进程，删除WAL文件
rm backend/data/graph.db-wal
rm backend/data/graph.db-shm
```

### 前端无法连接后端

1. 检查后端是否正常运行
2. 检查Vite代理配置
3. 检查CORS配置
4. 使用浏览器开发者工具查看网络请求

## 升级指南

### 升级步骤

1. 备份数据库
2. 拉取最新代码
3. 更新依赖
4. 运行数据库迁移 (如有)
5. 重启服务
6. 验证功能

### 回滚步骤

1. 停止服务
2. 恢复代码到上一版本
3. 恢复数据库备份
4. 重启服务

## 常见问题

### Q: 如何更换LLM提供商?

A: 修改 `.env` 中的 `OPENAI_BASE_URL` 和 `OPENAI_API_KEY`，确保新提供商兼容OpenAI API格式。

### Q: 如何扩展到多个用户?

A: 当前系统为演示版本，支持100个用户。如需扩展，需要:
1. 优化数据库查询
2. 增加LLM并发数
3. 考虑使用PostgreSQL替代SQLite
4. 添加用户认证和权限管理

### Q: 如何提高LLM响应速度?

A:
1. 增加 `MAX_LLM_WORKERS` 提高并发
2. 使用更快的模型
3. 优化prompt减少token消耗
4. 添加响应缓存

## 常见部署问题

### Python虚拟环境相关

**问题**: `error: externally-managed-environment`
**原因**: 现代Linux系统不允许直接使用pip安装包
**解决**: 使用虚拟环境
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**问题**: `ensurepip is not available`
**原因**: 系统缺少python3-venv包
**解决**:
```bash
# Ubuntu/Debian
sudo apt install python3-venv

# CentOS/RHEL
sudo yum install python3-venv
```

### 环境变量相关

**问题**: `ValueError: OPENAI_API_KEY environment variable is required`
**原因**: 未配置API密钥或.env文件未生效
**解决**:
1. 确认.env文件存在于backend目录
2. 确认OPENAI_API_KEY已设置且不为空
3. 重启后端服务

### 依赖安装相关

**问题**: `ModuleNotFoundError: No module named 'gunicorn'`
**原因**: 生产部署时未安装gunicorn
**解决**: `pip install gunicorn`

**问题**: 虚拟环境激活后仍然提示找不到模块
**原因**: 可能在错误的虚拟环境中安装了依赖
**解决**:
```bash
# 确认当前使用的是正确的虚拟环境
which python
# 应该显示 /path/to/backend/venv/bin/python

# 如果不对，重新激活虚拟环境
deactivate
source venv/bin/activate
pip install -r requirements.txt
```

## 技术支持

如遇到问题，请:

1. 查看日志文件获取详细错误信息
2. 检查本文档的故障排查章节
3. 查看项目README和CLAUDE.md
4. 提交Issue到项目仓库
