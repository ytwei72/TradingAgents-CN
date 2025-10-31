# 步骤检测增强总结

## 背景

在之前的修复中，我们通过补录机制（fallback）来确保所有已完成的步骤都能显示为"已完成"状态。然而，这种方法不符合用户的要求：**必须有明确的任务开始和结束的检测，才能判定该步骤任务的执行结果**。

## 问题

补录机制的问题：
1. 缺乏明确的开始/结束信号
2. 使用估算时间，不够准确
3. 无法确定步骤是否真正执行

## 解决方案

移除补录机制，改为**增强调试日志**，帮助精确定位为什么某些步骤的开始/完成没有被正确检测到。

## 修改内容

### 1. 移除补录逻辑

**文件：** `web/components/async_progress_display.py`

移除了 `elif i < current_step:` 分支中的补录逻辑，确保只有真正检测到开始和完成的步骤才会显示为"已完成"。

```python
# 修改前：有补录逻辑
if i in step_history_map:
    # 显示已完成
elif i < current_step:
    # 补录逻辑（已移除）
elif i == current_step:
    # 显示进行中

# 修改后：严格检测
if i in step_history_map:
    # 显示已完成
elif i == current_step:
    # 显示进行中
```

### 2. 增强模块开始检测日志

**文件：** `web/utils/async_progress_tracker.py`
**方法：** `_detect_step_from_message`

在检测到模块开始时，输出详细的调试信息：

```python
if detected_step is not None:
    step_name = self.analysis_steps[detected_step]['name'] if detected_step < len(self.analysis_steps) else "未知"
    # 记录该步骤的开始时间（如果还没有记录的话）
    if detected_step not in self.step_start_times:
        self.step_start_times[detected_step] = time.time()
        logger.info(f"✅ [步骤检测-开始] 模块: {module_name}, 步骤索引: {detected_step}, 步骤名称: {step_name}, 开始时间: {time.time()}")
    else:
        logger.warning(f"⚠️ [步骤检测-重复开始] 模块: {module_name}, 步骤索引: {detected_step}, 步骤名称: {step_name}, 已有开始时间: {self.step_start_times[detected_step]}")
else:
    logger.warning(f"⚠️ [步骤检测-未匹配] 检测到模块开始但未匹配到步骤, 消息: {message[:200]}")
```

**日志输出示例：**
```
✅ [步骤检测-开始] 模块: neutral_analyst, 步骤索引: 14, 步骤名称: ⚖️ 平衡策略, 开始时间: 1730294567.123
```

### 3. 增强模块完成检测日志

**文件：** `web/utils/async_progress_tracker.py`
**方法：** `_detect_step_from_message`

在检测到模块完成时，输出详细的调试信息：

```python
elif "模块完成" in message:
    current_step_info = self.analysis_steps[self.current_step] if self.current_step < len(self.analysis_steps) else {'name': '未知'}
    current_step_name = current_step_info['name']
    
    # 检查当前步骤是否已记录，如果没有则记录
    if self.current_step not in [s['step_index'] for s in self.step_history]:
        step_start = self.step_start_times.get(self.current_step, time.time())
        step_end = time.time()
        step_duration = step_end - step_start
        
        self.step_history.append({
            'step_index': self.current_step,
            'step_name': current_step_name,
            'start_time': step_start,
            'end_time': step_end,
            'duration': step_duration,
            'message': message
        })
        logger.info(f"✅ [步骤检测-完成] 步骤索引: {self.current_step}, 步骤名称: {current_step_name}, 用时: {step_duration:.2f}秒")
    else:
        logger.warning(f"⚠️ [步骤检测-重复完成] 步骤索引: {self.current_step}, 步骤名称: {current_step_name}, 已记录在历史中")
    
    # 模块完成时，从当前步骤推进到下一步
    next_step = min(self.current_step + 1, len(self.analysis_steps) - 1)
    logger.info(f"📍 [步骤检测-推进] 从步骤 {self.current_step} ({current_step_name}) 推进到步骤 {next_step}")
    return next_step
```

**日志输出示例：**
```
✅ [步骤检测-完成] 步骤索引: 14, 步骤名称: ⚖️ 平衡策略, 用时: 45.67秒
📍 [步骤检测-推进] 从步骤 14 (⚖️ 平衡策略) 推进到步骤 15
```

### 4. 增强步骤切换日志

**文件：** `web/utils/async_progress_tracker.py`
**方法：** `update_progress`

在步骤切换时，输出详细的调试信息：

```python
if step != old_step:
    old_step_name = self.analysis_steps[old_step]['name'] if old_step < len(self.analysis_steps) else '未知'
    new_step_name = self.analysis_steps[step]['name'] if step < len(self.analysis_steps) else '未知'
    
    # 记录旧步骤的完成时间
    if old_step not in [s['step_index'] for s in self.step_history]:
        step_start = self.step_start_times.get(old_step, current_time)
        step_duration = current_time - step_start
        self.step_history.append({
            'step_index': old_step,
            'step_name': old_step_name,
            'start_time': step_start,
            'end_time': current_time,
            'duration': step_duration,
            'message': message
        })
        logger.info(f"📝 [步骤切换-记录] 步骤 {old_step} ({old_step_name}) 完成，用时: {step_duration:.2f}秒")
    else:
        logger.info(f"📝 [步骤切换-跳过] 步骤 {old_step} ({old_step_name}) 已记录")
    
    logger.info(f"🔄 [步骤切换] 从步骤 {old_step} ({old_step_name}) → 步骤 {step} ({new_step_name})")
```

**日志输出示例：**
```
📝 [步骤切换-记录] 步骤 13 (🛡️ 保守策略) 完成，用时: 38.45秒
🔄 [步骤切换] 从步骤 13 (🛡️ 保守策略) → 步骤 14 (⚖️ 平衡策略)
```

## 日志类型

### 正常流程日志（INFO 级别）

| 图标 | 类型 | 说明 |
|-----|------|------|
| ✅ | 步骤检测-开始 | 检测到模块开始，记录步骤开始时间 |
| ✅ | 步骤检测-完成 | 检测到模块完成，记录步骤完成时间和用时 |
| 📍 | 步骤检测-推进 | 步骤推进到下一个步骤 |
| 📝 | 步骤切换-记录 | 在步骤切换时记录旧步骤完成 |
| 📝 | 步骤切换-跳过 | 步骤已记录，跳过重复记录 |
| 🔄 | 步骤切换 | 步骤从 A 切换到 B |

### 异常情况日志（WARNING 级别）

| 图标 | 类型 | 说明 |
|-----|------|------|
| ⚠️ | 步骤检测-重复开始 | 同一步骤被多次开始（可能的重复执行） |
| ⚠️ | 步骤检测-重复完成 | 同一步骤被多次完成（可能的重复执行） |
| ⚠️ | 步骤检测-未匹配 | 检测到模块开始/完成但无法匹配到步骤（配置问题） |

## 调试流程

### 1. 确认问题

如果某个步骤没有被正确跟踪（例如"阶段15: ⚖️ 平衡策略"显示为"等待执行"），首先确认：

- 该步骤是否在分析步骤列表中
- 该步骤对应的模块是否实际执行

### 2. 检查日志

在日志文件中搜索相关模块：

```bash
# 搜索 neutral_analyst 模块的所有日志
grep "neutral_analyst" web/logs/tradingagents.log

# 搜索步骤检测相关的所有日志
grep "步骤检测" web/logs/tradingagents.log

# 搜索警告信息
grep "⚠️" web/logs/tradingagents.log
```

### 3. 分析日志输出

#### 场景 1：找不到开始日志

**现象：**
```
# 没有输出
```

**原因：**
- 模块没有添加 `@log_analysis_module` 装饰器
- `_detect_step_from_message` 中缺少匹配逻辑

**解决：**
1. 在模块文件中添加装饰器
2. 在 `_detect_step_from_message` 中添加匹配规则

#### 场景 2：有开始日志，但找不到完成日志

**现象：**
```
✅ [步骤检测-开始] 模块: neutral_analyst, 步骤索引: 14, 步骤名称: ⚖️ 平衡策略, 开始时间: 1730294567.123
# 之后没有完成日志
```

**原因：**
- 模块执行异常终止
- 装饰器没有捕获到模块完成

**解决：**
1. 检查模块是否有异常
2. 检查装饰器实现是否正确

#### 场景 3：有未匹配警告

**现象：**
```
⚠️ [步骤检测-未匹配] 检测到模块开始但未匹配到步骤, 消息: 📊 [模块开始] some_module
```

**原因：**
- 模块名称在 `_detect_step_from_message` 中没有对应的匹配规则
- 步骤名称关键词不匹配

**解决：**
1. 在 `_detect_step_from_message` 中添加该模块的匹配规则
2. 确保 `_find_step_by_keyword` 能找到对应的步骤

#### 场景 4：有重复开始/完成警告

**现象：**
```
✅ [步骤检测-开始] 模块: neutral_analyst, 步骤索引: 14, ...
⚠️ [步骤检测-重复开始] 模块: neutral_analyst, 步骤索引: 14, ...
```

**原因：**
- 模块被多次调用
- 装饰器被重复触发

**解决：**
1. 检查是否有重复的模块调用
2. 检查分析流程是否有问题

## 修改的文件

1. **web/utils/async_progress_tracker.py**
   - 增强 `_detect_step_from_message` 的日志记录
   - 增强 `update_progress` 的日志记录

2. **web/components/async_progress_display.py**
   - 移除补录逻辑

3. **docs/fixes/step_detection_debugging.md**（新增）
   - 调试指南文档

4. **docs/fixes/step_detection_enhancement_summary.md**（新增）
   - 本文档

## 预期效果

通过详细的调试日志，我们可以：

1. **快速定位问题**：通过搜索日志，立即知道哪个模块的检测出了问题
2. **明确诊断原因**：通过警告信息，清楚地知道是缺少装饰器、匹配规则还是步骤定义
3. **准确记录时间**：只有真正执行的步骤才会被记录，确保时间的准确性
4. **便于维护**：新增模块时，如果忘记添加检测逻辑，日志会立即提示

## 后续步骤

1. **运行测试**：使用 Mock 模式和实际任务测试步骤检测
2. **检查日志**：确认所有步骤都有对应的开始和完成日志
3. **修复问题**：根据警告信息，补充缺失的装饰器或匹配规则
4. **验证完整性**：确保 `step_history` 中包含所有实际执行的步骤

## 相关文档

- [步骤检测调试指南](step_detection_debugging.md)
- [实际任务步骤跟踪修复](actual_analysis_step_tracking_fix.md)
- [进度时间记录修复](progress_timing_fix.md)
- [Mock 分析模式指南](../guides/mock_analysis_mode.md)

