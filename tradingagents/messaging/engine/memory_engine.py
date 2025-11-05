"""
内存消息引擎实现（用于测试和开发）
"""

from typing import Dict, Any, Callable
from collections import defaultdict
import threading

from tradingagents.utils.logging_manager import get_logger
from .base import MessageEngine

logger = get_logger('messaging.memory')


class MemoryEngine(MessageEngine):
    """内存消息引擎实现（用于测试和开发）"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """初始化内存引擎
        
        Args:
            config: 配置字典（可选，内存引擎不需要配置）
        """
        self.subscribers: Dict[str, list] = defaultdict(list)
        self.lock = threading.Lock()
        self._connected = False
        logger.info("内存消息引擎已初始化")
    
    def connect(self) -> bool:
        """连接（内存模式无需真实连接）"""
        self._connected = True
        logger.info("内存消息引擎已连接")
        return True
    
    def disconnect(self):
        """断开连接"""
        with self.lock:
            self.subscribers.clear()
        self._connected = False
        logger.info("内存消息引擎已断开")
    
    def publish(self, topic: str, message: Dict[str, Any]) -> bool:
        """发布消息"""
        if not self.is_connected():
            logger.warning("内存引擎未连接")
            return False
        
        with self.lock:
            callbacks = self.subscribers.get(topic, [])[:]  # 复制列表避免修改时迭代
        
        success_count = 0
        for callback in callbacks:
            try:
                callback(topic, message)
                success_count += 1
            except Exception as e:
                logger.error(f"内存引擎回调执行错误: {e}")
        
        logger.debug(f"内存引擎消息已发布: {topic} (订阅者: {success_count})")
        return True
    
    def subscribe(self, topic: str, callback: Callable[[str, Dict[str, Any]], None]) -> bool:
        """订阅主题"""
        with self.lock:
            if callback not in self.subscribers[topic]:
                self.subscribers[topic].append(callback)
                logger.info(f"内存引擎已订阅主题: {topic} (订阅者数: {len(self.subscribers[topic])})")
            else:
                logger.debug(f"内存引擎回调已存在: {topic}")
        return True
    
    def unsubscribe(self, topic: str) -> bool:
        """取消订阅"""
        with self.lock:
            if topic in self.subscribers:
                count = len(self.subscribers[topic])
                del self.subscribers[topic]
                logger.info(f"内存引擎已取消订阅: {topic} (移除订阅者数: {count})")
                return True
            else:
                logger.warning(f"内存引擎尝试取消未订阅的主题: {topic}")
                return False
    
    def is_connected(self) -> bool:
        """检查连接状态"""
        return self._connected

