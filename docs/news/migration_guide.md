# 新闻数据源迁移指南

## 📖 概述

本指南提供了从旧版新闻数据源迁移到新版 `news_engine` 的详细步骤和最佳实践。

## 📂 相关文档

| 文档 | 说明 | 路径 |
|------|------|------|
| **迁移评估报告** | 详细的技术评估和对比分析 | `docs/news/news_engine_migration_evaluation.md` |
| **V2实现草稿** | 混合模式的实现代码 | `tradingagents/tools/unified_news_tool_v2_draft.py` |
| **测试脚本** | 迁移测试工具 | `scripts/test_news_migration.py` |
| **新闻功能定义** | 新闻分析师的接口说明 | `docs/news/news_func_def.md` |
| **架构设计文档** | news_engine架构说明 | `docs/news/新闻模块架构设计.md` |

## 🚀 快速开始

### Step 1: 阅读评估报告

首先阅读详细的评估报告，了解迁移的影响：

```bash
# 打开评估报告
cat docs/news/news_engine_migration_evaluation.md
```

**关键内容**:
- 旧版 vs 新版的功能对比
- 数据源支持情况
- 切换风险评估
- 三种切换方案对比

### Step 2: 运行测试脚本

使用测试脚本验证新旧版本的效果：

```bash
# 测试单个股票（默认：000002 万科A）
python scripts/test_news_migration.py

# 测试指定股票
python scripts/test_news_migration.py --stock 600000

# 批量测试多个股票（A股、港股、美股）
python scripts/test_news_migration.py --batch
```

**测试输出包括**:
- ✅ 新闻获取成功率
- ⏱️ 响应时间对比
- 📊 数据量对比
- 🔗 数据源使用情况

### Step 3: 查看V2实现

查看混合模式的实现示例：

```bash
# 查看V2实现代码
cat tradingagents/tools/unified_news_tool_v2_draft.py
```

**核心特性**:
- 🔄 自动降级机制
- 🎯 针对不同市场的优化策略
- 🔧 保留旧版备选路径
- 📊 详细的日志记录

## 📋 迁移决策

根据评估报告，推荐使用 **混合模式（建议3）**：

### 为什么选择混合模式？

| 优势 | 说明 |
|------|------|
| **风险最低** | 保留所有备选路径，失败可快速回退 |
| **成功率最高** | 结合新旧版优势，最大化数据获取成功率 |
| **针对性优化** | 不同市场使用最适合的数据源策略 |
| **渐进式迁移** | 可以根据实际效果逐步调整策略 |

### 各市场策略

#### A股策略
```
1. news_engine (AKShare + Tushare) ← 首选
2. 东方财富（旧版）             ← 降级1
3. Google新闻                   ← 降级2
```

#### 港股策略
```
1. news_engine (EODHD + FinnHub) ← 首选
2. Google新闻                    ← 降级1
3. 实时新闻（旧版）              ← 降级2
```

#### 美股策略
```
1. news_engine (FinnHub + EODHD) ← 首选
2. OpenAI全球新闻                ← 降级1
3. Google新闻                    ← 降级2
```

## 🔧 实施步骤

### Phase 1: 准备阶段（1-2天）

#### 1.1 配置API密钥

确保以下API密钥已配置：

```bash
# .env 文件
TUSHARE_TOKEN=your_token_here
FINNHUB_API_KEY=your_key_here
EODHD_API_TOKEN=your_token_here
```

#### 1.2 测试news_engine可用性

```python
# 测试脚本
from tradingagents.news_engine import get_stock_news

# 测试A股
response = get_stock_news("000002", max_news=5)
print(f"A股测试: {'✅' if response.success else '❌'}")

# 测试港股
response = get_stock_news("0700.HK", max_news=5)
print(f"港股测试: {'✅' if response.success else '❌'}")

# 测试美股
response = get_stock_news("AAPL", max_news=5)
print(f"美股测试: {'✅' if response.success else '❌'}")
```

#### 1.3 运行对比测试

```bash
# 运行批量测试
python scripts/test_news_migration.py --batch

# 分析结果
# - 检查成功率是否 > 95%
# - 检查响应时间是否 < 5秒
# - 检查数据源覆盖情况
```

### Phase 2: 开发阶段（3-5天）

#### 2.1 创建V2版本

```bash
# 复制草稿为正式版本
cp tradingagents/tools/unified_news_tool_v2_draft.py \
   tradingagents/tools/unified_news_tool_v2.py

# 根据测试结果调整策略
vim tradingagents/tools/unified_news_tool_v2.py
```

#### 2.2 修改新闻分析师节点

在 `tradingagents/agents/analysts/news_analyst.py` 中切换到V2：

```python
# 旧版导入
# from tradingagents.tools.unified_news_tool import create_unified_news_tool

# 新版导入
from tradingagents.tools.unified_news_tool_v2 import create_unified_news_tool_v2

def create_news_analyst(llm, toolkit):
    @message_analysis_module("news_analyst")
    def news_analyst_node(state):
        # ... 其他代码 ...
        
        # 使用V2版本
        unified_news_tool = create_unified_news_tool_v2(
            toolkit,
            use_news_engine=True  # 可通过配置控制
        )
        
        # ... 其他代码 ...
```

#### 2.3 添加配置开关

在 `config/settings.json` 中添加配置：

```json
{
  "news": {
    "use_news_engine": true,
    "fallback_to_old": true,
    "default_hours_back": 6,
    "max_news": 10
  }
}
```

### Phase 3: 测试阶段（2-3天）

#### 3.1 单元测试

创建测试用例 `tests/test_news_analyst_migration.py`：

```python
import pytest
from tradingagents.tools.unified_news_tool_v2 import create_unified_news_tool_v2

def test_a_share_news():
    """测试A股新闻获取"""
    # ... 测试代码 ...
    pass

def test_hk_share_news():
    """测试港股新闻获取"""
    # ... 测试代码 ...
    pass

def test_us_share_news():
    """测试美股新闻获取"""
    # ... 测试代码 ...
    pass

def test_fallback_mechanism():
    """测试降级机制"""
    # ... 测试代码 ...
    pass
```

运行测试：

```bash
pytest tests/test_news_analyst_migration.py -v
```

#### 3.2 集成测试

在完整的交易流程中测试：

```bash
# 运行完整分析
python main.py --ticker 000002 --mode analysis

# 检查日志
tail -f logs/tradingagents.log | grep "新闻分析师"
```

#### 3.3 性能测试

```bash
# 压力测试（10个并发请求）
python scripts/stress_test_news.py --concurrent 10 --stocks "000002,600000,0700.HK,AAPL"
```

### Phase 4: 灰度发布（1-2周）

#### 4.1 小规模灰度（10%）

通过配置控制灰度比例：

```python
# 在 unified_news_tool_v2.py 中
import random

def create_unified_news_tool_v2(toolkit):
    # 10% 流量使用新版
    use_news_engine = random.random() < 0.1
    
    analyzer = UnifiedNewsAnalyzerV2(toolkit, use_news_engine)
    # ...
```

监控指标：
- 成功率 > 95%
- 响应时间 < 3秒
- 错误率 < 5%

#### 4.2 中规模灰度（50%）

调整灰度比例为 50%：

```python
use_news_engine = random.random() < 0.5
```

持续监控1周。

#### 4.3 全量发布（100%）

确认无问题后，全量切换：

```python
use_news_engine = True  # 始终使用新版
```

清理旧代码路径（保留备用）。

## 📊 监控与告警

### 监控指标

#### 核心指标

```python
# 在 unified_news_tool_v2.py 中添加指标收集
import time
from collections import defaultdict

class MetricsCollector:
    def __init__(self):
        self.metrics = defaultdict(list)
    
    def record_success(self, stock_type, source, elapsed_time):
        self.metrics[f"{stock_type}_{source}_success"].append(1)
        self.metrics[f"{stock_type}_{source}_time"].append(elapsed_time)
    
    def record_failure(self, stock_type, source):
        self.metrics[f"{stock_type}_{source}_failure"].append(1)
    
    def get_success_rate(self, stock_type, source):
        success = len(self.metrics[f"{stock_type}_{source}_success"])
        failure = len(self.metrics[f"{stock_type}_{source}_failure"])
        total = success + failure
        return success / total if total > 0 else 0
```

#### 告警规则

| 指标 | 阈值 | 告警级别 |
|------|------|---------|
| 成功率 < 85% | 持续1小时 | 🔴 严重 |
| 响应时间 > 10秒 | 持续30分钟 | 🟠 警告 |
| 错误率 > 20% | 持续30分钟 | 🟠 警告 |
| 数据源全部失败 | 立即 | 🔴 严重 |

### 日志分析

查看关键日志：

```bash
# 查看成功率
grep "统一新闻工具V2" logs/tradingagents.log | grep "成功" | wc -l

# 查看失败情况
grep "统一新闻工具V2" logs/tradingagents.log | grep "失败"

# 查看响应时间
grep "统一新闻工具V2" logs/tradingagents.log | grep "耗时"
```

## 🔙 回滚方案

### 触发条件

满足以下任一条件立即回滚：

1. 成功率 < 85%（持续1小时）
2. 响应时间 > 10秒（持续30分钟）
3. 错误率 > 20%（持续30分钟）
4. A股新闻获取完全失败

### 回滚步骤

#### 方案A: 配置开关回滚（推荐）

```python
# 在 news_analyst.py 中
unified_news_tool = create_unified_news_tool_v2(
    toolkit,
    use_news_engine=False  # 紧急关闭新版
)
```

#### 方案B: 代码回滚

```python
# 切换回旧版
from tradingagents.tools.unified_news_tool import create_unified_news_tool

unified_news_tool = create_unified_news_tool(toolkit)
```

#### 方案C: 热重载

```bash
# 修改配置文件
echo '{"news": {"use_news_engine": false}}' > config/news_override.json

# 重启服务
systemctl restart tradingagents-web
```

### 验证回滚成功

```bash
# 检查成功率恢复
python scripts/test_news_migration.py --batch

# 查看日志确认使用旧版
tail -f logs/tradingagents.log | grep "旧版"
```

## 📈 优化建议

### 短期优化（1-2周内）

1. **增加缓存**
   ```python
   from functools import lru_cache
   
   @lru_cache(maxsize=100)
   def get_cached_news(stock_code, date):
       # 缓存新闻数据，避免重复请求
       pass
   ```

2. **并行获取**
   ```python
   import asyncio
   
   async def get_news_parallel(stock_codes):
       tasks = [get_stock_news(code) for code in stock_codes]
       return await asyncio.gather(*tasks)
   ```

3. **智能重试**
   ```python
   from tenacity import retry, stop_after_attempt, wait_exponential
   
   @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
   def get_news_with_retry(stock_code):
       return get_stock_news(stock_code)
   ```

### 中期优化（1-2个月内）

1. **动态数据源选择**
   - 根据历史成功率动态调整数据源优先级
   - 自动禁用长期失败的数据源

2. **新闻质量评分**
   - 评估新闻的信息量和价值
   - 过滤低质量新闻

3. **用户反馈循环**
   - 收集用户对新闻质量的反馈
   - 优化相关性算法

### 长期优化（3-6个月内）

1. **机器学习模型**
   - 训练新闻相关性预测模型
   - 自动分类新闻重要程度

2. **实时流处理**
   - 使用消息队列处理新闻流
   - 实时推送重要新闻

3. **多语言支持**
   - 支持英文、中文新闻混合
   - 自动翻译关键新闻

## ❓ 常见问题

### Q1: news_engine 没有返回新闻怎么办？

**A**: 检查以下几点：
1. API密钥是否正确配置
2. 网络连接是否正常
3. 数据源是否有API限流
4. 查看详细日志定位问题

```bash
# 查看详细日志
tail -f logs/tradingagents.log | grep "news_engine"
```

### Q2: 新版响应时间比旧版慢？

**A**: 可能原因：
1. 重试机制增加了延迟（在失败时）
2. 多个Provider顺序调用
3. 网络延迟

优化方案：
- 调整重试策略
- 使用并行请求
- 添加缓存

### Q3: 如何临时禁用news_engine？

**A**: 两种方法：

方法1 - 配置文件：
```json
{
  "news": {
    "use_news_engine": false
  }
}
```

方法2 - 环境变量：
```bash
export USE_NEWS_ENGINE=false
```

### Q4: 新版和旧版可以同时运行吗？

**A**: 可以，推荐的混合模式就是同时使用两者。新版失败时自动降级到旧版。

### Q5: 如何判断当前使用的是哪个版本？

**A**: 查看日志：

```bash
# 查看数据源信息
grep "新闻数据来源" logs/tradingagents.log

# 新版会显示：news_engine
# 旧版会显示：东方财富、Google新闻等
```

## 📚 参考资料

### 内部文档
- [迁移评估报告](./news_engine_migration_evaluation.md)
- [新闻模块架构设计](./新闻模块架构设计.md)
- [新闻功能定义](./news_func_def.md)

### 外部资源
- [AKShare文档](https://akshare.akfamily.xyz/)
- [Tushare文档](https://tushare.pro/document/2)
- [FinnHub API文档](https://finnhub.io/docs/api)
- [EODHD API文档](https://eodhistoricaldata.com/financial-apis/)

## 📞 技术支持

如有问题，请联系：
- 📧 Email: support@example.com
- 💬 Slack: #trading-agents-news
- 📝 Issues: GitHub Issues

---

**文档版本**: v1.0  
**最后更新**: 2025-11-26  
**维护者**: AI Assistant

