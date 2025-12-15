#!/usr/bin/env python3
"""
模型使用记录 MongoDB 管理器
用于管理 model_usages 集合的完整 CRUD 操作
"""

import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

# 导入日志模块
from tradingagents.utils.logging_manager import get_logger
logger = get_logger('agents')

# 定义 UsageRecord 类
@dataclass
class UsageRecord:
    """使用记录"""
    timestamp: str  # 时间戳
    provider: str  # 供应商
    model_name: str  # 模型名称
    input_tokens: int  # 输入token数
    output_tokens: int  # 输出token数
    cost: float  # 成本
    session_id: str  # 会话ID
    analysis_type: str  # 分析类型

try:
    from pymongo import MongoClient
    from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError, DuplicateKeyError
    from bson import ObjectId
    MONGODB_AVAILABLE = True
except ImportError:
    MONGODB_AVAILABLE = False
    MongoClient = None
    ObjectId = None


class ModelUsageManager:
    """模型使用记录 MongoDB 管理器"""
    
    def __init__(self):
        """
        初始化 MongoDB 管理器（使用统一的连接管理）
        """
        if not MONGODB_AVAILABLE:
            raise ImportError("pymongo is not installed. Please install it with: pip install pymongo")
        
        self.collection_name = "model_usages"
        
        self.collection = None
        self._connected = False
        
        # 尝试连接
        self._connect()
    
    def _connect(self):
        """连接到 MongoDB（只使用统一的 storage 连接管理）"""
        try:
            # 只使用统一的 storage 连接管理
            from tradingagents.storage.manager import get_mongo_collection
            
            self.collection = get_mongo_collection(self.collection_name)
            if self.collection is None:
                logger.error("❌ 统一连接管理不可用，无法连接MongoDB")
                self._connected = False
                return
            
            # 创建索引
            self._create_indexes()
            
            self._connected = True
            logger.info(f"✅ MongoDB连接成功（使用统一连接管理）: {self.collection_name}")
            
        except Exception as e:
            logger.error(f"❌ MongoDB连接失败: {e}")
            logger.info(f"将使用本地JSON文件存储")
            self._connected = False
    
    def _create_indexes(self):
        """创建数据库索引"""
        try:
            # 创建复合索引：时间戳倒序、供应商、模型名称
            self.collection.create_index([
                ("timestamp", -1),
                ("provider", 1),
                ("model_name", 1)
            ])
            
            # 创建会话ID索引
            self.collection.create_index("session_id")
            
            # 创建分析类型索引
            self.collection.create_index("analysis_type")
            
            # 创建时间戳索引（用于时间范围查询）
            self.collection.create_index("timestamp")
            
            # 创建供应商和模型名称的复合索引
            self.collection.create_index([
                ("provider", 1),
                ("model_name", 1)
            ])
            
            logger.info("✅ MongoDB索引创建成功")
            
        except Exception as e:
            logger.error(f"创建MongoDB索引失败: {e}")
    
    def is_connected(self) -> bool:
        """检查是否连接到 MongoDB"""
        return self._connected
    
    def initialize(self) -> bool:
        """初始化数据库（创建索引等）"""
        if not self._connected:
            return False
        
        try:
            self._create_indexes()
            logger.info("✅ 数据库初始化完成")
            return True
        except Exception as e:
            logger.error(f"❌ 数据库初始化失败: {e}")
            return False
    
    def insert_usage_record(self, record: UsageRecord) -> Optional[str]:
        """
        插入单个使用记录
        
        Args:
            record: UsageRecord 对象
            
        Returns:
            插入记录的 _id，如果失败则返回 None
        """
        if not self._connected:
            return None
        
        try:
            # 转换为字典格式
            record_dict = asdict(record)
            
            # 添加MongoDB特有的字段
            record_dict['_created_at'] = datetime.now()
            
            # 插入记录
            result = self.collection.insert_one(record_dict)
            
            if result.inserted_id:
                logger.debug(f"✅ 使用记录已插入: {result.inserted_id}")
                return str(result.inserted_id)
            else:
                logger.error(f"❌ MongoDB插入失败：未返回插入ID")
                return None
                
        except DuplicateKeyError as e:
            logger.warning(f"⚠️ 记录已存在: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ 保存记录到MongoDB失败: {e}")
            return None
    
    def save_usage_record(self, record: UsageRecord) -> bool:
        """
        保存单个使用记录到MongoDB（兼容 MongoDBStorage 接口）
        
        Args:
            record: UsageRecord 对象
            
        Returns:
            是否保存成功
        """
        record_id = self.insert_usage_record(record)
        return record_id is not None
    
    def load_usage_records(self, limit: int = 10000, days: int = None) -> List[UsageRecord]:
        """
        从MongoDB加载使用记录（兼容 MongoDBStorage 接口）
        
        Args:
            limit: 返回记录数限制
            days: 最近N天的记录
            
        Returns:
            UsageRecord 对象列表
        """
        return self.query_usage_records(limit=limit, days=days)
    
    def insert_many_usage_records(self, records: List[UsageRecord]) -> int:
        """
        批量插入使用记录
        
        Args:
            records: UsageRecord 对象列表
            
        Returns:
            成功插入的记录数
        """
        if not self._connected:
            return 0
        
        if not records:
            return 0
        
        try:
            # 转换为字典格式
            records_dict = []
            for record in records:
                record_dict = asdict(record)
                record_dict['_created_at'] = datetime.now()
                records_dict.append(record_dict)
            
            # 批量插入
            result = self.collection.insert_many(records_dict, ordered=False)
            
            inserted_count = len(result.inserted_ids)
            logger.info(f"✅ 批量插入 {inserted_count} 条使用记录")
            return inserted_count
                
        except Exception as e:
            # 处理部分插入成功的情况
            if hasattr(e, 'details') and 'writeErrors' in e.details:
                inserted_count = e.details.get('nInserted', 0)
                logger.warning(f"⚠️ 部分插入成功: {inserted_count}/{len(records)}")
                return inserted_count
            logger.error(f"❌ 批量插入记录失败: {e}")
            return 0
    
    def update_usage_record(self, record_id: str, record: UsageRecord) -> bool:
        """
        更新使用记录
        
        Args:
            record_id: 记录的 _id
            record: 新的 UsageRecord 对象
            
        Returns:
            是否更新成功
        """
        if not self._connected:
            return False
        
        try:
            # 转换为字典格式
            record_dict = asdict(record)
            
            # 添加更新时间
            record_dict['_updated_at'] = datetime.now()
            
            # 更新记录
            result = self.collection.update_one(
                {"_id": ObjectId(record_id)},
                {"$set": record_dict}
            )
            
            if result.modified_count > 0:
                logger.info(f"✅ 使用记录已更新: {record_id}")
                return True
            else:
                logger.warning(f"⚠️ 未找到要更新的记录: {record_id}")
                return False
                
        except Exception as e:
            logger.error(f"❌ 更新记录失败: {e}")
            return False
    
    def query_usage_records(self, 
                           limit: int = 10000,
                           days: int = None,
                           provider: str = None,
                           model_name: str = None,
                           session_id: str = None,
                           analysis_type: str = None,
                           start_date: str = None,
                           end_date: str = None) -> List[UsageRecord]:
        """
        查询使用记录
        
        Args:
            limit: 返回记录数限制
            days: 最近N天的记录
            provider: 供应商过滤
            model_name: 模型名称过滤
            session_id: 会话ID过滤
            analysis_type: 分析类型过滤
            start_date: 开始日期（ISO格式字符串）
            end_date: 结束日期（ISO格式字符串）
            
        Returns:
            UsageRecord 对象列表
        """
        if not self._connected:
            return []
        
        try:
            # 构建查询条件
            query = {}
            
            # 时间范围查询
            if days:
                cutoff_date = datetime.now() - timedelta(days=days)
                query['timestamp'] = {'$gte': cutoff_date.isoformat()}
            elif start_date or end_date:
                date_query = {}
                if start_date:
                    date_query['$gte'] = start_date
                if end_date:
                    date_query['$lte'] = end_date
                if date_query:
                    query['timestamp'] = date_query
            
            # 其他过滤条件
            if provider:
                query['provider'] = provider
            if model_name:
                query['model_name'] = model_name
            if session_id:
                query['session_id'] = session_id
            if analysis_type:
                query['analysis_type'] = analysis_type
            
            # 查询记录，按时间倒序
            cursor = self.collection.find(query).sort('timestamp', -1).limit(limit)
            
            records = []
            for doc in cursor:
                # 移除MongoDB特有的字段
                doc.pop('_id', None)
                doc.pop('_created_at', None)
                doc.pop('_updated_at', None)
                
                # 转换为UsageRecord对象
                try:
                    record = UsageRecord(**doc)
                    records.append(record)
                except Exception as e:
                    logger.error(f"❌ 解析记录失败: {e}, 记录: {doc}")
                    continue
            
            return records
            
        except Exception as e:
            logger.error(f"❌ 从MongoDB查询记录失败: {e}")
            return []
    
    def get_usage_statistics(self, 
                            days: int = 30,
                            provider: str = None,
                            model_name: str = None,
                            start_date: str = None,
                            end_date: str = None) -> Dict[str, Any]:
        """
        获取使用统计信息
        
        Args:
            days: 统计最近N天的数据
            provider: 按供应商过滤
            model_name: 按模型名称过滤
            start_date: 开始日期（ISO格式字符串）
            end_date: 结束日期（ISO格式字符串）
            
        Returns:
            统计信息字典
        """
        if not self._connected:
            return {}
        
        try:
            # 构建匹配条件
            match_conditions = {}
            
            # 时间范围查询
            if start_date and end_date:
                match_conditions['timestamp'] = {
                    '$gte': start_date,
                    '$lte': end_date
                }
            elif days:
                cutoff_date = datetime.now() - timedelta(days=days)
                match_conditions['timestamp'] = {'$gte': cutoff_date.isoformat()}
            
            if provider:
                match_conditions['provider'] = provider
            if model_name:
                match_conditions['model_name'] = model_name
            
            # 聚合查询
            pipeline = [
                {
                    '$match': match_conditions
                },
                {
                    '$group': {
                        '_id': None,
                        'total_cost': {'$sum': '$cost'},
                        'total_input_tokens': {'$sum': '$input_tokens'},
                        'total_output_tokens': {'$sum': '$output_tokens'},
                        'total_requests': {'$sum': 1},
                        'avg_cost': {'$avg': '$cost'},
                        'avg_input_tokens': {'$avg': '$input_tokens'},
                        'avg_output_tokens': {'$avg': '$output_tokens'}
                    }
                }
            ]
            
            result = list(self.collection.aggregate(pipeline))
            
            if result:
                stats = result[0]
                return {
                    'period_days': days,
                    'total_cost': round(stats.get('total_cost', 0), 4),
                    'total_input_tokens': int(stats.get('total_input_tokens', 0)),
                    'total_output_tokens': int(stats.get('total_output_tokens', 0)),
                    'total_requests': stats.get('total_requests', 0),
                    'avg_cost': round(stats.get('avg_cost', 0), 6),
                    'avg_input_tokens': round(stats.get('avg_input_tokens', 0), 2),
                    'avg_output_tokens': round(stats.get('avg_output_tokens', 0), 2)
                }
            else:
                return {
                    'period_days': days,
                    'total_cost': 0,
                    'total_input_tokens': 0,
                    'total_output_tokens': 0,
                    'total_requests': 0,
                    'avg_cost': 0,
                    'avg_input_tokens': 0,
                    'avg_output_tokens': 0
                }
                
        except Exception as e:
            logger.error(f"❌ 获取统计信息失败: {e}")
            return {}
    
    def get_provider_statistics(self, days: int = 30, start_date: str = None, end_date: str = None) -> Dict[str, Dict[str, Any]]:
        """
        按供应商获取统计信息
        
        Args:
            days: 统计最近N天的数据
            start_date: 开始日期（ISO格式字符串）
            end_date: 结束日期（ISO格式字符串）
            
        Returns:
            按供应商分组的统计信息字典
        """
        if not self._connected:
            return {}
        
        try:
            # 构建匹配条件
            match_conditions = {}
            
            # 时间范围查询
            if start_date and end_date:
                match_conditions['timestamp'] = {
                    '$gte': start_date,
                    '$lte': end_date
                }
            elif days:
                cutoff_date = datetime.now() - timedelta(days=days)
                match_conditions['timestamp'] = {'$gte': cutoff_date.isoformat()}
            
            # 按供应商聚合
            pipeline = [
                {
                    '$match': match_conditions
                },
                {
                    '$group': {
                        '_id': '$provider',
                        'cost': {'$sum': '$cost'},
                        'input_tokens': {'$sum': '$input_tokens'},
                        'output_tokens': {'$sum': '$output_tokens'},
                        'requests': {'$sum': 1},
                        'avg_cost': {'$avg': '$cost'}
                    }
                }
            ]
            
            results = list(self.collection.aggregate(pipeline))
            
            provider_stats = {}
            for result in results:
                provider = result['_id']
                provider_stats[provider] = {
                    'cost': round(result.get('cost', 0), 4),
                    'input_tokens': result.get('input_tokens', 0),
                    'output_tokens': result.get('output_tokens', 0),
                    'requests': result.get('requests', 0),
                    'avg_cost': round(result.get('avg_cost', 0), 6)
                }
            
            return provider_stats
            
        except Exception as e:
            logger.error(f"❌ 获取供应商统计失败: {e}")
            return {}
    
    def get_model_statistics(self, days: int = 30, provider: str = None, start_date: str = None, end_date: str = None) -> Dict[str, Dict[str, Any]]:
        """
        按模型获取统计信息
        
        Args:
            days: 统计最近N天的数据
            provider: 按供应商过滤
            start_date: 开始日期（ISO格式字符串）
            end_date: 结束日期（ISO格式字符串）
            
        Returns:
            按模型分组的统计信息字典
        """
        if not self._connected:
            return {}
        
        try:
            # 构建匹配条件
            match_conditions = {}
            
            # 时间范围查询
            if start_date and end_date:
                match_conditions['timestamp'] = {
                    '$gte': start_date,
                    '$lte': end_date
                }
            elif days:
                cutoff_date = datetime.now() - timedelta(days=days)
                match_conditions['timestamp'] = {'$gte': cutoff_date.isoformat()}
            
            if provider:
                match_conditions['provider'] = provider
            
            # 按模型聚合
            pipeline = [
                {
                    '$match': match_conditions
                },
                {
                    '$group': {
                        '_id': {
                            'provider': '$provider',
                            'model_name': '$model_name'
                        },
                        'cost': {'$sum': '$cost'},
                        'input_tokens': {'$sum': '$input_tokens'},
                        'output_tokens': {'$sum': '$output_tokens'},
                        'requests': {'$sum': 1},
                        'avg_cost': {'$avg': '$cost'}
                    }
                }
            ]
            
            results = list(self.collection.aggregate(pipeline))
            
            model_stats = {}
            for result in results:
                model_key = f"{result['_id']['provider']}/{result['_id']['model_name']}"
                model_stats[model_key] = {
                    'provider': result['_id']['provider'],
                    'model_name': result['_id']['model_name'],
                    'cost': round(result.get('cost', 0), 4),
                    'input_tokens': result.get('input_tokens', 0),
                    'output_tokens': result.get('output_tokens', 0),
                    'requests': result.get('requests', 0),
                    'avg_cost': round(result.get('avg_cost', 0), 6)
                }
            
            return model_stats
            
        except Exception as e:
            logger.error(f"❌ 获取模型统计失败: {e}")
            return {}
    
    def get_daily_statistics(self, 
                             days: int = 7,
                             provider: str = None,
                             model_name: str = None,
                             start_date: str = None,
                             end_date: str = None) -> Dict[str, Dict[str, Any]]:
        """
        按日期获取统计信息
        
        Args:
            days: 统计最近N天的数据（默认7天）
            provider: 按供应商过滤
            model_name: 按模型名称过滤
            start_date: 开始日期（ISO格式字符串）
            end_date: 结束日期（ISO格式字符串）
            
        Returns:
            按日期分组的统计信息字典，格式为:
            {
                "2025-12-15": {
                    "dashscope/qwen-max": {
                        "provider": "dashscope",
                        "model_name": "qwen-max",
                        "input_tokens": 10000,
                        "output_tokens": 5000,
                        "total_tokens": 15000,
                        "cost": 0.5,
                        "requests": 10
                    },
                    ...
                },
                ...
            }
        """
        if not self._connected:
            return {}
        
        try:
            # 构建匹配条件
            match_conditions = {}
            
            # 时间范围查询
            if start_date and end_date:
                match_conditions['timestamp'] = {
                    '$gte': start_date,
                    '$lte': end_date
                }
            elif days:
                cutoff_date = datetime.now() - timedelta(days=days)
                match_conditions['timestamp'] = {'$gte': cutoff_date.isoformat()}
            
            if provider:
                match_conditions['provider'] = provider
            if model_name:
                match_conditions['model_name'] = model_name
            
            # 按日期和模型聚合
            pipeline = [
                {
                    '$match': match_conditions
                },
                {
                    '$addFields': {
                        # 从ISO时间戳中提取日期部分 (YYYY-MM-DD)
                        'date': {'$substr': ['$timestamp', 0, 10]}
                    }
                },
                {
                    '$group': {
                        '_id': {
                            'date': '$date',
                            'provider': '$provider',
                            'model_name': '$model_name'
                        },
                        'input_tokens': {'$sum': '$input_tokens'},
                        'output_tokens': {'$sum': '$output_tokens'},
                        'cost': {'$sum': '$cost'},
                        'requests': {'$sum': 1}
                    }
                },
                {
                    '$sort': {'_id.date': -1}  # 按日期倒序
                }
            ]
            
            results = list(self.collection.aggregate(pipeline))
            
            # 组织返回数据
            daily_stats = {}
            for result in results:
                date = result['_id']['date']
                provider_name = result['_id']['provider']
                model = result['_id']['model_name']
                model_key = f"{provider_name}/{model}"
                
                if date not in daily_stats:
                    daily_stats[date] = {}
                
                input_tokens = result.get('input_tokens', 0)
                output_tokens = result.get('output_tokens', 0)
                
                daily_stats[date][model_key] = {
                    'provider': provider_name,
                    'model_name': model,
                    'input_tokens': input_tokens,
                    'output_tokens': output_tokens,
                    'total_tokens': input_tokens + output_tokens,
                    'cost': round(result.get('cost', 0), 4),
                    'requests': result.get('requests', 0)
                }
            
            return daily_stats
            
        except Exception as e:
            logger.error(f"❌ 获取按日期统计失败: {e}")
            return {}
    
    def count_records(self, 
                     days: int = None,
                     provider: str = None,
                     model_name: str = None,
                     start_date: str = None,
                     end_date: str = None) -> int:
        """
        统计记录数量
        
        Args:
            days: 统计最近N天的记录
            provider: 按供应商过滤
            model_name: 按模型名称过滤
            start_date: 开始日期（ISO格式字符串）
            end_date: 结束日期（ISO格式字符串）
            
        Returns:
            记录数量
        """
        if not self._connected:
            return 0
        
        try:
            query = {}
            
            # 时间范围查询
            if start_date and end_date:
                query['timestamp'] = {
                    '$gte': start_date,
                    '$lte': end_date
                }
            elif days:
                cutoff_date = datetime.now() - timedelta(days=days)
                query['timestamp'] = {'$gte': cutoff_date.isoformat()}
            
            if provider:
                query['provider'] = provider
            if model_name:
                query['model_name'] = model_name
            
            return self.collection.count_documents(query)
            
        except Exception as e:
            logger.error(f"❌ 统计记录数量失败: {e}")
            return 0
    
    def cleanup_old_records(self, days: int = 90) -> int:
        """
        清理旧记录（兼容 MongoDBStorage 接口）
        
        Args:
            days: 删除N天前的记录
            
        Returns:
            删除的记录数
        """
        return self._delete_old_records(days)
    
    def delete_old_records(self, days: int = 90) -> int:
        """
        删除旧记录
        
        Args:
            days: 删除N天前的记录
            
        Returns:
            删除的记录数
        """
        return self._delete_old_records(days)
    
    def _delete_old_records(self, days: int = 90) -> int:
        """
        删除旧记录（内部实现）
        
        Args:
            days: 删除N天前的记录
            
        Returns:
            删除的记录数
        """
        if not self._connected:
            return 0
        
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            result = self.collection.delete_many({
                'timestamp': {'$lt': cutoff_date.isoformat()}
            })
            
            deleted_count = result.deleted_count
            if deleted_count > 0:
                logger.info(f"✅ 清理了 {deleted_count} 条超过 {days} 天的记录")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"❌ 清理旧记录失败: {e}")
            return 0
    
    def close(self):
        """关闭 MongoDB 连接（连接由统一管理器管理，此方法仅标记状态）"""
        self._connected = False
        logger.info(f"✅ MongoDB连接状态已更新")

