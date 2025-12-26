#!/usr/bin/env python3
"""
Cursor Usage MongoDB 管理器
用于管理 cursor_usage 集合的完整 CRUD 操作和统计功能
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from bson import ObjectId

from tradingagents.utils.logging_manager import get_logger
logger = get_logger('cursor_usage')

try:
    from pymongo.errors import BulkWriteError, DuplicateKeyError
    MONGODB_AVAILABLE = True
except ImportError:
    MONGODB_AVAILABLE = False
    BulkWriteError = None
    DuplicateKeyError = None


class CursorUsageManager:
    """Cursor Usage MongoDB 管理器"""
    
    def __init__(self):
        """
        初始化 MongoDB 管理器（使用统一的连接管理）
        """
        if not MONGODB_AVAILABLE:
            raise ImportError("pymongo is not installed. Please install it with: pip install pymongo")
        
        self.collection_name = "cursor_usage"
        self.collection = None
        self._connected = False
        
        # 尝试连接
        self._connect()
    
    def _connect(self):
        """连接到 MongoDB（使用统一的 storage 连接管理）"""
        try:
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
            self._connected = False
    
    def _create_indexes(self):
        """创建数据库索引"""
        try:
            # 创建复合索引用于去重查询
            self.collection.create_index(
                [("account_name", 1), ("Date", 1), ("Model", 1), ("Kind", 1)],
                background=True,
                name="unique_usage_record"
            )
            
            # 创建其他常用查询索引
            self.collection.create_index([("account_name", 1), ("Date", -1)], background=True)
            self.collection.create_index([("Date", -1)], background=True)
            self.collection.create_index([("account_name", 1)], background=True)
            self.collection.create_index([("Kind", 1)], background=True)
            self.collection.create_index([("Model", 1)], background=True)
            
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
    
    # ==================== 增删改查操作 ====================
    
    def insert_one(self, document: Dict[str, Any]) -> Optional[str]:
        """
        插入单条记录
        
        Args:
            document: 文档字典
            
        Returns:
            插入记录的 _id，如果失败则返回 None
        """
        if not self._connected:
            return None
        
        try:
            # 添加创建时间
            document['_created_at'] = datetime.now()
            
            # 插入记录
            result = self.collection.insert_one(document)
            
            logger.debug(f"✅ 插入记录成功: {result.inserted_id}")
            return str(result.inserted_id)
            
        except DuplicateKeyError:
            logger.warning(f"⚠️ 记录已存在（重复键）")
            return None
        except Exception as e:
            logger.error(f"❌ 插入记录失败: {e}")
            return None
    
    def insert_many(self, documents: List[Dict[str, Any]], skip_duplicates: bool = True) -> int:
        """
        批量插入记录
        
        Args:
            documents: 文档列表
            skip_duplicates: 是否跳过重复记录（基于 account_name + Date + Model + Kind）
            
        Returns:
            成功插入的记录数
        """
        if not self._connected:
            return 0
        
        if not documents:
            return 0
        
        try:
            # 如果需要去重，先过滤重复项
            if skip_duplicates:
                original_count = len(documents)
                documents = self._filter_duplicates(documents)
                if len(documents) < original_count:
                    logger.info(f"去重: {original_count} -> {len(documents)} 条")
            
            if not documents:
                return 0
            
            # 添加创建时间
            for doc in documents:
                doc['_created_at'] = datetime.now()
            
            # 批量插入（ordered=False 表示即使部分失败也继续插入）
            result = self.collection.insert_many(documents, ordered=False)
            
            inserted_count = len(result.inserted_ids)
            logger.info(f"✅ 批量插入 {inserted_count} 条记录")
            return inserted_count
            
        except BulkWriteError as e:
            # 处理部分成功的情况
            write_errors = e.details.get('writeErrors', [])
            successful_count = len(documents) - len(write_errors)
            if successful_count > 0:
                logger.warning(f"⚠️ 批量插入部分失败: {successful_count} 条成功，{len(write_errors)} 条失败")
            else:
                logger.error(f"❌ 批量插入全部失败")
            return successful_count
        except Exception as e:
            logger.error(f"❌ 批量插入记录失败: {e}")
            return 0
    
    def _filter_duplicates(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        过滤重复的文档（基于 account_name + Date + Model + Kind）
        
        Args:
            documents: 文档列表
            
        Returns:
            去重后的文档列表
        """
        if not documents:
            return documents
        
        try:
            # 构建批量查询条件（使用 $or 查询）
            queries = []
            for doc in documents:
                queries.append({
                    'account_name': doc.get('account_name'),
                    'Date': doc.get('Date'),
                    'Model': doc.get('Model'),
                    'Kind': doc.get('Kind')
                })
            
            if not queries:
                return documents
            
            # 批量查询已存在的记录（MongoDB 对 $or 查询有限制，所以分批查询）
            existing_records = set()
            batch_query_size = 100  # 每次查询100条
            for i in range(0, len(queries), batch_query_size):
                batch_queries = queries[i:i + batch_query_size]
                existing_docs = list(self.collection.find({
                    '$or': batch_queries
                }))
                
                # 构建已存在记录的集合
                for doc in existing_docs:
                    key = (
                        doc.get('account_name'),
                        doc.get('Date'),
                        doc.get('Model'),
                        doc.get('Kind')
                    )
                    existing_records.add(key)
            
            # 过滤掉已存在的记录
            filtered_docs = []
            for doc in documents:
                key = (
                    doc.get('account_name'),
                    doc.get('Date'),
                    doc.get('Model'),
                    doc.get('Kind')
                )
                if key not in existing_records:
                    filtered_docs.append(doc)
            
            return filtered_docs
            
        except Exception as e:
            logger.error(f"⚠️ 批量去重失败，将插入所有记录: {e}")
            return documents
    
    def update_one(self, document_id: str, update_data: Dict[str, Any]) -> bool:
        """
        更新单条记录
        
        Args:
            document_id: 记录的 _id
            update_data: 要更新的数据
            
        Returns:
            是否更新成功
        """
        if not self._connected:
            return False
        
        try:
            # 添加更新时间
            update_data['_updated_at'] = datetime.now()
            
            # 更新记录
            result = self.collection.update_one(
                {"_id": ObjectId(document_id)},
                {"$set": update_data}
            )
            
            if result.modified_count > 0:
                logger.info(f"✅ 记录已更新: {document_id}")
                return True
            else:
                logger.warning(f"⚠️ 未找到要更新的记录: {document_id}")
                return False
                
        except Exception as e:
            logger.error(f"❌ 更新记录失败: {e}")
            return False
    
    def delete_one(self, document_id: str) -> bool:
        """
        删除单条记录
        
        Args:
            document_id: 记录的 _id
            
        Returns:
            是否删除成功
        """
        if not self._connected:
            return False
        
        try:
            result = self.collection.delete_one({"_id": ObjectId(document_id)})
            
            if result.deleted_count > 0:
                logger.info(f"✅ 记录已删除: {document_id}")
                return True
            else:
                logger.warning(f"⚠️ 未找到要删除的记录: {document_id}")
                return False
                
        except Exception as e:
            logger.error(f"❌ 删除记录失败: {e}")
            return False
    
    def delete_many(self, filter_query: Dict[str, Any]) -> int:
        """
        批量删除记录
        
        Args:
            filter_query: 过滤条件
            
        Returns:
            删除的记录数
        """
        if not self._connected:
            return 0
        
        try:
            result = self.collection.delete_many(filter_query)
            deleted_count = result.deleted_count
            logger.info(f"✅ 批量删除 {deleted_count} 条记录")
            return deleted_count
                
        except Exception as e:
            logger.error(f"❌ 批量删除记录失败: {e}")
            return 0
    
    def find_one(self, filter_query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        查找单条记录
        
        Args:
            filter_query: 过滤条件
            
        Returns:
            文档字典，如果未找到返回 None
        """
        if not self._connected:
            return None
        
        try:
            doc = self.collection.find_one(filter_query)
            if doc:
                # 转换 _id 为字符串
                doc['_id'] = str(doc['_id'])
            return doc
                
        except Exception as e:
            logger.error(f"❌ 查找记录失败: {e}")
            return None
    
    def find_many(self, 
                  filter_query: Optional[Dict[str, Any]] = None,
                  limit: int = 10000,
                  skip: int = 0,
                  sort: Optional[List[tuple]] = None) -> List[Dict[str, Any]]:
        """
        查找多条记录
        
        Args:
            filter_query: 过滤条件
            limit: 返回记录数限制
            skip: 跳过记录数
            sort: 排序规则，例如 [("Date", -1)]
            
        Returns:
            文档列表
        """
        if not self._connected:
            return []
        
        try:
            cursor = self.collection.find(filter_query or {})
            
            if sort:
                cursor = cursor.sort(sort)
            
            cursor = cursor.skip(skip).limit(limit)
            
            documents = []
            for doc in cursor:
                # 转换 _id 为字符串
                doc['_id'] = str(doc['_id'])
                documents.append(doc)
            
            return documents
                
        except Exception as e:
            logger.error(f"❌ 查找记录失败: {e}")
            return []
    
    def count(self, filter_query: Optional[Dict[str, Any]] = None) -> int:
        """
        统计记录数
        
        Args:
            filter_query: 过滤条件
            
        Returns:
            记录数
        """
        if not self._connected:
            return 0
        
        try:
            return self.collection.count_documents(filter_query or {})
        except Exception as e:
            logger.error(f"❌ 统计记录数失败: {e}")
            return 0
    
    # ==================== 统计功能 ====================
    
    def get_available_dates(self, 
                           account_name: Optional[str] = None,
                           start_date: Optional[str] = None,
                           end_date: Optional[str] = None) -> List[str]:
        """
        获取所有可用的日期列表
        
        Args:
            account_name: 账户名称过滤
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            
        Returns:
            日期列表（格式：YYYY-MM-DD）
        """
        if not self._connected:
            return []
        
        try:
            # 构建查询条件
            match_conditions = {}
            if account_name:
                match_conditions['account_name'] = account_name
            
            if start_date or end_date:
                date_query = {}
                if start_date:
                    date_query['$gte'] = datetime.strptime(start_date, '%Y-%m-%d')
                if end_date:
                    date_query['$lte'] = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
                if date_query:
                    match_conditions['Date'] = date_query
            
            # 聚合查询，获取唯一的日期
            pipeline = [
                {'$match': match_conditions},
                {
                    '$group': {
                        '_id': {
                            '$dateToString': {
                                'format': '%Y-%m-%d',
                                'date': '$Date'
                            }
                        }
                    }
                },
                {'$sort': {'_id': 1}},
                {'$project': {'_id': 0, 'date': '$_id'}}
            ]
            
            result = list(self.collection.aggregate(pipeline))
            dates = [item['date'] for item in result]
            
            return dates
            
        except Exception as e:
            logger.error(f"❌ 获取可用日期失败: {e}")
            return []
    
    def get_total_statistics(self,
                            account_name: Optional[str] = None,
                            start_date: Optional[str] = None,
                            end_date: Optional[str] = None) -> Dict[str, Any]:
        """
        获取总体统计信息
        
        Args:
            account_name: 账户名称过滤
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            
        Returns:
            统计信息字典
        """
        if not self._connected:
            return {}
        
        try:
            # 构建匹配条件
            match_conditions = {}
            
            if account_name:
                match_conditions['account_name'] = account_name
            
            # 过滤掉 "Aborted, Not Charged" 的记录
            match_conditions['Kind'] = {'$ne': 'Aborted, Not Charged'}
            
            # 时间范围查询
            if start_date or end_date:
                date_query = {}
                if start_date:
                    date_query['$gte'] = datetime.strptime(start_date, '%Y-%m-%d')
                if end_date:
                    date_query['$lte'] = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
                if date_query:
                    match_conditions['Date'] = date_query
            
            # 聚合查询
            pipeline = [
                {'$match': match_conditions},
                {
                    '$group': {
                        '_id': None,
                        'total_requests': {'$sum': 1},
                        'total_cost': {'$sum': '$Cost'},
                        'total_input_tokens': {
                            '$sum': {
                                '$add': [
                                    '$Input (w/ Cache Write)',
                                    '$Input (w/o Cache Write)'
                                ]
                            }
                        },
                        'total_output_tokens': {'$sum': '$Output Tokens'},
                        'total_cache_read': {'$sum': '$Cache Read'},
                        'total_tokens': {'$sum': '$Total Tokens'},
                    }
                },
                {
                    '$project': {
                        '_id': 0,
                        'total_requests': 1,
                        'total_cost': {'$ifNull': ['$total_cost', 0]},
                        'total_input_tokens': 1,
                        'total_output_tokens': 1,
                        'total_cache_read': 1,
                        'total_tokens': 1,
                        'average_cost_per_request': {
                            '$cond': [
                                {'$gt': ['$total_requests', 0]},
                                {'$divide': ['$total_cost', '$total_requests']},
                                0
                            ]
                        },
                        'average_tokens_per_request': {
                            '$cond': [
                                {'$gt': ['$total_requests', 0]},
                                {'$divide': ['$total_tokens', '$total_requests']},
                                0
                            ]
                        }
                    }
                }
            ]
            
            result = list(self.collection.aggregate(pipeline))
            
            if result:
                stats = result[0]
                # 转换类型
                stats['total_cost'] = float(stats.get('total_cost', 0))
                stats['total_input_tokens'] = int(stats.get('total_input_tokens', 0))
                stats['total_output_tokens'] = int(stats.get('total_output_tokens', 0))
                stats['total_cache_read'] = int(stats.get('total_cache_read', 0))
                stats['total_tokens'] = int(stats.get('total_tokens', 0))
                stats['average_cost_per_request'] = float(stats.get('average_cost_per_request', 0))
                stats['average_tokens_per_request'] = float(stats.get('average_tokens_per_request', 0))
                return stats
            else:
                return {
                    'total_requests': 0,
                    'total_cost': 0.0,
                    'total_input_tokens': 0,
                    'total_output_tokens': 0,
                    'total_cache_read': 0,
                    'total_tokens': 0,
                    'average_cost_per_request': 0.0,
                    'average_tokens_per_request': 0.0,
                }
            
        except Exception as e:
            logger.error(f"❌ 获取总体统计失败: {e}")
            return {}
    
    def get_daily_statistics(self,
                            account_name: Optional[str] = None,
                            start_date: Optional[str] = None,
                            end_date: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        """
        获取按日期分组的统计信息
        
        Args:
            account_name: 账户名称过滤
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            
        Returns:
            按日期分组的统计信息字典
        """
        if not self._connected:
            return {}
        
        try:
            # 构建匹配条件
            match_conditions = {}
            
            if account_name:
                match_conditions['account_name'] = account_name
            
            # 过滤掉 "Aborted, Not Charged" 的记录
            match_conditions['Kind'] = {'$ne': 'Aborted, Not Charged'}
            
            # 时间范围查询
            if start_date or end_date:
                date_query = {}
                if start_date:
                    date_query['$gte'] = datetime.strptime(start_date, '%Y-%m-%d')
                if end_date:
                    date_query['$lte'] = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
                if date_query:
                    match_conditions['Date'] = date_query
            
            # 聚合查询
            pipeline = [
                {'$match': match_conditions},
                {
                    '$group': {
                        '_id': {
                            '$dateToString': {
                                'format': '%Y-%m-%d',
                                'date': '$Date'
                            }
                        },
                        'total_requests': {'$sum': 1},
                        'total_cost': {'$sum': '$Cost'},
                        'total_input_tokens': {
                            '$sum': {
                                '$add': [
                                    '$Input (w/ Cache Write)',
                                    '$Input (w/o Cache Write)'
                                ]
                            }
                        },
                        'total_output_tokens': {'$sum': '$Output Tokens'},
                        'total_cache_read': {'$sum': '$Cache Read'},
                        'total_tokens': {'$sum': '$Total Tokens'},
                    }
                },
                {'$sort': {'_id': 1}},
                {
                    '$project': {
                        '_id': 0,
                        'date': '$_id',
                        'total_requests': 1,
                        'total_cost': {'$ifNull': ['$total_cost', 0]},
                        'total_input_tokens': 1,
                        'total_output_tokens': 1,
                        'total_cache_read': 1,
                        'total_tokens': 1,
                        'average_cost_per_request': {
                            '$cond': [
                                {'$gt': ['$total_requests', 0]},
                                {'$divide': ['$total_cost', '$total_requests']},
                                0
                            ]
                        }
                    }
                }
            ]
            
            result = list(self.collection.aggregate(pipeline))
            
            daily_stats = {}
            for item in result:
                date_str = item['date']
                daily_stats[date_str] = {
                    'date': date_str,
                    'total_requests': item['total_requests'],
                    'total_cost': float(item.get('total_cost', 0)),
                    'total_input_tokens': int(item.get('total_input_tokens', 0)),
                    'total_output_tokens': int(item.get('total_output_tokens', 0)),
                    'total_cache_read': int(item.get('total_cache_read', 0)),
                    'total_tokens': int(item.get('total_tokens', 0)),
                    'average_cost_per_request': float(item.get('average_cost_per_request', 0)),
                }
            
            return daily_stats
            
        except Exception as e:
            logger.error(f"❌ 获取按日期统计失败: {e}")
            return {}
    
    def get_kind_statistics(self,
                           account_name: Optional[str] = None,
                           start_date: Optional[str] = None,
                           end_date: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        """
        按 Kind（免费/包含）分类统计
        
        Args:
            account_name: 账户名称过滤
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            
        Returns:
            按 Kind 分组的统计信息字典
        """
        if not self._connected:
            return {}
        
        try:
            # 构建匹配条件
            match_conditions = {}
            
            if account_name:
                match_conditions['account_name'] = account_name
            
            # 过滤掉 "Aborted, Not Charged" 的记录
            match_conditions['Kind'] = {'$ne': 'Aborted, Not Charged'}
            
            # 时间范围查询
            if start_date or end_date:
                date_query = {}
                if start_date:
                    date_query['$gte'] = datetime.strptime(start_date, '%Y-%m-%d')
                if end_date:
                    date_query['$lte'] = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
                if date_query:
                    match_conditions['Date'] = date_query
            
            # 聚合查询
            pipeline = [
                {'$match': match_conditions},
                {
                    '$group': {
                        '_id': '$Kind',
                        'total_requests': {'$sum': 1},
                        'total_cost': {'$sum': '$Cost'},
                        'total_input_tokens': {
                            '$sum': {
                                '$add': [
                                    '$Input (w/ Cache Write)',
                                    '$Input (w/o Cache Write)'
                                ]
                            }
                        },
                        'total_output_tokens': {'$sum': '$Output Tokens'},
                        'total_cache_read': {'$sum': '$Cache Read'},
                        'total_tokens': {'$sum': '$Total Tokens'},
                    }
                },
                {
                    '$project': {
                        '_id': 0,
                        'kind': '$_id',
                        'total_requests': 1,
                        'total_cost': {'$ifNull': ['$total_cost', 0]},
                        'total_input_tokens': 1,
                        'total_output_tokens': 1,
                        'total_cache_read': 1,
                        'total_tokens': 1,
                        'average_cost_per_request': {
                            '$cond': [
                                {'$gt': ['$total_requests', 0]},
                                {'$divide': ['$total_cost', '$total_requests']},
                                0
                            ]
                        }
                    }
                }
            ]
            
            result = list(self.collection.aggregate(pipeline))
            
            kind_stats = {}
            for item in result:
                kind = item['kind']
                kind_stats[kind] = {
                    'kind': kind,
                    'total_requests': item['total_requests'],
                    'total_cost': float(item.get('total_cost', 0)),
                    'total_input_tokens': int(item.get('total_input_tokens', 0)),
                    'total_output_tokens': int(item.get('total_output_tokens', 0)),
                    'total_cache_read': int(item.get('total_cache_read', 0)),
                    'total_tokens': int(item.get('total_tokens', 0)),
                    'average_cost_per_request': float(item.get('average_cost_per_request', 0)),
                }
            
            return kind_stats
            
        except Exception as e:
            logger.error(f"❌ 获取按 Kind 统计失败: {e}")
            return {}
    
    def get_model_statistics(self,
                            account_name: Optional[str] = None,
                            start_date: Optional[str] = None,
                            end_date: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        """
        按模型分类统计
        
        Args:
            account_name: 账户名称过滤
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            
        Returns:
            按模型分组的统计信息字典
        """
        if not self._connected:
            return {}
        
        try:
            # 构建匹配条件
            match_conditions = {}
            
            if account_name:
                match_conditions['account_name'] = account_name
            
            # 过滤掉 "Aborted, Not Charged" 的记录
            match_conditions['Kind'] = {'$ne': 'Aborted, Not Charged'}
            
            # 时间范围查询
            if start_date or end_date:
                date_query = {}
                if start_date:
                    date_query['$gte'] = datetime.strptime(start_date, '%Y-%m-%d')
                if end_date:
                    date_query['$lte'] = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
                if date_query:
                    match_conditions['Date'] = date_query
            
            # 聚合查询
            pipeline = [
                {'$match': match_conditions},
                {
                    '$group': {
                        '_id': '$Model',
                        'total_requests': {'$sum': 1},
                        'total_cost': {'$sum': '$Cost'},
                        'total_input_tokens': {
                            '$sum': {
                                '$add': [
                                    '$Input (w/ Cache Write)',
                                    '$Input (w/o Cache Write)'
                                ]
                            }
                        },
                        'total_output_tokens': {'$sum': '$Output Tokens'},
                        'total_cache_read': {'$sum': '$Cache Read'},
                        'total_tokens': {'$sum': '$Total Tokens'},
                    }
                },
                {
                    '$project': {
                        '_id': 0,
                        'model': '$_id',
                        'total_requests': 1,
                        'total_cost': {'$ifNull': ['$total_cost', 0]},
                        'total_input_tokens': 1,
                        'total_output_tokens': 1,
                        'total_cache_read': 1,
                        'total_tokens': 1,
                        'average_cost_per_request': {
                            '$cond': [
                                {'$gt': ['$total_requests', 0]},
                                {'$divide': ['$total_cost', '$total_requests']},
                                0
                            ]
                        }
                    }
                }
            ]
            
            result = list(self.collection.aggregate(pipeline))
            
            model_stats = {}
            for item in result:
                model = item['model']
                model_stats[model] = {
                    'model': model,
                    'total_requests': item['total_requests'],
                    'total_cost': float(item.get('total_cost', 0)),
                    'total_input_tokens': int(item.get('total_input_tokens', 0)),
                    'total_output_tokens': int(item.get('total_output_tokens', 0)),
                    'total_cache_read': int(item.get('total_cache_read', 0)),
                    'total_tokens': int(item.get('total_tokens', 0)),
                    'average_cost_per_request': float(item.get('average_cost_per_request', 0)),
                }
            
            return model_stats
            
        except Exception as e:
            logger.error(f"❌ 获取按模型统计失败: {e}")
            return {}
    
    def get_hourly_statistics(self,
                             account_name: Optional[str] = None,
                             start_date: Optional[str] = None,
                             end_date: Optional[str] = None) -> Dict[int, Dict[str, Any]]:
        """
        按小时统计
        
        Args:
            account_name: 账户名称过滤
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            
        Returns:
            按小时分组的统计信息字典（键为小时 0-23）
        """
        if not self._connected:
            return {}
        
        try:
            # 构建匹配条件
            match_conditions = {}
            
            if account_name:
                match_conditions['account_name'] = account_name
            
            # 过滤掉 "Aborted, Not Charged" 的记录
            match_conditions['Kind'] = {'$ne': 'Aborted, Not Charged'}
            
            # 时间范围查询
            if start_date or end_date:
                date_query = {}
                if start_date:
                    date_query['$gte'] = datetime.strptime(start_date, '%Y-%m-%d')
                if end_date:
                    date_query['$lte'] = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
                if date_query:
                    match_conditions['Date'] = date_query
            
            # 聚合查询
            pipeline = [
                {'$match': match_conditions},
                {
                    '$group': {
                        '_id': {'$hour': '$Date'},
                        'total_requests': {'$sum': 1},
                        'total_cost': {'$sum': '$Cost'},
                        'total_tokens': {'$sum': '$Total Tokens'},
                    }
                },
                {'$sort': {'_id': 1}},
                {
                    '$project': {
                        '_id': 0,
                        'hour': '$_id',
                        'total_requests': 1,
                        'total_cost': {'$ifNull': ['$total_cost', 0]},
                        'total_tokens': 1
                    }
                }
            ]
            
            result = list(self.collection.aggregate(pipeline))
            
            hourly_stats = {}
            for item in result:
                hour = int(item['hour'])
                hourly_stats[hour] = {
                    'hour': hour,
                    'total_requests': item['total_requests'],
                    'total_cost': float(item.get('total_cost', 0)),
                    'total_tokens': int(item.get('total_tokens', 0)),
                }
            
            return hourly_stats
            
        except Exception as e:
            logger.error(f"❌ 获取按小时统计失败: {e}")
            return {}
    
    def get_cost_statistics(self,
                           account_name: Optional[str] = None,
                           start_date: Optional[str] = None,
                           end_date: Optional[str] = None) -> Dict[str, Any]:
        """
        获取费用统计（区分free和Included，auto仅作参考，其他模型单独累计）
        
        Args:
            account_name: 账户名称过滤
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            
        Returns:
            费用统计信息字典
        """
        if not self._connected:
            return {}
        
        try:
            # 构建匹配条件
            match_conditions = {}
            
            if account_name:
                match_conditions['account_name'] = account_name
            
            # 过滤掉 "Aborted, Not Charged" 的记录
            match_conditions['Kind'] = {'$ne': 'Aborted, Not Charged'}
            
            # 时间范围查询
            if start_date or end_date:
                date_query = {}
                if start_date:
                    date_query['$gte'] = datetime.strptime(start_date, '%Y-%m-%d')
                if end_date:
                    date_query['$lte'] = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
                if date_query:
                    match_conditions['Date'] = date_query
            
            # 聚合查询：按 Kind 和 Model 分组
            pipeline = [
                {'$match': match_conditions},
                {
                    '$group': {
                        '_id': {
                            'kind': '$Kind',
                            'model': '$Model'
                        },
                        'total_requests': {'$sum': 1},
                        'total_cost': {'$sum': '$Cost'},
                        'total_tokens': {'$sum': '$Total Tokens'},
                    }
                }
            ]
            
            result = list(self.collection.aggregate(pipeline))
            
            # 组织数据结构
            stats = {
                'free': {
                    'total_cost': 0.0,
                    'total_requests': 0,
                    'auto_cost': 0.0,
                    'auto_requests': 0,
                    'models': {}
                },
                'Included': {
                    'total_cost': 0.0,
                    'total_requests': 0,
                    'auto_cost': 0.0,
                    'auto_requests': 0,
                    'models': {}
                }
            }
            
            for item in result:
                kind = item['_id']['kind']
                model = item['_id']['model']
                cost = float(item.get('total_cost', 0))
                requests = item.get('total_requests', 0)
                tokens = int(item.get('total_tokens', 0))
                
                if kind not in stats:
                    continue
                
                stats[kind]['total_cost'] += cost
                stats[kind]['total_requests'] += requests
                
                if model == 'auto':
                    stats[kind]['auto_cost'] += cost
                    stats[kind]['auto_requests'] += requests
                else:
                    if model not in stats[kind]['models']:
                        stats[kind]['models'][model] = {
                            'model': model,
                            'total_cost': 0.0,
                            'total_requests': 0,
                            'total_tokens': 0,
                        }
                    stats[kind]['models'][model]['total_cost'] += cost
                    stats[kind]['models'][model]['total_requests'] += requests
                    stats[kind]['models'][model]['total_tokens'] += tokens
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ 获取费用统计失败: {e}")
            return {}

