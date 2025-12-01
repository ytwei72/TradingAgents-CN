# Import all news providers for easy access
from .news_prov_tushare import TushareNewsProvider
from .news_prov_finnhub import FinnhubNewsProvider
from .news_prov_eodhd import EODHDNewsProvider
from .news_prov_akshare_cls import AkShareClsNewsProvider
from .news_prov_akshare_sina import AkShareSinaNewsProvider
from .news_prov_akshare_em import AkShareEmNewsProvider
from .news_prov_googlenews import GoogleNewsProvider
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
