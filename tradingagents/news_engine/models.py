#!/usr/bin/env python3
"""
News Module Data Models

定义新闻模块使用的数据模型
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class MarketType(Enum):
    """市场类型枚举"""
    A_SHARE = "A股"
    HK_SHARE = "港股"
    US_SHARE = "美股"
    UNKNOWN = "未知"


class NewsSource(Enum):
    """新闻来源枚举"""
    TUSHARE = "Tushare"
    AKSHARE = "AKShare"
    FINNHUB = "FinnHub"
    EODHD = "EODHD"
    NEWSAPI = "NewsAPI"
    ALPHA_VANTAGE = "Alpha Vantage"
    GOOGLE_NEWS = "Google News"
    DONGFANG_FORTUNE = "东方财富"
    SINA_FINANCE = "新浪财经"
    CLS_RSS = "财联社"
    UNKNOWN = "未知"


class NewsUrgency(Enum):
    """新闻紧急程度枚举"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class NewsItem:
    """
    新闻项目数据结构
    
    Attributes:
        title: 新闻标题
        content: 新闻内容
        source: 新闻来源
        publish_time: 发布时间
        url: 新闻链接
        urgency: 紧急程度 (high/medium/low)
        relevance_score: 相关性分数 (0.0-1.0)
        stock_code: 关联股票代码
        keywords: 关键词列表
        sentiment: 情绪分析 (positive/negative/neutral)
    """
    title: str
    content: str
    source: NewsSource
    publish_time: datetime
    url: str = ""
    urgency: NewsUrgency = NewsUrgency.LOW
    relevance_score: float = 0.0
    stock_code: Optional[str] = None
    keywords: Optional[list] = None
    sentiment: Optional[str] = None
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "title": self.title,
            "content": self.content,
            "source": self.source.value if isinstance(self.source, NewsSource) else str(self.source),
            "publish_time": self.publish_time.isoformat() if isinstance(self.publish_time, datetime) else str(self.publish_time),
            "url": self.url,
            "urgency": self.urgency.value if isinstance(self.urgency, NewsUrgency) else str(self.urgency),
            "relevance_score": self.relevance_score,
            "stock_code": self.stock_code,
            "keywords": self.keywords,
            "sentiment": self.sentiment,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "NewsItem":
        """从字典创建"""
        # 处理枚举类型
        if isinstance(data.get("source"), str):
            try:
                data["source"] = NewsSource[data["source"].upper()]
            except (KeyError, AttributeError):
                data["source"] = NewsSource.UNKNOWN
        
        if isinstance(data.get("urgency"), str):
            try:
                data["urgency"] = NewsUrgency[data["urgency"].upper()]
            except (KeyError, AttributeError):
                data["urgency"] = NewsUrgency.LOW
        
        # 处理时间
        if isinstance(data.get("publish_time"), str):
            data["publish_time"] = datetime.fromisoformat(data["publish_time"])
        
        return cls(**data)
    
    def __str__(self) -> str:
        """字符串表示"""
        return f"NewsItem(title='{self.title[:30]}...', source={self.source.value}, time={self.publish_time})"
    
    def __repr__(self) -> str:
        """详细表示"""
        return self.__str__()


@dataclass
class NewsQuery:
    """
    新闻查询参数
    
    Attributes:
        stock_code: 股票代码
        start_date: 开始日期
        end_date: 结束日期
        max_news: 最大新闻数量
        hours_back: 回溯小时数
        market_type: 市场类型
        sources: 指定新闻来源列表
        min_relevance: 最小相关性分数
    """
    stock_code: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    max_news: int = 10
    hours_back: int = 6
    market_type: Optional[MarketType] = None
    sources: Optional[list] = None
    min_relevance: float = 0.0
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "stock_code": self.stock_code,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "max_news": self.max_news,
            "hours_back": self.hours_back,
            "market_type": self.market_type.value if self.market_type else None,
            "sources": [s.value if isinstance(s, NewsSource) else s for s in self.sources] if self.sources else None,
            "min_relevance": self.min_relevance,
        }


@dataclass
class NewsResponse:
    """
    新闻响应数据结构
    
    Attributes:
        news_items: 新闻项目列表
        total_count: 总数量
        query: 查询参数
        sources_used: 实际使用的数据源
        fetch_time: 获取时间
        success: 是否成功
        error_message: 错误信息
    """
    news_items: list
    total_count: int
    query: NewsQuery
    sources_used: list
    fetch_time: datetime
    success: bool = True
    error_message: Optional[str] = None
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "news_items": [item.to_dict() if hasattr(item, 'to_dict') else item for item in self.news_items],
            "total_count": self.total_count,
            "query": self.query.to_dict() if hasattr(self.query, 'to_dict') else self.query,
            "sources_used": [s.value if isinstance(s, NewsSource) else s for s in self.sources_used],
            "fetch_time": self.fetch_time.isoformat() if isinstance(self.fetch_time, datetime) else str(self.fetch_time),
            "success": self.success,
            "error_message": self.error_message,
        }
    
    def format_report(self) -> str:
        """格式化为报告"""
        if not self.success:
            return f"❌ 新闻获取失败: {self.error_message}"
        
        if not self.news_items:
            return f"⚠️ 未找到 {self.query.stock_code} 的相关新闻"
        
        report = f"# {self.query.stock_code} 新闻报告\n\n"
        report += f"📅 获取时间: {self.fetch_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        report += f"📊 新闻总数: {self.total_count} 条\n"
        report += f"🔍 数据源: {', '.join([s.value if isinstance(s, NewsSource) else s for s in self.sources_used])}\n\n"
        
        # 按紧急程度分类
        high_urgency = [n for n in self.news_items if n.urgency == NewsUrgency.HIGH]
        medium_urgency = [n for n in self.news_items if n.urgency == NewsUrgency.MEDIUM]
        low_urgency = [n for n in self.news_items if n.urgency == NewsUrgency.LOW]
        
        if high_urgency:
            report += "## 🚨 紧急新闻\n\n"
            for news in high_urgency[:3]:
                report += f"### {news.title}\n"
                report += f"**来源**: {news.source.value} | **时间**: {news.publish_time.strftime('%Y-%m-%d %H:%M')}\n"
                report += f"{news.content[:200]}...\n\n"
        
        if medium_urgency:
            report += "## 📢 重要新闻\n\n"
            for news in medium_urgency[:5]:
                report += f"### {news.title}\n"
                report += f"**来源**: {news.source.value} | **时间**: {news.publish_time.strftime('%Y-%m-%d %H:%M')}\n"
                report += f"{news.content[:150]}...\n\n"
        
        return report
