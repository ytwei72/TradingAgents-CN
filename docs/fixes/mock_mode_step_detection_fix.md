# 模拟模式步骤检测修复

## 修复日期
2025-10-30

## 问题描述

在模拟分析模式中，所有步骤都被错误地归类到"启动引擎"步骤，没有正确推进到后续步骤。

**原因分析：**
模拟函数中的进度消息格式与 `_detect_step_from_message()` 函数所期望的格式不匹配，导致步骤检测失败。

## 解决方案

### 修改模拟消息格式

将模拟函数中的进度消息改为与实际分析相同的格式，使用"模块开始"和"模块完成"关键词。

#### 修改前（错误格式）：
```python
update_progress(f"📊 {analyst_name}开始分析...")
update_progress(f"📊 {analyst_name}完成分析")
```

#### 修改后（正确格式）：
```python
update_progress(f"📊 [模拟] 模块开始: {analyst_key}")
update_progress(f"✅ [模拟] 模块完成: {analyst_key}")
```

### 关键变更

**文件：** `web/utils/analysis_runner.py`

1. **分析师模拟**
   ```python
   # 使用分析师的英文key（与实际分析保持一致）
   analyst_mapping = {
       'market': 'market_analyst',
       'fundamentals': 'fundamentals_analyst',
       'technical': 'technical_analyst',
       'sentiment': 'sentiment_analyst',
       'news': 'news_analyst',
       'social_media': 'social_media_analyst',
       'risk': 'risk_analyst'
   }
   
   for analyst in analysts:
       analyst_key = analyst_mapping.get(analyst, f'{analyst}_analyst')
       update_progress(f"📊 [模拟] 模块开始: {analyst_key}")
       mock_sleep()
       update_progress(f"✅ [模拟] 模块完成: {analyst_key}")
   ```

2. **研究员辩论模拟**
   ```python
   update_progress("📈 [模拟] 模块开始: bull_researcher")
   mock_sleep()
   update_progress("✅ [模拟] 模块完成: bull_researcher")
   
   update_progress("📉 [模拟] 模块开始: bear_researcher")
   mock_sleep()
   update_progress("✅ [模拟] 模块完成: bear_researcher")
   
   update_progress("🤝 [模拟] 模块开始: research_manager")
   mock_sleep()
   update_progress("✅ [模拟] 模块完成: research_manager")
   ```

3. **投资建议模拟**
   ```python
   update_progress("💡 [模拟] 模块开始: trader")
   mock_sleep()
   update_progress("✅ [模拟] 模块完成: trader")
   ```

4. **风险评估模拟**
   ```python
   if research_depth >= 3:
       # 深度分析：4个风险步骤
       update_progress("🔥 [模拟] 正在评估激进策略...")
       mock_sleep()
       update_progress("✅ [模拟] 模块完成: 激进策略评估")
       
       update_progress("🛡️ [模拟] 正在评估保守策略...")
       mock_sleep()
       update_progress("✅ [模拟] 模块完成: 保守策略评估")
       
       update_progress("⚖️ [模拟] 正在评估平衡策略...")
       mock_sleep()
       update_progress("✅ [模拟] 模块完成: 平衡策略评估")
       
       update_progress("🎯 [模拟] 模块开始: risk_manager")
       mock_sleep()
       update_progress("✅ [模拟] 模块完成: risk_manager")
   else:
       # 快速/标准分析：1个风险步骤
       update_progress("⚠️ [模拟] 正在识别投资风险...")
       mock_sleep()
       update_progress("✅ [模拟] 模块完成: 风险提示")
   ```

5. **报告生成模拟**
   ```python
   update_progress("📊 [模拟] 模块开始: graph_signal_processing")
   mock_sleep()
   update_progress("✅ [模拟] 模块完成: graph_signal_processing")
   ```

## 步骤检测逻辑

`AsyncProgressTracker._detect_step_from_message()` 函数通过以下关键词识别步骤：

### 1. 准备阶段（步骤 0-4）
- `"🚀 开始股票分析"` → 步骤 0
- `"验证"` / `"预获取"` / `"数据准备"` → 步骤 0
- `"环境"` / `"api"` / `"密钥"` → 步骤 1
- `"成本"` / `"预估"` → 步骤 2
- `"配置"` / `"参数"` → 步骤 3
- `"初始化"` / `"引擎"` → 步骤 4

### 2. 分析阶段（"模块开始"）
- `"market_analyst"` / `"market"` → 查找"市场分析"步骤
- `"fundamentals_analyst"` → 查找"基本面分析"步骤
- `"technical_analyst"` → 查找"技术分析"步骤
- `"sentiment_analyst"` → 查找"情绪分析"步骤
- `"news_analyst"` → 查找"新闻分析"步骤
- `"social_media_analyst"` → 查找"社交媒体"步骤
- `"risk_analyst"` → 查找"风险分析"步骤

### 3. 辩论和决策阶段
- `"bull_researcher"` → 查找"多头观点"步骤
- `"bear_researcher"` → 查找"空头观点"步骤
- `"research_manager"` → 查找"观点整合"步骤
- `"trader"` → 查找"投资建议"步骤

### 4. 风险评估阶段
- `"risk_manager"` → 查找"风险控制"步骤
- `"graph_signal_processing"` → 查找"生成报告"步骤

### 5. 模块完成
- `"模块完成"` → 推进到下一步

## 测试验证

启用模拟模式后，验证以下行为：

### 1. 步骤正确推进
```
✅ 步骤 1: 📋 准备阶段 (用时: 3.2秒)
✅ 步骤 2: 🔧 环境检查 (用时: 5.8秒)
✅ 步骤 3: 💰 成本估算 (用时: 4.1秒)
✅ 步骤 4: ⚙️ 参数设置 (用时: 6.5秒)
✅ 步骤 5: 🚀 启动引擎 (用时: 7.2秒)
✅ 步骤 6: 📊 市场分析 (用时: 8.9秒)  ← 正确推进到这里
✅ 步骤 7: 💼 基本面分析 (用时: 5.3秒)
...
```

### 2. 每个步骤独立计时
- 每个步骤显示独立的用时（2-10秒）
- 不会所有步骤都归类到"启动引擎"

### 3. 时间戳不同
- 每个步骤的完成时间戳秒数不同
- 反映实际的步骤完成时间

## 测试方法

```bash
# 1. 启用模拟模式
echo "MOCK_ANALYSIS_MODE=true" >> .env

# 2. 启动Web应用
python start_web.py

# 3. 提交分析任务（选择多个分析师，研究深度3）

# 4. 展开"查看详细分析步骤日志"

# 5. 验证每个步骤都正确显示并独立计时
```

## 预期结果

### 快速分析（research_depth=1，2个分析师）
约10-12个步骤，每步2-10秒

### 标准分析（research_depth=2，3个分析师）
约13-15个步骤，每步2-10秒

### 深度分析（research_depth=3，4个分析师）
约17-19个步骤，每步2-10秒

## 相关文档

- [进度跟踪时间显示修复](progress_timing_fix.md)
- [模拟分析模式使用指南](../guides/mock_analysis_mode.md)
- [模拟模式快速启用](../guides/MOCK_MODE_QUICKSTART.md)

## 修改文件

1. **web/utils/analysis_runner.py**
   - 修改 `run_mock_analysis()` 函数中的所有进度消息格式
   - 使用"模块开始"和"模块完成"关键词
   - 使用与实际分析一致的模块名称

## 注意事项

1. **消息格式要求**
   - 必须包含"模块开始"或"模块完成"关键词
   - 模块名称必须与 `_detect_step_from_message()` 中的匹配逻辑一致

2. **步骤顺序**
   - 确保步骤顺序与 `_generate_dynamic_steps()` 生成的步骤顺序一致

3. **research_depth适配**
   - 根据不同的研究深度生成不同数量的步骤
   - 确保与实际分析的步骤数量匹配

## 未来改进

1. 可以考虑将步骤检测逻辑改为配置驱动，避免硬编码
2. 可以添加步骤验证机制，确保模拟和实际分析的步骤一致
3. 可以在日志中显示步骤检测的详细信息，便于调试

