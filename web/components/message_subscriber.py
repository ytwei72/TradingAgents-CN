#!/usr/bin/env python3
"""
Web页面消息订阅组件
用于在Web页面中订阅消息并实时更新进度显示
"""

import threading
import time
from typing import Optional, Dict, Any, Callable
from tradingagents.utils.logging_manager import get_logger

logger = get_logger('web.message_subscriber')

# 全局消息订阅管理器
_message_subscriber_manager: Optional['MessageSubscriberManager'] = None


class MessageSubscriberManager:
    """消息订阅管理器 - 单例模式"""
    
    _instance: Optional['MessageSubscriberManager'] = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self._progress_handler = None
        self._registered_trackers: Dict[str, Any] = {}
        self._message_callbacks: Dict[str, Callable] = {}
        self._is_initialized = False
        
        logger.info("消息订阅管理器已创建")
    
    def initialize(self) -> bool:
        """初始化消息订阅管理器
        
        Returns:
            bool: 是否初始化成功
        """
        if self._is_initialized:
            return True
        
        try:
            from tradingagents.messaging.config import get_progress_handler, is_message_mode_enabled
            
            if not is_message_mode_enabled():
                logger.debug("消息模式未启用，跳过消息订阅初始化")
                return False
            
            self._progress_handler = get_progress_handler()
            if self._progress_handler:
                self._is_initialized = True
                logger.info("消息订阅管理器初始化成功")
                return True
            else:
                logger.warning("进度消息处理器未初始化")
                return False
        except Exception as e:
            logger.error(f"初始化消息订阅管理器失败: {e}")
            return False
    
    def register_tracker(self, analysis_id: str, tracker: Any, 
                        progress_callback: Optional[Callable] = None) -> bool:
        """注册进度跟踪器并订阅消息
        
        Args:
            analysis_id: 分析ID
            tracker: 进度跟踪器实例
            progress_callback: 进度更新回调函数（可选）
            
        Returns:
            bool: 是否注册成功
        """
        if not self._is_initialized:
            if not self.initialize():
                logger.debug(f"消息订阅未初始化，跳过注册: {analysis_id}")
                return False
        
        if not self._progress_handler:
            logger.debug(f"进度消息处理器未初始化，跳过注册: {analysis_id}")
            return False
        
        try:
            # 检查是否已经注册过
            if analysis_id in self._registered_trackers:
                logger.debug(f"分析ID {analysis_id} 已注册，更新跟踪器和回调")
                # 更新跟踪器（底层会处理重复订阅问题）
                self._progress_handler.register_tracker(analysis_id, tracker)
                self._registered_trackers[analysis_id] = tracker
            else:
                # 首次注册
                self._progress_handler.register_tracker(analysis_id, tracker)
                self._registered_trackers[analysis_id] = tracker
            
            # 保存回调函数
            if progress_callback:
                self._message_callbacks[analysis_id] = progress_callback
            
            logger.info(f"已注册进度跟踪器并订阅消息: {analysis_id}")
            return True
        except Exception as e:
            logger.error(f"注册进度跟踪器失败: {analysis_id}, 错误: {e}")
            return False
    
    def unregister_tracker(self, analysis_id: str) -> bool:
        """注销进度跟踪器
        
        Args:
            analysis_id: 分析ID
            
        Returns:
            bool: 是否注销成功
        """
        if not self._is_initialized or not self._progress_handler:
            return False
        
        try:
            if analysis_id in self._registered_trackers:
                self._progress_handler.unregister_tracker(analysis_id)
                del self._registered_trackers[analysis_id]
            
            if analysis_id in self._message_callbacks:
                del self._message_callbacks[analysis_id]
            
            logger.info(f"已注销进度跟踪器: {analysis_id}")
            return True
        except Exception as e:
            logger.error(f"注销进度跟踪器失败: {analysis_id}, 错误: {e}")
            return False
    
    def is_registered(self, analysis_id: str) -> bool:
        """检查是否已注册
        
        Args:
            analysis_id: 分析ID
            
        Returns:
            bool: 是否已注册
        """
        return analysis_id in self._registered_trackers
    
    def trigger_callback(self, analysis_id: str, progress_data: Dict[str, Any]):
        """触发进度更新回调
        
        Args:
            analysis_id: 分析ID
            progress_data: 进度数据
        """
        if analysis_id in self._message_callbacks:
            try:
                callback = self._message_callbacks[analysis_id]
                callback(progress_data)
            except Exception as e:
                logger.error(f"执行进度回调失败: {analysis_id}, 错误: {e}")


def get_message_subscriber_manager() -> MessageSubscriberManager:
    """获取全局消息订阅管理器
    
    Returns:
        MessageSubscriberManager: 消息订阅管理器实例
    """
    global _message_subscriber_manager
    if _message_subscriber_manager is None:
        _message_subscriber_manager = MessageSubscriberManager()
    return _message_subscriber_manager


def register_analysis_tracker(analysis_id: str, tracker: Any, 
                             progress_callback: Optional[Callable] = None) -> bool:
    """注册分析任务跟踪器并订阅消息（便捷函数）
    
    Args:
        analysis_id: 分析ID
        tracker: 进度跟踪器实例
        progress_callback: 进度更新回调函数（可选）
        
    Returns:
        bool: 是否注册成功
    """
    manager = get_message_subscriber_manager()
    return manager.register_tracker(analysis_id, tracker, progress_callback)


def unregister_analysis_tracker(analysis_id: str) -> bool:
    """注销分析任务跟踪器（便捷函数）
    
    Args:
        analysis_id: 分析ID
        
    Returns:
        bool: 是否注销成功
    """
    manager = get_message_subscriber_manager()
    return manager.unregister_tracker(analysis_id)


def is_message_subscription_enabled() -> bool:
    """检查消息订阅是否启用
    
    Returns:
        bool: 是否启用
    """
    try:
        from tradingagents.messaging.config import is_message_mode_enabled
        return is_message_mode_enabled()
    except Exception:
        return False

