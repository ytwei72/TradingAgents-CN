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
        from datetime import datetime
        
        task_manager = get_task_manager()
        task = task_manager.tasks.get(analysis_id)
        
        if task:
            state_machine = task.state_machine
        else:
            from tradingagents.tasks.task_state_machine import TaskStateMachine
            state_machine = TaskStateMachine(analysis_id)
        
        # 获取任务的总步骤数
        if task and hasattr(task, 'calculate_total_steps'):
            total_steps = task.calculate_total_steps()
        else:
            total_steps = 10  # 默认值
        
        # 计算进度百分比
        if node_status == 'start':
            percentage = ((step_index - 1) / total_steps) * 100 if total_steps > 0 else 0
        else:
            percentage = (step_index / total_steps) * 100 if total_steps > 0 else 0
        
        # 计算 elapsed_time
        task_obj = state_machine.get_task_object()
        if task_obj:
            created_at = task_obj.get('created_at', datetime.now().isoformat())
            created_time = datetime.fromisoformat(created_at)
            elapsed_time = (datetime.now() - created_time).total_seconds()
        else:
            elapsed_time = 0.0
        
        # 估算剩余时间
        remaining_steps = max(0, total_steps - step_index)
        if step_index > 0 and elapsed_time > 0:
            avg_time_per_step = elapsed_time / step_index
            remaining_time = remaining_steps * avg_time_per_step
        else:
            remaining_time = remaining_steps * 5.0  # 默认每步5秒
        
        # 构建更新数据
        updates = {
            'progress': {
                'current_step': step_index,
                'total_steps': total_steps,
                'percentage': percentage,
                'message': description,
                'elapsed_time': elapsed_time,
                'remaining_time': remaining_time,
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
