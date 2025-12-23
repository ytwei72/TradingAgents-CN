#!/usr/bin/env python3
"""
MongoDB系统日志管理器
用于保存和读取系统日志到MongoDB数据库的trading_agents_logs集合
"""

import os
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple

from tradingagents.utils.logging_manager import get_logger
logger = get_logger('storage')

try:
    from pymongo import MongoClient
    from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
    MONGODB_AVAILABLE = True
except ImportError:
    MONGODB_AVAILABLE = False
    logger.warning("pymongo未安装，MongoDB功能不可用")


class SystemLogsManager:
    """MongoDB系统日志管理器"""
    
    def __init__(self):
        self.collection = None
        self.connected = False
        
        if MONGODB_AVAILABLE:
            self._connect()
    
    def _connect(self):
        """连接到MongoDB（使用统一的连接管理）"""
        try:
            # 使用统一的连接管理
            from tradingagents.storage.manager import get_mongo_collection
            
            self.collection = get_mongo_collection("trading_agents_logs")
            if self.collection is None:
                logger.warning("⚠️ [MongoDB系统日志] 统一连接管理不可用，无法连接MongoDB")
                self.connected = False
                return
            
            # 创建索引
            self._create_indexes()
            
            self.connected = True
            logger.info(f"✅ [MongoDB系统日志] 连接成功（使用统一连接管理）: trading_agents_logs")
            
        except Exception as e:
            logger.warning(f"⚠️ [MongoDB系统日志] 连接失败: {e}")
            self.connected = False
    
    def _create_indexes(self):
        """创建索引以提高查询性能"""
        try:
            if not self.connected or not self.collection:
                return
            
            # 创建复合索引用于去重查询
            try:
                self.collection.create_index(
                    [("timestamp", 1), ("logger", 1), ("message", 1)],
                    background=True,
                    name="timestamp_logger_message_idx"
                )
            except Exception:
                pass  # 索引可能已存在
            
            # 创建时间索引用于时间范围查询
            try:
                self.collection.create_index(
                    [("timestamp", -1)],
                    background=True,
                    name="timestamp_idx"
                )
            except Exception:
                pass
            
            # 创建 logger 索引用于按日志器查询
            try:
                self.collection.create_index(
                    [("logger", 1)],
                    background=True,
                    name="logger_idx"
                )
            except Exception:
                pass
            
            # 创建 level 索引用于按级别查询
            try:
                self.collection.create_index(
                    [("level", 1)],
                    background=True,
                    name="level_idx"
                )
            except Exception:
                pass
            
            logger.debug("✅ [MongoDB系统日志] 索引创建成功")
            
        except Exception as e:
            logger.warning(f"⚠️ [MongoDB系统日志] 索引创建失败: {e}")
    
    def clean_ansi_codes(self, text: str) -> str:
        """
        清理 ANSI 颜色代码
        
        Args:
            text: 包含 ANSI 代码的文本
            
        Returns:
            清理后的文本
        """
        if not text:
            return text
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        return ansi_escape.sub('', text)
    
    def insert_log(self, log_entry: Dict[str, Any]) -> bool:
        """
        插入单条日志记录
        
        Args:
            log_entry: 日志条目字典，应包含 timestamp, level, logger, message 等字段
            
        Returns:
            插入成功返回 True，否则返回 False
        """
        if not self.connected:
            logger.warning("⚠️ [MongoDB系统日志] MongoDB未连接，跳过插入")
            return False
        
        try:
            # 清理 ANSI 颜色代码
            if 'level' in log_entry and isinstance(log_entry['level'], str):
                log_entry['level'] = self.clean_ansi_codes(log_entry['level'])
            if 'message' in log_entry and isinstance(log_entry['message'], str):
                log_entry['message'] = self.clean_ansi_codes(log_entry['message'])
            
            # 确保 timestamp 是 datetime 类型
            if 'timestamp' in log_entry:
                if isinstance(log_entry['timestamp'], str):
                    try:
                        log_entry['timestamp'] = datetime.fromisoformat(
                            log_entry['timestamp'].replace('Z', '+00:00')
                        )
                    except Exception:
                        log_entry['timestamp'] = datetime.now()
                elif not isinstance(log_entry['timestamp'], datetime):
                    log_entry['timestamp'] = datetime.now()
            else:
                log_entry['timestamp'] = datetime.now()
            
            # 插入文档
            result = self.collection.insert_one(log_entry)
            
            if result.inserted_id:
                return True
            else:
                logger.warning("⚠️ [MongoDB系统日志] 插入失败，未返回 inserted_id")
                return False
            
        except Exception as e:
            logger.error(f"❌ [MongoDB系统日志] 插入日志失败: {e}")
            return False
    
    def insert_logs_batch(self, log_entries: List[Dict[str, Any]]) -> int:
        """
        批量插入日志记录
        
        Args:
            log_entries: 日志条目列表
            
        Returns:
            成功插入的记录数
        """
        if not self.connected:
            logger.warning("⚠️ [MongoDB系统日志] MongoDB未连接，跳过批量插入")
            return 0
        
        if not log_entries:
            return 0
        
        try:
            # 清理和规范化日志条目
            processed_entries = []
            for entry in log_entries:
                # 清理 ANSI 颜色代码
                if 'level' in entry and isinstance(entry['level'], str):
                    entry['level'] = self.clean_ansi_codes(entry['level'])
                if 'message' in entry and isinstance(entry['message'], str):
                    entry['message'] = self.clean_ansi_codes(entry['message'])
                
                # 确保 timestamp 是 datetime 类型
                if 'timestamp' in entry:
                    if isinstance(entry['timestamp'], str):
                        try:
                            entry['timestamp'] = datetime.fromisoformat(
                                entry['timestamp'].replace('Z', '+00:00')
                            )
                        except Exception:
                            entry['timestamp'] = datetime.now()
                    elif not isinstance(entry['timestamp'], datetime):
                        entry['timestamp'] = datetime.now()
                else:
                    entry['timestamp'] = datetime.now()
                
                processed_entries.append(entry)
            
            # 批量插入
            result = self.collection.insert_many(processed_entries, ordered=False)
            
            return len(result.inserted_ids)
            
        except Exception as e:
            # 处理部分成功的情况
            try:
                from pymongo.errors import BulkWriteError
                if isinstance(e, BulkWriteError):
                    successful_count = len(processed_entries) - len(e.details.get('writeErrors', []))
                    if successful_count > 0:
                        logger.warning(f"⚠️ [MongoDB系统日志] 批量插入部分失败: {successful_count} 条成功")
                    return successful_count
            except ImportError:
                pass
            
            logger.error(f"❌ [MongoDB系统日志] 批量插入失败: {e}")
            return 0
    
    def update_log(self, log_id: str, update_data: Dict[str, Any]) -> bool:
        """
        更新日志记录
        
        Args:
            log_id: 日志记录的 _id（ObjectId 字符串）
            update_data: 要更新的字段字典
            
        Returns:
            更新成功返回 True，否则返回 False
        """
        if not self.connected:
            logger.warning("⚠️ [MongoDB系统日志] MongoDB未连接，跳过更新")
            return False
        
        try:
            from bson import ObjectId
            
            # 清理 ANSI 颜色代码
            if 'level' in update_data and isinstance(update_data['level'], str):
                update_data['level'] = self.clean_ansi_codes(update_data['level'])
            if 'message' in update_data and isinstance(update_data['message'], str):
                update_data['message'] = self.clean_ansi_codes(update_data['message'])
            
            # 转换 _id 为 ObjectId
            try:
                object_id = ObjectId(log_id)
            except Exception:
                logger.error(f"❌ [MongoDB系统日志] 无效的日志ID: {log_id}")
                return False
            
            # 更新文档
            result = self.collection.update_one(
                {"_id": object_id},
                {"$set": update_data}
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"❌ [MongoDB系统日志] 更新日志失败: {e}")
            return False
    
    def query_logs(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        days: Optional[int] = None,
        keyword: Optional[str] = None,
        level: Optional[str] = None,
        logger_name: Optional[str] = None,
        limit: int = 1000,
        skip: int = 0
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        查询日志记录
        
        Args:
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            days: 近N天
            keyword: 关键字搜索（在 message, module, function, logger 字段中搜索）
            level: 日志级别过滤 (INFO, WARNING, ERROR等)
            logger_name: Logger名称过滤
            limit: 返回结果数量限制
            skip: 跳过的记录数（用于分页）
            
        Returns:
            (日志记录列表, 总记录数)
        """
        if not self.connected:
            logger.warning("⚠️ [MongoDB系统日志] MongoDB未连接，返回空结果")
            return [], 0
        
        try:
            # 构建查询条件
            query = {}
            
            # 日期筛选
            if days:
                # 近N天
                end_dt = datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999)
                start_dt = (end_dt - timedelta(days=days)).replace(hour=0, minute=0, second=0, microsecond=0)
                query['timestamp'] = {'$gte': start_dt, '$lte': end_dt}
            elif start_date or end_date:
                # 日期区间
                date_query = {}
                if start_date:
                    try:
                        start_dt = datetime.strptime(start_date, '%Y-%m-%d').replace(
                            hour=0, minute=0, second=0, microsecond=0
                        )
                        date_query['$gte'] = start_dt
                    except Exception as e:
                        logger.warning(f"⚠️ [MongoDB系统日志] 开始日期格式错误: {start_date}, {e}")
                
                if end_date:
                    try:
                        end_dt = datetime.strptime(end_date, '%Y-%m-%d').replace(
                            hour=23, minute=59, second=59, microsecond=999999
                        )
                        date_query['$lte'] = end_dt
                    except Exception as e:
                        logger.warning(f"⚠️ [MongoDB系统日志] 结束日期格式错误: {end_date}, {e}")
                
                if date_query:
                    query['timestamp'] = date_query
            
            # 日志级别过滤
            if level:
                # 清理 ANSI 代码后比较
                level_upper = self.clean_ansi_codes(level).upper()
                query['level'] = {'$regex': level_upper, '$options': 'i'}
            
            # Logger名称过滤
            if logger_name:
                query['logger'] = {'$regex': logger_name, '$options': 'i'}
            
            # 关键字搜索（在多个字段中搜索）
            if keyword:
                keyword_clean = self.clean_ansi_codes(keyword)
                keyword_regex = {'$regex': keyword_clean, '$options': 'i'}
                query['$or'] = [
                    {'message': keyword_regex},
                    {'module': keyword_regex},
                    {'function': keyword_regex},
                    {'logger': keyword_regex}
                ]
            
            # 统计总记录数
            total_count = self.collection.count_documents(query)
            
            # 查询记录，按时间倒序
            cursor = (
                self.collection.find(query)
                .sort('timestamp', -1)
                .skip(skip)
                .limit(limit)
            )
            
            logs = []
            for doc in cursor:
                # 移除 _id 字段（转换为字符串）或保留
                if '_id' in doc:
                    doc['_id'] = str(doc['_id'])
                
                # 确保 timestamp 是字符串格式（ISO格式）
                if 'timestamp' in doc and isinstance(doc['timestamp'], datetime):
                    doc['timestamp'] = doc['timestamp'].isoformat()
                
                logs.append(doc)
            
            return logs, total_count
            
        except Exception as e:
            logger.error(f"❌ [MongoDB系统日志] 查询日志失败: {e}")
            return [], 0
    
    def get_logs_stats(self) -> Dict[str, Any]:
        """
        获取日志统计信息
        
        Returns:
            统计信息字典
        """
        if not self.connected:
            logger.warning("⚠️ [MongoDB系统日志] MongoDB未连接，返回空统计")
            return {
                "success": False,
                "total_count": 0,
                "by_level": {},
                "by_logger": {},
                "latest_timestamp": None,
                "earliest_timestamp": None
            }
        
        try:
            # 总记录数
            total_count = self.collection.count_documents({})
            
            # 按级别统计
            pipeline_level = [
                {"$group": {"_id": "$level", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}}
            ]
            by_level = {}
            for item in self.collection.aggregate(pipeline_level):
                level = self.clean_ansi_codes(str(item.get('_id', '')))
                by_level[level] = item.get('count', 0)
            
            # 按 logger 统计（前10个）
            pipeline_logger = [
                {"$group": {"_id": "$logger", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}},
                {"$limit": 10}
            ]
            by_logger = {}
            for item in self.collection.aggregate(pipeline_logger):
                by_logger[str(item.get('_id', ''))] = item.get('count', 0)
            
            # 最早和最晚的时间戳
            earliest_doc = self.collection.find_one(sort=[("timestamp", 1)])
            latest_doc = self.collection.find_one(sort=[("timestamp", -1)])
            
            earliest_timestamp = None
            latest_timestamp = None
            
            if earliest_doc and 'timestamp' in earliest_doc:
                ts = earliest_doc['timestamp']
                if isinstance(ts, datetime):
                    earliest_timestamp = ts.isoformat()
                else:
                    earliest_timestamp = str(ts)
            
            if latest_doc and 'timestamp' in latest_doc:
                ts = latest_doc['timestamp']
                if isinstance(ts, datetime):
                    latest_timestamp = ts.isoformat()
                else:
                    latest_timestamp = str(ts)
            
            return {
                "success": True,
                "total_count": total_count,
                "by_level": by_level,
                "by_logger": by_logger,
                "latest_timestamp": latest_timestamp,
                "earliest_timestamp": earliest_timestamp
            }
            
        except Exception as e:
            logger.error(f"❌ [MongoDB系统日志] 获取统计信息失败: {e}")
            return {
                "success": False,
                "total_count": 0,
                "by_level": {},
                "by_logger": {},
                "latest_timestamp": None,
                "earliest_timestamp": None,
                "error": str(e)
            }
    
    def delete_logs(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        days: Optional[int] = None,
        level: Optional[str] = None,
        logger_name: Optional[str] = None
    ) -> int:
        """
        删除日志记录
        
        Args:
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            days: 近N天之前的记录
            level: 日志级别过滤
            logger_name: Logger名称过滤
            
        Returns:
            删除的记录数
        """
        if not self.connected:
            logger.warning("⚠️ [MongoDB系统日志] MongoDB未连接，跳过删除")
            return 0
        
        try:
            # 构建查询条件（与 query_logs 类似）
            query = {}
            
            # 日期筛选
            if days:
                # 删除N天之前的记录
                cutoff_dt = (datetime.now() - timedelta(days=days)).replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
                query['timestamp'] = {'$lt': cutoff_dt}
            elif start_date or end_date:
                date_query = {}
                if start_date:
                    try:
                        start_dt = datetime.strptime(start_date, '%Y-%m-%d').replace(
                            hour=0, minute=0, second=0, microsecond=0
                        )
                        date_query['$gte'] = start_dt
                    except Exception:
                        pass
                
                if end_date:
                    try:
                        end_dt = datetime.strptime(end_date, '%Y-%m-%d').replace(
                            hour=23, minute=59, second=59, microsecond=999999
                        )
                        date_query['$lte'] = end_dt
                    except Exception:
                        pass
                
                if date_query:
                    query['timestamp'] = date_query
            
            # 日志级别过滤
            if level:
                level_upper = self.clean_ansi_codes(level).upper()
                query['level'] = {'$regex': level_upper, '$options': 'i'}
            
            # Logger名称过滤
            if logger_name:
                query['logger'] = {'$regex': logger_name, '$options': 'i'}
            
            # 执行删除
            result = self.collection.delete_many(query)
            
            logger.info(f"✅ [MongoDB系统日志] 删除了 {result.deleted_count} 条日志记录")
            
            return result.deleted_count
            
        except Exception as e:
            logger.error(f"❌ [MongoDB系统日志] 删除日志失败: {e}")
            return 0


# 全局实例
_system_logs_manager = None

def get_system_logs_manager() -> SystemLogsManager:
    """获取系统日志管理器实例（单例模式）"""
    global _system_logs_manager
    if _system_logs_manager is None:
        _system_logs_manager = SystemLogsManager()
    return _system_logs_manager

