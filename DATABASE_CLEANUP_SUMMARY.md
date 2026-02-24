# 数据库清理总结

## 执行时间
2026-02-24

## 问题描述
项目中存在两个 `graph.db` 数据库文件：
1. `/home/linxiankun/adsagent/data/graph.db` (196KB, 旧数据)
2. `/home/linxiankun/adsagent/backend/data/graph.db` (61MB, 实际使用)

由于后端服务从 `backend/` 目录启动，所有代码使用相对路径 `"data/graph.db"`，因此实际使用的是 `backend/data/graph.db`。

## 执行的操作

### 1. 备份旧数据库
```bash
mv /home/linxiankun/adsagent/data/graph.db \
   /home/linxiankun/adsagent/data/graph.db.backup_old
```

### 2. 创建说明文档
在 `/home/linxiankun/adsagent/data/README.md` 中说明该目录已废弃。

### 3. 更新文档
- 更新 `CLAUDE.md` 中的数据库位置说明
- 明确指出必须从 `backend/` 目录启动后端服务

### 4. 修复脚本
修复了以下脚本中的数据库路径问题：
- `test_target_mining.sh` - 改为从 `backend/` 目录运行
- `verify_implementation.sh` - 改为从 `backend/` 目录访问数据库

### 5. 验证的脚本（已正确）
以下脚本已经正确配置：
- `backend/start.sh` - 正确 cd 到 backend 目录
- `run_tests.sh` - 正确 cd 到 backend 目录

## 当前状态

### 活跃数据库
- **路径**: `/home/linxiankun/adsagent/backend/data/graph.db`
- **大小**: 61MB
- **内容**:
  - 3465 个提取的事件
  - 33 个用户的事件序列
  - 完整的知识图谱数据

### 备份数据库
- **路径**: `/home/linxiankun/adsagent/data/graph.db.backup_old`
- **大小**: 196KB
- **状态**: 已备份，不再使用

## 重要提醒

### 启动后端服务
**必须从 backend 目录启动**：
```bash
cd /home/linxiankun/adsagent/backend
python main.py
```

**或使用启动脚本**：
```bash
bash /home/linxiankun/adsagent/backend/start.sh
```

### 不要这样做
❌ 从项目根目录启动：
```bash
cd /home/linxiankun/adsagent
python backend/main.py  # 错误！会使用错误的数据库路径
```

## 验证
后端服务正常运行，数据访问正确：
- Health check: ✓
- Event stats: 3465 events, 33 users ✓
- Database path: `/home/linxiankun/adsagent/backend/data/graph.db` ✓

## 相关修复
同时修复了高频子序列挖掘的两个bug：
1. 索引错误：截取序列时使用了错误的索引
2. 缓存bug：缓存键不包含 target_event/target_category 参数
