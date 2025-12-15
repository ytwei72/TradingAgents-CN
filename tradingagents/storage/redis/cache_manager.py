#!/usr/bin/env python3
"""
Redis 缓存管理器
提供统一的 Redis 缓存操作接口
"""

import json
import pickle
from typing import Optional, Dict, Any, Union
from datetime import timedelta

from tradingagents.utils.logging_manager import get_logger
from .connection import get_redis_client, REDIS_AVAILABLE

logger = get_logger('storage')


class RedisCacheManager:
    """Redis 缓存管理器"""
    
    def __init__(self):
        """初始化缓存管理器"""
        self._client = None
        self._connect()
    
    def _connect(self):
        """连接到 Redis"""
        if not REDIS_AVAILABLE:
            logger.warning("Redis 不可用，缓存功能将受限")
            return
        
        self._client = get_redis_client()
        if self._client:
            logger.info("✅ Redis缓存管理器已初始化")
        else:
            logger.warning("⚠️ Redis连接失败，缓存功能不可用")
    
    def is_available(self) -> bool:
        """检查 Redis 是否可用"""
        if not self._client:
            return False
        try:
            self._client.ping()
            return True
        except Exception:
            return False
    
    def get_client(self):
        """获取 Redis 客户端"""
        return self._client if self.is_available() else None
    
    def cache_set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        设置缓存
        
        Args:
            key: 缓存键
            value: 缓存值（支持 dict, list, str, int, float, bool）
            ttl: 过期时间（秒），None 表示不过期
        
        Returns:
            bool: 是否设置成功
        """
        if not self.is_available():
            return False
        
        try:
            # 序列化值
            if isinstance(value, (dict, list)):
                serialized_value = json.dumps(value, ensure_ascii=False)
            elif isinstance(value, (str, int, float, bool)):
                serialized_value = str(value)
            else:
                # 使用 pickle 序列化复杂对象
                serialized_value = pickle.dumps(value)
                # 使用特殊前缀标识 pickle 数据
                key = f"pickle:{key}"
            
            # 设置缓存
            if ttl:
                self._client.setex(key, ttl, serialized_value)
            else:
                self._client.set(key, serialized_value)
            
            return True
        except Exception as e:
            logger.error(f"Redis缓存设置失败: {e}")
            return False
    
    def cache_get(self, key: str, default: Any = None) -> Any:
        """
        获取缓存
        
        Args:
            key: 缓存键
            default: 默认值
        
        Returns:
            缓存值或默认值
        """
        if not self.is_available():
            return default
        
        try:
            # 先尝试普通键
            value = self._client.get(key)
            if value is not None:
                # 尝试 JSON 反序列化
                try:
                    return json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    # 如果不是 JSON，返回原始字符串
                    return value
            
            # 尝试 pickle 键
            pickle_key = f"pickle:{key}"
            value = self._client.get(pickle_key)
            if value is not None:
                return pickle.loads(value)
            
            return default
        except Exception as e:
            logger.error(f"Redis缓存获取失败: {e}")
            return default
    
    def cache_delete(self, key: str) -> bool:
        """
        删除缓存
        
        Args:
            key: 缓存键
        
        Returns:
            bool: 是否删除成功
        """
        if not self.is_available():
            return False
        
        try:
            # 删除普通键和 pickle 键
            deleted = self._client.delete(key, f"pickle:{key}")
            return deleted > 0
        except Exception as e:
            logger.error(f"Redis缓存删除失败: {e}")
            return False
    
    def cache_exists(self, key: str) -> bool:
        """
        检查缓存是否存在
        
        Args:
            key: 缓存键
        
        Returns:
            bool: 是否存在
        """
        if not self.is_available():
            return False
        
        try:
            return self._client.exists(key) > 0 or self._client.exists(f"pickle:{key}") > 0
        except Exception as e:
            logger.error(f"Redis缓存检查失败: {e}")
            return False
    
    def cache_ttl(self, key: str) -> int:
        """
        获取缓存的剩余过期时间
        
        Args:
            key: 缓存键
        
        Returns:
            int: 剩余秒数，-1 表示不过期，-2 表示不存在
        """
        if not self.is_available():
            return -2
        
        try:
            ttl = self._client.ttl(key)
            if ttl == -2:
                # 检查 pickle 键
                ttl = self._client.ttl(f"pickle:{key}")
            return ttl
        except Exception as e:
            logger.error(f"Redis缓存TTL获取失败: {e}")
            return -2
    
    def cache_clear_pattern(self, pattern: str) -> int:
        """
        清理匹配模式的缓存
        
        Args:
            pattern: 匹配模式（支持 * 通配符）
        
        Returns:
            int: 清理的键数量
        """
        if not self.is_available():
            return 0
        
        try:
            keys = self._client.keys(pattern)
            if keys:
                return self._client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Redis缓存清理失败: {e}")
            return 0
    
    def cache_clear_all(self) -> bool:
        """
        清空所有缓存
        
        Returns:
            bool: 是否清空成功
        """
        if not self.is_available():
            return False
        
        try:
            self._client.flushdb()
            logger.info("Redis缓存已清空")
            return True
        except Exception as e:
            logger.error(f"Redis缓存清空失败: {e}")
            return False
    
    def cache_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        if not self.is_available():
            return {
                "available": False,
                "keys": 0,
                "memory_usage": "N/A"
            }
        
        try:
            info = self._client.info()
            return {
                "available": True,
                "keys": self._client.dbsize(),
                "memory_usage": info.get("used_memory_human", "N/A"),
                "connected_clients": info.get("connected_clients", 0),
                "total_commands_processed": info.get("total_commands_processed", 0)
            }
        except Exception as e:
            logger.error(f"Redis统计获取失败: {e}")
            return {
                "available": False,
                "keys": 0,
                "memory_usage": "N/A"
            }


# 全局缓存管理器实例
_redis_cache_manager = None

def redis_cache_manager() -> RedisCacheManager:
    """获取全局 Redis 缓存管理器实例"""
    global _redis_cache_manager
    if _redis_cache_manager is None:
        _redis_cache_manager = RedisCacheManager()
    return _redis_cache_manager

