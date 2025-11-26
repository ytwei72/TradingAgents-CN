#!/usr/bin/env python3
"""
FinnHub News Provider

FinnHub 新闻提供器
"""

from datetime import datetime, timedelta
from typing import List, Optional

from .news_prov_base import NewsProvider
from .models import NewsItem, NewsSource
from tradingagents.utils.logging_manager import get_logger

logger = get_logger('news_engine.finnhub')


class FinnhubNewsProvider(NewsProvider):
    """FinnHub 新闻提供器"""
    
    def __init__(self):
        super().__init__(NewsSource.FINNHUB)
        self._check_connection()
    
    def _check_connection(self):
        """检查连接状态"""
        if not self.config.finnhub_enabled:
            logger.debug("FinnHub 数据源未启用")
            self.connected = False
            return
        
        if not self.config.finnhub_key:
            logger.warning("FinnHub API Key 未配置")
            self.connected = False
            return
        
        self.connected = True
        logger.debug("FinnHub 配置成功")
    
    def is_available(self) -> bool:
        return self.connected
    
    def get_news(
        self,
        stock_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        max_news: int = 10
    ) -> List[NewsItem]:
        """获取 FinnHub 新闻"""
        if not self.is_available():
            return []
        
        try:
            import requests
            
            logger.info(f"📝 FinnHub 获取 {stock_code} 的新闻")
            
            # 计算时间范围
            if not end_date:
                end_time = datetime.now()
            else:
                end_time = datetime.strptime(end_date, '%Y-%m-%d')
            
            if not start_date:
                start_time = end_time - timedelta(days=7)
            else:
                start_time = datetime.strptime(start_date, '%Y-%m-%d')
            
            # 调用 FinnHub API
            url = "https://finnhub.io/api/v1/company-news"
            params = {
                'symbol': stock_code,
                'from': start_time.strftime('%Y-%m-%d'),
                'to': end_time.strftime('%Y-%m-%d'),
                'token': self.config.finnhub_key
            }
            
            response = requests.get(url, params=params, timeout=self.config.request_timeout)
            response.raise_for_status()
            
            data = response.json()
            news_items = []
            
            for item in data[:max_news]:
                try:
                    publish_time = datetime.fromtimestamp(item.get('datetime', 0))
                    title = item.get('headline', '')
                    content = item.get('summary', '')
                    
                    news_item = NewsItem(
                        title=title,
                        content=content,
                        source=self.source,
                        publish_time=publish_time,
                        url=item.get('url', ''),
                        urgency=self.assess_urgency(title, content),
                        relevance_score=self.calculate_relevance(title, stock_code),
                        stock_code=stock_code
                    )
                    news_items.append(news_item)
                except Exception as e:
                    logger.warning(f"解析 FinnHub 新闻项失败: {e}")
                    continue
            
            logger.info(f"📝 FinnHub 获取 {len(news_items)} 条新闻")
            return news_items
            
        except Exception as e:
            logger.error(f"FinnHub 新闻获取失败: {e}")
            return []
