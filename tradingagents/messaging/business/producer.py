"""
任务消息生产者
"""

import time
from typing import Optional, Dict, Any

from tradingagents.utils.logging_manager import get_logger
from ..handler.message_handler import MessageHandler, MessageType
from .messages import (
    TaskStatus,
    NodeStatus,
    TaskProgressMessage,
    TaskStatusMessage
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
            'last_message': progress_data.last_message,
            'module_name': progress_data.module_name,  # 任务节点名称（英文ID）
            'node_status': progress_data.node_status  # 任务节点状态
        }
        self.handler.publish(MessageType.TASK_PROGRESS, payload)
        logger.debug(f"已发布进度消息: {progress_data.analysis_id} - {progress_data.progress_percentage:.1f}% - 节点: {progress_data.module_name} - 状态: {progress_data.node_status}")
    
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

