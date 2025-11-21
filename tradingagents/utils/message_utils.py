"""
消息发布工具模块
提供统一的消息发布接口，封装可复用的消息发布逻辑
"""

from typing import Optional, Any
from tradingagents.utils.logging_manager import get_logger

logger = get_logger('web')


def get_message_producer():
    """获取消息生产者实例"""
    try:
        from tradingagents.messaging.config import get_message_producer, is_message_mode_enabled
        return get_message_producer() if is_message_mode_enabled() else None
    except Exception as e:
        logger.debug(f"消息生产者初始化失败（可能未启用消息模式）: {e}")
        return None


def publish_progress_message(
    analysis_id: str,
    current_step: int,
    total_steps: int,
    step_name: str,
    step_description: str,
    last_message: str,
    module_name: str,
    node_status: str,
    async_tracker: Optional[Any] = None,
    analysis_start_time: Optional[float] = None,
    message_producer: Optional[Any] = None
) -> bool:
    """
    发布进度消息的通用函数
    
    Args:
        analysis_id: 分析ID
        current_step: 当前步骤索引（从0开始）
        total_steps: 总步骤数
        step_name: 步骤名称
        step_description: 步骤描述
        last_message: 最后一条消息
        module_name: 模块名称（英文ID）
        node_status: 节点状态（START/COMPLETE等）
        async_tracker: 异步进度跟踪器
        analysis_start_time: 分析开始时间
        message_producer: 消息生产者实例（如果为None则自动获取）
        
    Returns:
        是否成功发布
    """
    # 如果没有提供消息生产者，尝试获取
    if message_producer is None:
        message_producer = get_message_producer()
    
    if not message_producer or not analysis_id:
        return False
    
    try:
        from tradingagents.messaging.business.messages import TaskProgressMessage, NodeStatus
        
        # 计算进度百分比
        progress_percentage = (current_step + 1) / total_steps * 100 if total_steps > 0 else 0
        
        # 计算已用时间
        if async_tracker and hasattr(async_tracker, 'get_effective_elapsed_time'):
            elapsed_time = async_tracker.get_effective_elapsed_time()
        elif analysis_start_time:
            import time
            elapsed_time = time.time() - analysis_start_time
        else:
            elapsed_time = 0
        
        # 创建进度消息
        progress_msg = TaskProgressMessage(
            analysis_id=analysis_id,
            current_step=current_step,
            total_steps=total_steps,
            progress_percentage=progress_percentage,
            current_step_name=step_name,
            current_step_description=step_description,
            elapsed_time=elapsed_time,
            remaining_time=0,
            last_message=last_message,
            module_name=module_name,
            node_status=node_status
        )
        
        message_producer.publish_progress(progress_msg)
        return True
    except Exception as e:
        logger.debug(f"发布进度消息失败: {e}")
        return False


def publish_task_status(
    analysis_id: str,
    status: str,
    message: str,
    message_producer: Optional[Any] = None
) -> bool:
    """
    发布任务状态消息的通用函数
    
    Args:
        analysis_id: 分析ID
        status: 任务状态（RUNNING/COMPLETED/FAILED等，字符串或TaskStatus枚举）
        message: 状态消息
        message_producer: 消息生产者实例（如果为None则自动获取）
        
    Returns:
        是否成功发布
    """
    # 如果没有提供消息生产者，尝试获取
    if message_producer is None:
        message_producer = get_message_producer()
    
    if not message_producer or not analysis_id:
        return False
    
    try:
        from tradingagents.messaging.business.messages import TaskStatus
        
        # 如果status是字符串，转换为TaskStatus枚举
        if isinstance(status, str):
            status_map = {
                'RUNNING': TaskStatus.RUNNING,
                'COMPLETED': TaskStatus.COMPLETED,
                'FAILED': TaskStatus.FAILED,
                'STOPPED': TaskStatus.STOPPED
            }
            task_status = status_map.get(status.upper(), TaskStatus.RUNNING)
        else:
            task_status = status
        
        message_producer.publish_status(analysis_id, task_status, message)
        return True
    except Exception as e:
        logger.debug(f"发布任务状态消息失败: {e}")
        return False


def get_step_info(async_tracker: Optional[Any], step_index: int, default_total_steps: int = 12) -> tuple[int, int]:
    """
    获取步骤信息
    
    Args:
        async_tracker: 异步进度跟踪器
        step_index: 步骤索引（从0开始）
        default_total_steps: 默认总步骤数
        
    Returns:
        (current_step, total_steps)
    """
    if async_tracker and hasattr(async_tracker, 'analysis_steps'):
        total_steps = len(async_tracker.analysis_steps)
    else:
        total_steps = default_total_steps
    
    return step_index, total_steps

