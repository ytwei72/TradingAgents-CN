#!/usr/bin/env python3
"""
News Aggregator

新闻聚合器,整合多个数据源的新闻
"""

from datetime import datetime, timedelta
from typing import List, Optional

from .models import NewsItem, NewsQuery, NewsResponse, NewsSource, MarketType
from .news_prov_tushare import TushareNewsProvider
from .news_prov_finnhub import FinnhubNewsProvider
from .news_prov_eodhd import EODHDNewsProvider
from .news_prov_akshare_cls import AkShareClsNewsProvider
from .news_prov_akshare_sina import AkShareSinaNewsProvider
from .news_prov_akshare_em import AkShareEmNewsProvider
from .news_prov_googlenews import GoogleNewsProvider
from .config import get_news_config
from tradingagents.utils.logging_manager import get_logger

logger = get_logger('news_engine.aggregator')



class NewsAggregator:
    """新闻聚合器"""
    
    def __init__(self):
        """初始化新闻聚合器"""
        self.config = get_news_config()
        self.providers = self._init_providers()
    
    def _init_providers(self) -> List['NewsProvider']:
        """
        初始化所有新闻提供者
        
        Returns:
            可用的新闻提供者列表
        """
        all_providers = [
            TushareNewsProvider(),
            FinnhubNewsProvider(),
            EODHDNewsProvider(),
            AkShareClsNewsProvider(),
            AkShareSinaNewsProvider(),
            AkShareEmNewsProvider(),
            GoogleNewsProvider(),
        ]
        
        # 只保留可用的提供者
        available_providers = [p for p in all_providers if p.is_available()]
        
        logger.info(f"初始化新闻聚合器,可用数据源: {len(available_providers)}/{len(all_providers)}")
        for provider in available_providers:
            logger.debug(f"  ✅ {provider.source.value}")
        
        return available_providers
    
    def _call_provider_with_retry(
        self,
        provider: 'NewsProvider',
        stock_code: str,
        start_date: str,
        end_date: str,
        max_news: int
    ) -> List[NewsItem]:
        """
        使用重试机制调用 provider 的 get_news 方法
        
        Args:
            provider: 新闻提供器
            stock_code: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            max_news: 最大新闻数
            
        Returns:
            新闻列表
        """
        import time
        import requests
        
        last_exception = None
        
        for attempt in range(self.config.max_retries + 1):
            try:
                logger.debug(f"尝试从 {provider.source.value} 获取新闻 (第 {attempt + 1}/{self.config.max_retries + 1} 次)")
                
                news_items = provider.get_news(
                    stock_code=stock_code,
                    start_date=start_date,
                    end_date=end_date,
                    max_news=max_news
                )
                
                # 成功获取,返回结果
                if attempt > 0:
                    logger.info(f"✅ {provider.source.value} 重试成功 (第 {attempt + 1} 次尝试)")
                
                return news_items
                
            except requests.exceptions.HTTPError as e:
                last_exception = e
                
                # 获取状态码
                status_code = None
                if e.response is not None:
                    status_code = e.response.status_code
                else:
                    # 尝试从异常消息中提取状态码
                    import re
                    match = re.search(r'(\d{3})\s+Client Error|(\d{3})\s+Server Error', str(e))
                    if match:
                        status_code = int(match.group(1) or match.group(2))
                        logger.debug(f"从异常消息中提取状态码: {status_code}")
                
                # 记录详细错误信息
                logger.warning(
                    f"⚠️ {provider.source.value} HTTP 错误: {status_code} - {str(e)}"
                )
                
                # 记录响应内容（前 500 字符）
                if e.response is not None:
                    try:
                        response_text = e.response.text[:500]
                        logger.debug(f"响应内容: {response_text}")
                    except Exception:
                        pass
                
                # 判断是否应该重试
                if status_code not in self.config.retry_status_codes:
                    logger.error(
                        f"❌ {provider.source.value} 状态码 {status_code} 不可重试,放弃"
                    )
                    break
                
                # 如果还有重试机会
                if attempt < self.config.max_retries:
                    # 计算退避时间（指数退避）
                    wait_time = self.config.retry_delay * (2 ** attempt)
                    logger.info(
                        f"🔄 {provider.source.value} 将在 {wait_time} 秒后重试 "
                        f"({attempt + 1}/{self.config.max_retries})"
                    )
                    time.sleep(wait_time)
                else:
                    logger.error(
                        f"❌ {provider.source.value} 已达到最大重试次数 ({self.config.max_retries})"
                    )
                    
            except Exception as e:
                last_exception = e
                logger.error(f"❌ {provider.source.value} 发生异常: {type(e).__name__}: {str(e)}")
                
                # 对于非 HTTP 错误,不重试
                break
        
        # 所有重试都失败,返回空列表
        if last_exception:
            logger.error(f"❌ {provider.source.value} 最终失败: {str(last_exception)}")
        
        return []
    
    def get_news(
        self,
        stock_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        max_news: int = None,
        hours_back: int = None,
        sources: Optional[List[NewsSource]] = None,
        min_relevance: float = None
    ) -> NewsResponse:
        """
        获取股票新闻
        
        Args:
            stock_code: 股票代码
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            max_news: 最大新闻数量
            hours_back: 回溯小时数
            sources: 指定数据源列表
            min_relevance: 最小相关性分数
            
        Returns:
            NewsResponse 对象
        """
        # 使用配置的默认值
        if max_news is None:
            max_news = self.config.default_max_news
        if hours_back is None:
            hours_back = self.config.default_hours_back
        if min_relevance is None:
            min_relevance = self.config.relevance_threshold
        
        # 计算日期范围
        if not end_date:
            end_time = datetime.now()
            end_date = end_time.strftime('%Y-%m-%d %H:%M:%S')
        else:
            # 尝试解析带时间的格式,如果失败则使用仅日期格式
            try:
                end_time = datetime.strptime(end_date, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                end_time = datetime.strptime(end_date, '%Y-%m-%d')
        
        if not start_date:
            start_time = end_time - timedelta(hours=hours_back)
            start_date = start_time.strftime('%Y-%m-%d %H:%M:%S')
        
        # 创建查询对象
        query = NewsQuery(
            stock_code=stock_code,
            start_date=start_date,
            end_date=end_date,
            max_news=max_news,
            hours_back=hours_back,
            sources=sources,
            min_relevance=min_relevance
        )
        
        logger.info(f"开始获取 {stock_code} 的新闻, 日期范围: {start_date} ~ {end_date}")
        
        # 识别市场类型
        market_type = self._identify_market(stock_code)
        query.market_type = market_type
        logger.debug(f"股票市场类型: {market_type.value}")
        
        # 选择合适的提供者
        selected_providers = self._select_providers(market_type, sources)
        
        if not selected_providers:
            logger.warning(f"没有可用的新闻数据源")
            return NewsResponse(
                news_items=[],
                total_count=0,
                query=query,
                sources_used=[],
                fetch_time=datetime.now(),
                success=False,
                error_message="没有可用的新闻数据源"
            )
        
        # 从各个提供者获取新闻
        all_news = []
        sources_used = []
        
        
        for provider in selected_providers:
            try:
                # 使用重试机制调用 provider
                news_items = self._call_provider_with_retry(
                    provider=provider,
                    stock_code=stock_code,
                    start_date=start_date,
                    end_date=end_date,
                    max_news=max_news
                )
                
                if news_items:
                    all_news.extend(news_items)
                    sources_used.append(provider.source)
                    logger.info(f"从 {provider.source.value} 获取到 {len(news_items)} 条新闻")
                else:
                    logger.debug(f"⚠️ {provider.source.value} 未返回新闻")
                    
            except Exception as e:
                logger.error(f"从 {provider.source.value} 获取失败: {e}")
                continue
        
        # 去重和过滤
        unique_news = self._deduplicate_news(all_news)
        filtered_news = self._filter_news(unique_news, min_relevance)
        
        # 标准化所有datetime对象(将aware转为naive)
        for news_item in filtered_news:
            news_item.publish_time = self._normalize_datetime(news_item.publish_time)
        
        # 排序(按时间倒序)
        sorted_news = sorted(filtered_news, key=lambda x: x.publish_time, reverse=True)
        
        # 限制数量
        final_news = sorted_news[:max_news]
        
        logger.info(f"新闻聚合完成: 原始 {len(all_news)} 条 -> 去重 {len(unique_news)} 条 -> 过滤 {len(filtered_news)} 条 -> 最终 {len(final_news)} 条")
        
        return NewsResponse(
            news_items=final_news,
            total_count=len(final_news),
            query=query,
            sources_used=sources_used,
            fetch_time=datetime.now(),
            success=True
        )
    
    def _identify_market(self, stock_code: str) -> MarketType:
        """识别市场类型"""
        if not self.providers:
            return MarketType.UNKNOWN
        
        return self.providers[0].identify_market_type(stock_code)
    
    def _select_providers(
        self,
        market_type: MarketType,
        sources: Optional[List[NewsSource]] = None
    ) -> List['NewsProvider']:
        """
        根据市场类型和指定来源选择提供者
        
        Args:
            market_type: 市场类型
            sources: 指定的数据源列表
            
        Returns:
            选中的提供者列表
        """
        if sources:
            # 如果指定了数据源,只使用指定的
            return [p for p in self.providers if p.source in sources]
        
        # 根据市场类型选择合适的提供者
        if market_type == MarketType.A_SHARE:
            # A股优先级: AKShare > Tushare
            priority_sources = [NewsSource.AKSHARE, NewsSource.TUSHARE]
        elif market_type == MarketType.HK_SHARE:
            # 港股优先级: EODHD > FinnHub
            priority_sources = [NewsSource.EODHD, NewsSource.FINNHUB]
        elif market_type == MarketType.US_SHARE:
            # 美股优先级: FinnHub > EODHD
            priority_sources = [NewsSource.FINNHUB, NewsSource.EODHD]
        else:
            # 未知市场,使用所有可用提供者
            return self.providers
        
        # 按优先级排序
        sorted_providers = []
        for source in priority_sources:
            for provider in self.providers:
                if provider.source == source:
                    sorted_providers.append(provider)
                    break
        
        # 添加其他可用提供者
        for provider in self.providers:
            if provider not in sorted_providers:
                sorted_providers.append(provider)
        
        return sorted_providers
    
    def _normalize_datetime(self, dt: datetime) -> datetime:
        """
        标准化datetime对象,将timezone-aware转换为naive
        
        Args:
            dt: datetime对象
            
        Returns:
            naive datetime对象
        """
        if dt.tzinfo is not None and dt.utcoffset() is not None:
            # 转换为UTC时间,然后移除时区信息
            return dt.replace(tzinfo=None)
        return dt
    
    def _deduplicate_news(self, news_items: List[NewsItem]) -> List[NewsItem]:
        """
        去重新闻
        
        Args:
            news_items: 新闻列表
            
        Returns:
            去重后的新闻列表
        """
        seen_titles = set()
        unique_news = []
        
        for item in news_items:
            title_key = item.title.lower().strip()
            
            # 跳过标题过短的新闻
            if len(title_key) <= 10:
                continue
            
            # 检查是否重复
            if title_key in seen_titles:
                continue
            
            seen_titles.add(title_key)
            unique_news.append(item)
        
        logger.debug(f"新闻去重: {len(news_items)} -> {len(unique_news)}")
        return unique_news
    
    def _filter_news(
        self,
        news_items: List[NewsItem],
        min_relevance: float
    ) -> List[NewsItem]:
        """
        过滤新闻
        
        Args:
            news_items: 新闻列表
            min_relevance: 最小相关性分数
            
        Returns:
            过滤后的新闻列表
        """
        filtered = [
            item for item in news_items
            if item.relevance_score >= min_relevance
        ]
        
        logger.debug(f"新闻过滤(相关性>={min_relevance}): {len(news_items)} -> {len(filtered)}")
        return filtered


# 便捷函数

def get_stock_news(
    stock_code: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    max_news: int = 10,
    hours_back: int = 6,
    sources: Optional[List[NewsSource]] = None,
    min_relevance: float = 0.3
) -> NewsResponse:
    """
    获取股票新闻的便捷函数
    
    Args:
        stock_code: 股票代码
        start_date: 开始日期 (YYYY-MM-DD)
        end_date: 结束日期 (YYYY-MM-DD)
        max_news: 最大新闻数量
        hours_back: 回溯小时数
        sources: 指定数据源列表
        min_relevance: 最小相关性分数
        
    Returns:
        NewsResponse 对象
    
    Example:
        >>> from tradingagents.news_engine import get_stock_news
        >>> response = get_stock_news("000002", max_news=10)
        >>> for news in response.news_items:
        ...     print(news.title)
    """
    aggregator = NewsAggregator()
    return aggregator.get_news(
        stock_code=stock_code,
        start_date=start_date,
        end_date=end_date,
        max_news=max_news,
        hours_back=hours_back,
        sources=sources,
        min_relevance=min_relevance
    )
