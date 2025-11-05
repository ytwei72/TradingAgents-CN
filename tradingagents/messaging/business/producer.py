"""
任务消息生产者
"""

import time
from typing import Optional, Dict, Any

from tradingagents.utils.logging_manager import get_logger
from ..handler.message_handler import MessageHandler, MessageType
from .messages import (
    TaskStatus,
    ModuleEvent,
    TaskProgressMessage,
    TaskStatusMessage,
    ModuleEventMessage
)

logger = get_logger('messaging.producer')


class TaskMessageProducer:
    """任务消息生产者"""
    
    def __init__(self, message_handler: MessageHandler):
        """初始化生产者
        
        Args:
            message_handler: 消息处理器实例
        """
        self.handler = message_handler
        logger.info("任务消息生产者已初始化")
    
    def publish_progress(self, progress_data: TaskProgressMessage):
        """发布进度消息
        
        Args:
            progress_data: 进度消息数据
        """
        payload = {
            'analysis_id': progress_data.analysis_id,
            'current_step': progress_data.current_step,
            'total_steps': progress_data.total_steps,
            'progress_percentage': progress_data.progress_percentage,
            'current_step_name': progress_data.current_step_name,
            'current_step_description': progress_data.current_step_description,
            'elapsed_time': progress_data.elapsed_time,
            'remaining_time': progress_data.remaining_time,
            'last_message': progress_data.last_message
        }
        self.handler.publish(MessageType.TASK_PROGRESS, payload)
        logger.debug(f"已发布进度消息: {progress_data.analysis_id} - {progress_data.progress_percentage:.1f}%")
    
    def publish_status(self, analysis_id: str, status: TaskStatus, message: str):
        """发布状态消息
        
        Args:
            analysis_id: 分析ID
            status: 任务状态
            message: 状态消息
        """
        payload = {
            'analysis_id': analysis_id,
            'status': status.value,
            'message': message,
            'timestamp': time.time()
        }
        self.handler.publish(MessageType.TASK_STATUS, payload)
        logger.info(f"已发布状态消息: {analysis_id} - {status.value}")
    
    def publish_module_start(self, analysis_id: str, module_name: str, 
                            stock_symbol: Optional[str] = None, **extra):
        """发布模块开始消息
        
        Args:
            analysis_id: 分析ID
            module_name: 模块名称
            stock_symbol: 股票代码（可选）
            **extra: 额外数据
        """
        payload = {
            'analysis_id': analysis_id,
            'module_name': module_name,
            'stock_symbol': stock_symbol,
            'event': ModuleEvent.START.value,
            **extra
        }
        self.handler.publish(MessageType.MODULE_START, payload)
        logger.debug(f"已发布模块开始消息: {analysis_id} - {module_name}")
    
    def publish_module_complete(self, analysis_id: str, module_name: str,
                               duration: float, stock_symbol: Optional[str] = None,
                               **extra):
        """发布模块完成消息
        
        Args:
            analysis_id: 分析ID
            module_name: 模块名称
            duration: 执行时长（秒）
            stock_symbol: 股票代码（可选）
            **extra: 额外数据
        """
        payload = {
            'analysis_id': analysis_id,
            'module_name': module_name,
            'stock_symbol': stock_symbol,
            'event': ModuleEvent.COMPLETE.value,
            'duration': duration,
            **extra
        }
        self.handler.publish(MessageType.MODULE_COMPLETE, payload)
        logger.debug(f"已发布模块完成消息: {analysis_id} - {module_name} (耗时: {duration:.2f}s)")
    
    def publish_module_error(self, analysis_id: str, module_name: str,
                            error_message: str, stock_symbol: Optional[str] = None):
        """发布模块错误消息
        
        Args:
            analysis_id: 分析ID
            module_name: 模块名称
            error_message: 错误消息
            stock_symbol: 股票代码（可选）
        """
        payload = {
            'analysis_id': analysis_id,
            'module_name': module_name,
            'stock_symbol': stock_symbol,
            'event': ModuleEvent.ERROR.value,
            'error_message': error_message
        }
        self.handler.publish(MessageType.MODULE_ERROR, payload)
        logger.warning(f"已发布模块错误消息: {analysis_id} - {module_name} - {error_message}")

