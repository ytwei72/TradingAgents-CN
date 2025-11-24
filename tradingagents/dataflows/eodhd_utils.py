#!/usr/bin/env python3
"""
EODHD数据源工具类
提供EODHD API新闻数据获取功能
"""

import os
import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Optional
import warnings

# 导入日志模块
from tradingagents.utils.logging_manager import get_logger
logger = get_logger('agents')
warnings.filterwarnings('ignore')


class EODHDProvider:
    """EODHD数据提供器"""
    
    def __init__(self, api_token: str = None):
        """
        初始化EODHD提供器
        
        Args:
            api_token: EODHD API token
        """
        self.connected = False
        self.api_token = None
        
        # 获取API token
        if not api_token:
            try:
                from ..config.env_utils import parse_str_env
                api_token = parse_str_env('EODHD_API_TOKEN', '')
            except ImportError:
                # 回退到原始方法
                api_token = os.getenv('EODHD_API_TOKEN', '')
        
        if not api_token:
            logger.warning("⚠️ 未找到EODHD API token，请设置EODHD_API_TOKEN环境变量")
            return
        
        self.api_token = api_token
        self.connected = True
        logger.info("✅ EODHD API连接成功")
    
    def _normalize_symbol_for_eodhd(self, symbol: str) -> str:
        """
        标准化股票代码为EODHD格式
        
        EODHD格式:
        - A股上海: XXXXXX.SHG (如: 600519.SHG)
        - A股深圳: XXXXXX.SHE (如: 000001.SHE)
        - 美股: XXXX.US (如: AAPL.US)
        - 港股: XXXX.HK (如: 0700.HK)
        
        Args:
            symbol: 原始股票代码
            
        Returns:
            str: EODHD格式的股票代码
        """
        logger.debug(f"[EODHD] 标准化股票代码: '{symbol}'")
        
        # 如果已经包含交易所后缀，检查是否需要转换
        if '.' in symbol:
            # 处理A股代码转换
            if '.SH' in symbol or '.SS' in symbol or '.XSHG' in symbol:
                # 上海交易所 -> .SHG
                clean_code = symbol.split('.')[0]
                result = f"{clean_code}.SHG"
                logger.debug(f"[EODHD] 上海交易所转换: '{symbol}' -> '{result}'")
                return result
            elif '.SZ' in symbol or '.XSHE' in symbol:
                # 深圳交易所 -> .SHE
                clean_code = symbol.split('.')[0]
                result = f"{clean_code}.SHE"
                logger.debug(f"[EODHD] 深圳交易所转换: '{symbol}' -> '{result}'")
                return result
            elif '.HK' in symbol:
                # 港股保持 .HK
                logger.debug(f"[EODHD] 港股代码保持: '{symbol}'")
                return symbol
            elif any(suffix in symbol.upper() for suffix in ['.US', '.NYSE', '.NASDAQ']):
                # 美股统一为 .US
                clean_code = symbol.split('.')[0].upper()
                result = f"{clean_code}.US"
                logger.debug(f"[EODHD] 美股代码转换: '{symbol}' -> '{result}'")
                return result
            else:
                # 其他情况保持原样
                logger.debug(f"[EODHD] 代码保持原样: '{symbol}'")
                return symbol
        
        # 如果没有后缀，根据代码判断交易所
        if symbol.startswith('6'):
            result = f"{symbol}.SHG"  # 上海证券交易所
            logger.debug(f"[EODHD] 识别为上海股票: '{symbol}' -> '{result}'")
            return result
        elif symbol.startswith(('0', '3')):
            result = f"{symbol}.SHE"  # 深圳证券交易所
            logger.debug(f"[EODHD] 识别为深圳股票: '{symbol}' -> '{result}'")
            return result
        else:
            # 默认假设为美股
            result = f"{symbol.upper()}.US"
            logger.debug(f"[EODHD] 默认为美股: '{symbol}' -> '{result}'")
            return result
    
    def get_stock_news(self, symbol: str, start_date: str = None, end_date: str = None, max_news: int = 10) -> pd.DataFrame:
        """
        获取股票新闻（使用EODHD新闻接口）
        
        Args:
            symbol: 股票代码
            start_date: 开始日期（YYYY-MM-DD）
            end_date: 结束日期（YYYY-MM-DD）
            max_news: 最大新闻数量，默认10条
            
        Returns:
            DataFrame: 新闻数据，包含标题、内容、时间等
                      列名: 标题, 内容, 时间, 链接
        """
        start_time = datetime.now()
        logger.debug(f"[EODHD新闻] 开始获取新闻，股票: {symbol}, 日期范围: {start_date} 到 {end_date}")
        
        if not self.connected:
            logger.error(f"[EODHD新闻] ❌ EODHD未连接，无法获取新闻")
            return pd.DataFrame()
        
        try:
            # 标准化股票代码
            eodhd_symbol = self._normalize_symbol_for_eodhd(symbol)
            
            # 设置默认日期
            if end_date is None:
                end_date = datetime.now().strftime('%Y-%m-%d')
            
            if start_date is None:
                # 默认获取最近7天的新闻
                start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
            
            logger.debug(f"[EODHD新闻] 📰 调用EODHD API获取新闻: symbol={eodhd_symbol}, from={start_date}, to={end_date}")
            
            # 构建API URL
            url = f'https://eodhd.com/api/news'
            params = {
                's': eodhd_symbol,
                'from': start_date,
                'to': end_date,
                'offset': 0,
                'limit': max_news,
                'api_token': self.api_token,
                'fmt': 'json'
            }
            
            # 调用API
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            news_data = response.json()
            
            if not news_data or not isinstance(news_data, list):
                logger.warning(f"[EODHD新闻] ⚠️ API返回空数据或格式错误")
                return pd.DataFrame()
            
            logger.debug(f"[EODHD新闻] API返回 {len(news_data)} 条新闻")
            
            # 转换为DataFrame
            news_list = []
            for item in news_data:
                news_list.append({
                    '标题': item.get('title', ''),
                    '内容': item.get('content', ''),
                    '时间': item.get('date', ''),
                    '链接': item.get('link', '')
                })
            
            result_df = pd.DataFrame(news_list)
            
            if not result_df.empty:
                # 记录新闻标题示例
                sample_titles = [row.get('标题', '无标题') for _, row in result_df.head(3).iterrows()]
                logger.debug(f"[EODHD新闻] 新闻标题示例: {', '.join(sample_titles)}")
            
            elapsed_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"[EODHD新闻] ✅ 获取成功: {symbol}, 共{len(result_df)}条记录，耗时: {elapsed_time:.2f}秒")
            
            return result_df
            
        except requests.exceptions.RequestException as e:
            elapsed_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"[EODHD新闻] ❌ API请求失败: {e}, 耗时: {elapsed_time:.2f}秒")
            return pd.DataFrame()
        except Exception as e:
            elapsed_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"[EODHD新闻] ❌ 获取失败: {symbol}, 错误: {e}, 耗时: {elapsed_time:.2f}秒")
            import traceback
            logger.error(f"[EODHD新闻] 异常堆栈: {traceback.format_exc()}")
            return pd.DataFrame()
    
    def get_stock_news_items(self, symbol: str, start_date: str, end_date: str, ticker: str, max_news: int = 10):
        """
        获取股票新闻并转换为NewsItem列表（直接从JSON处理）
        
        Args:
            symbol: 股票代码（用于过滤新闻）
            start_date: 开始日期（YYYY-MM-DD）
            end_date: 结束日期（YYYY-MM-DD）
            ticker: 原始ticker（用于相关性计算）
            max_news: 最大新闻数量
            
        Returns:
            List[NewsItem]: 新闻项目列表
        """
        from .realtime_news_utils import NewsItem
        from .news_helper import assess_news_urgency, calculate_relevance_score, parse_news_time, filter_news_by_date_range
        
        start_time = datetime.now()
        logger.debug(f"[EODHD新闻] 开始获取NewsItem列表，股票: {symbol}, 日期范围: {start_date} 到 {end_date}")
        
        if not self.connected:
            logger.error(f"[EODHD新闻] ❌ EODHD未连接，无法获取新闻")
            return []
        
        try:
            # 标准化股票代码
            eodhd_symbol = self._normalize_symbol_for_eodhd(symbol)
            
            # 设置默认日期
            if end_date is None:
                end_date_str = datetime.now().strftime('%Y-%m-%d')
            else:
                end_date_str = end_date
            
            if start_date is None:
                start_date_str = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
            else:
                start_date_str = start_date
            
            logger.debug(f"[EODHD新闻] 📰 调用EODHD API获取新闻: symbol={eodhd_symbol}, from={start_date_str}, to={end_date_str}")
            
            # 构建API URL
            url = f'https://eodhd.com/api/news'
            params = {
                's': eodhd_symbol,
                'from': start_date_str,
                'to': end_date_str,
                'offset': 0,
                'limit': max_news,
                'api_token': self.api_token,
                'fmt': 'json'
            }
            
            # 调用API
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            news_data = response.json()
            
            if not news_data or not isinstance(news_data, list):
                logger.warning(f"[EODHD新闻] ⚠️ API返回空数据或格式错误")
                return []
            
            logger.debug(f"[EODHD新闻] API返回 {len(news_data)} 条新闻")
            
            # 计算时间范围
            end_datetime = datetime.strptime(end_date_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
            start_datetime = datetime.strptime(start_date_str, '%Y-%m-%d').replace(hour=0, minute=0, second=0)
            
            # 直接转换JSON为NewsItem列表
            news_items = []
            for item in news_data:
                try:
                    # 解析时间
                    time_str = item.get('date', '')
                    publish_time = parse_news_time(time_str)
                    
                    if not publish_time:
                        logger.warning(f"[EODHD新闻] 无法解析时间: {time_str}，跳过该新闻")
                        continue
                    
                    # 过滤日期范围
                    if not filter_news_by_date_range(publish_time, start_datetime, end_datetime):
                        continue
                    
                    # 获取新闻内容
                    title = item.get('title', '')
                    content = item.get('content', '')
                    url_link = item.get('link', '')
                    
                    # 评估紧急度和相关性
                    urgency = assess_news_urgency(title, content)
                    relevance_score = calculate_relevance_score(title, ticker)
                    
                    # 创建NewsItem对象
                    news_item = NewsItem(
                        title=title,
                        content=content,
                        source='EODHD',
                        publish_time=publish_time,
                        url=url_link,
                        urgency=urgency,
                        relevance_score=relevance_score
                    )
                    
                    news_items.append(news_item)
                    
                except Exception as e:
                    logger.error(f"[EODHD新闻] 处理新闻项失败: {e}")
                    continue
            
            elapsed_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"[EODHD新闻] ✅ 获取成功: {symbol}, 共{len(news_items)}条NewsItem，耗时: {elapsed_time:.2f}秒")
            
            # 记录新闻标题示例
            if news_items:
                sample_titles = [item.title[:50] for item in news_items[:3]]
                logger.debug(f"[EODHD新闻] 新闻标题示例: {', '.join(sample_titles)}")
            
            return news_items
            
        except requests.exceptions.RequestException as e:
            elapsed_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"[EODHD新闻] ❌ API请求失败: {e}, 耗时: {elapsed_time:.2f}秒")
            return []
        except Exception as e:
            elapsed_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"[EODHD新闻] ❌ 获取失败: {symbol}, 错误: {e}, 耗时: {elapsed_time:.2f}秒")
            import traceback
            logger.error(f"[EODHD新闻] 异常堆栈: {traceback.format_exc()}")
            return []


# 全局提供器实例
_eodhd_provider = None

def get_eodhd_provider() -> EODHDProvider:
    """获取全局EODHD提供器实例"""
    global _eodhd_provider
    if _eodhd_provider is None:
        _eodhd_provider = EODHDProvider()
    return _eodhd_provider
