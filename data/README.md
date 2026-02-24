# 数据目录说明

## 重要提示

**此目录已废弃，不再使用。**

实际使用的数据库位于：`/home/linxiankun/adsagent/backend/data/graph.db`

## 历史

- `graph.db.backup_old` - 旧数据库备份（2026-02-24），已不再使用
- 后端服务从 `backend/` 目录启动，使用相对路径 `data/graph.db`
- 因此实际数据库路径为 `backend/data/graph.db`

## 如何启动后端

```bash
cd /home/linxiankun/adsagent/backend
python main.py
```

**切勿从项目根目录启动后端**，否则会创建错误的数据库路径。
