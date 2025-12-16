#!/usr/bin/env python3
"""
A股历史交易数据管理器
用于从MongoDB的a_stock_his_trans集合中查询历史交易数据

集合名称: a_stock_his_trans
数据库: tradingagents (MongoDB)
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import pandas as pd

from tradingagents.utils.logging_manager import get_logger
logger = get_logger('storage')

try:
    from pymongo import ASCENDING, DESCENDING
    MONGODB_AVAILABLE = True
except ImportError:
    MONGODB_AVAILABLE = False
    logger.warning("pymongo未安装，MongoDB功能不可用")


class StockHistoryManager:
    """A股历史交易数据管理器"""
    
    # 集合名称
    COLLECTION_NAME = "a_stock_his_trans"
    
    def __init__(self):
        self.collection = None
        self.connected = False
        
        if MONGODB_AVAILABLE:
            self._connect()
    
    def _connect(self):
        """连接到MongoDB"""
        try:
            from tradingagents.storage.manager import get_mongo_collection
            
            self.collection = get_mongo_collection(self.COLLECTION_NAME)
            if self.collection is None:
                logger.error("❌ 统一连接管理不可用，无法连接MongoDB")
                self.connected = False
                return
            
            # 创建索引
            self._create_indexes()
            
            self.connected = True
            logger.info(f"✅ MongoDB连接成功: {self.COLLECTION_NAME}")
            
        except Exception as e:
            logger.error(f"❌ MongoDB连接失败: {e}")
            self.connected = False
    
    def _create_indexes(self):
        """创建索引以提高查询性能"""
        try:
            # 复合索引：股票代码 + 日期（最常用的查询组合）
            self.collection.create_index([
                ("code", ASCENDING),
                ("date", DESCENDING)
            ])
            
            # 单字段索引
            self.collection.create_index("code")
            self.collection.create_index("date")
            
            logger.info("✅ a_stock_his_trans索引创建成功")
            
        except Exception as e:
            logger.error(f"❌ a_stock_his_trans索引创建失败: {e}")
    
    def get_stock_history(
        self,
        stock_code: str,
        start_date: str,
        end_date: str
    ) -> pd.DataFrame:
        """
        获取股票指定日期区间的历史交易数据
        
        Args:
            stock_code: 股票代码（6位数字，如：000001）
            start_date: 开始日期（YYYY-MM-DD格式）
            end_date: 结束日期（YYYY-MM-DD格式）
        
        Returns:
            pd.DataFrame: 历史交易数据，包含以下列：
                - date: 交易日期
                - open: 开盘价
                - high: 最高价
                - low: 最低价
                - close: 收盘价
                - volume: 成交量
                如果查询失败或数据为空，返回空的DataFrame
        """
        if not self.connected:
            logger.error("❌ MongoDB未连接")
            return pd.DataFrame()
        
        try:
            # 将字符串日期转换为datetime对象（MongoDB的ISODate是datetime类型）
            try:
                start_dt = pd.to_datetime(start_date)
                end_dt = pd.to_datetime(end_date)
            except Exception as e:
                logger.error(f"日期格式转换失败: {e}")
                return pd.DataFrame()
            
            # 构建查询条件（MongoDB的date字段是ISODate类型，需要使用datetime对象查询）
            query = {
                'code': stock_code,
                'date': {
                    '$gte': start_dt.to_pydatetime(),
                    '$lte': end_dt.to_pydatetime()
                }
            }
            
            # 查询数据
            cursor = self.collection.find(query).sort('date', ASCENDING)
            records = list(cursor)
            
            if not records:
                logger.warning(f"⚠️ 未找到股票{stock_code}在{start_date}至{end_date}期间的历史数据")
                return pd.DataFrame()
            
            # 转换为DataFrame
            df = pd.DataFrame(records)
            
            # 移除_id字段
            if '_id' in df.columns:
                df = df.drop(columns=['_id'])
            
            # 标准化列名（兼容不同的字段名）
            column_mapping = {
                'trade_date': 'date',
                'ts_code': 'code',
                'vol': 'volume',
                'amount': 'amount'
            }
            
            for old_col, new_col in column_mapping.items():
                if old_col in df.columns and new_col not in df.columns:
                    df[new_col] = df[old_col]
            
            # 确保date列存在且为字符串格式
            if 'date' not in df.columns and 'trade_date' in df.columns:
                df['date'] = df['trade_date']
            
            # 确保date列是字符串格式（MongoDB返回的是ISODate即datetime对象）
            if 'date' in df.columns and not df.empty:
                if pd.api.types.is_datetime64_any_dtype(df['date']):
                    df['date'] = df['date'].dt.strftime('%Y-%m-%d')
                elif len(df) > 0 and not isinstance(df['date'].iloc[0], str):
                    df['date'] = df['date'].astype(str)
            
            # 确保数值列为数值类型
            numeric_columns = ['open', 'high', 'low', 'close', 'volume', 'amount']
            for col in numeric_columns:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # 按日期排序
            if 'date' in df.columns:
                df = df.sort_values('date').reset_index(drop=True)
            
            logger.info(f"✅ 获取股票{stock_code}历史数据成功: {len(df)}条（{start_date}至{end_date}）")
            
            return df
            
        except Exception as e:
            logger.error(f"❌ 获取股票历史数据失败: {e}", exc_info=True)
            return pd.DataFrame()
    
    def get_latest_date(self, stock_code: str) -> Optional[str]:
        """
        获取某只股票的最新交易日期
        
        Args:
            stock_code: 股票代码
        
        Returns:
            str: 最新交易日期（YYYY-MM-DD格式），如果不存在返回None
        """
        if not self.connected:
            return None
        
        try:
            result = self.collection.find_one(
                {'code': stock_code},
                {'date': 1},
                sort=[('date', DESCENDING)]
            )
            
            if result and 'date' in result:
                date = result['date']
                # 确保返回字符串格式
                if isinstance(date, datetime):
                    return date.strftime('%Y-%m-%d')
                return str(date)
            
            return None
            
        except Exception as e:
            logger.error(f"❌ 获取最新交易日期失败: {e}")
            return None
    
    def get_earliest_date(self, stock_code: str) -> Optional[str]:
        """
        获取某只股票的最早交易日期
        
        Args:
            stock_code: 股票代码
        
        Returns:
            str: 最早交易日期（YYYY-MM-DD格式），如果不存在返回None
        """
        if not self.connected:
            return None
        
        try:
            result = self.collection.find_one(
                {'code': stock_code},
                {'date': 1},
                sort=[('date', ASCENDING)]
            )
            
            if result and 'date' in result:
                date = result['date']
                # MongoDB的ISODate是datetime类型，转换为字符串格式
                if isinstance(date, datetime):
                    return date.strftime('%Y-%m-%d')
                elif hasattr(date, 'strftime'):  # 兼容pandas Timestamp等类型
                    return date.strftime('%Y-%m-%d')
                # 如果已经是字符串，直接返回
                return str(date)
            
            return None
            
        except Exception as e:
            logger.error(f"❌ 获取最早交易日期失败: {e}")
            return None
    
    def count_records(self, stock_code: str, start_date: Optional[str] = None, end_date: Optional[str] = None) -> int:
        """
        统计指定股票在指定日期范围内的记录数
        
        Args:
            stock_code: 股票代码
            start_date: 开始日期（可选，YYYY-MM-DD格式）
            end_date: 结束日期（可选，YYYY-MM-DD格式）
        
        Returns:
            int: 记录数
        """
        if not self.connected:
            return 0
        
        try:
            query = {'code': stock_code}
            
            if start_date or end_date:
                date_query = {}
                # 将字符串日期转换为datetime对象（MongoDB的ISODate是datetime类型）
                if start_date:
                    try:
                        start_dt = pd.to_datetime(start_date)
                        date_query['$gte'] = start_dt.to_pydatetime()
                    except Exception as e:
                        logger.error(f"开始日期格式转换失败: {e}")
                        return 0
                if end_date:
                    try:
                        end_dt = pd.to_datetime(end_date)
                        date_query['$lte'] = end_dt.to_pydatetime()
                    except Exception as e:
                        logger.error(f"结束日期格式转换失败: {e}")
                        return 0
                query['date'] = date_query
            
            count = self.collection.count_documents(query)
            return count
            
        except Exception as e:
            logger.error(f"❌ 统计记录数失败: {e}")
            return 0
    
    def get_stock_list(self) -> List[str]:
        """
        获取集合中所有股票代码列表
        
        Returns:
            List[str]: 股票代码列表
        """
        if not self.connected:
            return []
        
        try:
            codes = self.collection.distinct('code')
            return sorted(codes)
            
        except Exception as e:
            logger.error(f"❌ 获取股票列表失败: {e}")
            return []


# 单例实例
stock_history_manager = StockHistoryManager()

