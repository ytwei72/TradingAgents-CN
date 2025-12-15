#!/usr/bin/env python3
"""
Storage 模块
统一管理 MongoDB 和 Redis 相关的存储功能
"""

from .config import DatabaseConfig
from .manager import DatabaseManager, get_database_manager, is_mongodb_available, is_redis_available
from .manager import get_mongodb_client, get_mongodb_db, get_mongo_collection
from .manager import get_redis_client, cache_set, cache_get, cache_delete, cache_exists
from .mongodb.connection import MongoDBConnection
from .mongodb.report_manager import MongoDBReportManager, mongodb_report_manager
from .mongodb.steps_manager import MongoDBStepsStatusManager, mongodb_steps_status_manager
from .mongodb.model_usage_manager import ModelUsageManager, UsageRecord
from .redis.connection import RedisConnection, get_redis_client as get_redis_client_unified
from .redis.cache_manager import RedisCacheManager, redis_cache_manager

__all__ = [
    # 配置和管理
    'DatabaseConfig',
    'DatabaseManager',
    'get_database_manager',
    'is_mongodb_available',
    'is_redis_available',
    
    # MongoDB 连接管理
    'MongoDBConnection',
    'get_mongodb_client',
    'get_mongodb_db',
    'get_mongo_collection',
    
    # Redis 连接管理
    'RedisConnection',
    'get_redis_client',
    'get_redis_client_unified',
    'RedisCacheManager',
    'redis_cache_manager',
    
    # 缓存操作（统一接口）
    'cache_set',
    'cache_get',
    'cache_delete',
    'cache_exists',
    
    # MongoDB 存储管理器
    'MongoDBReportManager',
    'mongodb_report_manager',
    'MongoDBStepsStatusManager',
    'mongodb_steps_status_manager',
    'ModelUsageManager',
    'UsageRecord',
]

