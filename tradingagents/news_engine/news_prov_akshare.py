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
            logger.debug("✅ AKShare 连接成功")
        except Exception as e:
            logger.error(f"❌ AKShare 连接失败: {e}")
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
        
        # 清理股票代码
        clean_code = stock_code.replace('.SH', '').replace('.SZ', '').replace('.SS', '')
        
        try:
            logger.info(f"📝 AKShare 获取 {stock_code} 的新闻")
            logger.debug(f"AKShare API 调用参数: symbol={clean_code}")
            
            # 调用 AKShare API
            df = self.ak.stock_news_em(symbol=clean_code)
            
            if df is None or df.empty:
                logger.warning(f"AKShare 返回空数据 (stock_code={stock_code}, clean_code={clean_code})")
                return []
            
            logger.debug(f"AKShare 返回 {len(df)} 条原始新闻数据")
            
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
                    logger.warning(f"解析新闻项失败: {e}")
                    continue
            
            logger.info(f"📝 AKShare 成功获取 {len(news_items)} 条新闻")
            return news_items
            
        except Exception as e:
            import traceback
            
            # 记录详细的错误信息
            error_type = type(e).__name__
            logger.error(f"❌ AKShare 新闻获取失败 ({error_type}): {str(e)}")
            logger.debug(f"AKShare API 调用参数: stock_code={stock_code}, clean_code={clean_code}")
            logger.debug(f"完整异常堆栈:\n{traceback.format_exc()}")
            
            # 尝试获取更多的错误信息
            if hasattr(e, 'response') and e.response is not None:
                try:
                    status_code = e.response.status_code
                    response_text = e.response.text[:500] if hasattr(e.response, 'text') else 'N/A'
                    logger.error(f"HTTP 响应状态码: {status_code}")
                    logger.debug(f"HTTP 响应内容(前500字符): {response_text}")
                except Exception:
                    pass
            
            return []
