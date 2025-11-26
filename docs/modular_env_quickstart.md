# 模块化环境变量配置 - 快速入门

## 5 分钟快速上手

### 1. 创建 News 模块配置文件

```bash
cd tradingagents/dataflows
cp .env.news.example .env
```

### 2. 编辑配置文件

编辑 `tradingagents/dataflows/.env`:

```bash
# 启用你需要的新闻源
NEWS_FINNHUB_ENABLED=true
NEWS_NEWSAPI_ENABLED=true

# 配置 API 密钥
NEWSAPI_KEY=your_actual_newsapi_key_here

# 调整默认参数
NEWS_DEFAULT_HOURS_BACK=12
NEWS_DEFAULT_MAX_NEWS=20
```

### 3. 在代码中使用

```python
from tradingagents.dataflows.news_config import get_news_config

# 获取配置
config = get_news_config()

# 使用配置
print(f"FinnHub 启用: {config.finnhub_enabled}")
print(f"默认回溯时间: {config.default_hours_back} 小时")
print(f"最大新闻数: {config.default_max_news} 条")
```

### 4. 运行测试

```bash
.venv\Scripts\python.exe tests/test_modular_env.py
```

## 常用场景

### 场景 1: 只启用特定新闻源

```bash
# 在 .env 中
NEWS_FINNHUB_ENABLED=true
NEWS_AKSHARE_ENABLED=true
NEWS_NEWSAPI_ENABLED=false
NEWS_ALPHA_VANTAGE_ENABLED=false
```

### 场景 2: 调整缓存策略

```bash
# 启用缓存,1小时过期
NEWS_CACHE_ENABLED=true
NEWS_CACHE_EXPIRY=3600

# 或禁用缓存
NEWS_CACHE_ENABLED=false
```

### 场景 3: 开发调试

```bash
# 启用详细日志
NEWS_LOG_LEVEL=DEBUG
NEWS_VERBOSE_LOGGING=true
```

## 配置优先级

```
模块配置 > 全局配置 > 默认值
```

**示例**:
- 全局 `.env`: `FINNHUB_API_KEY=global_key`
- 模块 `.env`: `FINNHUB_API_KEY=module_key`
- **结果**: 使用 `module_key`

## 完整文档

- [使用文档](./modular_env_config.md) - 详细使用指南
- [实现文档](./modular_env_implementation.md) - 技术实现细节
- [示例代码](../examples/modular_env_example.py) - 完整示例

## 需要帮助?

查看 [故障排查](./modular_env_config.md#故障排查) 部分或运行示例代码:

```bash
.venv\Scripts\python.exe examples/modular_env_example.py
```
