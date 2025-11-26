#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TradingAgents News Engine

模块化新闻数据获取系统,支持A股、港股、美股等多个市场的新闻数据获取。

主要组件:
- NewsConfig: 新闻配置管理
- NewsAggregator: 新闻聚合器
- get_stock_news: 统一新闻获取接口
"""

from .config import NewsConfig, get_news_config, get_news_config_manager
from .aggregator import NewsAggregator, get_stock_news
from .models import NewsItem, NewsSource, MarketType

__version__ = "1.0.0"

__all__ = [
    # 配置
    "NewsConfig",
    "get_news_config",
    "get_news_config_manager",
    
    # 聚合器
    "NewsAggregator",
    "get_stock_news",
    
    # 模型
    "NewsItem",
    "NewsSource",
    "MarketType",
]