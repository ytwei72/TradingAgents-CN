# 模块化环境变量配置使用指南

## 概述

TradingAgents-CN 现在支持**模块化环境变量配置**,允许每个模块拥有自己的 `.env` 文件,同时保持与全局 `.env` 的兼容性。

## 配置优先级

配置加载的优先级顺序为:

```
模块级 .env > 全局 .env > 系统环境变量 > 默认值
```

这意味着:
1. 模块级配置会覆盖全局配置
2. 全局配置会覆盖系统环境变量
3. 如果都未配置,则使用代码中的默认值

## 目录结构

```
TradingAgents/
├── .env                          # 全局环境变量配置
├── tradingagents/
│   ├── utils/
│   │   └── env_loader.py        # 模块化环境变量加载器
│   ├── dataflows/
│   │   ├── .env                 # dataflows 模块的环境变量(可选)
│   │   ├── .env.news.example    # news 配置示例
│   │   ├── news_config.py       # news 配置管理器
│   │   └── realtime_news_utils.py
│   └── agents/
│       └── .env                 # agents 模块的环境变量(可选)
```

## 使用方法

### 方法 1: 使用配置管理器(推荐)

这是最简单和推荐的方式,适用于 news 模块:

```python
from tradingagents.dataflows.news_config import get_news_config

# 获取配置
config = get_news_config()

# 使用配置
if config.finnhub_enabled and config.finnhub_key:
    # 使用 FinnHub API
    pass

print(f"默认回溯时间: {config.default_hours_back} 小时")
print(f"最大新闻数: {config.default_max_news} 条")
```

### 方法 2: 直接使用环境变量加载器

适用于其他模块或自定义场景:

```python
from tradingagents.utils.env_loader import ModularEnvLoader
from pathlib import Path

# 方式 1: 通过模块名称加载
loader = ModularEnvLoader(module_name="dataflows")
loader.load_env(verbose=True)

# 方式 2: 通过模块路径加载
module_path = Path(__file__).parent
loader = ModularEnvLoader(module_path=module_path)
loader.load_env(verbose=True)

# 获取环境变量
api_key = loader.get_env('NEWSAPI_KEY')
enabled = loader.get_env_bool('NEWS_FINNHUB_ENABLED', default=True)
max_news = loader.get_env_int('NEWS_DEFAULT_MAX_NEWS', default=10)
```

### 方法 3: 使用便捷函数

```python
from tradingagents.utils.env_loader import load_module_env

# 加载指定模块的环境变量
loaded_vars = load_module_env('dataflows', verbose=True)

# 之后可以直接使用 os.getenv()
import os
api_key = os.getenv('NEWSAPI_KEY')
```

## 配置 News 模块

### 1. 创建模块级配置文件

```bash
# 复制示例文件
cd tradingagents/dataflows
cp .env.news.example .env
```

### 2. 编辑配置文件

编辑 `tradingagents/dataflows/.env` 文件:

```bash
# News 模块环境变量配置

# API 密钥
NEWSAPI_KEY=your_actual_newsapi_key
ALPHA_VANTAGE_API_KEY=your_actual_alpha_vantage_key

# 数据源启用状态
NEWS_FINNHUB_ENABLED=true
NEWS_ALPHA_VANTAGE_ENABLED=true
NEWS_NEWSAPI_ENABLED=true
NEWS_TUSHARE_ENABLED=true
NEWS_AKSHARE_ENABLED=true

# 获取配置
NEWS_DEFAULT_HOURS_BACK=12
NEWS_DEFAULT_MAX_NEWS=20
NEWS_RELEVANCE_THRESHOLD=0.5

# 缓存配置
NEWS_CACHE_ENABLED=true
NEWS_CACHE_EXPIRY=3600
```

### 3. 在代码中使用

```python
from tradingagents.dataflows.news_config import get_news_config_manager

# 获取配置管理器
config_manager = get_news_config_manager(verbose=True)

# 打印配置(用于调试)
config_manager.print_config()

# 获取配置对象
config = config_manager.get_config()

# 使用配置
if config.newsapi_enabled and config.newsapi_key:
    # 使用 NewsAPI
    pass
```

## 配置项说明

### API 密钥

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `NEWSAPI_KEY` | NewsAPI 密钥 | 无 |
| `ALPHA_VANTAGE_API_KEY` | Alpha Vantage 密钥 | 无 |
| `FINNHUB_API_KEY` | FinnHub 密钥(继承自全局) | 无 |

### 数据源启用状态

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `NEWS_FINNHUB_ENABLED` | 启用 FinnHub | true |
| `NEWS_ALPHA_VANTAGE_ENABLED` | 启用 Alpha Vantage | false |
| `NEWS_NEWSAPI_ENABLED` | 启用 NewsAPI | false |
| `NEWS_TUSHARE_ENABLED` | 启用 Tushare | true |
| `NEWS_AKSHARE_ENABLED` | 启用 AKShare | true |
| `NEWS_EODHD_ENABLED` | 启用 EODHD | false |
| `NEWS_CLS_RSS_ENABLED` | 启用财联社 RSS | true |

### 获取配置

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `NEWS_DEFAULT_HOURS_BACK` | 默认回溯时间(小时) | 6 |
| `NEWS_DEFAULT_MAX_NEWS` | 默认最大新闻数量 | 10 |
| `NEWS_RELEVANCE_THRESHOLD` | 新闻相关性阈值(0.0-1.0) | 0.3 |
| `NEWS_FRESHNESS_THRESHOLD` | 新闻时效性阈值(分钟) | 60 |

### 缓存配置

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `NEWS_CACHE_ENABLED` | 启用新闻缓存 | true |
| `NEWS_CACHE_EXPIRY` | 缓存过期时间(秒) | 1800 |
| `NEWS_CACHE_DIR` | 缓存目录 | ./cache/news |

### 日志配置

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `NEWS_LOG_LEVEL` | 日志级别 | INFO |
| `NEWS_VERBOSE_LOGGING` | 启用详细日志 | false |

### 高级配置

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `NEWS_REQUEST_TIMEOUT` | 请求超时时间(秒) | 10 |
| `NEWS_MAX_RETRIES` | 最大重试次数 | 3 |
| `NEWS_RETRY_DELAY` | 重试延迟(秒) | 1 |
| `NEWS_RATE_LIMIT` | API 请求限流(请求/秒) | 5 |

## 为其他模块创建配置

### 1. 创建模块的 .env 文件

在模块目录下创建 `.env` 文件:

```bash
# 示例: 为 agents 模块创建配置
cd tradingagents/agents
touch .env
```

### 2. 添加模块特定的配置

```bash
# Agents 模块环境变量配置

# Agent 配置
AGENT_MAX_ITERATIONS=10
AGENT_TIMEOUT=300
AGENT_VERBOSE=true

# 模型配置(覆盖全局配置)
DASHSCOPE_API_KEY=your_agent_specific_key
```

### 3. 在代码中加载

```python
from tradingagents.utils.env_loader import ModularEnvLoader
from pathlib import Path

# 在模块初始化时加载环境变量
module_path = Path(__file__).parent
loader = ModularEnvLoader(module_path=module_path)
loader.load_env(verbose=True)

# 获取配置
max_iterations = loader.get_env_int('AGENT_MAX_ITERATIONS', 10)
timeout = loader.get_env_int('AGENT_TIMEOUT', 300)
verbose = loader.get_env_bool('AGENT_VERBOSE', False)
```

## 最佳实践

### 1. 配置文件组织

- **全局配置**: 放在项目根目录的 `.env` 文件中
- **模块配置**: 放在模块目录下的 `.env` 文件中
- **示例文件**: 使用 `.env.example` 或 `.env.{module}.example` 命名

### 2. 配置命名规范

- 模块特定配置使用前缀,如 `NEWS_`, `AGENT_`, `DATA_`
- 全局配置不使用前缀,如 `DASHSCOPE_API_KEY`
- 使用大写字母和下划线,如 `NEWS_MAX_RETRIES`

### 3. 安全性

- 不要将 `.env` 文件提交到 Git
- 提供 `.env.example` 文件作为模板
- 敏感信息(API 密钥)只放在 `.env` 文件中

### 4. 文档

- 为每个配置项添加注释说明
- 提供默认值和可选值范围
- 说明配置项的用途和影响

## 故障排查

### 配置未生效

1. 检查 `.env` 文件是否存在
2. 检查配置项名称是否正确
3. 检查是否调用了 `load_env()`
4. 使用 `verbose=True` 查看加载日志

### 配置冲突

1. 检查全局和模块级配置的优先级
2. 使用 `print_config()` 查看最终配置
3. 检查是否有多个地方加载了环境变量

### 类型转换错误

1. 检查配置值格式是否正确
2. 使用正确的获取方法(`get_env_bool`, `get_env_int` 等)
3. 查看日志中的警告信息

## 示例代码

完整的使用示例请参考:

- `tradingagents/dataflows/news_config.py` - News 配置管理器
- `tradingagents/utils/env_loader.py` - 环境变量加载器
- `examples/modular_env_example.py` - 完整示例(待创建)

## 迁移指南

### 从全局配置迁移到模块配置

1. **识别模块特定配置**:
   ```python
   # 原来在全局 .env 中
   NEWSAPI_KEY=xxx
   ```

2. **创建模块配置文件**:
   ```bash
   cd tradingagents/dataflows
   touch .env
   ```

3. **移动配置**:
   ```bash
   # 在 tradingagents/dataflows/.env 中
   NEWSAPI_KEY=xxx
   NEWS_DEFAULT_MAX_NEWS=20
   ```

4. **更新代码**:
   ```python
   # 原来
   import os
   api_key = os.getenv('NEWSAPI_KEY')
   
   # 现在
   from tradingagents.dataflows.news_config import get_news_config
   config = get_news_config()
   api_key = config.newsapi_key
   ```

## 常见问题

**Q: 模块配置会完全替代全局配置吗?**

A: 不会。模块配置只会覆盖同名的配置项,其他配置仍然从全局继承。

**Q: 可以在运行时修改配置吗?**

A: 可以通过修改环境变量或调用 `reload_config()` 重新加载配置。

**Q: 如何禁用模块配置?**

A: 删除或重命名模块目录下的 `.env` 文件即可。

**Q: 配置加载会影响性能吗?**

A: 不会。环境变量只在模块初始化时加载一次,并有缓存机制。

## 相关资源

- [python-dotenv 文档](https://github.com/theskumar/python-dotenv)
- [环境变量最佳实践](https://12factor.net/config)
- [TradingAgents-CN 配置指南](../README.md)
