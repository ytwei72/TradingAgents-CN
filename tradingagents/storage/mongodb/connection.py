#!/usr/bin/env python3
"""
MongoDB 连接管理模块
提供统一的 MongoDB 连接管理功能
"""

import os
from typing import Optional, Dict, Any
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

from tradingagents.utils.logging_manager import get_logger
logger = get_logger('storage')

try:
    from pymongo import MongoClient
    from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
    MONGODB_AVAILABLE = True
except ImportError:
    MONGODB_AVAILABLE = False
    MongoClient = None
    logger.warning("pymongo未安装，MongoDB功能不可用")


class MongoDBConnection:
    """MongoDB 连接管理器"""
    
    _instance = None
    _client = None
    _db = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not MONGODB_AVAILABLE:
            self._connected = False
            return
        
        if self._client is None:
            self._connect()
    
    def _connect(self):
        """连接到 MongoDB"""
        try:
            # 加载环境变量
            from dotenv import load_dotenv
            load_dotenv()
            
            # 优先使用连接字符串
            connection_string = os.getenv("MONGODB_CONNECTION_STRING")
            
            if connection_string:
                # 使用连接字符串
                self._client = MongoClient(
                    connection_string,
                    serverSelectionTimeoutMS=5000,
                    connectTimeoutMS=5000
                )
            else:
                # 使用分离的配置参数
                mongodb_host = os.getenv("MONGODB_HOST", "localhost")
                mongodb_port = int(os.getenv("MONGODB_PORT", "27017"))
                mongodb_username = os.getenv("MONGODB_USERNAME", "")
                mongodb_password = os.getenv("MONGODB_PASSWORD", "")
                mongodb_auth_source = os.getenv("MONGODB_AUTH_SOURCE", "admin")
                
                connect_kwargs = {
                    "host": mongodb_host,
                    "port": mongodb_port,
                    "serverSelectionTimeoutMS": 5000,
                    "connectTimeoutMS": 5000
                }
                
                if mongodb_username and mongodb_password:
                    connect_kwargs.update({
                        "username": mongodb_username,
                        "password": mongodb_password,
                        "authSource": mongodb_auth_source
                    })
                
                self._client = MongoClient(**connect_kwargs)
            
            # 测试连接
            self._client.admin.command('ping')
            
            # 选择数据库
            database_name = os.getenv("MONGODB_DATABASE", "tradingagents")
            self._db = self._client[database_name]
            
            self._connected = True
            logger.info(f"✅ MongoDB连接成功: {database_name}")
            
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.warning(f"⚠️ MongoDB连接失败: {e}")
            self._connected = False
            self._client = None
            self._db = None
        except Exception as e:
            logger.warning(f"⚠️ MongoDB初始化失败: {e}")
            self._connected = False
            self._client = None
            self._db = None
    
    def get_client(self) -> Optional[MongoClient]:
        """获取 MongoDB 客户端"""
        return self._client if self._connected else None
    
    def get_database(self, database_name: Optional[str] = None):
        """获取数据库对象"""
        if not self._connected:
            return None
        
        if database_name:
            return self._client[database_name]
        return self._db
    
    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self._connected
    
    def close(self):
        """关闭连接"""
        if self._client:
            self._client.close()
            self._connected = False
            self._client = None
            self._db = None
            logger.info("MongoDB连接已关闭")


# 全局连接实例
_connection = None

def get_mongodb_client() -> Optional[MongoClient]:
    """获取 MongoDB 客户端（全局函数）"""
    global _connection
    if _connection is None:
        _connection = MongoDBConnection()
    return _connection.get_client()

