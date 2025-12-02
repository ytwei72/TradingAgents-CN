#!/usr/bin/env python3
"""
Tushare News Provider

Tushare 新闻提供器
"""

from datetime import datetime
from typing import List, Optional

from .news_prov_base import NewsProvider
from tradingagents.news_engine.models import NewsItem, NewsSource
from tradingagents.utils.logging_manager import get_logger

logger = get_logger('news_engine.tushare')


class TushareNewsProvider(NewsProvider):
    """Tushare 新闻提供器"""
    
    def __init__(self):
        super().__init__(NewsSource.TUSHARE)
        self._check_connection()
    
    def _check_connection(self):
        """检查连接状态"""
        if not self.config.tushare_enabled:
            logger.debug("Tushare 数据源未启用")
            self.connected = False
            return
        
        if not self.config.tushare_token:
            logger.warning("Tushare Token 未配置")
            self.connected = False
            return
        
        try:
            import tushare as ts
            ts.set_token(self.config.tushare_token)
            self.pro = ts.pro_api()
            self.connected = True
            logger.debug("Tushare 连接成功")
        except Exception as e:
            logger.error(f"Tushare 连接失败: {e}")
            self.connected = False
    
    def is_available(self) -> bool:
        return self.connected
    
    def get_news(
        self,
        stock_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        max_news: int = 10
    ) -> List[NewsItem]:
        """获取 Tushare 新闻"""
        if not self.is_available():
            logger.debug("Tushare 数据源不可用，跳过新闻获取")
            return []
        
        try:
            logger.info(f"📝 Tushare 开始获取 {stock_code} 的新闻")
            logger.debug(f"Tushare API 调用参数: ts_code={stock_code}, start_date={start_date}, end_date={end_date}, max_news={max_news}")
            
            # 转换股票代码格式
            # Tushare 需要的格式: 000001.SZ, 600000.SH
            ts_code = self._convert_to_tushare_code(stock_code)
            logger.debug(f"转换后的 Tushare 代码: {ts_code}")
            
            # 尝试调用 Tushare 新闻接口
            # 注意: Tushare 的新闻接口可能需要特定的积分权限
            try:
                # 检查 Tushare 是否支持新闻接口
                if not hasattr(self.pro, 'news'):
                    logger.warning("⚠️ 当前 Tushare 版本不支持 news 接口，或权限不足")
                    logger.info("💡 提示: Tushare 新闻接口可能需要更高的积分权限")
                    return []
                
                # 转换日期格式为 YYYYMMDD，支持秒级输入
                if start_date:
                    start_dt = datetime.strptime(start_date, '%Y-%m-%d %H:%M:%S')
                    ts_start_date = start_dt.strftime('%Y%m%d')
                else:
                    ts_start_date = None
                
                if end_date:
                    end_dt = datetime.strptime(end_date, '%Y-%m-%d %H:%M:%S')
                    ts_end_date = end_dt.strftime('%Y%m%d')
                else:
                    ts_end_date = None
                
                logger.debug(f"调用 Tushare API: pro.news(src='sina', start_date={ts_start_date}, end_date={ts_end_date})")
                
                # 调用 Tushare 新闻接口
                # Tushare 新闻接口通常按日期获取，不是按个股
                df = self.pro.news(
                    src='sina',  # 新闻来源
                    start_date=ts_start_date,
                    end_date=ts_end_date
                )
                
                if df is None or df.empty:
                    logger.info(f"📭 Tushare 未获取到新闻 (ts_code={ts_code}, start_date={ts_start_date}, end_date={ts_end_date})")
                    return []
                
                logger.debug(f"Tushare 返回 {len(df)} 条原始新闻数据")
                
                # 解析新闻数据
                news_items = []
                for _, row in df.head(max_news).iterrows():
                    try:
                        # 解析时间
                        datetime_str = row.get('datetime', '')
                        if datetime_str:
                            publish_time = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M:%S')
                        else:
                            publish_time = datetime.now()
                        
                        title = row.get('title', '')
                        content = row.get('content', '')
                        
                        news_item = NewsItem(
                            title=title,
                            content=content,
                            source=self.source,
                            publish_time=publish_time,
                            url=row.get('url', ''),
                            urgency=self.assess_urgency(title, content),
                            relevance_score=self.calculate_relevance(title, stock_code),
                            stock_code=stock_code
                        )
                        news_items.append(news_item)
                    except Exception as e:
                        logger.warning(f"解析 Tushare 新闻项失败: {e}")
                        continue
                
                logger.info(f"📝 Tushare 成功获取 {len(news_items)} 条新闻")
                return news_items
                
            except AttributeError as e:
                logger.warning(f"⚠️ Tushare API 不支持 news 接口: {e}")
                logger.info("💡 提示: 请检查 Tushare 账户权限或升级 tushare 包")
                return []
                
        except Exception as e:
            import traceback
            error_type = type(e).__name__
            logger.error(f"❌ Tushare 新闻获取失败 ({error_type}): {str(e)}")
            logger.debug(f"Tushare API 调用参数: stock_code={stock_code}, start_date={start_date}, end_date={end_date}")
            logger.debug(f"完整异常堆栈:\n{traceback.format_exc()}")
            return []
    
    def _convert_to_tushare_code(self, stock_code: str) -> str:
        """
        转换股票代码为 Tushare 格式
        
        Args:
            stock_code: 原始股票代码
            
        Returns:
            Tushare 格式的股票代码
        """
        # 如果已经是 Tushare 格式，直接返回
        if '.' in stock_code and (stock_code.endswith('.SH') or stock_code.endswith('.SZ')):
            return stock_code
        
        # A股代码转换规则
        # 60xxxx, 688xxx -> 上交所 (.SH)
        # 000xxx, 002xxx, 300xxx -> 深交所 (.SZ)
        if stock_code.startswith('6') or stock_code.startswith('688'):
            return f"{stock_code}.SH"
        elif stock_code.startswith('0') or stock_code.startswith('3'):
            return f"{stock_code}.SZ"
        
        # 默认返回原代码
        return stock_code
