#!/usr/bin/env python3
"""
News 模块配置管理器
使用模块化环境变量加载器
"""

import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

from tradingagents.utils.env_loader import ModularEnvLoader
from tradingagents.utils.logging_manager import get_logger

logger = get_logger('agents')


@dataclass
class NewsConfig:
    """News 模块配置"""
    
    # API 密钥
    newsapi_key: Optional[str] = None
    alpha_vantage_key: Optional[str] = None
    finnhub_key: Optional[str] = None
    
    # 数据源启用状态
    finnhub_enabled: bool = True
    alpha_vantage_enabled: bool = False
    newsapi_enabled: bool = False
    tushare_enabled: bool = True
    akshare_enabled: bool = True
    eodhd_enabled: bool = False
    cls_rss_enabled: bool = True
    
    # 获取配置
    default_hours_back: int = 6
    default_max_news: int = 10
    relevance_threshold: float = 0.3
    freshness_threshold: int = 60
    
    # 缓存配置
    cache_enabled: bool = True
    cache_expiry: int = 1800
    cache_dir: str = "./cache/news"
    
    # 日志配置
    log_level: str = "INFO"
    verbose_logging: bool = False
    
    # 高级配置
    request_timeout: int = 10
    max_retries: int = 3
    retry_delay: int = 1
    rate_limit: int = 5


class NewsConfigManager:
    """News 模块配置管理器"""
    
    def __init__(self, module_path: Optional[Path] = None, verbose: bool = False):
        """
        初始化配置管理器
        
        Args:
            module_path: 模块路径,如果为 None 则自动检测
            verbose: 是否输出详细日志
        """
        self.verbose = verbose
        
        # 如果未提供模块路径,使用当前文件所在目录
        if module_path is None:
            module_path = Path(__file__).parent
        
        self.module_path = module_path
        
        # 创建环境变量加载器
        self.env_loader = ModularEnvLoader(module_path=module_path)
        
        # 加载环境变量
        self._load_env()
        
        # 加载配置
        self.config = self._load_config()
    
    def _load_env(self):
        """加载环境变量"""
        try:
            loaded_vars = self.env_loader.load_env(override=True, verbose=self.verbose)
            
            if self.verbose and loaded_vars:
                logger.info(f"✅ News 模块加载了 {len(loaded_vars)} 个环境变量")
        except Exception as e:
            logger.error(f"❌ News 模块环境变量加载失败: {e}")
    
    def _load_config(self) -> NewsConfig:
        """
        从环境变量加载配置
        
        Returns:
            NewsConfig 实例
        """
        config = NewsConfig()
        
        # API 密钥
        config.newsapi_key = self.env_loader.get_env('NEWSAPI_KEY')
        config.alpha_vantage_key = self.env_loader.get_env('ALPHA_VANTAGE_API_KEY')
        config.finnhub_key = self.env_loader.get_env('FINNHUB_API_KEY')
        
        # 数据源启用状态
        config.finnhub_enabled = self.env_loader.get_env_bool('NEWS_FINNHUB_ENABLED', True)
        config.alpha_vantage_enabled = self.env_loader.get_env_bool('NEWS_ALPHA_VANTAGE_ENABLED', False)
        config.newsapi_enabled = self.env_loader.get_env_bool('NEWS_NEWSAPI_ENABLED', False)
        config.tushare_enabled = self.env_loader.get_env_bool('NEWS_TUSHARE_ENABLED', True)
        config.akshare_enabled = self.env_loader.get_env_bool('NEWS_AKSHARE_ENABLED', True)
        config.eodhd_enabled = self.env_loader.get_env_bool('NEWS_EODHD_ENABLED', False)
        config.cls_rss_enabled = self.env_loader.get_env_bool('NEWS_CLS_RSS_ENABLED', True)
        
        # 获取配置
        config.default_hours_back = self.env_loader.get_env_int('NEWS_DEFAULT_HOURS_BACK', 6)
        config.default_max_news = self.env_loader.get_env_int('NEWS_DEFAULT_MAX_NEWS', 10)
        config.relevance_threshold = self.env_loader.get_env_float('NEWS_RELEVANCE_THRESHOLD', 0.3)
        config.freshness_threshold = self.env_loader.get_env_int('NEWS_FRESHNESS_THRESHOLD', 60)
        
        # 缓存配置
        config.cache_enabled = self.env_loader.get_env_bool('NEWS_CACHE_ENABLED', True)
        config.cache_expiry = self.env_loader.get_env_int('NEWS_CACHE_EXPIRY', 1800)
        config.cache_dir = self.env_loader.get_env('NEWS_CACHE_DIR', './cache/news')
        
        # 日志配置
        config.log_level = self.env_loader.get_env('NEWS_LOG_LEVEL', 'INFO')
        config.verbose_logging = self.env_loader.get_env_bool('NEWS_VERBOSE_LOGGING', False)
        
        # 高级配置
        config.request_timeout = self.env_loader.get_env_int('NEWS_REQUEST_TIMEOUT', 10)
        config.max_retries = self.env_loader.get_env_int('NEWS_MAX_RETRIES', 3)
        config.retry_delay = self.env_loader.get_env_int('NEWS_RETRY_DELAY', 1)
        config.rate_limit = self.env_loader.get_env_int('NEWS_RATE_LIMIT', 5)
        
        return config
    
    def get_config(self) -> NewsConfig:
        """获取配置"""
        return self.config
    
    def reload_config(self):
        """重新加载配置"""
        self._load_env()
        self.config = self._load_config()
        logger.info("🔄 News 模块配置已重新加载")
    
    def print_config(self):
        """打印当前配置(用于调试)"""
        logger.info("=" * 60)
        logger.info("News 模块配置:")
        logger.info("=" * 60)
        
        logger.info("\n📡 API 密钥:")
        logger.info(f"  NewsAPI: {'已配置' if self.config.newsapi_key else '未配置'}")
        logger.info(f"  Alpha Vantage: {'已配置' if self.config.alpha_vantage_key else '未配置'}")
        logger.info(f"  FinnHub: {'已配置' if self.config.finnhub_key else '未配置'}")
        
        logger.info("\n🔧 数据源状态:")
        logger.info(f"  FinnHub: {'✅ 启用' if self.config.finnhub_enabled else '❌ 禁用'}")
        logger.info(f"  Alpha Vantage: {'✅ 启用' if self.config.alpha_vantage_enabled else '❌ 禁用'}")
        logger.info(f"  NewsAPI: {'✅ 启用' if self.config.newsapi_enabled else '❌ 禁用'}")
        logger.info(f"  Tushare: {'✅ 启用' if self.config.tushare_enabled else '❌ 禁用'}")
        logger.info(f"  AKShare: {'✅ 启用' if self.config.akshare_enabled else '❌ 禁用'}")
        logger.info(f"  EODHD: {'✅ 启用' if self.config.eodhd_enabled else '❌ 禁用'}")
        logger.info(f"  财联社RSS: {'✅ 启用' if self.config.cls_rss_enabled else '❌ 禁用'}")
        
        logger.info("\n⚙️ 获取配置:")
        logger.info(f"  默认回溯时间: {self.config.default_hours_back} 小时")
        logger.info(f"  默认最大新闻数: {self.config.default_max_news} 条")
        logger.info(f"  相关性阈值: {self.config.relevance_threshold}")
        logger.info(f"  时效性阈值: {self.config.freshness_threshold} 分钟")
        
        logger.info("\n💾 缓存配置:")
        logger.info(f"  缓存启用: {'✅ 是' if self.config.cache_enabled else '❌ 否'}")
        logger.info(f"  缓存过期时间: {self.config.cache_expiry} 秒")
        logger.info(f"  缓存目录: {self.config.cache_dir}")
        
        logger.info("\n📝 日志配置:")
        logger.info(f"  日志级别: {self.config.log_level}")
        logger.info(f"  详细日志: {'✅ 启用' if self.config.verbose_logging else '❌ 禁用'}")
        
        logger.info("\n🔧 高级配置:")
        logger.info(f"  请求超时: {self.config.request_timeout} 秒")
        logger.info(f"  最大重试次数: {self.config.max_retries}")
        logger.info(f"  重试延迟: {self.config.retry_delay} 秒")
        logger.info(f"  请求限流: {self.config.rate_limit} 请求/秒")
        
        logger.info("=" * 60)


# 全局配置管理器实例
_news_config_manager: Optional[NewsConfigManager] = None


def get_news_config_manager(verbose: bool = False) -> NewsConfigManager:
    """
    获取 News 配置管理器单例
    
    Args:
        verbose: 是否输出详细日志
        
    Returns:
        NewsConfigManager 实例
    """
    global _news_config_manager
    
    if _news_config_manager is None:
        _news_config_manager = NewsConfigManager(verbose=verbose)
    
    return _news_config_manager


def get_news_config(verbose: bool = False) -> NewsConfig:
    """
    获取 News 配置
    
    Args:
        verbose: 是否输出详细日志
        
    Returns:
        NewsConfig 实例
    """
    manager = get_news_config_manager(verbose=verbose)
    return manager.get_config()
