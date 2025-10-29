# 任务控制按钮可见性调试指南

## 🔍 问题
在分析任务运行中，还是看不到暂停和停止按钮。

## 🛠️ 调试步骤

我已经添加了详细的调试信息，请按以下步骤排查问题：

### 步骤1：启动分析任务

1. 打开Web界面
2. 填写分析表单
3. 点击"🚀 开始分析"按钮
4. 等待任务启动

### 步骤2：查看调试信息

在"开始分析"按钮下方，您应该能看到以下调试信息之一：

#### 情况A：有分析ID
```
🔍 调试：分析ID = analysis_xxxxx_20250128_xxxxx
🔍 调试：任务状态 = 'running'
✅ 调试：条件满足，应该显示按钮！状态=running
────────────────────────
🎮 任务控制
[⏸️ 暂停分析] [⏹️ 停止分析]
```

**说明：** 这是正常情况，按钮应该显示。

#### 情况B：没有分析ID
```
🔍 调试：没有找到 current_analysis_id
```

**原因：** `st.session_state.current_analysis_id` 为空或None

**解决：**
1. 检查任务是否真的启动了
2. 查看日志确认 `current_analysis_id` 是否被设置
3. 刷新页面，看状态是否恢复

#### 情况C：状态不匹配
```
🔍 调试：分析ID = analysis_xxxxx_20250128_xxxxx
🔍 调试：任务状态 = 'completed'
⚠️ 调试：状态 'completed' 不在 ['running', 'paused'] 中
```

**原因：** 任务状态不是 'running' 或 'paused'

**可能的状态：**
- `completed` - 任务已完成
- `failed` - 任务失败
- `stopped` - 任务已停止
- `not_found` - 线程未找到

**说明：** 按钮只在 running 或 paused 状态显示，这是正常的

#### 情况D：获取状态失败
```
🔍 调试：分析ID = analysis_xxxxx_20250128_xxxxx
❌ 调试：获取状态失败 - [错误信息]
```

**原因：** `check_analysis_status` 函数抛出异常

**解决：**
1. 查看完整的错误信息
2. 检查 `utils/thread_tracker.py` 是否正常
3. 查看应用日志

### 步骤3：根据调试信息采取措施

#### 如果看到"没有找到 current_analysis_id"

**检查项：**
```python
# 在浏览器控制台或日志中查找：
- "🚀 [后台分析] 分析线程已启动: analysis_xxxx"
- "📊 [状态检查] 分析 xxxx 实际状态: running"
```

**可能原因：**
1. 任务启动失败
2. `current_analysis_id` 没有正确保存到 session_state
3. 页面刷新导致 session_state 丢失

**解决方法：**
```python
# 在 app.py 中检查这行是否执行：
st.session_state.current_analysis_id = analysis_id
```

#### 如果看到状态为 'not_found'

**原因：** 线程跟踪器中没有找到对应的分析线程

**检查项：**
```python
# 在日志中查找：
- "🧵 [后台分析] 分析线程已启动: xxxx"
- "🧵 [线程清理] 分析线程和任务控制已注销: xxxx"
```

**可能原因：**
1. 线程已经结束但状态没有更新
2. 线程注册失败
3. 线程被意外清理

**解决方法：**
1. 检查 `register_analysis_thread` 是否被调用
2. 确认线程是否还在运行
3. 清理僵尸状态：点击侧边栏的"🧹 清理分析状态"

## 📊 预期的正常流程

### 1. 任务启动
```
用户点击"开始分析"
    ↓
设置 st.session_state.current_analysis_id = "analysis_xxx"
    ↓
启动后台线程
    ↓
注册线程跟踪：register_analysis_thread(analysis_id, thread)
    ↓
页面刷新
```

### 2. 页面刷新后
```
render_analysis_form() 被调用
    ↓
form_current_analysis_id = st.session_state.get('current_analysis_id')
    ↓
显示调试信息："分析ID = xxx"
    ↓
actual_status = check_analysis_status(form_current_analysis_id)
    ↓
显示调试信息："任务状态 = 'running'"
    ↓
if actual_status in ['running', 'paused']:  # True
    ↓
显示任务控制按钮
```

## 🔧 临时修复

如果按钮确实应该显示但没显示，可以尝试：

### 方法1：刷新页面
直接刷新浏览器 (F5 或 Ctrl+R)

### 方法2：清理状态
点击侧边栏的"🧹 清理分析状态"按钮

### 方法3：检查浏览器控制台
1. 打开浏览器开发者工具 (F12)
2. 查看 Console 标签
3. 寻找错误信息或警告

### 方法4：查看应用日志
```bash
# 查看 Streamlit 日志
tail -f logs/tradingagents.log
```

## 📝 需要收集的信息

如果问题仍然存在，请提供以下信息：

1. **调试信息截图**
   - 开始分析按钮下方的所有调试信息

2. **日志片段**
   ```bash
   grep "任务控制" logs/tradingagents.log
   grep "current_analysis_id" logs/tradingagents.log
   ```

3. **浏览器信息**
   - 浏览器类型和版本
   - 控制台中的错误信息

4. **操作步骤**
   - 详细的操作过程
   - 何时开始看不到按钮

## 🎯 下一步

根据您看到的调试信息，我们可以：

1. 如果显示"没有找到 current_analysis_id"
   → 修复 session_state 管理

2. 如果显示"状态 'not_found'"
   → 修复线程跟踪

3. 如果显示其他状态
   → 检查状态转换逻辑

4. 如果显示按钮
   → 移除调试信息（问题已解决）

---

**注意：** 这些调试信息是临时添加的，在确认问题解决后会移除。

