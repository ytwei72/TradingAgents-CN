#!/usr/bin/env python3
"""
MongoDB步骤状态管理器
用于保存和读取分析步骤状态到MongoDB数据库的analysis_steps_status集合
"""

import os
from datetime import datetime
from typing import Dict, Optional, Any

from tradingagents.utils.logging_manager import get_logger
logger = get_logger('utils')

try:
    from pymongo import MongoClient
    from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
    MONGODB_AVAILABLE = True
except ImportError:
    MONGODB_AVAILABLE = False
    logger.warning("pymongo未安装，MongoDB功能不可用")


class MongoDBStepsStatusManager:
    """MongoDB步骤状态管理器"""
    
    def __init__(self):
        self.collection = None
        self.connected = False
        
        if MONGODB_AVAILABLE:
            self._connect()
    
    def _connect(self):
        """连接到MongoDB（只使用统一的连接管理）"""
        try:
            # 只使用统一的连接管理
            from tradingagents.storage.manager import get_mongo_collection
            
            self.collection = get_mongo_collection("analysis_steps_status")
            if self.collection is None:
                logger.warning("⚠️ [MongoDB步骤状态] 统一连接管理不可用，无法连接MongoDB")
                self.connected = False
                return
            
            # 创建索引
            self._create_indexes()
            
            self.connected = True
            logger.info(f"✅ [MongoDB步骤状态] 连接成功（使用统一连接管理）: analysis_steps_status")
            
        except Exception as e:
            logger.warning(f"⚠️ [MongoDB步骤状态] 连接失败: {e}")
            self.connected = False
    
    def _create_indexes(self):
        """创建索引以提高查询性能"""
        try:
            if not self.connected or not self.collection:
                return
                
            # 创建复合唯一索引，确保每个股票代码和日期只有一条记录
            # 注意：由于现在支持按参数查询，这个唯一索引可能需要调整
            # 但为了保持向后兼容，暂时保留
            try:
                self.collection.create_index(
                    [("company_of_interest", 1), ("trade_date", 1)],
                    unique=True,
                    name="ticker_date_unique"
                )
            except Exception:
                # 如果索引已存在，忽略错误
                pass
            
            # 创建单字段索引
            self.collection.create_index("company_of_interest")
            self.collection.create_index("trade_date")
            self.collection.create_index("analysis_id")
            # 为缓存查询添加索引
            self.collection.create_index("research_depth")
            self.collection.create_index("analysts")
            self.collection.create_index("market_type")
            
            logger.debug("✅ [MongoDB步骤状态] 索引创建成功")
            
        except Exception as e:
            logger.warning(f"⚠️ [MongoDB步骤状态] 索引创建失败: {e}")
    
    def _normalize_date(self, trade_date: str) -> str:
        """规范化日期格式为 YYYY-MM-DD
        
        Args:
            trade_date: 日期字符串，支持多种格式
            
        Returns:
            规范化后的日期字符串 (YYYY-MM-DD)
        """
        if not trade_date:
            return trade_date
        
        # 如果已经是 YYYY-MM-DD 格式，直接返回
        if len(trade_date) == 10 and '-' in trade_date:
            return trade_date
        
        # 如果是 YYYYMMDD 格式，转换为 YYYY-MM-DD
        if len(trade_date) == 8 and '-' not in trade_date:
            return f"{trade_date[:4]}-{trade_date[4:6]}-{trade_date[6:8]}"
        
        # 尝试解析其他格式
        try:
            from datetime import datetime as dt
            # 尝试多种日期格式
            for fmt in ['%Y-%m-%d', '%Y%m%d', '%Y/%m/%d']:
                try:
                    dt_obj = dt.strptime(trade_date, fmt)
                    return dt_obj.strftime('%Y-%m-%d')
                except ValueError:
                    continue
        except Exception:
            pass
        
        # 如果无法解析，返回原值并记录警告
        logger.warning(f"⚠️ [MongoDB步骤状态] 日期格式异常: {trade_date}")
        return trade_date
    
    def save_step_status(self, step_data: Dict[str, Any]) -> bool:
        """保存步骤状态到MongoDB
        
        Args:
            step_data: 步骤数据字典，必须包含 company_of_interest 和 trade_date 字段
            
        Returns:
            保存成功返回 True，否则返回 False
        """
        if not self.connected:
            logger.warning("⚠️ [MongoDB步骤状态] 未连接，跳过保存")
            return False

        try:
            # 提取关键字段
            ticker = step_data.get('company_of_interest', '')
            trade_date = step_data.get('trade_date', '')
            
            if not ticker or not trade_date:
                logger.warning(f"⚠️ [MongoDB步骤状态] 跳过无效数据：ticker={ticker}, trade_date={trade_date}")
                return False
            
            # 规范化日期格式
            normalized_date = self._normalize_date(trade_date)
            
            # 创建文档，使用步骤数据的所有字段
            document = step_data.copy()
            document['trade_date'] = normalized_date
            
            # 确保有analysis_id
            if 'analysis_id' not in document or not document.get('analysis_id'):
                if 'session_id' in document and document.get('session_id'):
                    document['analysis_id'] = document['session_id']
            
            # 使用upsert操作，基于ticker和trade_date的唯一性
            result = self.collection.update_one(
                {
                    "company_of_interest": ticker,
                    "trade_date": normalized_date
                },
                {
                    "$set": document
                },
                upsert=True
            )
            
            if result.upserted_id:
                logger.debug(f"✅ [MongoDB步骤状态] 插入新记录: {ticker} - {normalized_date}")
            else:
                logger.debug(f"🔄 [MongoDB步骤状态] 更新已存在记录: {ticker} - {normalized_date}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ [MongoDB步骤状态] 保存失败: {e}")
            return False
    
    def load_step_status(self, ticker: str, trade_date: str) -> Optional[Dict[str, Any]]:
        """从MongoDB加载步骤状态
        
        Args:
            ticker: 股票代码
            trade_date: 交易日期
            
        Returns:
            如果找到记录则返回文档字典（移除_id字段），否则返回None
        """
        if not self.connected:
            logger.debug("⚠️ [MongoDB步骤状态] 未连接，无法读取")
            return None

        try:
            # 规范化日期格式
            normalized_date = self._normalize_date(trade_date)
            
            # 查询MongoDB：根据股票代码和日期查询一条记录
            query = {
                "company_of_interest": ticker,
                "trade_date": normalized_date
            }
            
            doc = self.collection.find_one(query)
            
            if doc:
                # 移除MongoDB的_id字段，避免序列化问题
                doc.pop('_id', None)
                logger.debug(f"✅ [MongoDB步骤状态] 找到记录: {ticker} - {normalized_date}")
                return doc
            else:
                logger.debug(f"🔍 [MongoDB步骤状态] 未找到记录: {ticker} - {normalized_date}")
                return None
                
        except Exception as e:
            logger.warning(f"⚠️ [MongoDB步骤状态] 读取失败: {e}")
            return None
    
    def find_cached_step_status(
        self,
        ticker: str,
        trade_date: str,
        research_depth: Optional[int] = None,
        analysts: Optional[list] = None,
        market_type: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """根据完整参数查找缓存的步骤状态（用于结果复用）
        
        Args:
            ticker: 股票代码
            trade_date: 交易日期
            research_depth: 研究深度（可选）
            analysts: 分析师列表（可选）
            market_type: 市场类型（可选）
            
        Returns:
            如果找到匹配的记录则返回文档字典（移除_id字段），否则返回None
        """
        if not self.connected:
            logger.debug("⚠️ [MongoDB步骤状态] 未连接，无法查询缓存")
            return None

        try:
            # 规范化日期格式
            normalized_date = self._normalize_date(trade_date)
            
            # 构建查询条件
            query = {
                "company_of_interest": ticker,
                "trade_date": normalized_date
            }
            
            # 如果提供了研究深度，添加到查询条件
            if research_depth is not None:
                query["research_depth"] = research_depth
            
            # 如果提供了分析师列表，添加到查询条件（需要完全匹配）
            if analysts is not None:
                # 规范化分析师列表（排序后比较，确保顺序不影响匹配）
                normalized_analysts = sorted([str(a).lower() for a in analysts])
                # 使用 $all 和 $size 确保完全匹配（顺序无关）
                # 注意：这要求数据库中的 analysts 字段也是排序的列表
                query["analysts"] = {"$all": normalized_analysts, "$size": len(normalized_analysts)}
            
            # 如果提供了市场类型，添加到查询条件
            if market_type is not None:
                query["market_type"] = market_type
            
            # 查询MongoDB，按时间倒序排列，取最新的一条
            doc = self.collection.find_one(
                query,
                sort=[("timestamp", -1)]  # 按时间戳倒序，取最新的
            )
            
            if doc:
                # 移除MongoDB的_id字段，避免序列化问题
                doc.pop('_id', None)
                logger.info(f"✅ [缓存查询] 找到匹配的缓存记录: {ticker} - {normalized_date} (研究深度: {research_depth}, 分析师: {analysts})")
                return doc
            else:
                logger.debug(f"🔍 [缓存查询] 未找到匹配的缓存记录: {ticker} - {normalized_date}")
                return None
                
        except Exception as e:
            logger.warning(f"⚠️ [MongoDB步骤状态] 缓存查询失败: {e}")
            return None
    
    def is_connected(self) -> bool:
        """检查是否已连接到MongoDB
        
        Returns:
            如果已连接返回True，否则返回False
        """
        return self.connected


# 创建全局实例
mongodb_steps_status_manager = MongoDBStepsStatusManager()

