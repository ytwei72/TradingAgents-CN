"""
进度消息处理器 - 集成到现有的进度跟踪系统
"""

from tradingagents.utils.logging_manager import get_logger
from ..handler.message_handler import MessageHandler, MessageType
from .producer import TaskMessageProducer
from .consumer import TaskMessageConsumer

logger = get_logger('messaging.progress_handler')


class ProgressMessageHandler:
    """进度消息处理器 - 集成到现有的进度跟踪系统"""
    
    def __init__(self, message_handler: MessageHandler):
        """初始化处理器
        
        Args:
            message_handler: 消息处理器实例
        """
        self.handler = message_handler
        self.consumer = TaskMessageConsumer(message_handler)
        self.producer = TaskMessageProducer(message_handler)
        logger.info("进度消息处理器已初始化")
    
    def initialize(self):
        """初始化处理器"""
        # 订阅全局任务状态消息
        self.handler.subscribe(
            MessageType.TASK_STATUS,
            self._handle_task_status
        )
        logger.info("进度消息处理器已启动")
    
    def register_tracker(self, analysis_id: str, tracker):
        """注册跟踪器
        
        Args:
            analysis_id: 分析ID
            tracker: 进度跟踪器实例
        """
        self.consumer.register_tracker(analysis_id, tracker)
    
    def unregister_tracker(self, analysis_id: str):
        """注销跟踪器
        
        Args:
            analysis_id: 分析ID
        """
        self.consumer.unregister_tracker(analysis_id)
    
    def get_producer(self) -> TaskMessageProducer:
        """获取消息生产者
        
        Returns:
            TaskMessageProducer: 消息生产者实例
        """
        return self.producer
    
    def _handle_task_status(self, payload: dict):
        """处理任务状态消息
        
        Args:
            payload: 消息负载
        """
        # 可以在这里添加全局状态处理逻辑
        logger.debug(f"收到任务状态消息: {payload.get('analysis_id')} - {payload.get('status')}")

