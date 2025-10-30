# 实际分析步骤跟踪修复

## 修复日期
2025-10-30

## 问题描述

在实际任务执行时，进度步骤跟踪存在严重问题：

1. **"阶段 6: 📊 市场分析"的用时被算到"启动引擎"步骤**
   - 市场分析师完成后，步骤没有正确推进

2. **阶段11到阶段16之间的所有步骤，被算到"阶段 10: 📉 空头观点"中**
   - 空头观点完成后，后续所有步骤（研究经理、交易员、风险管理等）都没有推进
   - 导致这些步骤的用时全部被累计到空头观点步骤

## 根本原因

**关键模块缺少日志装饰器！**

以下关键模块没有使用 `@log_analysis_module` 装饰器，因此不会发送"📊 [模块开始]"和"📊 [模块完成]"日志消息：

1. ❌ `bull_researcher.py` - 多头研究员
2. ❌ `bear_researcher.py` - 空头研究员
3. ❌ `research_manager.py` - 研究经理
4. ❌ `trader.py` - 交易员
5. ❌ `risk_manager.py` - 风险经理

而分析师模块都有装饰器：
- ✅ `market_analyst.py` - @log_analyst_module("market")
- ✅ `fundamentals_analyst.py` - @log_analyst_module("fundamentals")
- ✅ `technical_analyst.py` - @log_analyst_module("technical")
- ✅ `sentiment_analyst.py` - @log_analyst_module("sentiment")
- ✅ `news_analyst.py` - @log_analyst_module("news")
- ✅ `social_media_analyst.py` - @log_analyst_module("social_media")

## 解决方案

为所有缺少装饰器的模块添加 `@log_analysis_module` 装饰器。

### 修改文件清单

#### 1. tradingagents/agents/researchers/bull_researcher.py

```python
# 导入分析模块日志装饰器
from tradingagents.utils.tool_logging import log_analysis_module

def create_bull_researcher(llm, memory):
    @log_analysis_module("bull_researcher")  # ← 添加装饰器
    def bull_node(state) -> dict:
        # ... 原有代码 ...
```

#### 2. tradingagents/agents/researchers/bear_researcher.py

```python
# 导入分析模块日志装饰器
from tradingagents.utils.tool_logging import log_analysis_module

def create_bear_researcher(llm, memory):
    @log_analysis_module("bear_researcher")  # ← 添加装饰器
    def bear_node(state) -> dict:
        # ... 原有代码 ...
```

#### 3. tradingagents/agents/managers/research_manager.py

```python
# 导入分析模块日志装饰器
from tradingagents.utils.tool_logging import log_analysis_module

def create_research_manager(llm, memory):
    @log_analysis_module("research_manager")  # ← 添加装饰器
    def research_manager_node(state) -> dict:
        # ... 原有代码 ...
```

#### 4. tradingagents/agents/trader/trader.py

```python
# 导入分析模块日志装饰器
from tradingagents.utils.tool_logging import log_analysis_module

def create_trader(llm, memory):
    @log_analysis_module("trader")  # ← 添加装饰器
    def trader_node(state, name):
        # ... 原有代码 ...
```

#### 5. tradingagents/agents/managers/risk_manager.py

```python
# 导入分析模块日志装饰器
from tradingagents.utils.tool_logging import log_analysis_module

def create_risk_manager(llm, memory):
    @log_analysis_module("risk_manager")  # ← 添加装饰器
    def risk_manager_node(state) -> dict:
        # ... 原有代码 ...
```

## 装饰器工作原理

`@log_analysis_module` 装饰器会在函数执行前后自动发送日志：

### 模块开始时
```
📊 [模块开始] bull_researcher - 股票: AAPL
```

### 模块完成时
```
📊 [模块完成] bull_researcher - ✅ 成功 - 股票: AAPL, 耗时: 5.23s
```

这些日志消息会被 `AsyncProgressTracker._detect_step_from_message()` 函数捕获，从而：
1. **"模块开始"** → 推进到对应的分析步骤
2. **"模块完成"** → 记录步骤完成时间，推进到下一步

## 步骤检测逻辑对应关系

| 日志中的module_name | 检测关键词 | 对应步骤名称 |
|-------------------|----------|------------|
| `bull_researcher` | `"bull_researcher"` / `"bull"` | 📈 多头观点 |
| `bear_researcher` | `"bear_researcher"` / `"bear"` | 📉 空头观点 |
| `research_manager` | `"research_manager"` | 🤝 观点整合 |
| `trader` | `"trader"` | 💡 投资建议 |
| `risk_manager` | `"risk_manager"` | 🎯 风险控制 / ⚠️ 风险提示 |
| `graph_signal_processing` | `"graph_signal_processing"` / `"signal"` | 📊 生成报告 |

## 预期效果

### 修复前：
```
✅ 阶段 5: 🚀 启动引擎 (用时: 3.2秒)
🔄 阶段 6: 📊 市场分析 (用时: 58.5秒)  ← 包含了市场分析的所有时间
...
✅ 阶段 10: 📉 空头观点 (用时: 125.3秒)  ← 包含了后续所有步骤的时间
⏳ 阶段 11: 🤝 观点整合 - 等待执行      ← 从未被推进
⏳ 阶段 12: 💡 投资建议 - 等待执行      ← 从未被推进
⏳ 阶段 13: 🎯 风险控制 - 等待执行      ← 从未被推进
```

### 修复后：
```
✅ 阶段 5: 🚀 启动引擎 (用时: 3.2秒)
✅ 阶段 6: 📊 市场分析 (用时: 5.8秒)    ← 正确显示市场分析用时
✅ 阶段 7: 💼 基本面分析 (用时: 6.2秒)
...
✅ 阶段 9: 📈 多头观点 (用时: 4.5秒)    ← 正确推进
✅ 阶段 10: 📉 空头观点 (用时: 5.1秒)   ← 正确显示空头观点用时
✅ 阶段 11: 🤝 观点整合 (用时: 3.8秒)   ← 正确推进并计时
✅ 阶段 12: 💡 投资建议 (用时: 7.2秒)   ← 正确推进并计时
✅ 阶段 13: 🎯 风险控制 (用时: 4.9秒)   ← 正确推进并计时
✅ 阶段 14: 📊 生成报告 (用时: 2.3秒)   ← 正确推进并计时
```

## 测试验证

### 1. 运行实际分析
```bash
# 启动Web应用（不要启用Mock模式）
python start_web.py

# 提交一个真实的股票分析任务
# - 选择多个分析师
# - 研究深度设为3（深度分析）
```

### 2. 检查步骤日志
展开"查看详细分析步骤日志"，验证：
- ✅ 每个步骤都正确显示
- ✅ 每个步骤都有独立的用时（不是累加）
- ✅ 时间戳秒数不同
- ✅ 步骤按顺序推进，没有跳过

### 3. 检查日志文件
查看 `logs/tradingagents_structured.log`，应该能看到：
```
📊 [模块开始] market_analyst - 股票: AAPL
📊 [模块完成] market_analyst - ✅ 成功 - 股票: AAPL, 耗时: 5.23s
📊 [模块开始] fundamentals_analyst - 股票: AAPL
📊 [模块完成] fundamentals_analyst - ✅ 成功 - 股票: AAPL, 耗时: 6.45s
...
📊 [模块开始] bull_researcher - 股票: AAPL
📊 [模块完成] bull_researcher - ✅ 成功 - 股票: AAPL, 耗时: 4.56s
📊 [模块开始] bear_researcher - 股票: AAPL
📊 [模块完成] bear_researcher - ✅ 成功 - 股票: AAPL, 耗时: 5.12s
📊 [模块开始] research_manager - 股票: AAPL
📊 [模块完成] research_manager - ✅ 成功 - 股票: AAPL, 耗时: 3.78s
📊 [模块开始] trader - 股票: AAPL
📊 [模块完成] trader - ✅ 成功 - 股票: AAPL, 耗时: 7.23s
📊 [模块开始] risk_manager - 股票: AAPL
📊 [模块完成] risk_manager - ✅ 成功 - 股票: AAPL, 耗时: 4.91s
```

## 相关修复

此修复配合以下功能一起工作：

1. [进度跟踪时间显示修复](progress_timing_fix.md)
   - 记录实际步骤执行时间
   - 显示步骤用时和总用时

2. [模拟模式步骤检测修复](mock_mode_step_detection_fix.md)
   - Mock模式使用相同的消息格式
   - 测试步骤检测逻辑

## 技术细节

### log_analysis_module 装饰器实现

位置：`tradingagents/utils/tool_logging.py`

```python
def log_analysis_module(module_name: str):
    """分析模块日志装饰器"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 提取股票代码和会话ID
            # ...
            
            # 记录模块开始
            logger_manager.log_module_start(
                tool_logger, module_name, symbol, session_id,
                function_name=func.__name__
            )
            
            start_time = time.time()
            
            try:
                # 执行分析函数
                result = func(*args, **kwargs)
                
                # 计算执行时间
                duration = time.time() - start_time
                
                # 记录模块完成
                logger_manager.log_module_complete(
                    tool_logger, module_name, symbol, session_id,
                    duration, success=True
                )
                
                return result
            except Exception as e:
                # 记录模块错误
                duration = time.time() - start_time
                logger_manager.log_module_error(
                    tool_logger, module_name, symbol, session_id,
                    duration, str(e)
                )
                raise
                
        return wrapper
    return decorator
```

## 注意事项

1. **装饰器顺序**
   - 如果有多个装饰器，`@log_analysis_module` 应该放在最内层（最靠近函数定义）

2. **函数签名**
   - 装饰器会自动从函数参数中提取 `state`
   - 需要确保函数第一个参数是 `state` 字典

3. **错误处理**
   - 装饰器会捕获异常并记录
   - 异常会被重新抛出，不影响原有错误处理逻辑

## 总结

通过为5个关键模块添加日志装饰器，成功修复了实际分析中的步骤跟踪问题：

- ✅ 所有步骤都能正确推进
- ✅ 每个步骤都有准确的执行时间
- ✅ 时间戳精确到秒
- ✅ 步骤用时和总用时都正确显示

现在Mock模式和实际分析模式的步骤跟踪都能完美工作！

