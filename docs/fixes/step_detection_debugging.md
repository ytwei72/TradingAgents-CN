# 步骤检测调试增强

## 概述

为了确保每个分析步骤都能被准确检测和记录，我们增强了步骤检测机制的日志记录功能。现在系统会输出详细的调试信息，帮助诊断步骤跟踪问题。

## 增强的日志记录

### 1. 模块开始检测

当检测到模块开始时，系统会输出以下日志：

```
✅ [步骤检测-开始] 模块: {module_name}, 步骤索引: {detected_step}, 步骤名称: {step_name}, 开始时间: {timestamp}
```

**示例：**
```
✅ [步骤检测-开始] 模块: neutral_analyst, 步骤索引: 14, 步骤名称: ⚖️ 平衡策略, 开始时间: 1730294567.123
```

**重复开始警告：**
如果同一步骤被重复开始，会输出警告：
```
⚠️ [步骤检测-重复开始] 模块: neutral_analyst, 步骤索引: 14, 步骤名称: ⚖️ 平衡策略, 已有开始时间: 1730294567.123
```

**未匹配警告：**
如果检测到模块开始但无法匹配到具体步骤：
```
⚠️ [步骤检测-未匹配] 检测到模块开始但未匹配到步骤, 消息: 📊 [模块开始] unknown_module
```

### 2. 模块完成检测

当检测到模块完成时，系统会输出以下日志：

```
✅ [步骤检测-完成] 步骤索引: {step_index}, 步骤名称: {step_name}, 用时: {duration}秒
```

**示例：**
```
✅ [步骤检测-完成] 步骤索引: 14, 步骤名称: ⚖️ 平衡策略, 用时: 45.67秒
```

**步骤推进日志：**
```
📍 [步骤检测-推进] 从步骤 14 (⚖️ 平衡策略) 推进到步骤 15
```

**重复完成警告：**
```
⚠️ [步骤检测-重复完成] 步骤索引: 14, 步骤名称: ⚖️ 平衡策略, 已记录在历史中
```

### 3. 步骤切换

在 `update_progress` 方法中，当步骤切换时会输出：

```
📝 [步骤切换-记录] 步骤 {old_step} ({old_step_name}) 完成，用时: {duration}秒
🔄 [步骤切换] 从步骤 {old_step} ({old_step_name}) → 步骤 {new_step} ({new_step_name})
```

**示例：**
```
📝 [步骤切换-记录] 步骤 13 (🛡️ 保守策略) 完成，用时: 38.45秒
🔄 [步骤切换] 从步骤 13 (🛡️ 保守策略) → 步骤 14 (⚖️ 平衡策略)
```

## 如何使用调试日志

### 1. 查看实时日志

在开发模式下启动 Web 应用：
```bash
python start_web.py
```

日志会输出到控制台和日志文件：
- `web/logs/tradingagents.log`
- `logs/tradingagents_structured.log`

### 2. 诊断步骤跟踪问题

如果某个步骤没有被正确跟踪，检查以下内容：

#### a) 检查模块装饰器

确保相关模块已添加 `@log_analysis_module` 或 `@log_analyst_module` 装饰器：

```python
from tradingagents.tools.log_analysis_module import log_analysis_module

@log_analysis_module("neutral_analyst")
async def neutral_node(state):
    # ... 实现代码
```

#### b) 检查步骤检测逻辑

在 `web/utils/async_progress_tracker.py` 的 `_detect_step_from_message` 方法中，确保模块名称能被正确匹配：

```python
elif "neutral_analyst" in message or "neutral" in message:
    detected_step = self._find_step_by_keyword(["平衡策略", "平衡"])
    module_name = "neutral_analyst"
```

#### c) 查看日志输出

搜索日志中的警告信息：
```bash
grep "⚠️" web/logs/tradingagents.log
```

常见问题：
- `⚠️ [步骤检测-未匹配]`：模块名称无法匹配到步骤
- `⚠️ [步骤检测-重复开始]`：同一步骤被多次启动
- `⚠️ [步骤检测-重复完成]`：同一步骤被多次完成

### 3. 验证步骤历史

在分析完成后，检查步骤历史记录：

```python
tracker = AsyncProgressTracker(...)
progress_data = tracker.get_progress()

# 查看步骤历史
for step in progress_data.get('step_history', []):
    print(f"步骤 {step['step_index']}: {step['step_name']}")
    print(f"  开始: {step['start_time']}")
    print(f"  结束: {step['end_time']}")
    print(f"  用时: {step['duration']:.2f}秒")
```

## 日志级别

调试日志使用以下级别：

- **INFO**：正常的步骤检测和切换
  - ✅ 步骤开始
  - ✅ 步骤完成
  - 📍 步骤推进
  - 📝 步骤切换记录
  - 🔄 步骤切换

- **WARNING**：异常情况（不一定是错误）
  - ⚠️ 重复开始/完成
  - ⚠️ 未匹配的模块

## 关键代码位置

### 步骤检测逻辑
- 文件：`web/utils/async_progress_tracker.py`
- 方法：`_detect_step_from_message` (第 438-554 行)

### 步骤切换逻辑
- 文件：`web/utils/async_progress_tracker.py`
- 方法：`update_progress` (第 332-400 行)

### 日志装饰器
- 文件：`tradingagents/tools/log_analysis_module.py`
- 装饰器：`@log_analysis_module`, `@log_analyst_module`

## 故障排查示例

### 问题：某个步骤显示为"等待执行"

**步骤 1：检查是否有开始日志**
```bash
grep "neutral_analyst" web/logs/tradingagents.log | grep "步骤检测-开始"
```

如果没有：
- 检查模块是否添加了装饰器
- 检查 `_detect_step_from_message` 中的匹配逻辑

**步骤 2：检查是否有完成日志**
```bash
grep "neutral_analyst" web/logs/tradingagents.log | grep "步骤检测-完成"
```

如果没有：
- 检查模块是否正常执行完毕
- 检查是否有异常终止

**步骤 3：检查是否有警告**
```bash
grep "neutral_analyst" web/logs/tradingagents.log | grep "⚠️"
```

根据警告类型采取相应措施。

## 最佳实践

1. **添加新模块时**
   - 始终添加适当的装饰器
   - 在 `_detect_step_from_message` 中添加匹配逻辑
   - 运行测试验证步骤能被正确检测

2. **调试步骤跟踪问题时**
   - 先查看日志中的警告信息
   - 使用 Mock 模式快速复现问题
   - 对比 Mock 模式和实际执行的日志差异

3. **性能考虑**
   - 调试日志使用 INFO 级别，生产环境可调整为 WARNING
   - 避免在循环中输出大量日志
   - 定期清理旧日志文件

## 相关文档

- [实际任务步骤跟踪修复](actual_analysis_step_tracking_fix.md)
- [进度时间记录修复](progress_timing_fix.md)
- [Mock 分析模式指南](../guides/mock_analysis_mode.md)

