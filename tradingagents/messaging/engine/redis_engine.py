"""
Redis Pub/Sub 消息引擎实现
"""

import json
import threading
from typing import Dict, Any, Callable, Optional
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

from tradingagents.utils.logging_manager import get_logger
from .base import MessageEngine

logger = get_logger('messaging.redis')


class RedisPubSubEngine(MessageEngine):
    """Redis Pub/Sub 消息引擎实现"""
    
    def __init__(self, config: Dict[str, Any]):
        """初始化Redis引擎
        
        Args:
            config: 配置字典（已弃用，现在使用统一的连接管理）
        """
        if not REDIS_AVAILABLE:
            raise ImportError("redis 未安装，请运行: pip install redis")
        
        self.config = config
        self.client: Optional[redis.Redis] = None
        self.pubsub: Optional[redis.client.PubSub] = None
        self.callbacks: Dict[str, Callable] = {}
        self.subscribe_thread: Optional[threading.Thread] = None
        self.running = False
        self._connected = False
        self._lock = threading.Lock()
    
    def connect(self) -> bool:
        """连接Redis服务器（使用统一连接管理）"""
        try:
            from tradingagents.storage.redis.connection import get_redis_client, REDIS_AVAILABLE
            
            if not REDIS_AVAILABLE:
                logger.error("Redis不可用，请检查Redis服务是否启动")
                self._connected = False
                return False
            
            self.client = get_redis_client()
            if not self.client:
                logger.error("无法获取Redis客户端，请检查Redis连接配置")
                self._connected = False
                return False
            
            # 测试连接
            self.client.ping()
            self.pubsub = self.client.pubsub()
            self.running = True
            self._connected = True
            logger.info("Redis连接成功（使用统一连接管理）")
            return True
        except Exception as e:
            logger.error(f"Redis连接失败: {e}")
            self._connected = False
            return False
    
    def disconnect(self):
        """断开连接（使用统一连接管理，只关闭PubSub，不关闭共享连接）"""
        self.running = False
        if self.subscribe_thread and self.subscribe_thread.is_alive():
            self.subscribe_thread.join(timeout=2.0)
        
        if self.pubsub:
            try:
                self.pubsub.close()
            except Exception as e:
                logger.error(f"关闭Redis PubSub失败: {e}")
        
        # 注意：使用统一连接管理时，不应该关闭共享的client连接
        # 只关闭pubsub即可，client由统一管理器管理
        
        self._connected = False
        logger.info("Redis连接已断开")
    
    def publish(self, topic: str, message: Dict[str, Any]) -> bool:
        """发布消息"""
        if not self.is_connected():
            logger.warning("Redis未连接，无法发布消息")
            return False
        
        try:
            payload = json.dumps(message, ensure_ascii=False)
            self.client.publish(topic, payload)
            logger.debug(f"Redis消息已发布: {topic}")
            return True
        except Exception as e:
            logger.error(f"Redis发布消息异常: {e}")
            return False
    
    def subscribe(self, topic: str, callback: Callable[[str, Dict[str, Any]], None]) -> bool:
        """订阅主题"""
        if not self.is_connected():
            logger.warning("Redis未连接，无法订阅")
            return False
        
        try:
            with self._lock:
                self.callbacks[topic] = callback
                self.pubsub.subscribe(topic)
            
            if not self.subscribe_thread or not self.subscribe_thread.is_alive():
                self.subscribe_thread = threading.Thread(
                    target=self._message_loop,
                    daemon=True,
                    name="RedisPubSubMessageLoop"
                )
                self.subscribe_thread.start()
            
            logger.info(f"Redis已订阅主题: {topic}")
            return True
        except Exception as e:
            logger.error(f"Redis订阅异常: {e}")
            return False
    
    def unsubscribe(self, topic: str) -> bool:
        """取消订阅"""
        if not self.is_connected():
            return False
        
        try:
            self.pubsub.unsubscribe(topic)
            with self._lock:
                if topic in self.callbacks:
                    del self.callbacks[topic]
            logger.info(f"Redis已取消订阅: {topic}")
            return True
        except Exception as e:
            logger.error(f"Redis取消订阅异常: {e}")
            return False
    
    def is_connected(self) -> bool:
        """检查连接状态"""
        if not self._connected or not self.client:
            return False
        try:
            self.client.ping()
            return True
        except Exception:
            self._connected = False
            return False
    
    def _message_loop(self):
        """消息循环"""
        logger.info("Redis消息循环已启动")
        while self.running:
            try:
                message = self.pubsub.get_message(timeout=1.0, ignore_subscribe_messages=True)
                if message and message['type'] == 'message':
                    topic = message['channel']
                    try:
                        data = json.loads(message['data'])
                    except json.JSONDecodeError:
                        logger.error(f"Redis消息JSON解析失败: {message['data']}")
                        continue
                    
                    with self._lock:
                        callback = self.callbacks.get(topic)
                    
                    if callback:
                        try:
                            callback(topic, data)
                        except Exception as e:
                            logger.error(f"Redis消息回调执行错误: {e}")
                    else:
                        logger.debug(f"收到未订阅主题的消息: {topic}")
            except Exception as e:
                if self.running:
                    logger.error(f"Redis消息循环错误: {e}")
                break
        
        logger.info("Redis消息循环已停止")

