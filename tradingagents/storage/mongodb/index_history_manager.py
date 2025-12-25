#!/usr/bin/env python3
"""
指数历史数据管理器
用于从MongoDB集合thematic_index_daily中读取指数历史数据

集合名称: thematic_index_daily
数据库: tradingagents (MongoDB)
"""

from datetime import datetime
from typing import List, Optional
import pandas as pd

from tradingagents.utils.logging_manager import get_logger
logger = get_logger('storage')

try:
    from pymongo import ASCENDING, DESCENDING
    MONGODB_AVAILABLE = True
except ImportError:
    MONGODB_AVAILABLE = False
    logger.warning("pymongo未安装，MongoDB功能不可用")


class IndexHistoryManager:
    """指数历史数据管理器
    
    从thematic_index_daily集合读取指数历史数据
    """
    
    # 集合名称
    COLLECTION_NAME = "thematic_index_daily"
    
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
            # 复合索引：指数代码 + 日期（最常用的查询组合）
            self.collection.create_index([
                ("code", ASCENDING),
                ("date", DESCENDING)
            ])
            
            # 唯一索引：指数代码 + 日期（避免重复数据）
            self.collection.create_index([
                ("code", ASCENDING),
                ("date", ASCENDING)
            ], unique=True)
            
            # 单字段索引
            self.collection.create_index("code")
            self.collection.create_index("date")
            
            logger.info("✅ thematic_index_daily索引创建成功")
            
        except Exception as e:
            logger.error(f"❌ thematic_index_daily索引创建失败: {e}")
    
    def _convert_index_code(self, index_code: str) -> str:
        """
        将标准指数代码转换为数据库中存储的格式
        
        数据库中的格式: sh000908, sz399001
        标准格式: 000001, 399001
        
        Args:
            index_code: 标准指数代码（如：000001、399001）
        
        Returns:
            str: 数据库格式的指数代码（如：sh000001、sz399001）
        """
        # 如果已经包含前缀，直接返回
        if index_code.startswith(('sh', 'sz')):
            return index_code
        
        # 根据指数代码判断交易所
        # 39开头的是深圳指数，其他的默认是上海指数
        if index_code.startswith('39'):
            return f"sz{index_code}"
        else:
            return f"sh{index_code}"
    
    def get_index_history(
        self,
        index_code: str,
        start_date: str,
        end_date: str
    ) -> pd.DataFrame:
        """
        获取指数指定日期区间的历史数据
        完全从数据库集合thematic_index_daily中读取
        
        Args:
            index_code: 指数代码（如：000001、399001）
            start_date: 开始日期（YYYY-MM-DD格式）
            end_date: 结束日期（YYYY-MM-DD格式）
        
        Returns:
            pd.DataFrame: 指数历史数据，包含以下列：
                - date: 交易日期
                - open: 开盘价
                - high: 最高价
                - low: 最低价
                - close: 收盘价
                - volume: 成交量
                - amount: 成交额
                - name: 指数名称
                如果查询失败或数据为空，返回空的DataFrame
        """
        if not self.connected:
            logger.error("❌ MongoDB未连接")
            return pd.DataFrame()
        
        try:
            # 转换指数代码格式
            db_index_code = self._convert_index_code(index_code)
            
            # 将字符串日期转换为datetime对象
            try:
                start_dt = pd.to_datetime(start_date)
                end_dt = pd.to_datetime(end_date)
            except Exception as e:
                logger.error(f"日期格式转换失败: {e}")
                return pd.DataFrame()
            
            # 构建查询条件
            query = {
                'code': db_index_code,
                'date': {
                    '$gte': start_dt.to_pydatetime(),
                    '$lte': end_dt.to_pydatetime()
                }
            }
            
            # 查询数据
            cursor = self.collection.find(query).sort('date', ASCENDING)
            records = list(cursor)
            
            if not records:
                logger.warning(f"⚠️ 未找到指数{index_code}({db_index_code})在{start_date}至{end_date}期间的历史数据")
                return pd.DataFrame()
            
            # 转换为DataFrame
            df = pd.DataFrame(records)
            
            # 移除_id字段
            if '_id' in df.columns:
                df = df.drop(columns=['_id'])
            
            # 确保date列存在且为字符串格式
            if 'date' not in df.columns:
                logger.warning(f"指数数据缺少date列: {list(df.columns)}")
                return pd.DataFrame()
            
            # 确保date列是字符串格式（MongoDB返回的是ISODate即datetime对象）
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
            df = df.sort_values('date').reset_index(drop=True)
            
            logger.info(f"✅ 获取指数{index_code}历史数据成功: {len(df)}条（{start_date}至{end_date}）")
            
            return df
            
        except Exception as e:
            logger.error(f"❌ 获取指数历史数据失败: {e}", exc_info=True)
            return pd.DataFrame()
    
    def get_latest_date(self, index_code: str) -> Optional[str]:
        """
        获取某个指数的最新交易日期
        
        Args:
            index_code: 指数代码
        
        Returns:
            str: 最新交易日期（YYYY-MM-DD格式），如果不存在返回None
        """
        if not self.connected:
            return None
        
        try:
            db_index_code = self._convert_index_code(index_code)
            
            result = self.collection.find_one(
                {'code': db_index_code},
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
    
    def get_earliest_date(self, index_code: str) -> Optional[str]:
        """
        获取某个指数的最早交易日期
        
        Args:
            index_code: 指数代码
        
        Returns:
            str: 最早交易日期（YYYY-MM-DD格式），如果不存在返回None
        """
        if not self.connected:
            return None
        
        try:
            db_index_code = self._convert_index_code(index_code)
            
            result = self.collection.find_one(
                {'code': db_index_code},
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
    
    def count_records(
        self, 
        index_code: str, 
        start_date: Optional[str] = None, 
        end_date: Optional[str] = None
    ) -> int:
        """
        统计指定指数在指定日期范围内的记录数
        
        Args:
            index_code: 指数代码
            start_date: 开始日期（可选，YYYY-MM-DD格式）
            end_date: 结束日期（可选，YYYY-MM-DD格式）
        
        Returns:
            int: 记录数
        """
        if not self.connected:
            return 0
        
        try:
            db_index_code = self._convert_index_code(index_code)
            query = {'code': db_index_code}
            
            if start_date or end_date:
                date_query = {}
                # 将字符串日期转换为datetime对象
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
    
    def get_index_list(self) -> List[str]:
        """
        获取集合中所有指数代码列表
        
        Returns:
            List[str]: 指数代码列表（原始格式，如sh000001）
        """
        if not self.connected:
            return []
        
        try:
            codes = self.collection.distinct('code')
            return sorted(codes)
            
        except Exception as e:
            logger.error(f"❌ 获取指数列表失败: {e}")
            return []


# 单例实例
index_history_manager = IndexHistoryManager()

