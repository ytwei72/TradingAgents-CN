# 节点级别模拟模式使用指南

## 📋 概述

节点级别模拟模式允许你为每个分析节点单独启用模拟模式。当某个节点启用模拟模式时，系统会从历史步骤输出中提取该节点的历史数据，然后随机sleep 2-10秒后返回，而不是执行实际的LLM调用。

## 🎯 使用场景

- **测试特定节点**：只想测试某个节点的行为，而不执行完整分析
- **节省API成本**：某些节点使用模拟模式，其他节点正常执行
- **调试和开发**：快速验证流程，无需等待真实API响应

## 🔧 配置方法

在项目根目录的 `.env` 文件中配置：

### 1. 启用所有节点的模拟模式

```bash
MOCK_ANALYSIS_MODE=true
```

### 2. 只启用特定节点的模拟模式

```bash
# 只启用市场分析师和新闻分析师的模拟模式
MOCK_ANALYSIS_MODE=market,news
```

### 3. 使用节点完整名称

```bash
# 支持多种命名方式
MOCK_ANALYSIS_MODE=market_analyst,bull_researcher,trader
```

### 4. 禁用模拟模式

```bash
MOCK_ANALYSIS_MODE=false
```

## 📊 支持的节点名称

### 完整节点名称列表

系统支持以下所有节点的模拟模式配置：

| 节点类型 | 标准名称 | 支持的别名 | Graph显示名称 | 节点描述 |
|---------|---------|-----------|--------------|---------|
| **分析师节点** | | | | |
| | `market_analyst` | `market` | Market Analyst | 市场分析师：负责技术分析、价格趋势、市场情绪分析 |
| | `fundamentals_analyst` | `fundamentals` | Fundamentals Analyst | 基本面分析师：负责财务指标、财务报表、公司基本面分析 |
| | `news_analyst` | `news` | News Analyst | 新闻分析师：负责新闻事件分析、全球要闻分析 |
| | `social_media_analyst` | `social` | Social Media Analyst | 社交媒体分析师：负责社交媒体情绪、Reddit分析 |
| **研究员节点** | | | | |
| | `bull_researcher` | `bull` | Bull Researcher | 看涨研究员：负责多头观点分析 |
| | `bear_researcher` | `bear` | Bear Researcher | 看跌研究员：负责空头观点分析 |
| | `research_manager` | - | Research Manager | 研究经理：综合多头和空头观点，做出投资判断 |
| **交易节点** | | | | |
| | `trader` | - | Trader | 交易员：基于研究结果制定交易计划 |
| **风险分析节点** | | | | |
| | `risky_analyst` | `risky` | Risky Analyst | 激进风险分析师：从高风险高收益角度分析 |
| | `safe_analyst` | `safe` | Safe Analyst | 保守风险分析师：从风险控制角度分析 |
| | `neutral_analyst` | `neutral` | Neutral Analyst | 中性风险分析师：从平衡角度分析风险 |
| | `risk_manager` | `risk_judge` | Risk Judge | 风险经理：综合各方风险评估，做出最终风险决策 |

### 节点名称说明

#### 分析师节点（4个）
- **market_analyst** / **market** - 市场分析师
  - 功能：技术分析、价格趋势、市场情绪
  - 使用工具：市场数据工具、技术指标工具
  
- **fundamentals_analyst** / **fundamentals** - 基本面分析师
  - 功能：财务指标、财务报表、公司基本面
  - 使用工具：基本面数据工具、财务数据工具
  
- **news_analyst** / **news** - 新闻分析师
  - 功能：新闻事件分析、全球要闻
  - 使用工具：新闻获取工具、Google News工具
  
- **social_media_analyst** / **social** - 社交媒体分析师
  - 功能：社交媒体情绪、Reddit分析
  - 使用工具：Reddit工具、社交媒体工具

#### 研究员节点（3个）
- **bull_researcher** / **bull** - 看涨研究员
  - 功能：从乐观角度分析投资机会
  - 输出：看涨观点、投资理由
  
- **bear_researcher** / **bear** - 看跌研究员
  - 功能：从谨慎角度分析投资风险
  - 输出：看跌观点、风险提醒
  
- **research_manager** - 研究经理
  - 功能：综合多头和空头观点
  - 输出：投资判断、综合建议

#### 交易节点（1个）
- **trader** - 交易员
  - 功能：基于研究结果制定交易计划
  - 输出：交易计划、投资建议

#### 风险分析节点（4个）
- **risky_analyst** / **risky** - 激进风险分析师
  - 功能：从高风险高收益角度分析
  - 输出：激进策略建议
  
- **safe_analyst** / **safe** - 保守风险分析师
  - 功能：从风险控制角度分析
  - 输出：保守策略建议
  
- **neutral_analyst** / **neutral** - 中性风险分析师
  - 功能：从平衡角度分析风险
  - 输出：平衡策略建议
  
- **risk_manager** / **risk_judge** - 风险经理
  - 功能：综合各方风险评估
  - 输出：最终风险决策、风险评级

### 节点执行顺序

节点在分析流程中的执行顺序：

1. **分析师阶段**（并行执行）
   - Market Analyst → Fundamentals Analyst → News Analyst → Social Media Analyst
   
2. **研究阶段**（顺序执行）
   - Bull Researcher → Bear Researcher → Research Manager
   
3. **交易阶段**
   - Trader
   
4. **风险分析阶段**（顺序执行）
   - Risky Analyst → Safe Analyst → Neutral Analyst → Risk Manager

## 🔄 工作流程

1. **节点执行时**：系统检查该节点是否启用模拟模式
2. **查找历史数据**：从 `eval_results/{ticker}/TradingAgentsStrategy_logs/step_outputs/{trade_date}/all_steps.json` 中查找匹配的历史步骤
3. **匹配节点输出**：根据节点名称和内容关键词匹配历史步骤
4. **返回历史数据**：如果找到匹配的历史数据，返回历史状态
5. **随机延迟**：sleep 2-10秒（可配置）模拟真实执行时间
6. **正常执行**：如果未启用模拟模式或未找到历史数据，正常执行节点

## ⚙️ 高级配置

### 自定义sleep时间范围

在 `.env` 文件中配置：

```bash
# 模拟模式的sleep时间范围（秒）
MOCK_SLEEP_MIN=3   # 最小sleep时间，默认2秒
MOCK_SLEEP_MAX=8   # 最大sleep时间，默认10秒
```

**说明：**
- `MOCK_SLEEP_MIN`: 模拟模式时节点sleep的最小时间（秒），默认值为2
- `MOCK_SLEEP_MAX`: 模拟模式时节点sleep的最大时间（秒），默认值为10
- 系统会在最小值和最大值之间随机选择一个时间进行sleep
- 支持小数，例如 `MOCK_SLEEP_MIN=1.5` 表示1.5秒

**示例配置：**

```bash
# 快速模式：1-3秒
MOCK_SLEEP_MIN=1
MOCK_SLEEP_MAX=3

# 标准模式：2-10秒（默认）
MOCK_SLEEP_MIN=2
MOCK_SLEEP_MAX=10

# 慢速模式：5-15秒
MOCK_SLEEP_MIN=5
MOCK_SLEEP_MAX=15
```

## 📝 示例配置

### 示例1：只模拟市场分析师

```bash
MOCK_ANALYSIS_MODE=market
# 或
MOCK_ANALYSIS_MODE=market_analyst
```

### 示例2：模拟多个分析师节点

```bash
MOCK_ANALYSIS_MODE=market,news,fundamentals
# 或使用完整名称
MOCK_ANALYSIS_MODE=market_analyst,news_analyst,fundamentals_analyst
```

### 示例3：模拟研究员辩论阶段

```bash
MOCK_ANALYSIS_MODE=bull,bear,research_manager
# 或
MOCK_ANALYSIS_MODE=bull_researcher,bear_researcher,research_manager
```

### 示例4：模拟所有节点

```bash
MOCK_ANALYSIS_MODE=true
```

### 示例5：模拟所有分析师节点

```bash
MOCK_ANALYSIS_MODE=market,fundamentals,news,social
```

### 示例6：模拟所有风险分析节点

```bash
MOCK_ANALYSIS_MODE=risky,safe,neutral,risk_manager
```

### 示例7：混合配置（部分节点模拟，部分正常执行）

```bash
# 模拟市场分析师和新闻分析师，其他节点正常执行
MOCK_ANALYSIS_MODE=market,news
```

## 🔍 快速参考表

### 所有节点名称速查

| 类别 | 标准名称 | 别名 | 快速配置示例 |
|-----|---------|------|------------|
| 分析师 | `market_analyst` | `market` | `MOCK_ANALYSIS_MODE=market` |
| 分析师 | `fundamentals_analyst` | `fundamentals` | `MOCK_ANALYSIS_MODE=fundamentals` |
| 分析师 | `news_analyst` | `news` | `MOCK_ANALYSIS_MODE=news` |
| 分析师 | `social_media_analyst` | `social` | `MOCK_ANALYSIS_MODE=social` |
| 研究员 | `bull_researcher` | `bull` | `MOCK_ANALYSIS_MODE=bull` |
| 研究员 | `bear_researcher` | `bear` | `MOCK_ANALYSIS_MODE=bear` |
| 研究员 | `research_manager` | - | `MOCK_ANALYSIS_MODE=research_manager` |
| 交易 | `trader` | - | `MOCK_ANALYSIS_MODE=trader` |
| 风险 | `risky_analyst` | `risky` | `MOCK_ANALYSIS_MODE=risky` |
| 风险 | `safe_analyst` | `safe` | `MOCK_ANALYSIS_MODE=safe` |
| 风险 | `neutral_analyst` | `neutral` | `MOCK_ANALYSIS_MODE=neutral` |
| 风险 | `risk_manager` | `risk_judge` | `MOCK_ANALYSIS_MODE=risk_manager` |

**总计：12个节点**（4个分析师 + 3个研究员 + 1个交易员 + 4个风险分析师）

## 🔍 日志标识

启用模拟模式的节点会输出以下日志：

```
🎭 [模拟模式] 节点 market_analyst 启用模拟模式
🎭 [模拟模式] 找到历史输出: market_analyst (步骤 5)
🎭 [模拟模式] 节点 market_analyst 使用历史数据，sleep 6.32 秒
```

如果未找到历史数据：

```
⚠️ [模拟模式] 未找到节点 market_analyst 的历史输出
⚠️ [模拟模式] 节点 market_analyst 未找到历史数据，使用正常模式
```

## ⚠️ 注意事项

1. **历史数据要求**：模拟模式需要先执行一次完整分析，生成历史步骤输出文件
2. **数据匹配**：系统通过关键词匹配查找历史数据，可能不够精确
3. **日期格式**：历史数据按日期组织，确保交易日期格式一致
4. **顺序执行**：模拟模式不会改变节点的执行顺序，只是跳过真实的LLM调用

## 🐛 故障排除

### 问题1：节点没有使用模拟模式

**检查：**
1. 确认 `.env` 文件中的配置正确
2. 检查日志中是否有 `🎭 [模拟模式配置] 已加载` 的消息
3. 确认节点名称拼写正确

### 问题2：找不到历史数据

**解决方案：**
1. 先执行一次完整的分析任务，生成历史步骤文件
2. 检查 `eval_results/{ticker}/TradingAgentsStrategy_logs/step_outputs/{trade_date}/all_steps.json` 是否存在
3. 确认交易日期格式正确（YYYY-MM-DD）

### 问题3：匹配到错误的历史数据

**解决方案：**
- 系统使用关键词匹配，可能不够精确
- 可以手动检查 `all_steps.json` 文件，确认数据是否正确
- 未来版本可能会改进匹配算法

## 📚 相关文档

- [模拟分析模式指南](mock_analysis_mode.md)

