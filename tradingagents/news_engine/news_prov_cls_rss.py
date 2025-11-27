#!/usr/bin/env python3
"""
CLS (财联社) RSS News Provider

通过财联社 RSS / Feed 接口获取新闻,并适配到统一的 NewsItem 结构。
"""

from datetime import datetime, timedelta
from typing import List, Optional

from .news_prov_base import NewsProvider
from .models import NewsItem, NewsSource
from tradingagents.utils.logging_manager import get_logger
from .config import get_news_config

logger = get_logger("news_engine.cls_rss")


class CLSRSSNewsProvider(NewsProvider):
    """财联社 RSS 新闻提供器"""

    def __init__(self):
        super().__init__(NewsSource.CLS_RSS)
        self._check_connection()

    def _check_connection(self):
        """检查数据源是否启用以及依赖是否存在"""
        # 配置开关
        cfg = get_news_config()
        if not getattr(cfg, "cls_rss_enabled", False):
            logger.debug("财联社 RSS 数据源未启用 (NEWS_CLS_RSS_ENABLED=false)")
            self.connected = False
            return

        try:
            import feedparser  # noqa: F401

            self.connected = True
            logger.debug("✅ 财联社 RSS 依赖检查通过,数据源可用")
        except Exception as e:
            logger.error(f"❌ 财联社 RSS 依赖检查失败(feedparser): {e}")
            self.connected = False

    def is_available(self) -> bool:
        return self.connected

    def get_news(
        self,
        stock_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        max_news: int = 10,
    ) -> List[NewsItem]:
        """
        获取财联社 RSS 新闻

        说明:
            - 财联社官方接口没有按股票代码精确过滤,这里只做简单关键词匹配:
                - 标题/摘要中包含股票代码或其数字代码则认为相关
            - 只返回时间范围内的新闻
        """
        if not self.is_available():
            logger.debug("财联社 RSS 数据源不可用,跳过获取")
            return []

        try:
            import feedparser
        except Exception as e:
            logger.error(f"❌ 导入 feedparser 失败: {e}")
            return []

        # 计算时间范围
        try:
            if end_date:
                end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            else:
                end_dt = datetime.now()

            if start_date:
                start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            else:
                # 默认回溯 3 天,避免抓取过多历史数据
                start_dt = end_dt - timedelta(days=3)
        except Exception as e:
            logger.warning(f"解析日期失败(start_date={start_date}, end_date={end_date}): {e}")
            end_dt = datetime.now()
            start_dt = end_dt - timedelta(days=3)

        logger.info(
            f"📝 财联社 RSS 获取 {stock_code} 的新闻, 时间范围: "
            f"{start_dt.strftime('%Y-%m-%d')} ~ {end_dt.strftime('%Y-%m-%d')}"
        )

        # 使用 akshare 获取财联社电报
        try:
            import akshare as ak
            logger.debug("调用 akshare.stock_info_global_cls() 获取电报数据")
            df = ak.stock_info_global_cls()
            
            if df is None or df.empty:
                logger.warning("财联社电报返回空数据")
                return []
                
            logger.debug(f"获取到 {len(df)} 条电报数据")
            
            all_items: List[NewsItem] = []
            
            for _, row in df.iterrows():
                try:
                    # 解析时间
                    date_str = str(row.get('发布日期', ''))
                    time_str = str(row.get('发布时间', ''))
                    
                    if date_str and time_str:
                        full_time_str = f"{date_str} {time_str}"
                        try:
                            publish_time = datetime.strptime(full_time_str, "%Y-%m-%d %H:%M:%S")
                        except:
                            # 尝试其他格式或仅使用日期
                            publish_time = datetime.strptime(date_str, "%Y-%m-%d")
                    else:
                        publish_time = datetime.now()
                        
                    # 过滤时间范围
                    if publish_time < start_dt or publish_time > end_dt:
                        continue
                        
                    title = str(row.get('标题', ''))
                    content = str(row.get('内容', ''))
                    
                    # 简单相关性: 标题/内容包含股票代码或纯数字部分
                    if not self._is_related_to_stock(title, content, stock_code):
                        continue
                        
                    urgency = self.assess_urgency(title, content)
                    relevance = self.calculate_relevance(title, stock_code)
                    
                    news_item = NewsItem(
                        title=title,
                        content=content,
                        source=self.source,
                        publish_time=publish_time,
                        url="", # 电报通常无独立URL
                        urgency=urgency,
                        relevance_score=relevance,
                        stock_code=stock_code,
                    )
                    all_items.append(news_item)
                    
                    if len(all_items) >= max_news:
                        break
                        
                except Exception as e:
                    logger.warning(f"解析电报条目失败: {e}")
                    continue
                    
            # 根据结果数量使用不同的日志级别
            if len(all_items) == 0:
                logger.debug(
                    f"📝 财联社电报未找到 {stock_code} 的相关新闻 "
                    f"(时间范围: {start_dt.strftime('%Y-%m-%d')} ~ {end_dt.strftime('%Y-%m-%d')}, "
                    f"总电报数: {len(df)})"
                )
            else:
                logger.info(f"📝 财联社电报成功获取 {len(all_items)} 条相关新闻")
            return all_items
            
        except Exception as e:
            logger.error(f"获取财联社电报失败: {e}")
            return []

    def _is_related_to_stock(self, title: str, content: str, stock_code: str) -> bool:
        """判断新闻是否与指定股票相关(简单规则)"""
        text = (title + " " + content).lower()
        code_lower = stock_code.lower()

        if code_lower in text:
            return True

        # 数字代码匹配(适用于 A 股/港股)
        pure_code = "".join(filter(str.isdigit, stock_code))
        if pure_code and pure_code in text:
            return True

        return False


