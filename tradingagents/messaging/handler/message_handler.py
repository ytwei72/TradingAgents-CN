"""
消息处理器 - 统一的消息发布/订阅接口
"""

import time
from typing import Dict, Any, Callable, Optional
from enum import Enum

from tradingagents.utils.logging_manager import get_logger
from ..engine.base import MessageEngine

logger = get_logger('messaging.handler')


class MessageType(Enum):
    """消息类型枚举"""
    TASK_PROGRESS = "task.progress"
    TASK_STATUS = "task.status"
    MODULE_START = "module.start"
    MODULE_COMPLETE = "module.complete"
    MODULE_ERROR = "module.error"
    STEP_UPDATE = "step.update"


class MessageHandler:
    """消息处理器 - 统一的消息发布/订阅接口"""
    
    def __init__(self, engine: MessageEngine):
        """初始化消息处理器
        
        Args:
            engine: 消息引擎实例
        """
        self.engine = engine
        self.handlers: Dict[str, list] = {}
        self._initialized = False
    
    def initialize(self) -> bool:
        """初始化消息处理器"""
        if self._initialized:
            logger.warning("消息处理器已经初始化")
            return True
        
        result = self.engine.connect()
        if result:
            self._initialized = True
            logger.info("消息处理器初始化成功")
        else:
            logger.error("消息处理器初始化失败")
        return result
    
    def shutdown(self):
        """关闭消息处理器"""
        if self._initialized:
            self.engine.disconnect()
            self._initialized = False
            logger.info("消息处理器已关闭")
    
    def publish(self, message_type: MessageType, payload: Dict[str, Any]) -> bool:
        """发布消息
        
        Args:
            message_type: 消息类型
            payload: 消息负载（字典格式）
            
        Returns:
            bool: 发布是否成功
        """
        if not self._initialized:
            logger.warning("消息处理器未初始化，无法发布消息")
            return False
        
        topic = self._get_topic(message_type, payload)
        message = {
            'type': message_type.value,
            'timestamp': time.time(),
            'payload': payload
        }
        
        result = self.engine.publish(topic, message)
        if result:
            logger.debug(f"消息已发布: {message_type.value} -> {topic}")
        return result
    
    def subscribe(self, message_type: MessageType, 
                  handler: Callable[[Dict[str, Any]], None],
                  topic_filter: Optional[str] = None) -> bool:
        """订阅消息
        
        Args:
            message_type: 消息类型
            handler: 消息处理函数，接收 payload 字典
            topic_filter: 主题过滤器（可选，用于精确匹配特定主题）
            
        Returns:
            bool: 订阅是否成功
        """
        if not self._initialized:
            logger.warning("消息处理器未初始化，无法订阅消息")
            return False
        
        if topic_filter:
            topic = topic_filter
        else:
            # 使用通配符订阅所有匹配的消息类型
            topic = self._get_topic(message_type, {'*': '*'})
        
        def callback(topic_received: str, message: Dict[str, Any]):
            """内部回调函数"""
            try:
                # 验证消息类型
                if message.get('type') == message_type.value:
                    handler(message['payload'])
                else:
                    logger.debug(f"消息类型不匹配: 期望 {message_type.value}, 收到 {message.get('type')}")
            except Exception as e:
                logger.error(f"消息处理错误: {e}", exc_info=True)
        
        result = self.engine.subscribe(topic, callback)
        if result:
            # 记录订阅信息
            if topic not in self.handlers:
                self.handlers[topic] = []
            self.handlers[topic].append(handler)
            logger.info(f"已订阅消息: {message_type.value} -> {topic}")
        return result
    
    def unsubscribe(self, message_type: MessageType, topic_filter: Optional[str] = None) -> bool:
        """取消订阅
        
        Args:
            message_type: 消息类型
            topic_filter: 主题过滤器（可选）
            
        Returns:
            bool: 取消订阅是否成功
        """
        if topic_filter:
            topic = topic_filter
        else:
            topic = self._get_topic(message_type, {'*': '*'})
        
        result = self.engine.unsubscribe(topic)
        if result and topic in self.handlers:
            del self.handlers[topic]
            logger.info(f"已取消订阅: {topic}")
        return result
    
    def _get_topic(self, message_type: MessageType, payload: Dict[str, Any]) -> str:
        """生成主题名称
        
        Args:
            message_type: 消息类型
            payload: 消息负载
            
        Returns:
            str: 主题名称
        """
        # 将消息类型转换为主题路径，例如: "task.progress" -> "task/progress"
        base_topic = message_type.value.replace('.', '/')
        
        # 如果负载中包含 analysis_id，添加到主题路径
        if 'analysis_id' in payload:
            return f"{base_topic}/{payload['analysis_id']}"
        
        # 如果使用通配符，返回通配符主题
        if '*' in payload:
            return base_topic
        
        return base_topic
    
    def is_initialized(self) -> bool:
        """检查是否已初始化"""
        return self._initialized and self.engine.is_connected()

