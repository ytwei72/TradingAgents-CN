#!/usr/bin/env python3
"""
EODHD News Provider

EODHD 新闻提供�?
"""

from datetime import datetime
from typing import List, Optional

from .news_prov_base import NewsProvider
from .models import NewsItem, NewsSource
from tradingagents.utils.logging_manager import get_logger

logger = get_logger('news_engine.eodhd')


class EODHDNewsProvider(NewsProvider):
    """EODHD 新闻提供器"""
    
    def __init__(self):
        super().__init__(NewsSource.EODHD)
        self._check_connection()
    
    def _check_connection(self):
        """检查连接状态"""
        if not self.config.eodhd_enabled:
            logger.debug("EODHD 数据源未启用")
            self.connected = False
            return
        
        if not self.config.eodhd_token:
            logger.warning("EODHD API Token 未配置")
            self.connected = False
            return
        
        self.connected = True
        logger.debug("EODHD 配置成功")
    
    def is_available(self) -> bool:
        return self.connected
    
    def get_news(
        self,
        stock_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        max_news: int = 10
    ) -> List[NewsItem]:
        """获取 EODHD 新闻"""
        if not self.is_available():
            return []
        
        try:
            import requests
            
            logger.info(f"📝 EODHD 获取 {stock_code} 的新闻")
            
            # 调用 EODHD API
            url = f"https://eodhd.com/api/news"
            params = {
                's': stock_code,
                'api_token': self.config.eodhd_token,
                'limit': max_news
            }
            
            if start_date:
                params['from'] = start_date
            if end_date:
                params['to'] = end_date
            
            response = requests.get(url, params=params, timeout=self.config.request_timeout)
            response.raise_for_status()
            
            data = response.json()
            news_items = []
            
            for item in data:
                try:
                    publish_time = datetime.fromisoformat(item.get('date', ''))
                    title = item.get('title', '')
                    content = item.get('content', '')
                    
                    news_item = NewsItem(
                        title=title,
                        content=content,
                        source=self.source,
                        publish_time=publish_time,
                        url=item.get('link', ''),
                        urgency=self.assess_urgency(title, content),
                        relevance_score=self.calculate_relevance(title, stock_code),
                        stock_code=stock_code
                    )
                    news_items.append(news_item)
                except Exception as e:
                    logger.warning(f"解析 EODHD 新闻项失败: {e}")
                    continue
            
            logger.info(f"📝 EODHD 获取 {len(news_items)} 条新闻")
            return news_items
            
        except Exception as e:
            logger.error(f"EODHD 新闻获取失败: {e}")
            return []
