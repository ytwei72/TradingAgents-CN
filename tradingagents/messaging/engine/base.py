"""
消息引擎抽象基类
"""

from abc import ABC, abstractmethod
from typing import Callable, Optional, Dict, Any


class MessageEngine(ABC):
    """消息引擎抽象基类"""
    
    @abstractmethod
    def connect(self) -> bool:
        """连接消息服务器
        
        Returns:
            bool: 连接是否成功
        """
        pass
    
    @abstractmethod
    def disconnect(self):
        """断开连接"""
        pass
    
    @abstractmethod
    def publish(self, topic: str, message: Dict[str, Any]) -> bool:
        """发布消息
        
        Args:
            topic: 主题名称
            message: 消息内容（字典格式）
            
        Returns:
            bool: 发布是否成功
        """
        pass
    
    @abstractmethod
    def subscribe(self, topic: str, callback: Callable[[str, Dict[str, Any]], None]) -> bool:
        """订阅消息
        
        Args:
            topic: 主题名称
            callback: 回调函数，接收 (topic, message) 参数
            
        Returns:
            bool: 订阅是否成功
        """
        pass
    
    @abstractmethod
    def unsubscribe(self, topic: str) -> bool:
        """取消订阅
        
        Args:
            topic: 主题名称
            
        Returns:
            bool: 取消订阅是否成功
        """
        pass
    
    @abstractmethod
    def is_connected(self) -> bool:
        """检查连接状态
        
        Returns:
            bool: 是否已连接
        """
        pass

