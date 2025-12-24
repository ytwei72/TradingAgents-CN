#!/usr/bin/env python3
"""
自选股管理器
用于管理用户的自选股列表，支持查询、插入、更新、统计等功能

集合名称: favorite_stocks
数据库: tradingagents (MongoDB)

【使用方式】
from tradingagents.storage.mongodb.favorite_stocks_manager import favorite_stocks_manager
stocks = favorite_stocks_manager.get_by_user_id("user123")
"""

import os
from datetime import datetime
from typing import Dict, Optional, Any, List

from tradingagents.utils.logging_manager import get_logger
logger = get_logger('storage')

try:
    from pymongo import MongoClient, ASCENDING, DESCENDING
    from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError, DuplicateKeyError
    MONGODB_AVAILABLE = True
except ImportError:
    MONGODB_AVAILABLE = False
    logger.warning("pymongo未安装，MongoDB功能不可用")


class FavoriteStocksManager:
    """自选股管理器"""
    
    # 集合名称
    COLLECTION_NAME = "favorite_stocks"
    
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
                logger.warning("⚠️ [自选股管理] 统一连接管理不可用，无法连接MongoDB")
                self.connected = False
                return
            
            # 创建索引
            self._create_indexes()
            
            self.connected = True
            logger.info(f"✅ [自选股管理] MongoDB连接成功: {self.COLLECTION_NAME}")
            
        except Exception as e:
            logger.warning(f"⚠️ [自选股管理] MongoDB连接失败: {e}")
            self.connected = False
    
    def _create_indexes(self):
        """创建索引以提高查询性能"""
        try:
            if not self.connected or not self.collection:
                return
            
            # 复合唯一索引：用户ID + 股票代码唯一
            try:
                self.collection.create_index(
                    [("user_id", ASCENDING), ("stock_code", ASCENDING)],
                    unique=True,
                    name="user_stock_unique"
                )
            except Exception:
                # 如果索引已存在，忽略错误
                pass
            
            # 单字段索引
            self.collection.create_index("user_id")
            self.collection.create_index("stock_code")
            self.collection.create_index("tags")
            self.collection.create_index("themes")
            self.collection.create_index("sectors")
            self.collection.create_index([("created_at", DESCENDING)])
            self.collection.create_index([("updated_at", DESCENDING)])
            
            logger.debug("✅ [自选股管理] 索引创建成功")
            
        except Exception as e:
            logger.warning(f"⚠️ [自选股管理] 索引创建失败: {e}")
    
    def insert(self, stock_data: Dict[str, Any]) -> bool:
        """
        插入自选股记录
        
        Args:
            stock_data: 自选股数据字典，必须包含 stock_code 字段
                      可选字段：user_id, stock_name, market_type, tags, category, notes, themes, sectors 等
        
        Returns:
            插入成功返回 True，否则返回 False
        """
        if not self.connected:
            logger.warning("⚠️ [自选股管理] 未连接，跳过插入")
            return False
        
        try:
            stock_code = stock_data.get('stock_code', '')
            if not stock_code:
                logger.warning("⚠️ [自选股管理] 股票代码不能为空")
                return False
            
            # 准备文档数据
            document = stock_data.copy()
            
            # 设置默认值
            if 'user_id' not in document:
                document['user_id'] = 'default'  # 默认用户ID
            
            # 如果没有stock_name，从股票字典查询填充
            if 'stock_name' not in document or not document.get('stock_name'):
                try:
                    from tradingagents.storage.mongodb.stock_dict_manager import stock_dict_manager
                    if stock_dict_manager.connected:
                        stock_name = stock_dict_manager.get_stock_name(stock_code)
                        if stock_name:
                            document['stock_name'] = stock_name
                            logger.debug(f"✅ [自选股管理] 自动填充股票名称: {stock_code} -> {stock_name}")
                except Exception as e:
                    logger.warning(f"⚠️ [自选股管理] 查询股票名称失败: {e}")
            
            if 'tags' not in document:
                document['tags'] = []
            elif not isinstance(document['tags'], list):
                document['tags'] = [document['tags']]
            
            if 'themes' not in document:
                document['themes'] = []
            elif not isinstance(document['themes'], list):
                document['themes'] = [document['themes']]
            
            if 'sectors' not in document:
                document['sectors'] = []
            elif not isinstance(document['sectors'], list):
                document['sectors'] = [document['sectors']]
            
            if 'category' not in document:
                document['category'] = 'default'
            
            if 'notes' not in document or not document.get('notes'):
                document['notes'] = '无'
            
            # 设置时间戳
            now = datetime.now()
            if 'created_at' not in document:
                document['created_at'] = now
            if 'updated_at' not in document:
                document['updated_at'] = now
            
            # 插入记录
            result = self.collection.insert_one(document)
            
            if result.inserted_id:
                logger.debug(f"✅ [自选股管理] 插入成功: {stock_code} (用户: {document.get('user_id')})")
                return True
            else:
                logger.warning(f"⚠️ [自选股管理] 插入失败: {stock_code}")
                return False
                
        except DuplicateKeyError:
            logger.warning(f"⚠️ [自选股管理] 记录已存在: {stock_data.get('stock_code')} (用户: {stock_data.get('user_id')})")
            return False
        except Exception as e:
            logger.error(f"❌ [自选股管理] 插入失败: {e}")
            return False
    
    def update(self, filter_dict: Dict[str, Any], update_data: Dict[str, Any]) -> bool:
        """
        更新自选股记录
        
        Args:
            filter_dict: 查询条件，例如 {"user_id": "user123", "stock_code": "000001"}
            update_data: 要更新的数据字典
        
        Returns:
            更新成功返回 True，否则返回 False
        """
        if not self.connected:
            logger.warning("⚠️ [自选股管理] 未连接，跳过更新")
            return False
        
        try:
            # 添加更新时间
            update_data['updated_at'] = datetime.now()
            
            # 使用 $set 操作符更新
            result = self.collection.update_one(
                filter_dict,
                {"$set": update_data}
            )
            
            if result.modified_count > 0:
                logger.debug(f"✅ [自选股管理] 更新成功: {filter_dict}")
                return True
            elif result.matched_count > 0:
                logger.debug(f"ℹ️ [自选股管理] 数据未变化: {filter_dict}")
                return True
            else:
                logger.warning(f"⚠️ [自选股管理] 未找到记录: {filter_dict}")
                return False
                
        except Exception as e:
            logger.error(f"❌ [自选股管理] 更新失败: {e}")
            return False
    
    def delete(self, filter_dict: Dict[str, Any]) -> bool:
        """
        删除自选股记录
        
        Args:
            filter_dict: 查询条件，例如 {"user_id": "user123", "stock_code": "000001"}
        
        Returns:
            删除成功返回 True，否则返回 False
        """
        if not self.connected:
            logger.warning("⚠️ [自选股管理] 未连接，跳过删除")
            return False
        
        try:
            result = self.collection.delete_one(filter_dict)
            
            if result.deleted_count > 0:
                logger.debug(f"✅ [自选股管理] 删除成功: {filter_dict}")
                return True
            else:
                logger.warning(f"⚠️ [自选股管理] 未找到记录: {filter_dict}")
                return False
                
        except Exception as e:
            logger.error(f"❌ [自选股管理] 删除失败: {e}")
            return False
    
    def find(self, filter_dict: Optional[Dict[str, Any]] = None, 
             sort: Optional[List[tuple]] = None, 
             limit: Optional[int] = None,
             skip: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        查询自选股记录
        
        Args:
            filter_dict: 查询条件，例如 {"user_id": "user123"} 或 {"tags": "科技"}
            sort: 排序规则，例如 [("created_at", DESCENDING)]
            limit: 返回记录数限制
            skip: 跳过记录数（用于分页）
        
        Returns:
            自选股记录列表
        """
        if not self.connected:
            logger.warning("⚠️ [自选股管理] 未连接，无法查询")
            return []
        
        try:
            query = filter_dict or {}
            
            cursor = self.collection.find(query)
            
            # 排序
            if sort:
                cursor = cursor.sort(sort)
            
            # 跳过
            if skip:
                cursor = cursor.skip(skip)
            
            # 限制
            if limit:
                cursor = cursor.limit(limit)
            
            # 转换为列表并移除_id字段
            results = []
            for doc in cursor:
                doc.pop('_id', None)
                results.append(doc)
            
            logger.debug(f"✅ [自选股管理] 查询成功，返回 {len(results)} 条记录")
            return results
                
        except Exception as e:
            logger.error(f"❌ [自选股管理] 查询失败: {e}")
            return []
    
    def get_by_user_id(self, user_id: str, sort: Optional[List[tuple]] = None) -> List[Dict[str, Any]]:
        """
        根据用户ID查询自选股列表
        
        Args:
            user_id: 用户ID
            sort: 排序规则，默认按创建时间倒序
        
        Returns:
            自选股记录列表
        """
        if sort is None:
            sort = [("created_at", DESCENDING)]
        
        return self.find({"user_id": user_id}, sort=sort)
    
    def get_by_stock_code(self, stock_code: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        根据股票代码查询自选股记录
        
        Args:
            stock_code: 股票代码
            user_id: 用户ID（可选，如果提供则同时匹配用户ID）
        
        Returns:
            自选股记录，如果未找到返回 None
        """
        filter_dict = {"stock_code": stock_code}
        if user_id:
            filter_dict["user_id"] = user_id
        
        results = self.find(filter_dict, limit=1)
        return results[0] if results else None
    
    def count(self, filter_dict: Optional[Dict[str, Any]] = None) -> int:
        """
        统计自选股记录数量
        
        Args:
            filter_dict: 查询条件
        
        Returns:
            记录数量
        """
        if not self.connected:
            logger.warning("⚠️ [自选股管理] 未连接，无法统计")
            return 0
        
        try:
            query = filter_dict or {}
            count = self.collection.count_documents(query)
            logger.debug(f"✅ [自选股管理] 统计成功: {count} 条记录")
            return count
                
        except Exception as e:
            logger.error(f"❌ [自选股管理] 统计失败: {e}")
            return 0
    
    def get_statistics(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        获取自选股统计信息
        
        Args:
            user_id: 用户ID（可选，如果提供则只统计该用户的数据）
        
        Returns:
            统计信息字典
        """
        filter_dict = {"user_id": user_id} if user_id else {}
        
        total_count = self.count(filter_dict)
        
        # 按分类统计
        category_stats = {}
        if user_id:
            stocks = self.get_by_user_id(user_id)
            for stock in stocks:
                category = stock.get('category', 'default')
                category_stats[category] = category_stats.get(category, 0) + 1
        else:
            # 使用聚合查询
            try:
                pipeline = []
                if user_id:
                    pipeline.append({"$match": {"user_id": user_id}})
                pipeline.append({
                    "$group": {
                        "_id": "$category",
                        "count": {"$sum": 1}
                    }
                })
                
                for result in self.collection.aggregate(pipeline):
                    category_stats[result.get('_id', 'default')] = result.get('count', 0)
            except Exception as e:
                logger.warning(f"⚠️ [自选股管理] 分类统计失败: {e}")
        
        # 按标签统计
        tag_stats = {}
        try:
            pipeline = []
            if user_id:
                pipeline.append({"$match": {"user_id": user_id}})
            pipeline.append({"$unwind": "$tags"})
            pipeline.append({
                "$group": {
                    "_id": "$tags",
                    "count": {"$sum": 1}
                }
            })
            
            for result in self.collection.aggregate(pipeline):
                tag = result.get('_id')
                if tag:
                    tag_stats[tag] = result.get('count', 0)
        except Exception as e:
            logger.warning(f"⚠️ [自选股管理] 标签统计失败: {e}")
        
        return {
            "total_count": total_count,
            "category_stats": category_stats,
            "tag_stats": tag_stats
        }
    
    def is_connected(self) -> bool:
        """检查是否已连接到MongoDB"""
        return self.connected


# 创建全局实例
favorite_stocks_manager = FavoriteStocksManager()

