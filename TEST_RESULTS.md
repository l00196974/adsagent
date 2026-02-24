# 目标导向序列挖掘测试报告

## 测试时间
2026-02-24 10:10

## 测试环境
- 后端服务：✅ 运行中 (http://localhost:8000)
- 数据库：✅ 已准备 (500用户, 48,437行为)
- event_category 列：✅ 已添加

## 测试结果

### ✅ 成功的部分

1. **数据生成** - 完成
   - 500个用户
   - 48,437条行为
   - 120条转化行为 (purchase + add_cart)
   - behavior_text 100%填充

2. **数据库迁移** - 完成
   - event_category 列已添加
   - 表结构正确

3. **事件抽取** - 部分成功
   - 单用户抽取正常 (user_0023, 161个事件)
   - 抽取速度：约2分钟/用户

### ❌ 失败的部分

**核心问题：LLM 未正确识别转化行为**

#### 问题详情

**原始数据**（user_0023）：
```
2025-12-25 22:56:46 | add_cart  | 将长城_哈弗H6加入购物车 在汽车之家上
2025-12-30 14:56:46 | add_cart  | 将长城_哈弗H6加入购物车 在汽车之家上
2025-12-31 11:56:46 | add_cart  | 将长城_WEY VV7加入购物车 在汽车之家上
2026-01-01 04:56:46 | purchase  | 购买长城_WEY VV7 在长城4S店
2026-01-01 05:56:46 | add_cart  | 将长城_哈弗H9加入购物车 在汽车之家上
2026-01-01 06:56:46 | purchase  | 购买长城_哈弗H9 在长城4S店
2026-01-02 10:56:46 | purchase  | 购买长城_哈弗H9 在长城4S店
```

**LLM 抽取结果**：
```
所有事件都被抽象为"使用APP"
所有事件都被标注为 engagement
转化事件数：0
```

#### 根本原因

1. **LLM 过度抽象**：将 "购买长城_WEY VV7 在长城4S店" 抽象为 "使用APP"
2. **未识别关键词**：prompt 中要求识别 purchase/add_cart，但 LLM 没有执行
3. **默认分类问题**：所有事件默认为 engagement

## 解决方案

### 方案1：增强 Prompt（推荐）

**当前 prompt 问题**：
- 提示词太长，LLM 可能忽略关键指令
- 没有明确示例说明如何识别转化行为
- 没有强调"必须保留原始 action 字段"

**改进建议**：

```python
prompt = f"""
【重要】你必须识别并保留转化行为！

原始数据中的 action 字段包含：
- purchase（购买）→ 必须抽取为"购买"事件，标注为 conversion
- add_cart（加购）→ 必须抽取为"加购"事件，标注为 conversion  
- visit_poi（到店）→ 必须抽取为"到店"事件，标注为 conversion

【示例】
原始行为：action=purchase, behavior_text="购买长城_WEY VV7 在长城4S店"
正确抽取：user_001|购买|2026-01-01 04:56:46|长城_WEY VV7,长城4S店|conversion

原始行为：action=add_cart, behavior_text="将长城_哈弗H6加入购物车 在汽车之家上"
正确抽取：user_001|加购|2025-12-25 22:56:46|长城_哈弗H6,汽车之家|conversion

【用户行为数据】
{user_behaviors_str}

【输出格式】
用户ID|事件类型|时间戳|上下文信息|事件分类
"""
```

### 方案2：基于规则的后处理

在事件抽取后，基于原始 action 字段补充分类：

```python
# 在保存事件时
if original_action == 'purchase':
    event_category = 'conversion'
    event_type = '购买'
elif original_action == 'add_cart':
    event_category = 'conversion'
    event_type = '加购'
elif original_action == 'visit_poi' and 'S店' in poi_id:
    event_category = 'conversion'
    event_type = '到店'
```

### 方案3：两阶段抽取

1. **第一阶段**：LLM 抽取事件类型
2. **第二阶段**：规则引擎标注事件分类

## 推荐行动

### 立即执行（方案2）

使用规则后处理，因为：
- 实现简单，不依赖 LLM
- 100%准确
- 不需要重新调整 prompt

### 中期优化（方案1）

优化 prompt，让 LLM 学会识别转化行为

### 长期方案（方案3）

建立完整的事件分类体系

## 当前状态

- ✅ 数据准备完成
- ✅ 代码实现完成
- ❌ LLM 识别失败
- ⏸️  测试暂停

## 下一步

1. 实现方案2（规则后处理）
2. 重新抽取 user_0023
3. 验证转化事件识别
4. 测试目标导向挖掘
