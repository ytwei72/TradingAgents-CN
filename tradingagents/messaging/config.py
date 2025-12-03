"""
消息配置管理和工厂类
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional

from tradingagents.utils.logging_manager import get_logger
from .engine.base import MessageEngine
from .engine.mqtt_engine import MQTTEngine
from .engine.redis_engine import RedisPubSubEngine
from .engine.memory_engine import MemoryEngine
from .handler.message_handler import MessageHandler
from .business.handler import ProgressMessageHandler
from .engine.websocket_engine import WebSocketEngine

logger = get_logger('messaging.config')

# 全局消息处理器实例
_global_message_handler: Optional[MessageHandler] = None
_global_progress_handler: Optional[ProgressMessageHandler] = None


class MessageConfig:
    """消息配置管理"""
    
    @staticmethod
    def load_config() -> Dict[str, Any]:
        """加载消息配置
        
        Returns:
            Dict[str, Any]: 配置字典
        """
        config_path = Path("config/message_config.json")
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    logger.debug(f"已加载消息配置: {config_path}")
                    return config
            except Exception as e:
                logger.warning(f"加载消息配置失败: {e}，使用默认配置")
        
        return MessageConfig.get_default_config()
    
    @staticmethod
    def get_default_config() -> Dict[str, Any]:
        """获取默认配置
        
        Returns:
            Dict[str, Any]: 默认配置字典
        """
        return {
            "message_engine": {
                "type": "memory",  # 默认使用内存引擎
                "memory": {"enabled": True},
                "mqtt": {
                    "host": "localhost",
                    "port": 1883,
                    "username": None,
                    "password": None,
                    "client_id": "tradingagents",
                    "clean_session": True,
                    "keepalive": 60
                },
                "redis": {
                    "host": "localhost",
                    "port": 6379,
                    "password": None,
                    "db": 0
                },
                "websocket": {
                    "enabled": True
                }
            },
            "topics": {
                "task_progress": "task/progress",
                "task_status": "task/status",
                "module_start": "module/start",
                "module_complete": "module/complete",
                "module_error": "module/error"
            },
            "enabled": os.getenv('MESSAGE_MODE_ENABLED', 'false').lower() == 'true'
        }
    
    @staticmethod
    def create_engine(config: Dict[str, Any]) -> MessageEngine:
        """根据配置创建消息引擎
        
        Args:
            config: 配置字典
            
        Returns:
            MessageEngine: 消息引擎实例
            
        Raises:
            ValueError: 不支持的消息引擎类型
        """
        engine_type = config['message_engine']['type']
        engine_config = config['message_engine'].get(engine_type, {})
        
        if engine_type == 'mqtt':
            logger.info("创建MQTT消息引擎")
            return MQTTEngine(engine_config)
        elif engine_type == 'redis':
            logger.info("创建Redis Pub/Sub消息引擎")
            return RedisPubSubEngine(engine_config)
        elif engine_type == 'memory':
            logger.info("创建内存消息引擎")
            return MemoryEngine(engine_config)
        elif engine_type == 'websocket':
            logger.info("创建WebSocket消息引擎")
            return WebSocketEngine(engine_config)
        else:
            raise ValueError(f"不支持的消息引擎类型: {engine_type}")
    
    @staticmethod
    def create_message_handler(config: Optional[Dict[str, Any]] = None) -> MessageHandler:
        """创建消息处理器
        
        Args:
            config: 配置字典（可选，如果为None则从文件加载）
            
        Returns:
            MessageHandler: 消息处理器实例
        """
        if config is None:
            config = MessageConfig.load_config()
        
        engine = MessageConfig.create_engine(config)
        handler = MessageHandler(engine)
        
        # 初始化
        if handler.initialize():
            logger.info("消息处理器创建并初始化成功")
        else:
            logger.warning("消息处理器初始化失败，但已创建实例")
        
        return handler
    
    @staticmethod
    def create_progress_handler(config: Optional[Dict[str, Any]] = None) -> ProgressMessageHandler:
        """创建进度消息处理器
        
        Args:
            config: 配置字典（可选，如果为None则从文件加载）
            
        Returns:
            ProgressMessageHandler: 进度消息处理器实例
        """
        handler = MessageConfig.create_message_handler(config)
        progress_handler = ProgressMessageHandler(handler)
        progress_handler.initialize()
        return progress_handler


def get_message_handler() -> Optional[MessageHandler]:
    """获取全局消息处理器实例
    
    Returns:
        Optional[MessageHandler]: 消息处理器实例，如果未初始化则返回None
    """
    global _global_message_handler
    
    if _global_message_handler is None:
        # 检查是否启用消息模式
        config = MessageConfig.load_config()
        if config.get('enabled', False):
            try:
                _global_message_handler = MessageConfig.create_message_handler(config)
                logger.info("全局消息处理器已初始化")
            except Exception as e:
                logger.error(f"初始化全局消息处理器失败: {e}")
        else:
            logger.debug("消息模式未启用，跳过消息处理器初始化")
    
    return _global_message_handler


def get_message_producer():
    """获取全局消息生产者实例
    
    Returns:
        Optional[TaskMessageProducer]: 消息生产者实例，如果未初始化则返回None
    """
    global _global_progress_handler
    
    if _global_progress_handler is None:
        # 检查是否启用消息模式
        config = MessageConfig.load_config()
        if config.get('enabled', False):
            try:
                _global_progress_handler = MessageConfig.create_progress_handler(config)
                logger.info("全局进度消息处理器已初始化")
            except Exception as e:
                logger.error(f"初始化全局进度消息处理器失败: {e}")
        else:
            logger.debug("消息模式未启用，跳过进度消息处理器初始化")
    
    if _global_progress_handler:
        return _global_progress_handler.get_producer()
    return None


def get_progress_handler() -> Optional[ProgressMessageHandler]:
    """获取全局进度消息处理器实例
    
    Returns:
        Optional[ProgressMessageHandler]: 进度消息处理器实例
    """
    global _global_progress_handler
    
    if _global_progress_handler is None:
        # 检查是否启用消息模式
        config = MessageConfig.load_config()
        if config.get('enabled', False):
            try:
                _global_progress_handler = MessageConfig.create_progress_handler(config)
                logger.info("全局进度消息处理器已初始化")
            except Exception as e:
                logger.error(f"初始化全局进度消息处理器失败: {e}")
        else:
            logger.debug("消息模式未启用，跳过进度消息处理器初始化")
    
    return _global_progress_handler


def is_message_mode_enabled() -> bool:
    """检查消息模式是否启用
    
    Returns:
        bool: 是否启用消息模式
    """
    config = MessageConfig.load_config()
    return config.get('enabled', False)

