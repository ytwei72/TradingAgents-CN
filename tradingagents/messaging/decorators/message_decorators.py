"""
消息装饰器 - 替代日志装饰器
统一使用 TASK_PROGRESS 消息格式，与预备步骤保持一致
"""

import functools
import time
from typing import Callable, Any, Dict, Optional
from datetime import datetime

from tradingagents.utils.logging_manager import get_logger
from ..config import get_message_producer, is_message_mode_enabled
from ..business.messages import NodeStatus, TaskProgressMessage
from tradingagents.tasks import get_task_state_machine

logger = get_logger('messaging.decorators')


def _extract_analysis_id(*args, **kwargs) -> Optional[str]:
    """从参数中提取分析ID"""
    # 尝试从state字典中获取
    if args:
        first_arg = args[0]
        if isinstance(first_arg, dict):
            # 优先使用analysis_id，如果没有则使用session_id
            analysis_id = first_arg.get('analysis_id')
            if analysis_id:
                return str(analysis_id)
            session_id = first_arg.get('session_id')
            if session_id:
                return str(session_id)
    
    # 从kwargs中查找
    for key in ['analysis_id', 'session_id', 'task_id']:
        if key in kwargs:
            value = kwargs[key]
            if value:
                return str(value)
    
    return None


def _extract_stock_symbol(*args, **kwargs) -> Optional[str]:
    """从参数中提取股票代码"""
    symbol = None
    
    if args:
        first_arg = args[0]
        if isinstance(first_arg, dict) and 'company_of_interest' in first_arg:
            symbol = str(first_arg['company_of_interest'])
        elif isinstance(first_arg, str) and len(first_arg) <= 10:
            symbol = first_arg
    
    if not symbol:
        for key in ['symbol', 'ticker', 'stock_code', 'stock_symbol', 'company_of_interest']:
            if key in kwargs:
                symbol = str(kwargs[key])
                break
    
    return symbol or 'unknown'


def _find_step_by_module_name(module_name: str, analysis_steps: list) -> Optional[int]:
    """根据模块名称查找步骤索引（与AsyncProgressTracker保持一致）"""
    # 模块到关键字的映射
    module_keywords_map = {
        'market_analyst': ['市场分析', '市场'],
        'fundamentals_analyst': ['基本面分析', '基本面'],
        'technical_analyst': ['技术分析', '技术'],
        'sentiment_analyst': ['情绪分析', '情绪'],
        'news_analyst': ['新闻分析', '新闻'],
        'social_media_analyst': ['社交媒体', '社交'],
        'risk_analyst': ['风险分析', '风险'],
        'bull_researcher': ['看涨研究员', '多头观点', '多头', '看涨'],
        'bear_researcher': ['看跌研究员', '空头观点', '空头', '看跌'],
        'research_manager': ['研究经理', '观点整合', '整合'],
        'trader': ['交易员', '投资建议', '建议'],
        'risky_analyst': ['激进风险分析师', '激进策略', '激进'],
        'safe_analyst': ['保守风险分析师', '保守策略', '保守'],
        'neutral_analyst': ['中性风险分析师', '平衡策略', '平衡'],
        'risk_manager': ['风险经理', '风险控制', '控制'],
        'graph_signal_processing': ['信号处理', '处理信号'],  # 信号处理在风险经理之后，应该映射到信号处理步骤
    }
    
    keywords = module_keywords_map.get(module_name, [])
    if not keywords:
        return None
    
    # 在步骤中查找匹配的关键字
    for i, step in enumerate(analysis_steps):
        step_name = step.get('name', '')
        for keyword in keywords:
            if keyword in step_name:
                return i
    
    return None


def _get_progress_info(analysis_id: str) -> Optional[Dict[str, Any]]:
    """获取进度信息"""
    try:
        from tradingagents.utils.async_progress_tracker import get_progress_by_id
        return get_progress_by_id(analysis_id)
    except Exception as e:
        logger.debug(f"获取进度信息失败: {e}")
        return None


def _old_publish(producer, analysis_id: str, module_name: str, 
                              node_status: str, duration: float = 0.0,
                              error_message: str = None):
    """发布进度消息（统一格式） - 旧版本"""
    # 获取进度信息
    progress_data = _get_progress_info(analysis_id)
    if not progress_data:
        logger.warning(f"无法获取进度信息，跳过消息发布: {analysis_id}")
        return
    
    analysis_steps = progress_data.get('steps', [])
    current_step = progress_data.get('current_step', 0)
    total_steps = progress_data.get('total_steps', len(analysis_steps))
    elapsed_time = progress_data.get('elapsed_time', 0.0)
    
    # 根据模块名称查找步骤索引
    step_index = _find_step_by_module_name(module_name, analysis_steps)
    if step_index is None:
        # 如果找不到，使用当前步骤
        step_index = current_step
    
    # 如果是完成状态，使用步骤索引；如果是开始状态，也使用步骤索引
    # 如果是错误状态，保持当前步骤
    if node_status == 'complete':
        # 完成当前步骤，推进到下一步
        progress_step = step_index
        # 进度百分比基于下一步
        next_step = min(step_index + 1, total_steps - 1)
        progress_percentage = (next_step + 1) / total_steps * 100 if total_steps > 0 else 0
    elif node_status == 'start':
        progress_step = step_index
        progress_percentage = (step_index + 1) / total_steps * 100 if total_steps > 0 else 0
    else:  # error
        progress_step = step_index
        progress_percentage = (step_index + 1) / total_steps * 100 if total_steps > 0 else 0
    
    # 获取步骤信息
    step_info = analysis_steps[progress_step] if progress_step < len(analysis_steps) else {'name': '未知', 'description': ''}
    step_name = step_info.get('name', '未知')
    step_description = step_info.get('description', '')
    
    # 构建消息文本
    if node_status == 'complete':
        last_message = f"模块完成: {module_name}"
        if duration > 0:
            last_message += f" (耗时: {duration:.2f}s)"
    elif node_status == 'error':
        last_message = f"模块错误: {module_name} - {error_message or '未知错误'}"
    else:  # start
        last_message = f"模块开始: {module_name}"
    
    # 估算剩余时间
    remaining_time = max(0.0, progress_data.get('estimated_total_time', 0.0) - elapsed_time)
    
    # 创建进度消息
    progress_msg = TaskProgressMessage(
        analysis_id=analysis_id,
        current_step=progress_step,
        total_steps=total_steps,
        progress_percentage=progress_percentage,
        current_step_name=step_name,
        current_step_description=step_description,
        elapsed_time=elapsed_time,
        remaining_time=remaining_time,
        last_message=last_message,
        module_name=module_name,  # 任务节点名称（英文ID）
        node_status=node_status  # 任务节点状态
    )
    
    # 发布进度消息
    producer.publish_progress(progress_msg)


def _publish_step_message(producer, analysis_id: str, module_name: str, 
                          node_status: str, duration: float = 0.0,
                          error_message: str = None):
    # 旧版发布逻辑（用于老版web页面切换，取消注释使用）
    # _old_publish(producer, analysis_id, module_name, node_status, duration, error_message)
    # return
    
    """发布步骤消息 - 新版本"""
    # 更新任务状态机
    state_machine = get_task_state_machine()
    
    # 从状态机获取当前任务信息
    current_state = state_machine.get_current_state(analysis_id)
    if current_state is None:
        # 创建初始任务
        task_params = {'task_id': analysis_id}
        initial_state = state_machine.initialize(task_params)
        current_state = initial_state
        logger.warning(f"任务 {analysis_id} 不存在，已创建初始状态")
    
    progress = current_state.get('progress', {})
    current_step = progress.get('current_step', 0)
    total_steps = progress.get('total_steps', 10)  # 默认总步骤数，如果状态机无则假设
    step_index = current_step  # 使用当前步骤作为索引，无需查找
    
    # 计算进度步骤
    if node_status == 'complete':
        progress_step = step_index
        next_step = min(step_index + 1, total_steps)
        progress_percentage = (next_step + 1) / total_steps * 100 if total_steps > 0 else 0
    elif node_status == 'start':
        progress_step = step_index
        progress_percentage = (step_index + 1) / total_steps * 100 if total_steps > 0 else 0
    else:  # error
        progress_step = step_index
        progress_percentage = (step_index + 1) / total_steps * 100 if total_steps > 0 else 0
    
    # 步骤信息从模块名派生
    step_name = module_name
    step_description = ''
    
    # 计算elapsed_time从created_at
    created_time = datetime.fromisoformat(current_state.get('created_at', datetime.now().isoformat()))
    elapsed_time = (datetime.now() - created_time).total_seconds()
    
    # 构建消息文本
    if node_status == 'complete':
        last_message = f"模块完成: {module_name}"
        if duration > 0:
            last_message += f" (耗时: {duration:.2f}s)"
    elif node_status == 'error':
        last_message = f"模块错误: {module_name} - {error_message or '未知错误'}"
    else:  # start
        last_message = f"模块开始: {module_name}"
    
    # 估算剩余时间，简化
    remaining_time = max(0.0, total_steps * 5.0 - elapsed_time)  # 假设每步5秒
    
    # 构建更新（设置当前步骤状态并添加到历史）
    updates = {
        'module_name': module_name,
        'node_status': node_status,
        'progress_step': progress_step,
        'progress_percentage': progress_percentage,
        'step_name': step_name,
        'step_description': step_description,
        'elapsed_time': elapsed_time,
        'remaining_time': remaining_time,
        'last_message': last_message,
        'duration': duration,
        'error_message': error_message,
        'timestamp': time.time(),
    }
    # 更新progress
    progress_update = {
        'current_step': progress_step,
        'total_steps': total_steps,
        'percentage': progress_percentage,
        'message': last_message
    }
    updates['progress'] = progress_update
    state_machine.update_state(analysis_id, updates)
    
    # 创建进度消息（直接发布）
    progress_msg = TaskProgressMessage(
        analysis_id=analysis_id,
        current_step=progress_step,
        total_steps=total_steps,
        progress_percentage=progress_percentage,
        current_step_name=step_name,
        current_step_description=step_description,
        elapsed_time=elapsed_time,
        remaining_time=remaining_time,
        last_message=last_message,
        module_name=module_name,  # 任务节点名称（英文ID）
        node_status=node_status  # 任务节点状态
    )
    
    # 发布进度消息
    producer.publish_progress(progress_msg)
    



def message_analysis_module(module_name: str, session_id: str = None):
    """消息版分析模块装饰器
    
    统一使用 TASK_PROGRESS 消息格式，与预备步骤保持一致。
    自动发送模块开始/完成/错误消息，替代日志关键字识别方式。
    如果不符合消息机制的要求（消息模式未启用、生产者未初始化、无法获取analysis_id），
    则直接调用被装饰的函数，不做任何额外处理。
    
    Args:
        module_name: 模块名称（如：market_analyst、fundamentals_analyst等）
        session_id: 会话ID（可选）
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 提取分析ID和股票代码
            analysis_id = _extract_analysis_id(*args, **kwargs) or session_id
            
            # 如果消息模式启用，使用消息机制
            if is_message_mode_enabled():
                producer = get_message_producer()
                if producer and analysis_id:
                    # 发送模块开始消息（使用 TASK_PROGRESS 格式）
                    _publish_step_message(
                        producer=producer,
                        analysis_id=analysis_id,
                        module_name=module_name,
                        node_status=NodeStatus.START.value
                    )
                    
                    start_time = time.time()
                    try:
                        # 执行分析函数
                        result = func(*args, **kwargs)
                        
                        # 计算执行时间
                        duration = time.time() - start_time
                        
                        # 发送模块完成消息（使用 TASK_PROGRESS 格式）
                        _publish_step_message(
                            producer=producer,
                            analysis_id=analysis_id,
                            module_name=module_name,
                            node_status=NodeStatus.COMPLETE.value,
                            duration=duration
                        )
                        
                        return result
                    except Exception as e:
                        # 计算执行时间
                        duration = time.time() - start_time
                        
                        # 发送模块错误消息（使用 TASK_PROGRESS 格式）
                        _publish_step_message(
                            producer=producer,
                            analysis_id=analysis_id,
                            module_name=module_name,
                            node_status=NodeStatus.ERROR.value,
                            duration=duration,
                            error_message=str(e)
                        )
                        
                        # 重新抛出异常
                        raise
                else:
                    if not producer:
                        logger.debug(f"消息生产者未初始化，直接执行函数: {module_name}")
                    elif not analysis_id:
                        logger.debug(f"无法获取分析ID，直接执行函数: {module_name}")
                    # 直接调用函数，不做任何额外处理
                    return func(*args, **kwargs)
            else:
                # 消息模式未启用，直接调用函数
                logger.debug(f"消息模式未启用，直接执行函数: {module_name}")
                return func(*args, **kwargs)
        
        return wrapper
    return decorator
