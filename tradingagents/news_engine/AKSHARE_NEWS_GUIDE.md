# AkShare 新闻源配置指南

## 概述

项目现在支持三个独立的 AkShare 新闻源,可以通过 `.env` 文件单独控制每个源的开关。

## 可用的新闻源

### 1. 财联社电报 (CLS)
- **函数**: `akshare.stock_info_global_cls()`
- **配置**: `NEWS_AKSHARE_CLS_ENABLED`
- **特点**: 实时财经电报,更新频繁
- **默认**: 启用

### 2. 新浪财经全球财经 (Sina Finance)
- **函数**: `akshare.stock_info_global_sina()`
- **配置**: `NEWS_AKSHARE_SINA_ENABLED`
- **特点**: 全球财经快讯
- **默认**: 启用

### 3. 东方财富全球财经 (EastMoney)
- **函数**: `akshare.stock_info_global_em()`
- **配置**: `NEWS_AKSHARE_EM_ENABLED`
- **特点**: 包含文章链接,内容较详细
- **默认**: 禁用

## 配置方法

### 1. 编辑 `.env` 文件

在 `tradingagents/news_engine/.env` 中添加或修改:

```env
# AkShare 数据源细分配置
NEWS_AKSHARE_CLS_ENABLED=true      # 财联社
NEWS_AKSHARE_SINA_ENABLED=true     # 新浪财经
NEWS_AKSHARE_EM_ENABLED=false      # 东方财富
```

### 2. 配置示例

#### 仅使用财联社
```env
NEWS_AKSHARE_CLS_ENABLED=true
NEWS_AKSHARE_SINA_ENABLED=false
NEWS_AKSHARE_EM_ENABLED=false
```

#### 使用所有源
```env
NEWS_AKSHARE_CLS_ENABLED=true
NEWS_AKSHARE_SINA_ENABLED=true
NEWS_AKSHARE_EM_ENABLED=true
```

#### 仅使用新浪和东方财富
```env
NEWS_AKSHARE_CLS_ENABLED=false
NEWS_AKSHARE_SINA_ENABLED=true
NEWS_AKSHARE_EM_ENABLED=true
```

## 使用方法

### 方法 1: 使用聚合器 (推荐)

```python
from tradingagents.news_engine.aggregator import NewsAggregator

# 创建聚合器(自动加载所有启用的提供器)
aggregator = NewsAggregator()

# 获取新闻
response = aggregator.get_news(
    stock_code="000001",
    max_news=10,
    hours_back=24
)

# 查看使用了哪些数据源
print(f"使用的数据源: {[s.value for s in response.sources_used]}")

# 访问新闻
for news in response.news_items:
    print(f"{news.title} - {news.source.value}")
```

### 方法 2: 直接使用单个提供器

```python
from tradingagents.news_engine.news_prov_akshare_cls import CLSNewsProvider
from tradingagents.news_engine.news_prov_akshare_sina import AkShareSinaNewsProvider
from tradingagents.news_engine.news_prov_akshare_em import AkShareEmNewsProvider

# 使用财联社
cls_provider = CLSNewsProvider()
if cls_provider.is_available():
    news = cls_provider.get_news(stock_code="000001", max_news=5)

# 使用新浪财经
sina_provider = AkShareSinaNewsProvider()
if sina_provider.is_available():
    news = sina_provider.get_news(stock_code="", max_news=5)  # 空代码获取通用新闻

# 使用东方财富
em_provider = AkShareEmNewsProvider()
if em_provider.is_available():
    news = em_provider.get_news(stock_code="", max_news=5)
```

## 向后兼容性

旧代码仍然可以使用:

```python
# 这两种方式都可以
from tradingagents.news_engine.news_prov_cls_rss import CLSRSSNewsProvider
from tradingagents.news_engine.news_prov_akshare_cls import CLSNewsProvider

# 它们是同一个类
provider1 = CLSRSSNewsProvider()
provider2 = CLSNewsProvider()
```

## 查看配置状态

```python
from tradingagents.news_engine.config import get_news_config_manager

manager = get_news_config_manager()
manager.print_config()
```

输出示例:
```
🔧 数据源状态:
  AKShare: ✅ 启用
    - 财联社: ✅ 启用
    - 新浪财经: ✅ 启用
    - 东方财富: ❌ 禁用
```

## 常见问题

### Q: 如何禁用某个新闻源?
A: 在 `.env` 文件中将对应的配置设为 `false`:
```env
NEWS_AKSHARE_SINA_ENABLED=false
```

### Q: 配置修改后需要重启吗?
A: 是的,需要重启应用程序以加载新的配置。

### Q: 如何添加新的 AkShare 新闻源?
A: 
1. 创建新的提供器类继承 `AkShareNewsProviderBase`
2. 实现 `_fetch_dataframe()` 和 `_get_column_mapping()`
3. 在 `config.py` 中添加配置字段
4. 在 `aggregator.py` 中注册提供器

### Q: 为什么某些新闻源没有返回结果?
A: 可能的原因:
- 新闻源被禁用(检查 `.env` 配置)
- 股票代码不匹配(某些源是通用新闻,不针对特定股票)
- 时间范围内没有相关新闻
- 网络问题或 API 限制

## 技术细节

### 架构
```
AkShareNewsProviderBase (基类)
├── CLSNewsProvider (财联社)
├── AkShareSinaNewsProvider (新浪财经)
└── AkShareEmNewsProvider (东方财富)
```

### 列映射

每个提供器定义自己的列映射:

**财联社**:
```python
{
    "title": "标题",
    "content": "内容",
    "date": "发布日期",
    "time": "发布时间",
}
```

**新浪财经**:
```python
{
    "title": "内容",      # 使用内容作为标题
    "content": "内容",
    "datetime": "时间",
}
```

**东方财富**:
```python
{
    "title": "标题",
    "content": "摘要",
    "datetime": "发布时间",
    "url": "链接",
}
```
