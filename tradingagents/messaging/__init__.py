"""
TradingAgents 消息机制模块

提供基于消息的任务状态更新机制，替代日志关键字识别方式。
"""

from .handler.message_handler import MessageHandler
from .business.producer import TaskMessageProducer
from .business.consumer import TaskMessageConsumer
from .business.handler import ProgressMessageHandler
from .config import MessageConfig, get_message_handler, get_message_producer

__all__ = [
    'MessageHandler',
    'TaskMessageProducer',
    'TaskMessageConsumer',
    'ProgressMessageHandler',
    'MessageConfig',
    'get_message_handler',
    'get_message_producer',
]

