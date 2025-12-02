#!/usr/bin/env python3
"""
AkShare News Provider Base Class

为所有基于 AkShare 的新闻提供器提供通用功能
"""

from abc import abstractmethod
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import pandas as pd

from .news_prov_base import NewsProvider
from tradingagents.news_engine.models import NewsItem, NewsSource
from tradingagents.utils.logging_manager import get_logger
from tradingagents.utils.time_utils import TaTimes

logger = get_logger("news_engine.akshare_base")


class AkShareNewsProviderBase(NewsProvider):
    """AkShare 新闻提供器基类"""

    def __init__(self, source: NewsSource, config_key: str):
        """
        初始化 AkShare 新闻提供器

        Args:
            source: 新闻来源
            config_key: 配置键名,用于检查是否启用
        """
        super().__init__(source)
        self.config_key = config_key
        self._check_connection()

    def _check_connection(self):
        """检查数据源是否启用以及依赖是否存在"""
        # 检查配置开关
        if not getattr(self.config, self.config_key, False):
            logger.debug(f"{self.source.value} 数据源未启用 ({self.config_key}=false)")
            self.connected = False
            return

        try:
            import akshare  # noqa: F401

            self.connected = True
            logger.debug(f"✅ {self.source.value} 依赖检查通过,数据源可用")
        except Exception as e:
            logger.error(f"❌ {self.source.value} 依赖检查失败(akshare): {e}")
            self.connected = False

    def is_available(self) -> bool:
        """检查数据源是否可用"""
        return self.connected

    @abstractmethod
    def _fetch_dataframe(self) -> pd.DataFrame:
        """
        获取原始数据 DataFrame (子类实现)

        Returns:
            包含新闻数据的 DataFrame
        """
        pass

    @abstractmethod
    def _get_column_mapping(self) -> Dict[str, str]:
        """
        获取列名映射 (子类实现)

        Returns:
            列名映射字典,格式:
            {
                'title': '标题列名',
                'content': '内容列名',
                'date': '日期列名',
                'time': '时间列名',  # 可选
                'url': 'URL列名',    # 可选
            }
        """
        pass

    def get_news(
        self,
        stock_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        max_news: int = 10,
    ) -> List[NewsItem]:
        """
        获取新闻数据

        Args:
            stock_code: 股票代码
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            max_news: 最大新闻数量

        Returns:
            新闻项目列表
        """
        if not self.is_available():
            logger.debug(f"{self.source.value} 数据源不可用,跳过获取")
            return []

        # 计算时间范围
        start_dt, end_dt = self._parse_date_range(start_date, end_date)

        logger.info(
            f"📝 {self.source.value} 获取 {stock_code} 的新闻, 时间范围: "
            f"{start_dt.strftime('%Y-%m-%d %H:%M:%S')} ~ {end_dt.strftime('%Y-%m-%d %H:%M:%S')}"
        )

        try:
            # 获取原始数据
            df = self._fetch_dataframe()

            if df is None or df.empty:
                logger.warning(f"{self.source.value} 返回空数据")
                return []

            logger.debug(f"获取到 {len(df)} 条数据")

            # 转换为 NewsItem 列表
            news_items = self._dataframe_to_news_items(
                df, stock_code, start_dt, end_dt, max_news
            )

            # 记录结果
            if len(news_items) == 0:
                logger.debug(
                    f"📝 {self.source.value} 未找到 {stock_code} 的相关新闻 "
                    f"(时间范围: {start_dt.strftime('%Y-%m-%d %H:%M:%S')} ~ {end_dt.strftime('%Y-%m-%d %H:%M:%S')}, "
                    f"总数据: {len(df)})"
                )
            else:
                logger.info(f"📝 {self.source.value} 成功获取 {len(news_items)} 条相关新闻")

            return news_items

        except Exception as e:
            logger.error(f"获取 {self.source.value} 数据失败: {e}")
            return []

    def _parse_date_range(
        self, start_date: Optional[str], end_date: Optional[str]
    ) -> tuple:
        """
        解析日期范围

        Args:
            start_date: 开始日期 (支持 YYYY-MM-DD 或 YYYY-MM-DD HH:MM:SS)
            end_date: 结束日期 (支持 YYYY-MM-DD 或 YYYY-MM-DD HH:MM:SS)

        Returns:
            (start_dt, end_dt) 元组
        """
        try:
            if end_date:
                try:
                    end_dt = datetime.strptime(end_date, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
                    end_dt = end_dt.replace(hour=23, minute=59, second=59)
            else:
                end_dt = datetime.now()

            if start_date:
                try:
                    start_dt = datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            else:
                # 默认回溯 3 天
                start_dt = end_dt - timedelta(days=3)
        except Exception as e:
            logger.warning(
                f"解析日期失败(start_date={start_date}, end_date={end_date}): {e}"
            )
            end_dt = datetime.now()
            start_dt = end_dt - timedelta(days=3)

        return start_dt, end_dt

    def _dataframe_to_news_items(
        self,
        df: pd.DataFrame,
        stock_code: str,
        start_dt: datetime,
        end_dt: datetime,
        max_news: int,
    ) -> List[NewsItem]:
        """
        将 DataFrame 转换为 NewsItem 列表

        Args:
            df: 原始数据 DataFrame
            stock_code: 股票代码
            start_dt: 开始时间
            end_dt: 结束时间
            max_news: 最大新闻数量

        Returns:
            NewsItem 列表
        """
        column_mapping = self._get_column_mapping()
        all_items: List[NewsItem] = []

        for _, row in df.iterrows():
            try:
                # 解析时间
                publish_time = self._parse_publish_time(row, column_mapping)

                # 过滤时间范围
                if publish_time < start_dt or publish_time > end_dt:
                    continue

                # 提取标题和内容
                title = self._extract_field(row, column_mapping, "title", "")
                content = self._extract_field(row, column_mapping, "content", "")
                url = self._extract_field(row, column_mapping, "url", "")

                # 相关性判断
                if stock_code:
                    if not self._is_related_to_stock(title, content, stock_code):
                        continue
                    urgency = self.assess_urgency(title, content)
                    relevance = self.calculate_relevance(title, stock_code)
                else:
                    urgency = 0
                    relevance = 0

                # 创建 NewsItem
                news_item = NewsItem(
                    title=title,
                    content=content,
                    source=self.source,
                    publish_time=publish_time,
                    url=url,
                    urgency=urgency,
                    relevance_score=relevance,
                    stock_code=stock_code,
                )
                all_items.append(news_item)

                if len(all_items) >= max_news:
                    break

            except Exception as e:
                logger.warning(f"解析数据行失败: {e}")
                continue

        return all_items

    def _parse_publish_time(
        self, row: pd.Series, column_mapping: Dict[str, str]
    ) -> datetime:
        """
        解析发布时间

        Args:
            row: DataFrame 行
            column_mapping: 列名映射

        Returns:
            发布时间
        """
        try:
            # 尝试组合日期和时间列
            if "date" in column_mapping and "time" in column_mapping:
                date_col = column_mapping["date"]
                time_col = column_mapping["time"]

                if date_col and time_col and date_col in row and time_col in row:
                    date_str = str(row[date_col])
                    time_str = str(row[time_col])

                    if date_str and time_str:
                        full_time_str = f"{date_str} {time_str}"
                        try:
                            return datetime.strptime(full_time_str, "%Y-%m-%d %H:%M:%S")
                        except:
                            # 尝试其他格式
                            return datetime.strptime(date_str, "%Y-%m-%d")

            # 尝试单独的时间列
            if "datetime" in column_mapping:
                datetime_col = column_mapping["datetime"]
                if datetime_col and datetime_col in row:
                    datetime_str = str(row[datetime_col])
                    try:
                        return datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
                    except:
                        try:
                            return datetime.strptime(datetime_str, "%Y-%m-%d")
                        except:
                            pass

            # 尝试日期列
            if "date" in column_mapping:
                date_col = column_mapping["date"]
                if date_col and date_col in row:
                    date_str = str(row[date_col])
                    try:
                        return datetime.strptime(date_str, "%Y-%m-%d")
                    except:
                        pass

        except Exception as e:
            logger.debug(f"解析时间失败: {e}")

        # 默认返回当前时间
        return datetime.now()

    def _extract_field(
        self, row: pd.Series, column_mapping: Dict[str, str], field: str, default: str
    ) -> str:
        """
        从行中提取字段

        Args:
            row: DataFrame 行
            column_mapping: 列名映射
            field: 字段名
            default: 默认值

        Returns:
            字段值
        """
        if field in column_mapping:
            col_name = column_mapping[field]
            if col_name and col_name in row:
                value = row[col_name]
                return str(value) if pd.notna(value) else default
        return default

    def _is_related_to_stock(self, title: str, content: str, stock_code: str) -> bool:
        """
        判断新闻是否与指定股票相关

        Args:
            title: 标题
            content: 内容
            stock_code: 股票代码

        Returns:
            是否相关
        """
        text = (title + " " + content).lower()
        code_lower = stock_code.lower()

        if code_lower in text:
            return True

        # 数字代码匹配(适用于 A 股/港股)
        pure_code = "".join(filter(str.isdigit, stock_code))
        if pure_code and pure_code in text:
            return True

        return False
