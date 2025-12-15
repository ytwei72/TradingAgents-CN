#!/usr/bin/env python3
"""
Redis 连接管理模块
提供统一的 Redis 连接管理功能
"""

import os
from typing import Optional

from tradingagents.utils.logging_manager import get_logger
logger = get_logger('storage')

try:
    import redis
    from redis.exceptions import ConnectionError as RedisConnectionError, TimeoutError as RedisTimeoutError
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None
    logger.warning("redis 未安装，Redis功能不可用")


class RedisConnection:
    """Redis 连接管理器"""
    
    _instance = None
    _client = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not REDIS_AVAILABLE:
            self._connected = False
            return
        
        if self._client is None:
            self._connect()
    
    def _connect(self):
        """连接到 Redis"""
        try:
            # 加载环境变量
            from dotenv import load_dotenv
            load_dotenv()
            
            # 优先使用连接字符串
            connection_string = os.getenv("REDIS_CONNECTION_STRING")
            
            if connection_string:
                # 使用连接字符串
                self._client = redis.from_url(
                    connection_string,
                    socket_timeout=5,
                    socket_connect_timeout=5,
                    decode_responses=True
                )
            else:
                # 使用分离的配置参数
                redis_host = os.getenv("REDIS_HOST", "localhost")
                redis_port = int(os.getenv("REDIS_PORT", "6379"))
                redis_password = os.getenv("REDIS_PASSWORD")
                redis_db = int(os.getenv("REDIS_DB", "0"))
                
                connect_kwargs = {
                    "host": redis_host,
                    "port": redis_port,
                    "db": redis_db,
                    "socket_timeout": 5,
                    "socket_connect_timeout": 5,
                    "decode_responses": True
                }
                
                if redis_password:
                    connect_kwargs["password"] = redis_password
                
                self._client = redis.Redis(**connect_kwargs)
            
            # 测试连接
            self._client.ping()
            
            self._connected = True
            if connection_string:
                logger.info(f"✅ Redis连接成功（使用连接字符串）")
            else:
                logger.info(f"✅ Redis连接成功: {redis_host}:{redis_port}")
            
        except (RedisConnectionError, RedisTimeoutError) as e:
            logger.warning(f"⚠️ Redis连接失败: {e}")
            self._connected = False
            self._client = None
        except Exception as e:
            logger.warning(f"⚠️ Redis初始化失败: {e}")
            self._connected = False
            self._client = None
    
    def get_client(self) -> Optional[redis.Redis]:
        """获取 Redis 客户端"""
        return self._client if self._connected else None
    
    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self._connected
    
    def close(self):
        """关闭连接"""
        if self._client:
            self._client.close()
            self._connected = False
            self._client = None
            logger.info("Redis连接已关闭")


# 全局连接实例
_connection = None

def get_redis_client() -> Optional[redis.Redis]:
    """获取 Redis 客户端（全局函数）"""
    global _connection
    if _connection is None:
        _connection = RedisConnection()
    return _connection.get_client()

