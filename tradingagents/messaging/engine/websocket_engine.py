"""
WebSocket 消息引擎实现
"""

import json
from typing import Dict, Any, Callable, Optional, List
from tradingagents.utils.logging_manager import get_logger
from .base import MessageEngine

logger = get_logger('messaging.websocket')

class WebSocketEngine(MessageEngine):
    """WebSocket 消息引擎实现
    
    此引擎本身不直接管理WebSocket连接，而是作为一个桥梁，
    将消息委托给外部注册的回调函数（通常是Web服务器的广播方法）进行发送。
    """
    
    def __init__(self, config: Dict[str, Any]):
        """初始化WebSocket引擎
        
        Args:
            config: 配置字典
        """
        self.config = config
        self.broadcast_callback: Optional[Callable[[Dict[str, Any]], None]] = None
        self._connected = False
        self._subscribers: Dict[str, List[Callable]] = {}
        
    def set_broadcast_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """设置广播回调函数
        
        Args:
            callback: 接收消息字典并进行广播的函数
        """
        self.broadcast_callback = callback
        logger.info("WebSocket广播回调已注册")
        
    def connect(self) -> bool:
        """连接（激活）引擎"""
        self._connected = True
        logger.info("WebSocket引擎已激活")
        return True
    
    def disconnect(self):
        """断开（停用）引擎"""
        self._connected = False
        self.broadcast_callback = None
        logger.info("WebSocket引擎已停用")
    
    def publish(self, topic: str, message: Dict[str, Any]) -> bool:
        """发布消息
        
        将消息包装后通过回调广播出去。
        消息格式通常包含 topic 和 payload。
        """
        if not self.is_connected():
            logger.warning("WebSocket引擎未激活，无法发布消息")
            return False
            
        if not self.broadcast_callback:
            logger.warning("WebSocket广播回调未设置，消息将被丢弃")
            return False
            
        try:
            # 构造标准消息格式
            ws_message = {
                "topic": topic,
                "payload": message,
                "timestamp": message.get("timestamp")
            }
            
            # 调用回调进行广播
            self.broadcast_callback(ws_message)
            logger.debug(f"WebSocket消息已通过回调发布: {topic}")
            return True
        except Exception as e:
            logger.error(f"WebSocket发布消息异常: {e}")
            return False
    
    def subscribe(self, topic: str, callback: Callable[[str, Dict[str, Any]], None]) -> bool:
        """订阅主题
        
        注意：WebSocket引擎主要用于向前端推送，后端内部订阅通常不通过此引擎。
        但为了接口一致性，这里提供简单的内存订阅实现。
        """
        if topic not in self._subscribers:
            self._subscribers[topic] = []
        self._subscribers[topic].append(callback)
        logger.debug(f"已添加本地订阅: {topic}")
        return True
    
    def unsubscribe(self, topic: str) -> bool:
        """取消订阅"""
        if topic in self._subscribers:
            del self._subscribers[topic]
        return True
    
    def is_connected(self) -> bool:
        """检查连接状态"""
        return self._connected
