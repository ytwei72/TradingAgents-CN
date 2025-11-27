#!/usr/bin/env python3
"""
Google News Provider

基于现有的 tradingagents.dataflows.googlenews_utils 抓取逻辑,
将 Google News 结果适配到统一的 NewsItem 结构。
"""

from datetime import datetime, timedelta
from typing import List, Optional

from .news_prov_base import NewsProvider
from .models import NewsItem, NewsSource
from tradingagents.utils.logging_manager import get_logger
from .config import get_news_config

logger = get_logger("news_engine.googlenews")


class GoogleNewsProvider(NewsProvider):
    """Google News 新闻提供器"""

    def __init__(self):
        super().__init__(NewsSource.GOOGLE_NEWS)
        self._check_connection()

    def _check_connection(self):
        """检查配置开关以及依赖"""
        cfg = get_news_config()
        if not getattr(cfg, "google_news_enabled", False):
            logger.debug("Google News 数据源未启用 (NEWS_GOOGLE_NEWS_ENABLED=false)")
            self.connected = False
            return

        try:
            # 仅检查依赖是否存在,真正调用在 get_news 中完成
            import tradingagents.dataflows.googlenews_utils as _gn  # noqa: F401

            self.connected = True
            logger.debug("✅ Google News 依赖检查通过,数据源可用")
        except Exception as e:
            logger.error(f"❌ Google News 依赖检查失败: {e}")
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
        获取 Google News 新闻

        说明:
            - 使用 tradingagents.dataflows.googlenews_utils.getNewsData
              抓取给定时间范围内的搜索结果
            - 因 Google News 没有直接按股票字段,这里只能通过搜索关键词近似筛选
        """
        if not self.is_available():
            logger.debug("Google News 数据源不可用,跳过获取")
            return []

        try:
            from tradingagents.dataflows.googlenews_utils import getNewsData
        except Exception as e:
            logger.error(f"❌ 无法导入 googlenews_utils.getNewsData: {e}")
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
                # Google News 搜索默认回溯若干天
                start_dt = end_dt - timedelta(days=3)
        except Exception as e:
            logger.warning(f"解析日期失败(start_date={start_date}, end_date={end_date}): {e}")
            end_dt = datetime.now()
            start_dt = end_dt - timedelta(days=3)

        # 构建搜索 query: 股票代码 + 通用关键词
        query = f"{stock_code} stock news"
        logger.info(
            f"📝 Google News 获取 {stock_code} 的新闻, query='{query}', "
            f"时间范围: {start_dt.strftime('%Y-%m-%d')} ~ {end_dt.strftime('%Y-%m-%d')}"
        )

        try:
            raw_items = getNewsData(
                query=query,
                start_date=start_dt.strftime("%Y-%m-%d"),
                end_date=end_dt.strftime("%Y-%m-%d"),
            )
        except Exception as e:
            logger.error(f"❌ 调用 getNewsData 失败: {e}")
            return []

        if not raw_items:
            logger.warning(f"Google News getNewsData returned empty list for query: {query}")
            return []
            
        logger.info(f"Google News raw items count: {len(raw_items)}")

        news_items: List[NewsItem] = []

        for item in raw_items:
            try:
                title = item.get("title", "") or ""
                snippet = item.get("snippet", "") or ""
                link = item.get("link", "") or ""
                date_str = item.get("date", "") or ""

                publish_time = self._parse_publish_time(date_str, end_dt)

                # 简单相关性判断,避免过多无关新闻
                if not self._is_related_to_stock(title, snippet, stock_code):
                    continue

                urgency = self.assess_urgency(title, snippet)
                relevance = self.calculate_relevance(title, stock_code)

                news_items.append(
                    NewsItem(
                        title=title,
                        content=snippet,
                        source=self.source,
                        publish_time=publish_time,
                        url=link,
                        urgency=urgency,
                        relevance_score=relevance,
                        stock_code=stock_code,
                    )
                )

                if len(news_items) >= max_news:
                    break
            except Exception as e:
                logger.warning(f"解析 Google News 项失败: {e}")
                continue

        logger.info(f"📝 Google News 成功获取 {len(news_items)} 条新闻")
        return news_items

    def _parse_publish_time(self, date_str: str, fallback_end: datetime) -> datetime:
        """
        将 Google News 抓取结果中的 date 字段解析为 datetime.

        googlenews_utils 中的 date 通常是类似 '2 days ago', '3 hours ago', 'Jan 1, 2024' 等格式,
        这里做一个尽量鲁棒的解析,解析失败时使用 fallback_end 作为时间。
        """
        date_str = (date_str or "").strip()
        if not date_str:
            return fallback_end

        # 相对时间: '2 days ago' / '3 hours ago'
        try:
            parts = date_str.split()
            if len(parts) >= 3 and parts[-1].lower() == "ago":
                value = int(parts[0])
                unit = parts[1].lower()
                delta = None
                if "hour" in unit:
                    delta = timedelta(hours=value)
                elif "day" in unit:
                    delta = timedelta(days=value)
                elif "minute" in unit:
                    delta = timedelta(minutes=value)
                if delta is not None:
                    return datetime.now() - delta
        except Exception:
            pass

        # 绝对日期,尝试常见格式
        for fmt in ("%b %d, %Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(date_str, fmt)
            except Exception:
                continue

        # 解析失败,回退
        return fallback_end

    def _is_related_to_stock(self, title: str, content: str, stock_code: str) -> bool:
        """判断 Google News 结果是否与股票相关(简单关键词规则)"""
        text = (title + " " + content).lower()
        code_lower = stock_code.lower()

        if code_lower in text:
            return True

        pure_code = "".join(filter(str.isdigit, stock_code))
        if pure_code and pure_code in text:
            return True

        return False


