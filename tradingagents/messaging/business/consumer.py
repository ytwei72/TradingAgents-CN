"""
任务消息消费者
"""

from typing import Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from tradingagents.utils.async_progress_tracker import AsyncProgressTracker

from tradingagents.utils.logging_manager import get_logger
from ..handler.message_handler import MessageHandler, MessageType

logger = get_logger('messaging.consumer')


class TaskMessageConsumer:
    """任务消息消费者"""
    
    def __init__(self, message_handler: MessageHandler):
        """初始化消费者
        
        Args:
            message_handler: 消息处理器实例
        """
        self.handler = message_handler
        self.progress_trackers: Dict[str, 'AsyncProgressTracker'] = {}
        self._subscribed_analyses: set = set()  # 跟踪已订阅的分析ID，避免重复订阅
        logger.info("任务消息消费者已初始化")
    
    def register_tracker(self, analysis_id: str, tracker: 'AsyncProgressTracker'):
        """注册进度跟踪器
        
        Args:
            analysis_id: 分析ID
            tracker: 进度跟踪器实例
        """
        # 如果已经注册过，先注销旧的订阅
        if analysis_id in self.progress_trackers:
            logger.warning(f"分析ID {analysis_id} 已注册，将更新跟踪器")
            # 不取消订阅，只更新跟踪器，避免消息丢失
        
        self.progress_trackers[analysis_id] = tracker
        
        # 订阅该分析ID的所有消息（如果尚未订阅）
        if analysis_id not in self._subscribed_analyses:
            self._subscribe_to_analysis(analysis_id)
        
        logger.info(f"已注册进度跟踪器: {analysis_id}")
    
    def unregister_tracker(self, analysis_id: str):
        """注销进度跟踪器
        
        Args:
            analysis_id: 分析ID
        """
        if analysis_id in self.progress_trackers:
            del self.progress_trackers[analysis_id]
            logger.info(f"已注销进度跟踪器: {analysis_id}")
        
        # 取消订阅（如果已订阅）
        if analysis_id in self._subscribed_analyses:
            self._unsubscribe_from_analysis(analysis_id)
    
    def _subscribe_to_analysis(self, analysis_id: str):
        """订阅分析相关的消息
        
        Args:
            analysis_id: 分析ID
        """
        # 检查是否已经订阅过
        if analysis_id in self._subscribed_analyses:
            logger.debug(f"分析ID {analysis_id} 已订阅，跳过重复订阅")
            return
        
        # 订阅进度消息（统一使用 TASK_PROGRESS 消息格式）
        topic_filter = f"task/progress/{analysis_id}"
        self.handler.subscribe(
            MessageType.TASK_PROGRESS,
            lambda payload: self._handle_progress(analysis_id, payload),
            topic_filter=topic_filter
        )
        
        # 标记为已订阅
        self._subscribed_analyses.add(analysis_id)
        logger.debug(f"已订阅分析消息: {analysis_id} (主题: {topic_filter})")
    
    def _unsubscribe_from_analysis(self, analysis_id: str):
        """取消订阅分析相关的消息
        
        Args:
            analysis_id: 分析ID
        """
        if analysis_id not in self._subscribed_analyses:
            logger.debug(f"分析ID {analysis_id} 未订阅，跳过取消订阅")
            return
        
        # 取消订阅进度消息
        topic_filter = f"task/progress/{analysis_id}"
        self.handler.unsubscribe(
            MessageType.TASK_PROGRESS,
            topic_filter=topic_filter
        )
        
        # 从已订阅集合中移除
        self._subscribed_analyses.discard(analysis_id)
        logger.debug(f"已取消订阅分析消息: {analysis_id} (主题: {topic_filter})")
    
    def _handle_progress(self, analysis_id: str, payload: Dict[str, Any]):
        """处理进度消息
        
        Args:
            analysis_id: 分析ID
            payload: 消息负载
        """
        if analysis_id in self.progress_trackers:
            tracker = self.progress_trackers[analysis_id]
            tracker.update_progress_from_message(payload)
        else:
            logger.debug(f"收到未注册跟踪器的进度消息: {analysis_id}")

