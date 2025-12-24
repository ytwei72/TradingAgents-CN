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
            self.connected = True
            logger.info(f"✅ [自选股管理] MongoDB连接成功: {self.COLLECTION_NAME}")
            
            # 创建索引
            self._create_indexes()
            
            # 验证索引是否正确创建
            self._verify_unique_index()            
            
        except Exception as e:
            logger.warning(f"⚠️ [自选股管理] MongoDB连接失败: {e}")
            self.connected = False
    
    def _create_indexes(self):
        """创建索引以提高查询性能"""
        try:
            if not self.connected or self.collection is None:
                return
            
            # 创建新的复合唯一索引：用户ID + 股票代码 + 分类唯一
            # 注意：不使用background=True，确保索引立即生效
            try:
                # 创建唯一索引（不使用background，确保立即生效）
                try:
                    self.collection.create_index(
                        [("user_id", ASCENDING), ("stock_code", ASCENDING), ("category", ASCENDING)],
                        unique=True,
                        name="user_stock_category_unique"
                    )
                    logger.info("✅ [自选股管理] 创建唯一索引成功: user_stock_category_unique")
                except Exception as create_e:
                    # 如果是因为重复数据导致创建失败，记录警告
                    error_str = str(create_e).lower()
                    if "duplicate key" in error_str or "e11000" in error_str:
                        logger.warning("⚠️ [自选股管理] 检测到重复数据，索引创建失败")
                        logger.warning("⚠️ [自选股管理] 请先清理重复数据，然后重启应用以创建索引")
                        raise
                    else:
                        raise
            except Exception as e:
                error_msg = str(e).lower()
                if "already exists" in error_msg or "duplicate" in error_msg or "index already exists" in error_msg:
                    logger.debug("✅ [自选股管理] 唯一索引已存在")
                elif "duplicate key" in error_msg or "E11000" in error_msg:
                    # 如果是因为数据重复导致索引创建失败，记录警告
                    logger.warning(f"⚠️ [自选股管理] 创建唯一索引失败，可能存在重复数据: {e}")
                    logger.warning("⚠️ [自选股管理] 请先清理重复数据，然后手动创建索引")
                else:
                    logger.warning(f"⚠️ [自选股管理] 创建唯一索引时出错: {e}")
            
            # 单字段索引
            self.collection.create_index("user_id")
            self.collection.create_index("stock_code")
            self.collection.create_index("tags")
            self.collection.create_index("themes")
            self.collection.create_index("sectors")
            self.collection.create_index([("created_at", DESCENDING)])
            self.collection.create_index([("updated_at", DESCENDING)])
            
            logger.debug("✅ [自选股管理] 索引创建成功")
            
            # 验证唯一索引是否正确创建
            self._verify_unique_index()
            
        except Exception as e:
            logger.warning(f"⚠️ [自选股管理] 索引创建失败: {e}")
    
    def _verify_unique_index(self):
        """验证唯一索引是否正确创建"""
        try:
            if not self.connected or self.collection is None:
                return
            
            indexes = list(self.collection.list_indexes())
            found = False
            for idx in indexes:
                if idx.get('name') == 'user_stock_category_unique':
                    found = True
                    keys = idx.get('key', {})
                    expected_keys = ['user_id', 'stock_code', 'category']
                    actual_keys = list(keys.keys())
                    is_unique = idx.get('unique', False)
                    
                    if actual_keys == expected_keys and is_unique:
                        logger.info(f"✅ [自选股管理] 唯一索引验证通过: {idx.get('name')}")
                    else:
                        logger.error(f"❌ [自选股管理] 唯一索引验证失败: 期望字段={expected_keys}, 实际字段={actual_keys}, unique={is_unique}")
                    break
            
            if not found:
                logger.error("❌ [自选股管理] 未找到唯一索引: user_stock_category_unique")
        except Exception as e:
            logger.warning(f"⚠️ [自选股管理] 验证索引时出错: {e}")
    
    def validate_and_prepare_stock_data(self, stock_data: Dict[str, Any], 
                                        set_timestamps: bool = True) -> Optional[Dict[str, Any]]:
        """
        验证和预处理自选股数据，设置默认值
        
        Args:
            stock_data: 自选股数据字典，必须包含 stock_code 字段
            set_timestamps: 是否设置时间戳（created_at, updated_at），默认为 True
        
        Returns:
            处理后的文档数据字典，如果验证失败返回 None
        """
        # 检查股票代码
        stock_code = stock_data.get('stock_code', '')
        if not stock_code:
            logger.warning("⚠️ [自选股管理] 股票代码不能为空")
            return None
        
        # 准备文档数据
        document = stock_data.copy()
        
        # 设置默认值
        if 'user_id' not in document or not document.get('user_id'):
            document['user_id'] = 'guest'  # 默认用户ID
        
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
        
        # 处理列表字段，确保它们是列表类型
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
        
        # 设置分类默认值
        if 'category' not in document:
            document['category'] = '自选股'
        
        # 设置备注默认值
        if 'notes' not in document or not document.get('notes'):
            document['notes'] = '无'
        
        # 设置时间戳
        if set_timestamps:
            now = datetime.now()
            if 'created_at' not in document:
                document['created_at'] = now
            if 'updated_at' not in document:
                document['updated_at'] = now
        
        return document
    
    def insert(self, stock_data: Dict[str, Any]) -> bool:
        """
        插入自选股记录
        
        Args:
            stock_data: 自选股数据字典，必须包含 stock_code 字段
                       注意：此方法不进行数据验证和默认值处理，请先调用 validate_and_prepare_stock_data
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
            
            # 确保关键字段有值（MongoDB唯一索引对None值处理可能有问题）
            user_id = stock_data.get('user_id') or 'guest'
            category = stock_data.get('category') or '自选股'
            
            # 确保插入数据中的字段值不为None
            insert_data = stock_data.copy()
            insert_data['user_id'] = user_id
            insert_data['category'] = category
            
            # 插入记录（依赖唯一索引约束保证唯一性）
            result = self.collection.insert_one(insert_data)
            
            if result.inserted_id:
                logger.debug(f"✅ [自选股管理] 插入成功: {stock_code} (用户: {user_id}, 分类: {category})")
                return True
            else:
                logger.warning(f"⚠️ [自选股管理] 插入失败: {stock_code}")
                return False
                
        except DuplicateKeyError as e:
            stock_code = stock_data.get('stock_code', '')
            user_id = stock_data.get('user_id', 'guest')
            category = stock_data.get('category', '自选股')
            error_msg = str(e)
            logger.warning(f"⚠️ [自选股管理] 唯一性约束违反: {stock_code} (用户: {user_id}, 分类: {category})")
            logger.warning(f"⚠️ [自选股管理] 错误详情: {error_msg}")
            return False
        except Exception as e:
            # 检查是否是唯一性约束错误（可能以其他形式抛出）
            error_str = str(e).lower()
            if "duplicate" in error_str or "e11000" in error_str:
                stock_code = stock_data.get('stock_code', '')
                user_id = stock_data.get('user_id', 'guest')
                category = stock_data.get('category', '自选股')
                logger.warning(f"⚠️ [自选股管理] 检测到重复记录: {stock_code} (用户: {user_id}, 分类: {category})")
                logger.warning(f"⚠️ [自选股管理] 错误: {e}")
                return False
            else:
                logger.error(f"❌ [自选股管理] 插入失败: {e}")
                logger.debug(f"插入数据: {stock_data}", exc_info=True)
                return False
        except Exception as e:
            logger.error(f"❌ [自选股管理] 插入失败: {e}")
            logger.debug(f"插入数据: {stock_data}", exc_info=True)
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
    
    def get_by_stock_code(self, stock_code: str, user_id: Optional[str] = None, category: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        根据股票代码查询自选股记录
        
        Args:
            stock_code: 股票代码
            user_id: 用户ID（可选，如果提供则同时匹配用户ID）
            category: 分类（可选，如果提供则同时匹配分类）
        
        Returns:
            自选股记录，如果未找到返回 None
        """
        filter_dict = {"stock_code": stock_code}
        if user_id:
            filter_dict["user_id"] = user_id
        if category:
            filter_dict["category"] = category
        
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
                category = stock.get('category', '自选股')
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
                    category_stats[result.get('_id', '自选股')] = result.get('count', 0)
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

