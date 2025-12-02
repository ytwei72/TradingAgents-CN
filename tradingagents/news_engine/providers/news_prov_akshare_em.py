#!/usr/bin/env python3
"""
EM Finance Global News Provider using AkShare

通过 AkShare 获取东方财富全球新闻
"""

from typing import Dict
import pandas as pd

from .news_prov_akshare_base import AkShareNewsProviderBase
from tradingagents.news_engine.models import NewsSource
from tradingagents.utils.logging_manager import get_logger

logger = get_logger("news_engine.akshare_em")


class AkShareEmNewsProvider(AkShareNewsProviderBase):
    """东方财富全球新闻提供器"""

    def __init__(self):
        super().__init__(
            source=NewsSource.AKSHARE_EM,
            config_key="akshare_em_enabled"
        )

    def _fetch_dataframe(self) -> pd.DataFrame:
        """
        获取东方财富全球新闻数据 DataFrame

        Returns:
            包含新闻数据的 DataFrame
        """
        try:
            import akshare as ak
            df = ak.stock_info_global_em()
            logger.info(f"📊 东方财富获取到 {len(df)} 条数据")
            return df
        except Exception as e:
            logger.error(f"获取东方财富数据失败: {e}")
            return pd.DataFrame()

    def _get_column_mapping(self) -> Dict[str, str]:
        """
        获取列名映射

        Returns:
            列名映射字典
        """
        return {
            "title": "标题",
            "content": "内容",
            "date": "发布时间",
            "url": "链接",
        }
