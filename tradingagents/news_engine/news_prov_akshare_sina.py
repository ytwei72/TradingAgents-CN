#!/usr/bin/env python3
"""
Sina Finance Global News Provider using AkShare

通过 AkShare 获取新浪财经全球新闻
"""

from typing import Dict
import pandas as pd

from .news_prov_akshare_base import AkShareNewsProviderBase
from .models import NewsSource
from tradingagents.utils.logging_manager import get_logger

logger = get_logger("news_engine.akshare_sina")


class AkShareSinaNewsProvider(AkShareNewsProviderBase):
    """新浪财经全球新闻提供器"""

    def __init__(self):
        super().__init__(
            source=NewsSource.AKSHARE_SINA,
            config_key="akshare_sina_enabled"
        )

    def _fetch_dataframe(self) -> pd.DataFrame:
        """
        获取新浪财经全球新闻数据 DataFrame

        Returns:
            包含新闻数据的 DataFrame
        """
        try:
            import akshare as ak
            df = ak.stock_info_global_sina()
            logger.info(f"📊 新浪财经获取到 {len(df)} 条数据")
            return df
        except Exception as e:
            logger.error(f"获取新浪财经数据失败: {e}")
            return pd.DataFrame()

    def _get_column_mapping(self) -> Dict[str, str]:
        """
        获取列名映射

        Returns:
            列名映射字典
        """
        return {
            "title": "title",
            "content": "content",
            "datetime": "日期时间",
            "url": None,  # 新浪财经无 URL
        }
