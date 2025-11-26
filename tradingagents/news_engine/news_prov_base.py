#!/usr/bin/env python3
"""
News Provider Base Class

新闻提供者基类
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional
import re

from .models import NewsItem, NewsSource, NewsUrgency, MarketType
from .config import get_news_config
from tradingagents.utils.logging_manager import get_logger

logger = get_logger('news_engine.providers')


class NewsProvider(ABC):
    """新闻提供者基类"""
    
    def __init__(self, source: NewsSource):
        """
        初始化新闻提供器
        
        Args:
            source: 新闻来源
        """
        self.source = source
        self.config = get_news_config()
        self.connected = False
    
    @abstractmethod
    def get_news(
        self,
        stock_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        max_news: int = 10
    ) -> List[NewsItem]:
        """
        获取新闻数据
        
        Args:
            stock_code: 股票代码
            start_date: 开始日期(YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            max_news: 最大新闻数量
            
        Returns:
            新闻项目列表
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """检查数据源是否可用"""
        pass
    
    def identify_market_type(self, stock_code: str) -> MarketType:
        """
        识别股票市场类型
        
        Args:
            stock_code: 股票代码
            
        Returns:
            市场类型
        """
        stock_code = stock_code.upper().strip()
        
        # A股判断
        if re.match(r'^(00|30|60|68)\d{4}$', stock_code):
            return MarketType.A_SHARE
        elif re.match(r'^(SZ|SH)\d{6}$', stock_code):
            return MarketType.A_SHARE
        
        # 港股判断
        elif re.match(r'^\d{4,5}\.HK$', stock_code):
            return MarketType.HK_SHARE
        elif re.match(r'^\d{4,5}$', stock_code) and len(stock_code) <= 5:
            return MarketType.HK_SHARE
        
        # 美股判断
        elif re.match(r'^[A-Z]{1,5}$', stock_code):
            return MarketType.US_SHARE
        elif '.' in stock_code and not stock_code.endswith('.HK'):
            return MarketType.US_SHARE
        
        return MarketType.UNKNOWN
    
    def assess_urgency(self, title: str, content: str) -> NewsUrgency:
        """
        评估新闻紧急程度
        
        Args:
            title: 新闻标题
            content: 新闻内容
            
        Returns:
            紧急程度
        """
        text = (title + ' ' + content).lower()
        
        # 高紧急度关键词
        high_keywords = [
            'breaking', 'urgent', 'alert', 'emergency', 'halt', 'suspend',
            '突发', '紧急', '暂停', '停牌', '重大', '警告'
        ]
        
        # 中等紧急度关键词
        medium_keywords = [
            'earnings', 'report', 'announce', 'launch', 'merger', 'acquisition',
            '财报', '发布', '宣布', '并购', '收购', '业绩'
        ]
        
        for keyword in high_keywords:
            if keyword in text:
                return NewsUrgency.HIGH
        
        for keyword in medium_keywords:
            if keyword in text:
                return NewsUrgency.MEDIUM
        
        return NewsUrgency.LOW
    
    def calculate_relevance(self, title: str, stock_code: str) -> float:
        """
        计算新闻相关性分数
        
        Args:
            title: 新闻标题
            stock_code: 股票代码
            
        Returns:
            相关性分数(0.0-1.0)
        """
        text = title.lower()
        ticker_lower = stock_code.lower()
        
        # 股票代码直接出现
        if ticker_lower in text:
            return 1.0
        
        # 提取纯数字部分
        pure_code = ''.join(filter(str.isdigit, stock_code))
        if pure_code and pure_code in text:
            return 0.9
        
        return 0.3
