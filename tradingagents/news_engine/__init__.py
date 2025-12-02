# Import all news providers for easy access
from providers.news_prov_tushare import TushareNewsProvider
from providers.news_prov_finnhub import FinnhubNewsProvider
from providers.news_prov_eodhd import EODHDNewsProvider
from providers.news_prov_akshare_cls import AkShareClsNewsProvider
from providers.news_prov_akshare_sina import AkShareSinaNewsProvider
from providers.news_prov_akshare_em import AkShareEmNewsProvider
from providers.news_prov_googlenews import GoogleNewsProvider
from .aggregator import NewsAggregator, get_stock_news

__all__ = [
    'TushareNewsProvider',
    'FinnhubNewsProvider',
    'EODHDNewsProvider',
    'AkShareClsNewsProvider',
    'AkShareSinaNewsProvider',
    'AkShareEmNewsProvider',
    'GoogleNewsProvider',
    'NewsAggregator',
    'get_stock_news'
]
