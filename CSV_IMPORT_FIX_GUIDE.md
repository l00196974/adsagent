# CSV导入功能修复说明

## 问题诊断

### 原始问题
用户在"基础建模"页面点击"导入CSV"时报错：**"上传失败,请检查文件格式"**

### 根本原因
1. **后端服务未启动** - 最主要的原因
2. **前端错误提示不友好** - 没有显示具体的错误信息
3. **后端缺少输入验证** - 没有检查文件格式和必需字段

## 修复内容

### 1. 启动后端服务
```bash
cd /home/linxiankun/adsagent/backend
python main.py
```

验证服务是否启动：
```bash
curl http://localhost:8000/health
# 应返回: {"status":"ok","message":"广告知识图谱系统运行中"}
```

### 2. 改进前端错误处理

**文件**: [frontend/src/views/BaseModeling.vue](file:///home/linxiankun/adsagent/frontend/src/views/BaseModeling.vue)

**改进内容**:
- 添加详细的错误信息解析
- 区分不同类型的错误（连接失败、格式错误、服务器错误等）
- 显示具体的错误详情给用户

**改进后的错误处理**:
```javascript
const handleUploadError = (error) => {
  console.error('上传失败', error)
  
  let errorMessage = '上传失败,请检查文件格式'
  
  if (error.response) {
    const response = error.response
    if (response.data && response.data.detail) {
      errorMessage = `上传失败: ${response.data.detail}`
    } else if (response.status === 422) {
      errorMessage = '文件格式错误，请确保上传CSV文件'
    } else if (response.status === 500) {
      errorMessage = '服务器处理失败，请查看后端日志'
    } else if (response.status === 0) {
      errorMessage = '无法连接到服务器，请检查后端是否启动'
    }
  } else if (error.message) {
    errorMessage = `上传失败: ${error.message}`
  }
  
  ElMessage.error(errorMessage)
}
```

### 3. 增强后端验证

**文件**: [backend/app/api/base_modeling_routes.py](file:///home/linxiankun/adsagent/backend/app/api/base_modeling_routes.py)

**改进内容**:
- 添加文件格式验证（必须为.csv）
- 添加CSV解析错误处理
- 验证必需字段（user_id, action, timestamp）
- 提供详细的错误提示

**改进后的验证逻辑**:
```python
@router.post("/behavior/import")
async def import_behavior_data(file: UploadFile = File(...)):
    """导入行为数据CSV"""
    try:
        # 1. 文件格式验证
        if not file.filename.endswith('.csv'):
            raise HTTPException(status_code=400, detail="文件格式错误，请上传CSV文件")

        # 2. CSV解析错误处理
        try:
            content = await file.read()
            df = pd.read_csv(io.BytesIO(content))
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"CSV文件解析失败: {str(e)}")

        # 3. 必需字段验证
        required_columns = ['user_id', 'action', 'timestamp']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise HTTPException(
                status_code=400, 
                detail=f"CSV文件缺少必需列: {', '.join(missing_columns)}。当前列: {', '.join(df.columns)}"
            )
        
        # ... 其余导入逻辑
```

## CSV文件格式要求

### 行为数据 (behavior_data)

**必需字段**:
- `user_id` - 用户ID
- `action` - 行为类型（如：click, view, purchase等）
- `timestamp` - 时间戳

**可选字段**:
- `item_id` - 商品ID
- `app_id` - APP ID
- `media_id` - 媒体ID
- `poi_id` - POI ID
- `duration` - 时长（秒）
- `properties` - 其他属性（JSON格式）

**示例CSV**:
```csv
user_id,action,timestamp,item_id,app_id,media_id,poi_id,duration
U000001,click,2026-02-20 10:00:00,item_001,app_001,media_001,poi_001,30
U000001,view,2026-02-20 10:05:00,item_002,app_002,media_002,poi_002,60
U000002,purchase,2026-02-20 11:10:00,item_004,app_003,media_002,poi_001,120
```

### APP标签 (app_tags)

**必需字段**:
- `app_id` - APP ID
- `app_name` - APP名称

**可选字段**:
- `category` - 分类
- `tags` - 标签（JSON数组格式）

### 媒体标签 (media_tags)

**必需字段**:
- `media_id` - 媒体ID
- `media_name` - 媒体名称

**可选字段**:
- `media_type` - 媒体类型
- `tags` - 标签（JSON数组格式）

### 用户画像 (user_profiles)

**必需字段**:
- `user_id` - 用户ID

**可选字段**:
- `age` - 年龄
- `gender` - 性别
- `city` - 城市
- `occupation` - 职业
- `properties` - 其他属性（JSON格式）

## 测试验证

### 1. 测试成功导入
```bash
# 使用测试文件
curl -X POST "http://localhost:8000/api/v1/modeling/behavior/import" \
  -F "file=@/home/linxiankun/adsagent/test_data/behavior_test.csv"

# 预期返回
{"code":0,"message":"成功导入 5 条行为数据","data":{"total_count":5,"columns":[...]}}
```

### 2. 测试错误处理
```bash
# 测试缺少必需字段
curl -X POST "http://localhost:8000/api/v1/modeling/behavior/import" \
  -F "file=@/home/linxiankun/adsagent/test_data/behavior_error.csv"

# 预期返回详细的错误信息
{"code":500,"message":"导入失败: CSV文件缺少必需列: timestamp..."}
```

### 3. 查询导入的数据
```bash
curl "http://localhost:8000/api/v1/modeling/behavior/list?limit=10"
```

## 常见错误及解决方案

### 1. "无法连接到服务器，请检查后端是否启动"
**原因**: 后端服务未启动
**解决**: 
```bash
cd backend
python main.py
```

### 2. "文件格式错误，请确保上传CSV文件"
**原因**: 上传的文件不是CSV格式
**解决**: 确保文件扩展名为.csv

### 3. "CSV文件缺少必需列: xxx"
**原因**: CSV文件缺少必需的字段
**解决**: 参考上面的CSV格式要求，添加必需字段

### 4. "CSV文件解析失败"
**原因**: CSV文件格式不正确（如编码问题、分隔符问题等）
**解决**: 
- 确保CSV文件使用UTF-8编码
- 确保使用逗号作为分隔符
- 检查是否有特殊字符

### 5. "服务器处理失败，请查看后端日志"
**原因**: 后端处理过程中出现异常
**解决**: 
```bash
# 查看后端日志
tail -f backend/logs/adsagent.log
tail -f backend/logs/adsagent_error.log
```

## 后续改进建议

### 1. 添加数据预览功能
- 在导入前显示CSV前几行数据
- 让用户确认字段映射

### 2. 支持更多文件格式
- Excel文件（.xlsx）
- JSON文件

### 3. 批量导入优化
- 支持大文件分块上传
- 显示导入进度条
- 支持断点续传

### 4. 数据验证增强
- 数据类型验证
- 数据范围验证
- 重复数据检测

### 5. 导入历史记录
- 记录每次导入的文件名、时间、记录数
- 支持查看导入历史
- 支持回滚导入的数据

## 相关文件

- 前端页面: [frontend/src/views/BaseModeling.vue](file:///home/linxiankun/adsagent/frontend/src/views/BaseModeling.vue)
- 后端路由: [backend/app/api/base_modeling_routes.py](file:///home/linxiankun/adsagent/backend/app/api/base_modeling_routes.py)
- 后端服务: [backend/app/services/base_modeling.py](file:///home/linxiankun/adsagent/backend/app/services/base_modeling.py)
- 数据库初始化: [backend/app/core/persistence.py](file:///home/linxiankun/adsagent/backend/app/core/persistence.py)

## 日志文件位置

- 应用日志: `backend/logs/adsagent.log`
- 错误日志: `backend/logs/adsagent_error.log`

---

**修复时间**: 2026-02-20  
**修复版本**: v1.0.1
