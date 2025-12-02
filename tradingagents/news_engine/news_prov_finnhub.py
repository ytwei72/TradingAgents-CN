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
        
        import requests
        
        # 计算时间范围
        if not end_date:
            end_time = datetime.now()
        else:
            try:
                end_time = datetime.strptime(end_date, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                end_time = datetime.strptime(end_date, '%Y-%m-%d')
        
        if not start_date:
            start_time = end_time - timedelta(days=7)
        else:
            try:
                start_time = datetime.strptime(start_date, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                start_time = datetime.strptime(start_date, '%Y-%m-%d')
        
        # 调用 FinnHub API
        url = "https://finnhub.io/api/v1/company-news"
        params = {
            'symbol': stock_code,
            'from': start_time.strftime('%Y-%m-%d'),
            'to': end_time.strftime('%Y-%m-%d'),
            'token': self.config.finnhub_key
        }
        
        try:
            logger.info(f"📝 FinnHub 获取 {stock_code} 的新闻")
            logger.debug(f"FinnHub API 请求: URL={url}, params={params}")
            
            response = requests.get(url, params=params, timeout=self.config.request_timeout)
            
            # 记录响应状态
            logger.debug(f"FinnHub HTTP 响应状态码: {response.status_code}")
            
            # 检查HTTP错误
            response.raise_for_status()
            
            data = response.json()
            
            if not isinstance(data, list):
                logger.warning(f"FinnHub 返回非列表数据: {type(data)}")
                return []
            
            logger.debug(f"FinnHub 返回 {len(data)} 条原始新闻数据")
            
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
            
            logger.info(f"📝 FinnHub 成功获取 {len(news_items)} 条新闻")
            return news_items
            
        except requests.exceptions.HTTPError as e:
            # HTTP 错误需要重新抛出，以便 aggregator 的重试机制处理
            status_code = None
            if e.response is not None:
                status_code = e.response.status_code
            else:
                # 尝试从异常消息中提取状态码
                import re
                match = re.search(r'(\d{3})\s+Client Error|(\d{3})\s+Server Error', str(e))
                if match:
                    status_code = int(match.group(1) or match.group(2))
                else:
                    status_code = 'Unknown'
            
            logger.error(f"❌ FinnHub HTTP 错误 {status_code}: {str(e)}")
            logger.debug(f"请求URL: {url}")
            logger.debug(f"请求参数: {params}")
            
            # 记录响应内容（前500字符）
            if e.response is not None:
                try:
                    response_text = e.response.text[:500]
                    logger.debug(f"响应内容(前500字符): {response_text}")
                except Exception:
                    pass
            
            # 重新抛出 HTTPError，让 aggregator 的重试机制处理
            raise
            
        except requests.exceptions.RequestException as e:
            # 其他请求异常（超时、连接错误等）
            logger.error(f"❌ FinnHub 请求异常: {type(e).__name__}: {str(e)}")
            logger.debug(f"请求URL: {url}")
            logger.debug(f"请求参数: {params}")
            return []
            
        except Exception as e:
            # 其他异常（JSON解析错误等）
            import traceback
            logger.error(f"❌ FinnHub 新闻获取失败: {type(e).__name__}: {str(e)}")
            logger.debug(f"完整异常堆栈:\n{traceback.format_exc()}")
            return []
