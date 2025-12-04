"""
准备步骤状态机辅助函数
"""
from typing import Optional
from tradingagents.utils.logging_manager import get_logger

logger = get_logger('analysis.prep_steps')


def update_preparation_step(
    analysis_id: Optional[str],
    step_name: str,
    step_index: int,
    description: str,
    node_status: str  # 'start' or 'complete'
):
    """更新准备步骤的状态机
    
    Args:
        analysis_id: 分析任务ID
        step_name: 步骤名称（如 'environment_validation'）
        step_index: 步骤索引
        description: 步骤描述
        node_status: 节点状态 ('start' 或 'complete')
    """
    if not analysis_id:
        return
    
    try:
        from tradingagents.tasks import get_task_manager
        task_manager = get_task_manager()
        task = task_manager.tasks.get(analysis_id)
        
        if task:
            state_machine = task.state_machine
        else:
            from tradingagents.tasks.task_state_machine import TaskStateMachine
            state_machine = TaskStateMachine(analysis_id)
        
        # 构建更新数据
        updates = {
            'progress': {
                'current_step': step_index,
                'message': description
            }
        }
        
        # 根据状态决定如何更新
        if node_status == 'start':
            # 开始新步骤
            updates['step_name'] = step_name
            updates['step_index'] = step_index
        elif node_status == 'complete':
            # 完成当前步骤
            updates['step_status'] = 'completed'
        
        state_machine.update_state(updates)
        
    except Exception as e:
        logger.debug(f"更新准备步骤状态失败: {e}")
