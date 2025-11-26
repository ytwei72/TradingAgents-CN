# 调试港股新闻获取问题

## 问题描述

在测试港股 (9988.HK) 新闻获取时发现以下问题:

1. **AKShare 新闻获取失败**: `Expecting value: line 1 column 1 (char 0)` - JSON 解析错误
2. **FinnHub 新闻获取失败**: `403 Client Error: Forbidden` - 可能是反爬或 API 限制
3. **Tushare 新闻获取**: 没有任何信息输出，无法判断是否成功或失败

## 优化目标

1. **AKShare**: 添加详细的响应日志，包括响应码、响应内容，以便定位问题
2. **FinnHub**: 检查并优化重试机制，处理 403 错误
3. **Tushare**: 添加完整的日志输出，包括成功获取的新闻数量和错误信息

## 修改方案

### AKShare Provider ([news_prov_akshare.py](file:///e:/Develop/AI-Agents/TradingAgents/tradingagents/news_engine/news_prov_akshare.py))

#### 问题分析
当前代码直接调用 `self.ak.stock_news_em(symbol=clean_code)`，如果 AKShare 内部返回的不是有效 JSON，会抛出 JSON 解析错误，但没有记录原始响应内容。

#### 修改内容
1. 在 `get_news` 方法中添加异常捕获，记录详细的错误信息
2. 尝试捕获 AKShare 内部的 HTTP 响应（如果可能）
3. 添加响应数据的日志输出，包括:
   - API 调用参数
   - 响应状态码（如果可访问）
   - 响应内容的前 500 字符
   - 完整的异常堆栈

---

### 集中式重试机制 ([aggregator.py](file:///e:/Develop/AI-Agents/TradingAgents/tradingagents/news_engine/aggregator.py))

#### 问题分析
当前各个 provider 的 `get_news` 方法直接调用 API，没有统一的重试机制。403 错误和其他网络问题可能是:
- API 速率限制
- 临时网络故障
- 服务器过载
- 反爬虫机制

#### 修改内容
1. **在 aggregator.py 中实现集中式重试机制**:
   - 在 `NewsAggregator` 类中添加 `_call_provider_with_retry` 方法
   - 使用装饰器模式包装 provider 的 `get_news` 调用
   - 实现指数退避策略（exponential backoff）
   - 根据 HTTP 状态码决定是否重试:
     - **可重试**: 403 (Forbidden), 429 (Too Many Requests), 500, 502, 503, 504
     - **不可重试**: 400, 401, 404
   
2. **配置化重试参数**:
   - 在 `.env.news.example` 中添加 `NEWS_RETRY_STATUS_CODES` 配置
   - 使用现有的 `NEWS_MAX_RETRIES` 和 `NEWS_RETRY_DELAY` 配置
   - 在 `NewsConfig` 中添加 `retry_status_codes` 字段
   
3. **增强错误日志**:
   - 记录每次重试的详细信息（第几次重试、等待时间）
   - 对不可重试的错误（如 403）记录详细信息
   - 记录请求 URL、参数和响应内容

4. **修改 aggregator.py 的 get_news 方法**:
   - 将第 138-143 行的 `provider.get_news()` 调用改为通过重试机制调用
   - 捕获并记录所有异常

---

### FinnHub Provider ([news_prov_finnhub.py](file:///e:/Develop/AI-Agents/TradingAgents/tradingagents/news_engine/news_prov_finnhub.py))

#### 修改内容
1. **增强错误处理**:
   - 对 HTTP 错误进行特殊处理，抛出包含状态码的异常
   - 记录请求 URL 和参数
   - 记录响应状态码和内容（前 500 字符）
   - 将 `requests.HTTPError` 重新抛出，以便 aggregator 的重试机制处理

---

### Tushare Provider ([news_prov_tushare.py](file:///e:/Develop/AI-Agents/TradingAgents/tradingagents/news_engine/news_prov_tushare.py))

#### 问题分析
当前代码在第 66 行有 `TODO` 注释，实际没有实现新闻获取逻辑，只是返回空列表。没有任何日志输出表明是否尝试获取新闻。

#### 修改内容
1. **添加详细日志**:
   - 记录开始获取新闻的信息（股票代码、时间范围）
   - 记录 API 调用结果（成功/失败）
   - 记录获取到的新闻数量
   - 如果为空，明确记录"未获取到新闻"

2. **实现新闻获取逻辑**（如果 Tushare API 支持）:
   - 调用 Tushare 的新闻接口（需要确认 API 是否支持港股）
   - 解析返回的数据
   - 转换为 `NewsItem` 对象

3. **错误处理**:
   - 捕获所有异常并记录详细信息
   - 区分"API 不支持"和"获取失败"两种情况

## 验证计划

### 自动化测试
运行 `test_news.py` 中的 `test_comprehensive_news` 测试，特别关注港股 9988.HK 的测试结果。

### 日志验证
检查日志输出是否包含:
1. **重试机制**: 重试次数、等待时间、最终成功/失败状态
2. **AKShare**: 响应状态码、响应内容片段、详细错误信息
3. **FinnHub**: HTTP 状态码、响应内容、403 错误的详细信息
4. **Tushare**: 明确的"开始获取"、"获取结果"或"获取失败"日志

### 手动验证
1. 检查 AKShare API 是否支持港股代码格式
2. 验证 FinnHub API Key 是否有效
3. 确认 Tushare 是否支持港股新闻查询
4. 测试重试机制是否正确处理不同的 HTTP 状态码
