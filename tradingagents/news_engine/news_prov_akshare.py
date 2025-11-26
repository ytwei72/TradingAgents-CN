#!/usr/bin/env python3
"""
AKShare News Provider

AKShare 新闻提供器
"""

from datetime import datetime
from typing import List, Optional

from .news_prov_base import NewsProvider
from .models import NewsItem, NewsSource
from tradingagents.utils.logging_manager import get_logger

logger = get_logger('news_engine.akshare')


class AKShareNewsProvider(NewsProvider):
    """AKShare 新闻提供器"""
    
    def __init__(self):
        super().__init__(NewsSource.AKSHARE)
        self._check_connection()
    
    def _check_connection(self):
        """检查连接状态"""
        if not self.config.akshare_enabled:
            logger.debug("AKShare 数据源未启用")
            self.connected = False
            return
        
        try:
            import akshare as ak
            self.ak = ak
            self.connected = True
            logger.debug("�?AKShare 连接成功")
        except Exception as e:
            logger.error(f"�?AKShare 连接失败: {e}")
            self.connected = False
    
    def is_available(self) -> bool:
        return self.connected
    
    def get_news(
        self,
        stock_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        max_news: int = 10
    ) -> List[NewsItem]:
        """获取 AKShare 新闻"""
        if not self.is_available():
            return []
        
        try:
            logger.info(f"📝 AKShare 获取 {stock_code} 的新闻")
            
            # 清理股票代码
            clean_code = stock_code.replace('.SH', '').replace('.SZ', '').replace('.SS', '')
            
            # 调用 AKShare API
            df = self.ak.stock_news_em(symbol=clean_code)
            
            if df is None or df.empty:
                return []
            
            news_items = []
            for _, row in df.head(max_news).iterrows():
                try:
                    # 解析时间
                    time_str = row.get('时间', '')
                    if time_str:
                        if ' ' in time_str:
                            publish_time = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
                        else:
                            publish_time = datetime.strptime(time_str, '%Y-%m-%d')
                    else:
                        publish_time = datetime.now()
                    
                    title = row.get('标题', '')
                    content = row.get('内容', '')
                    
                    news_item = NewsItem(
                        title=title,
                        content=content,
                        source=self.source,
                        publish_time=publish_time,
                        url=row.get('链接', ''),
                        urgency=self.assess_urgency(title, content),
                        relevance_score=self.calculate_relevance(title, stock_code),
                        stock_code=stock_code
                    )
                    news_items.append(news_item)
                except Exception as e:
                    logger.warning(f"解析新闻项失�? {e}")
                    continue
            
            logger.info(f"📝 AKShare 获取 {len(news_items)} 条新闻")
            return news_items
            
        except Exception as e:
            logger.error(f"AKShare 新闻获取失败: {e}")
            return []
