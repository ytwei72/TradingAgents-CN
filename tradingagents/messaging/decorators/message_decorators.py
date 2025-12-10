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

logger = get_logger('messaging.decorators')

# 模块描述映射表
MODULE_DESCRIPTIONS = {
    'market_analyst': "技术面分析：K线形态、均线系统、价格趋势。技术指标分析：MACD、RSI、KDJ、布林带等。支撑阻力位分析、成交量分析。输出保存：market_report字段（每个节点的输出都会被实时保存到步骤文件）",
    'news_analyst': "新闻事件收集：相关新闻抓取和筛选。事件影响分析：重大事件对股价的影响评估。市场动态追踪：行业动态、政策变化。输出保存：news_report字段（每个节点的输出都会被实时保存到步骤文件）",
    'fundamentals_analyst': "财务数据分析：营收、利润、现金流、财务比率。公司基本面研究：业务模式、竞争优势。估值水平评估：PE、PB、PS、ROE等估值指标。输出保存：fundamentals_report字段（每个节点的输出都会被实时保存到步骤文件）",
    'bull_researcher': "从乐观角度分析投资机会，输出看涨观点和投资理由。输出保存：investment_debate_state.bull_history",
    'bear_researcher': "从谨慎角度分析投资风险，输出看跌观点和风险提醒。输出保存：investment_debate_state.bear_history",
    'research_manager': "综合多头和空头观点，做出综合投资判断。输出保存：investment_debate_state.judge_decision、investment_plan",
    'trader': "基于研究结果制定交易计划，输出具体的投资建议和执行策略。输出保存：trader_investment_plan",
    'risky_analyst': "从高风险高收益角度分析，输出激进策略建议。输出保存：risk_debate_state.risky_history",
    'safe_analyst': "从风险控制角度分析，输出保守策略建议。输出保存：risk_debate_state.safe_history",
    'neutral_analyst': "从平衡角度分析风险，输出平衡策略建议。输出保存：risk_debate_state.neutral_history",
    'risk_manager': "综合各方风险评估，做出最终风险决策和风险评级。输出保存：risk_debate_state.judge_decision、final_trade_decision",
    'graph_signal_processing': "处理最终交易决策信号，提取结构化的投资建议（买入/持有/卖出）",
}


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


def _check_has_tool_calls(result: Any) -> bool:
    """检查结果是否包含工具调用
    
    用于检测分析师节点是否返回了工具调用请求，
    如果是，则该步骤还未完成，不应记录为 completed。
    
    Args:
        result: 函数返回结果
        
    Returns:
        如果包含工具调用返回 True
    """
    if isinstance(result, dict):
        messages = result.get('messages', [])
        for msg in messages:
            # 检查 LangChain AIMessage 的 tool_calls 属性
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                return True
    return False


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


def _publish_step_message(producer, analysis_id: str, module_name: str, 
                          node_status: str, duration: float = 0.0,
                          error_message: str = None):
    """发布步骤消息 - 新版本"""
    # 动态导入以避免循环依赖
    from tradingagents.tasks import get_task_manager
    from tradingagents.tasks.task_state_machine import TaskStateMachine
    
    task_manager = get_task_manager()
    task = task_manager.tasks.get(analysis_id)
    
    if task:
        state_machine = task.state_machine
    else:
        # 如果任务不在管理器中（例如非任务管理器启动的任务），创建临时状态机
        state_machine = TaskStateMachine(analysis_id)
    
    # 从状态机获取当前任务对象
    task_obj = state_machine.get_task_object()
    
    # 获取当前步骤信息
    current_state = state_machine.get_current_state() or {}
    current_step_index = current_state.get('step_index', 0)
    
    # 从历史记录中获取最大的 step_index
    # 这确保分析师步骤在准备步骤的基础上继续累计
    # history = state_machine.get_history_states() or []
    # if history:
    #     # 获取历史记录中最大的 step_index
    #     max_history_index = max(
    #         step.get('step_index', 0) for step in history
    #     )
    #     # 使用 current_step_index 和 max_history_index 中较大的值
    #     current_step_index = max(current_step_index, max_history_index)
    
    progress = task_obj.get('progress', {})
    # 从 progress 获取 total_steps，如果为 0 或不存在，尝试从任务计算
    total_steps = progress.get('total_steps', 0)
    if total_steps == 0:
        # 尝试从任务对象计算
        if task and hasattr(task, 'calculate_total_steps'):
            total_steps = task.calculate_total_steps()
        else:
            total_steps = 10  # 默认总步骤数
    
    # 尝试从 planned_steps 中查找 step_index
    planned_step_index = None
    if task_manager and analysis_id:
        planned_steps = task_manager.get_task_planned_steps(analysis_id)
        if planned_steps:
            for step in planned_steps:
                if step.get('step_name') == module_name:
                    planned_step_index = step.get('step_index')
                    break
    
    # 根据节点状态决定步骤索引和状态
    if planned_step_index is not None:
        # 如果在计划步骤中找到了，直接使用计划的索引
        step_index = planned_step_index
    elif node_status == 'start':
        # 开始新步骤且未在计划中找到：递增索引
        step_index = current_step_index + 1
    else:
        # 其他状态：保持当前索引
        step_index = current_step_index

    if node_status == 'start':
        step_status = None  # 新步骤开始时不设置 step_status，由 step_name 触发新步骤
    elif node_status == 'complete':
        step_status = 'completed'  # 明确标记步骤完成
    elif node_status == 'tool_calling':
        step_status = 'tool_calling'  # 追加工具调用事件
    else:  # error
        step_status = 'failed'  # 明确标记步骤失败
    
    # 计算进度百分比
    progress_percentage = (step_index + 1) / total_steps * 100 if total_steps > 0 else 0
    
    # 步骤信息从模块名派生
    step_name = module_name
    
    # 计算elapsed_time
    created_at = task_obj.get('created_at', datetime.now().isoformat())
    created_time = datetime.fromisoformat(created_at)
    elapsed_time = (datetime.now() - created_time).total_seconds()
    
    # 构建消息文本
    if node_status == 'complete':
        last_message = f"模块完成: {module_name}"
        if duration > 0:
            last_message += f" (耗时: {duration:.2f}s)"
    elif node_status == 'tool_calling':
        last_message = f"工具调用中: {module_name}"
        if duration > 0:
            last_message += f" (耗时: {duration:.2f}s)"
    elif node_status == 'error':
        last_message = f"模块错误: {module_name} - {error_message or '未知错误'}"
    else:  # start
        last_message = f"模块开始: {module_name}"
    
    # 估算剩余时间：调用任务的估算函数或使用简单估算
    if task and hasattr(task, 'estimate_remaining_time'):
        remaining_time = task.estimate_remaining_time()
    else:
        # 回退：基于剩余步骤和平均步骤时间估算
        remaining_steps = max(0, total_steps - step_index)
        if step_index > 0 and elapsed_time > 0:
            avg_time_per_step = elapsed_time / step_index
            remaining_time = remaining_steps * avg_time_per_step
        else:
            remaining_time = remaining_steps * 5.0  # 默认每步5秒
    
    # 获取详细描述
    step_description = MODULE_DESCRIPTIONS.get(module_name, last_message)
    
    # 更新状态机（关键：传递 step_name 和 step_status）
    # 注意：elapsed_time 和 remaining_time 放在 progress 中
    updates = {
        'progress': {
            'current_step': step_index,
            'total_steps': total_steps,
            'percentage': progress_percentage,
            'message': step_description,  # 使用详细描述
            'duration': duration,  # 传递 duration
            'elapsed_time': elapsed_time,
            'remaining_time': remaining_time,
        },
    }
    
    # 只在开始新步骤时传递 step_name，触发新步骤创建
    if node_status == 'start':
        updates['step_name'] = step_name
        updates['step_index'] = step_index
    
    # 在完成或错误时传递 step_status，触发步骤完成
    if step_status:
        updates['step_status'] = step_status
    
    state_machine.update_state(updates)
    
    # 创建进度消息（直接发布）
    progress_msg = TaskProgressMessage(
        analysis_id=analysis_id,
        current_step=step_index,
        total_steps=total_steps,
        progress_percentage=progress_percentage,
        current_step_name=step_name,
        current_step_description=step_description,  # 使用详细描述
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
                        
                        # 检查返回结果是否包含工具调用
                        has_tool_calls = _check_has_tool_calls(result)
                        
                        if has_tool_calls:
                            # 工具调用中 - 不记录为完成，只追加事件
                            _publish_step_message(
                                producer=producer,
                                analysis_id=analysis_id,
                                module_name=module_name,
                                node_status=NodeStatus.TOOL_CALLING.value,
                                duration=duration
                            )
                        else:
                            # 真正完成 - 记录历史
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
