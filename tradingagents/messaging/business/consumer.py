"""
任务消息消费者
"""

from typing import Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from web.utils.async_progress_tracker import AsyncProgressTracker

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
        logger.info("任务消息消费者已初始化")
    
    def register_tracker(self, analysis_id: str, tracker: 'AsyncProgressTracker'):
        """注册进度跟踪器
        
        Args:
            analysis_id: 分析ID
            tracker: 进度跟踪器实例
        """
        self.progress_trackers[analysis_id] = tracker
        
        # 订阅该分析ID的所有消息
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
    
    def _subscribe_to_analysis(self, analysis_id: str):
        """订阅分析相关的消息
        
        Args:
            analysis_id: 分析ID
        """
        # 订阅进度消息
        self.handler.subscribe(
            MessageType.TASK_PROGRESS,
            lambda payload: self._handle_progress(analysis_id, payload),
            topic_filter=f"task/progress/{analysis_id}"
        )
        
        # 订阅模块事件消息
        for msg_type in [MessageType.MODULE_START, MessageType.MODULE_COMPLETE, 
                        MessageType.MODULE_ERROR]:
            self.handler.subscribe(
                msg_type,
                lambda payload, mt=msg_type: self._handle_module_event(
                    analysis_id, mt, payload
                ),
                topic_filter=f"{mt.value.replace('.', '/')}/{analysis_id}"
            )
        
        logger.debug(f"已订阅分析消息: {analysis_id}")
    
    def _handle_progress(self, analysis_id: str, payload: Dict[str, Any]):
        """处理进度消息
        
        Args:
            analysis_id: 分析ID
            payload: 消息负载
        """
        if analysis_id in self.progress_trackers:
            tracker = self.progress_trackers[analysis_id]
            # 更新跟踪器（不再需要关键字匹配）
            if hasattr(tracker, 'update_progress_from_message'):
                tracker.update_progress_from_message(payload)
            else:
                logger.warning(f"跟踪器 {analysis_id} 不支持 update_progress_from_message")
        else:
            logger.debug(f"收到未注册跟踪器的进度消息: {analysis_id}")
    
    def _handle_module_event(self, analysis_id: str, message_type: MessageType,
                           payload: Dict[str, Any]):
        """处理模块事件消息
        
        Args:
            analysis_id: 分析ID
            message_type: 消息类型
            payload: 消息负载
        """
        if analysis_id in self.progress_trackers:
            tracker = self.progress_trackers[analysis_id]
            
            if message_type == MessageType.MODULE_START:
                if hasattr(tracker, 'handle_module_start'):
                    tracker.handle_module_start(payload)
                else:
                    logger.warning(f"跟踪器 {analysis_id} 不支持 handle_module_start")
            elif message_type == MessageType.MODULE_COMPLETE:
                if hasattr(tracker, 'handle_module_complete'):
                    tracker.handle_module_complete(payload)
                else:
                    logger.warning(f"跟踪器 {analysis_id} 不支持 handle_module_complete")
            elif message_type == MessageType.MODULE_ERROR:
                if hasattr(tracker, 'handle_module_error'):
                    tracker.handle_module_error(payload)
                else:
                    logger.warning(f"跟踪器 {analysis_id} 不支持 handle_module_error")
        else:
            logger.debug(f"收到未注册跟踪器的模块事件消息: {analysis_id}")

