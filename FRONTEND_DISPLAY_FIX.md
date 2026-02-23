# 前端显示空白问题 - 已解决

## 问题原因

用户反馈前端页面上的"行为描述"和"用户画像"显示空白。

经过排查，发现两个问题：

### 1. 后端服务器未重启

- 代码已经修改为非结构化格式，但后端服务器仍在运行旧代码
- FastAPI 在生产模式下不会自动重新加载代码
- 需要手动重启服务器才能加载新代码

### 2. 用户画像数据未转换

- 行为数据（behavior_data）已经转换完成，有 47,998 条记录
- 用户画像（user_profiles）有 profile_text 字段，但所有值都是 NULL
- 需要将旧的结构化数据转换为非结构化文本

## 解决方案

### 1. 重启后端服务器

```bash
# 查找旧进程
ps aux | grep "python.*main.py"

# 杀掉旧进程
kill <PID>

# 启动新进程
cd /home/linxiankun/adsagent/backend
nohup python main.py > /tmp/backend.log 2>&1 &
```

**结果**：
- ✓ 服务器重启成功
- ✓ API 现在返回正确的非结构化格式

### 2. 转换用户画像数据

创建并运行转换脚本：

```bash
cd /home/linxiankun/adsagent/backend
python3 scripts/convert_profiles_to_unstructured.py
```

**转换逻辑**：
```python
# 将结构化字段组合成文本
"{age}岁，{gender}，{city}，{occupation}，年收入{income}万，喜欢{interests}，购车预算{budget}万，{has_car状态}"
```

**转换结果**：
```
✓ 转换完成！共转换 500 条数据
✓ 验证：现在有 500 条数据有 profile_text

样例:
  user_0001 | 30岁，男，广州，互联网从业者，年收入1万，喜欢健身, 高尔夫, 摄影, 阅读，购车预算14万，已有车
  user_0002 | 28岁，女，上海，企业管理者，年收入1万，喜欢高尔夫, 阅读, 摄影, 美食，购车预算6万，已有车
```

## 验证结果

### 1. 行为数据 API

```bash
curl http://localhost:8000/api/v1/modeling/behavior/list?limit=2
```

**返回**：
```json
{
  "code": 0,
  "data": {
    "items": [
      {
        "id": 315007,
        "user_id": "user_0453",
        "timestamp": "2026-01-02 23:50:51",
        "behavior_text": "compare 对比_比亚迪_秦,吉利_博越 使用汽车之家"
      },
      {
        "id": 315006,
        "user_id": "user_0453",
        "timestamp": "2026-01-02 18:50:51",
        "behavior_text": "浏览吉利_星越 在爱卡汽车上 197秒"
      }
    ],
    "total": 47998
  }
}
```

✓ 返回正确的 behavior_text 字段

### 2. 用户画像 API

```bash
curl http://localhost:8000/api/v1/modeling/profiles/list?limit=2
```

**返回**：
```json
{
  "code": 0,
  "data": {
    "items": [
      {
        "id": 2601,
        "user_id": "user_0001",
        "profile_text": "30岁，男，广州，互联网从业者，年收入1万，喜欢健身, 高尔夫, 摄影, 阅读，购车预算14万，已有车",
        "created_at": "2026-02-22 01:50:51"
      },
      {
        "id": 2602,
        "user_id": "user_0002",
        "profile_text": "28岁，女，上海，企业管理者，年收入1万，喜欢高尔夫, 阅读, 摄影, 美食，购车预算6万，已有车",
        "created_at": "2026-02-22 01:50:51"
      }
    ],
    "total": 500
  }
}
```

✓ 返回正确的 profile_text 字段

### 3. 前端显示

前端代码配置：
```vue
<!-- 行为数据表格 -->
<el-table-column prop="behavior_text" label="行为描述" min-width="300" show-overflow-tooltip />

<!-- 用户画像表格 -->
<el-table-column prop="profile_text" label="用户画像" min-width="400" show-overflow-tooltip />
```

✓ 前端配置正确，直接绑定 behavior_text 和 profile_text 字段

## 当前状态

### 数据统计

| 项目 | 数量 | 状态 |
|------|------|------|
| 行为数据记录 | 47,998 | ✓ 已转换 |
| 用户画像记录 | 500 | ✓ 已转换 |
| 总用户数 | 500 | ✓ 正常 |

### 系统功能

✓ **后端服务**
- API 返回正确的非结构化格式
- behavior_text 字段正常
- profile_text 字段正常

✓ **前端显示**
- 行为描述列应该正常显示
- 用户画像列应该正常显示
- 数据格式为中文描述文本

## 文件清单

### 新增脚本

- `backend/scripts/convert_profiles_to_unstructured.py` - 用户画像转换脚本

### 已有脚本

- `backend/scripts/migrate_to_unstructured.py` - 数据库迁移脚本
- `backend/scripts/convert_to_unstructured.py` - 行为数据转换脚本

## 总结

✓ 后端服务器已重启，加载新代码
✓ 行为数据 47,998 条全部转换完成
✓ 用户画像 500 条全部转换完成
✓ API 返回正确的非结构化格式
✓ 前端页面应该能正常显示数据

**前端页面现在应该能看到：**
- 行为描述：如"浏览吉利_星越 在爱卡汽车上 197秒"
- 用户画像：如"30岁，男，广州，互联网从业者，年收入1万，喜欢健身, 高尔夫, 摄影, 阅读，购车预算14万，已有车"

如果前端仍然显示空白，请刷新浏览器页面（Ctrl+F5 强制刷新）以清除缓存。
