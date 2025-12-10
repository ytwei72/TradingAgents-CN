"""
分析辅助函数模块
提供环境验证、股票代码格式化、成本估算等辅助功能
"""

import os
from typing import Dict, Any, Optional, Callable
from pathlib import Path

# 导入日志模块
from tradingagents.utils.logging_manager import get_logger
from tradingagents.messaging.business.messages import NodeStatus
from tradingagents.tasks import get_task_manager
logger = get_logger('analysis')


def validate_environment(
    analysis_id: Optional[str] = None,
    async_tracker: Optional[Any] = None
) -> tuple[bool, Optional[str]]:
    """
    验证环境变量配置
    
    Args:
        
    Returns:
        (是否通过验证, 错误信息)
    """
    
    dashscope_key = os.getenv("DASHSCOPE_API_KEY")
    finnhub_key = os.getenv("FINNHUB_API_KEY")
    
    logger.info(f"环境变量检查:")
    logger.info(f"  DASHSCOPE_API_KEY: {'已设置' if dashscope_key else '未设置'}")
    logger.info(f"  FINNHUB_API_KEY: {'已设置' if finnhub_key else '未设置'}")
    
    if not dashscope_key:
        error_msg = "DASHSCOPE_API_KEY 环境变量未设置"
        return False, error_msg
    
    # if not finnhub_key:
    #     error_msg = "FINNHUB_API_KEY 环境变量未设置"
    #     return False, error_msg
    
    return True, None


def format_stock_symbol(stock_symbol: str, market_type: str) -> str:
    """
    根据市场类型格式化股票代码
    
    Args:
        stock_symbol: 原始股票代码
        market_type: 市场类型（A股/港股/美股）
        
    Returns:
        格式化后的股票代码
    """
    logger.debug(f"🔍 [代码格式化] 原始代码: '{stock_symbol}', 市场类型: '{market_type}'")
    
    if market_type == "A股":
        # A股代码不需要特殊处理，保持原样
        formatted_symbol = stock_symbol
        logger.debug(f"🔍 [代码格式化] A股代码保持原样: '{formatted_symbol}'")
    elif market_type == "港股":
        # 港股代码转为大写，确保.HK后缀
        formatted_symbol = stock_symbol.upper()
        if not formatted_symbol.endswith('.HK'):
            # 如果是纯数字，添加.HK后缀
            if formatted_symbol.isdigit():
                formatted_symbol = f"{formatted_symbol.zfill(4)}.HK"
        logger.debug(f"🔍 [代码格式化] 港股代码: '{stock_symbol}' -> '{formatted_symbol}'")
    else:
        # 美股代码转为大写
        formatted_symbol = stock_symbol.upper()
        logger.debug(f"🔍 [代码格式化] 美股代码转大写: '{stock_symbol}' -> '{formatted_symbol}'")
    
    logger.debug(f"🔍 [代码格式化] 最终代码: '{formatted_symbol}'")
    return formatted_symbol


def estimate_analysis_cost(
    llm_provider: str,
    llm_model: str,
    analysts: list,
    research_depth: int,
    analysis_id: Optional[str] = None,
    async_tracker: Optional[Any] = None
) -> Optional[float]:
    """
    估算分析成本
    
    Args:
        llm_provider: LLM提供商
        llm_model: 模型名称
        analysts: 分析师列表
        research_depth: 研究深度
        analysis_id: 分析ID（用于消息发布）
        async_tracker: 异步进度跟踪器（用于消息发布）
        
    Returns:
        估算的成本（元），如果无法估算则返回None
    """
    # 获取消息生产者（如果消息模式启用）
    message_producer = None
    if analysis_id:
        try:
            from tradingagents.messaging.config import get_message_producer, is_message_mode_enabled
            message_producer = get_message_producer() if is_message_mode_enabled() else None
        except Exception:
            pass
    try:
        from tradingagents.config.config_manager import token_tracker
    except ImportError:
        return False, None, "⚠️ Token跟踪功能未启用，无法估算成本"
    
    # 估算每个分析师的token使用量（根据研究深度调整）
    base_input_tokens = 2000
    base_output_tokens = 1000
    
    # 研究深度越高，token使用越多
    depth_multiplier = {
        1: 1.0,
        2: 1.2,
        3: 1.5,
        4: 2.0,
        5: 2.5,
    }.get(research_depth, 1.5)
    
    estimated_input = int(base_input_tokens * len(analysts) * depth_multiplier)
    estimated_output = int(base_output_tokens * len(analysts) * depth_multiplier)
    
    estimated_cost = token_tracker.estimate_cost(
        llm_provider, llm_model, estimated_input, estimated_output
    )
    return True, estimated_cost, None


def prepare_stock_data_for_analysis(
    stock_symbol: str,
    market_type: str,
    analysis_date: str,
    analysis_id: Optional[str] = None,
    async_tracker: Optional[Any] = None
) -> tuple[bool, Optional[str], Optional[Any]]:
    """
    预获取和验证股票数据
    
    Args:
        stock_symbol: 股票代码
        market_type: 市场类型
        analysis_date: 分析日期
        
    Returns:
        (是否成功, 错误信息, 准备结果)
    """
    
    try:
        from tradingagents.utils.stock_validator import prepare_stock_data
        
        # 预获取股票数据（默认30天历史数据）
        preparation_result = prepare_stock_data(
            stock_code=stock_symbol,
            market_type=market_type,
            period_days=30,
            analysis_date=analysis_date
        )
        
        if not preparation_result.is_valid:
            error_msg = f"❌ 股票数据验证失败: {preparation_result.error_message}"
            logger.error(error_msg)
            return False, preparation_result.error_message, preparation_result
        
        # 数据预获取成功
        success_msg = f"✅ 数据准备完成: {preparation_result.stock_name} ({preparation_result.market_type})"
        logger.info(success_msg)
        logger.info(f"缓存状态: {preparation_result.cache_status}")
        return True, None, preparation_result
        
    except Exception as e:
        error_msg = f"❌ 数据预获取过程中发生错误: {str(e)}"
        logger.error(error_msg)
        return False, error_msg, None


def check_task_control(
    analysis_id: Optional[str],
    async_tracker: Optional[Any]
) -> bool:
    """
    检查任务控制信号（暂停/停止）
    
    Args:
        analysis_id: 分析任务ID
        async_tracker: 异步进度跟踪器
        
    Returns:
        是否继续执行（True继续，False停止）
    """
    if not analysis_id:
        return True  # 没有analysis_id，继续执行
    
    try:
        from tradingagents.tasks import get_task_manager
        task_manager = get_task_manager()
        
        # 检查停止信号
        if task_manager.should_stop(analysis_id):
            logger.info(f"⏹️ [任务控制] 收到停止信号: {analysis_id}")
            if async_tracker:
                async_tracker.mark_stopped("用户停止了分析任务")
            return False
        
        # 检查暂停信号
        if task_manager.should_pause(analysis_id):
            logger.info(f"⏸️ [任务控制] 收到暂停信号: {analysis_id}")
            if async_tracker:
                async_tracker.mark_paused()
            
            # 等待直到恢复或停止
            task_manager.wait_if_paused(analysis_id)
            
            # 检查是否在暂停期间被停止
            if task_manager.should_stop(analysis_id):
                logger.info(f"⏹️ [任务控制] 暂停期间收到停止信号: {analysis_id}")
                if async_tracker:
                    async_tracker.mark_stopped("用户停止了分析任务")
                return False
            
            # 恢复执行
            logger.info(f"▶️ [任务控制] 任务恢复执行: {analysis_id}")
            if async_tracker:
                async_tracker.mark_resumed()
        
        return True  # 继续执行
        
    except Exception as e:
        logger.error(f"❌ [任务控制] 检查任务控制状态失败: {e}")
        return True  # 出错时继续执行


def track_token_usage(
    llm_provider: str,
    llm_model: str,
    session_id: str,
    analysts: list,
    research_depth: int,
    market_type: str
) -> Optional[float]:
    """
    记录Token使用情况
        llm_provider: LLM提供商
        llm_model: 模型名称
        session_id: 会话ID
        analysts: 分析师列表
        research_depth: 研究深度
        market_type: 市场类型
        update_progress: 进度回调函数
        
    Returns:
        总成本（元），如果无法跟踪则返回None
    """
    try:
        from tradingagents.config.config_manager import token_tracker
    except ImportError:
        return None
    
    # 估算实际使用的token（基于分析师数量和研究深度）
    depth_token_map = {
        1: (1500, 800),
        2: (2000, 1000),
        3: (2500, 1200),
        4: (3000, 1500),
        5: (4000, 2000),
    }
    
    input_per_analyst, output_per_analyst = depth_token_map.get(research_depth, (2500, 1200))
    actual_input_tokens = len(analysts) * input_per_analyst
    actual_output_tokens = len(analysts) * output_per_analyst
    
    usage_record = token_tracker.track_usage(
        provider=llm_provider,
        model_name=llm_model,
        input_tokens=actual_input_tokens,
        output_tokens=actual_output_tokens,
        session_id=session_id,
        analysis_type=f"{market_type}_analysis"
    )
    
    if usage_record:
        return usage_record.cost
    
    return None


def prepare_analysis_steps(
    stock_symbol: str,
    analysis_date: str,
    market_type: str,
    analysts: list,
    research_depth: int,
    llm_provider: str,
    llm_model: str,
    analysis_id: Optional[str],
    async_tracker: Optional[Any]
) -> tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
    """
    准备分析步骤：执行所有前期准备工作
    
    准备步骤包括：
    - 准备步骤1: 🚀 分析启动
    - 准备步骤2: 💰 成本估算
    - 准备步骤3: 🔍 数据预获取和验证
    - 准备步骤4: 🔧 环境验证
    - 准备步骤5: ⚙️ 构建配置
    - 准备步骤6: 📝 格式化股票代码
    - 准备步骤7: 🏗️ 初始化分析引擎
    - 准备步骤8: 📁 步骤输出目录准备

    Args:
        stock_symbol: 股票代码
        analysis_date: 分析日期
        market_type: 市场类型
        analysts: 分析师列表
        research_depth: 研究深度
        llm_provider: LLM提供商
        llm_model: 模型名称
        analysis_id: 分析任务ID
        async_tracker: 异步进度跟踪器
        
    Returns:
        (是否成功, 准备结果字典, 错误信息)
        准备结果字典包含: config, formatted_symbol, graph, session_id
    """
    task_manager = get_task_manager()
    if not task_manager or not analysis_id:
        raise ValueError("Task manager or analysis_id: {analysis_id} is not available")
    from .analysis_config import AnalysisConfigBuilder
    
    preparation_result = None
    formatted_symbol = None
    config = None
    graph = None
    step_name = ""
    
    def _update_step_start(message: str):
        task_manager.update_task_progress(analysis_id, step_name, message, 'start')

    def _update_step_success(message: str):
        task_manager.update_task_progress(analysis_id, step_name, message, 'success')
    
    def _update_step_error(message: str):
        task_manager.update_task_progress(analysis_id, step_name, message, 'error')
    
    # ========== Step 1: 分析启动 ==========
    step_name = "analysis_start"
    _update_step_start("🚀 开始股票分析...")
    logger_manager, analysis_start_time = log_analysis_start(analysis_id)
    _update_step_success("✅ 分析启动完成")

    # ========== Step 2: 成本估算 ==========
    step_name = "cost_estimation"
    _update_step_start("💰 开始成本估算...")
    success, estimated_cost, exec_msg = estimate_analysis_cost(
        llm_provider, llm_model, analysts, research_depth, 
        analysis_id, async_tracker
    )
    if not success:
        _update_step_error(exec_msg)
    _update_step_success(f"✅ 成本估算完成，💰 预估分析成本: ¥{estimated_cost:.4f}")
    
    # ========== Step 3: 数据预获取和验证 ==========
    step_name = "data_preparation"
    _update_step_start("🔍 验证股票代码并预获取数据...")
    success, exec_msg, result = prepare_stock_data_for_analysis(
        stock_symbol, market_type, analysis_date, analysis_id, async_tracker
    )
    
    if not success:
        _update_step_error(exec_msg)
        return False, None, exec_msg
    _update_step_success(f"✅ 数据准备完成: {result.stock_name} ({result.market_type})")
    
    # ========== Step 4: 环境验证 ==========
    step_name = "environment_validation"
    _update_step_start("🔧 开始环境验证...")
    env_valid, env_error = validate_environment(analysis_id, async_tracker)
    if not env_valid:
        _update_step_error(f"⚠️ 环境验证失败：{env_error}")
        return False, None, env_error
    _update_step_success("✅ 环境验证完成")
    
    # ========== Step 5: 构建配置 ==========
    step_name = "config_builder"
    _update_step_start("⚙️ 开始构建配置...")
    try:
        config_builder = AnalysisConfigBuilder()
        config = config_builder.build_config(
            llm_provider=llm_provider,
            llm_model=llm_model,
            research_depth=research_depth,
            market_type=market_type
        )
        _update_step_success("✅ 配置构建完成")
    except Exception as e:
        _update_step_error(f"⚠️ 配置构建失败：{str(e)}")
        raise
    
    logger.info(f"使用配置: {config}")
    logger.info(f"分析师列表: {analysts}")
    logger.info(f"股票代码: {stock_symbol}")
    logger.info(f"分析日期: {analysis_date}")
    
    # ========== Step 6: 格式化股票代码 ==========
    step_name = "symbol_formatting"
    _update_step_start("📝 开始格式化股票代码...")
    formatted_symbol = format_stock_symbol(stock_symbol, market_type)
    
    market_icons = {"A股": "🇨🇳", "港股": "🇭🇰", "美股": "🇺🇸"}
    market_icon = market_icons.get(market_type, "📊")
    _update_step_success(f"✅ {market_icon} 股票代码格式化完成: {formatted_symbol}")
    
    # ========== Step 7: 初始化分析引擎 ==========
    step_name = "graph_initialization"
    _update_step_start("🏗️ 开始初始化分析引擎...")
    
    if not check_task_control(analysis_id, async_tracker):
        error_msg = '⚠️ 任务已被停止'
        _update_step_error(error_msg)
        return False, None, error_msg
    
    try:
        from tradingagents.graph.trading_graph import TradingAgentsGraph
        graph = TradingAgentsGraph(analysts, config=config, debug=False)
        _update_step_success("✅ 分析引擎初始化完成")
    except Exception as e:
        _update_step_error(f"⚠️ 分析引擎初始化失败：{str(e)}")
        raise

    # ========== Step 8: 步骤输出目录准备 ==========
    step_name = "step_output_directory"
    _update_step_start("📁 准备步骤输出目录...")
    step_output_base_dir = prepare_step_output_directory(
        formatted_symbol=formatted_symbol,
        analysis_date=analysis_date,
        analysis_id=analysis_id,
        async_tracker=async_tracker,
        analysis_start_time=analysis_start_time
    )
    _update_step_success(f"✅ 步骤输出目录已准备: {step_output_base_dir}") 

    # 返回准备结果
    preparation_result_dict = {
        'config': config,
        'formatted_symbol': formatted_symbol,
        'graph': graph,
        'session_id': analysis_id,
        'analysis_start_time': analysis_start_time,
        'preparation_result': preparation_result
    }
    
    return True, preparation_result_dict, None


def save_analysis_results(
    results: Dict[str, Any],
    analysis_id: Optional[str] = None,
    stock_symbol: Optional[str] = None
) -> tuple[bool, Dict[str, str]]:
    """
    保存分析结果到本地和MongoDB
    
    Args:
        results: 分析结果
        analysis_id: 分析ID
        stock_symbol: 股票代码 (可选)
        
    Returns:
        (是否成功, 保存的文件路径字典)
    """
    from tradingagents.tasks import get_task_manager

    task_manager = get_task_manager() if analysis_id else None

    # Fetch stock_symbol if not provided
    if stock_symbol is None and analysis_id and task_manager:
        task_status = task_manager.get_task_status(analysis_id)
        if task_status:
            params = task_status.get('params', {})
            stock_symbol = params.get('stock_symbol')
    
    # Fallback if still None (try to get from results)
    if stock_symbol is None:
        stock_symbol = results.get('stock_symbol', 'UNKNOWN')

    # 更新任务进度（开始）
    step_info = {
        "step_index": 23,
        "step_name": "save_results",
        "display_name": "💾 保存分析结果",
        "description": "保存分模块报告到本地目录，保存分析报告到MongoDB，步骤输出已实时保存到eval_results目录"
    }
    total_steps = 12
    if analysis_id and task_manager:
        planned_steps = task_manager.get_task_planned_steps(analysis_id)
        if planned_steps:
            total_steps = len(planned_steps)
            for step in planned_steps:
                if step['step_name'] == "save_results":
                    step_info = step
                    break
        task_manager.update_task_progress(
            analysis_id,
            step_info.get('step_name', 'save_results'),
            step_info['description'],
            'start'
        )
    
    saved_files = {}
    
    try:
        from .report_exporter import save_analysis_report, save_modular_reports_to_results_dir
        from tradingagents.utils.analysis_runner import format_analysis_results
        
        # 格式化结果
        formatted_results = format_analysis_results(results)
        
        # 1. 保存分模块报告到本地目录
        logger.info(f"📁 [本地保存] 开始保存分模块报告到本地目录")
        local_files = save_modular_reports_to_results_dir(
            formatted_results, stock_symbol, analysis_id=analysis_id
        )
        
        if local_files:
            logger.info(f"✅ [本地保存] 已保存 {len(local_files)} 个本地报告文件")
            saved_files.update(local_files)
            for module, path in local_files.items():
                logger.info(f"  - {module}: {path}")
        else:
            logger.warning(f"⚠️ [本地保存] 本地报告文件保存失败")
        
        # 2. 保存分析报告到MongoDB
        logger.info(f"🗄️ [MongoDB保存] 开始保存分析报告到MongoDB")
        save_success = save_analysis_report(
            stock_symbol=stock_symbol,
            analysis_results=formatted_results,
            analysis_id=analysis_id
        )
        
        if save_success:
            logger.info(f"✅ [MongoDB保存] 分析报告已成功保存到MongoDB")
        else:
            logger.warning(f"⚠️ [MongoDB保存] MongoDB报告保存失败")
        
        if analysis_id and task_manager:
            task_manager.update_task_progress(
                analysis_id,
                step_info.get('step_name', 'save_results'),
                step_info['description'],
                'success'
            )

        return save_success or bool(local_files), saved_files
        
    except Exception as save_error:
        logger.error(f"❌ [报告保存] 保存分析报告时发生错误: {str(save_error)}")
        error_msg = f"⚠️ 报告保存出错: {str(save_error)}"

        if analysis_id and task_manager:
            task_manager.update_task_progress(
                analysis_id,
                step_info.get('step_name', 'save_results'),
                error_msg,
                'error'
            )
        return False, saved_files


# ========== 封装的步骤函数 ==========

def log_analysis_start(analysis_id: Optional[str] = None) -> tuple[Any, float]:
    """
    步骤1: 记录分析开始日志
    
    Args:
        analysis_id: 分析ID
        
    Returns:
        (logger_manager, analysis_start_time)
    """
    from tradingagents.utils.logging_manager import get_logger_manager
    import time
    
    logger_manager = get_logger_manager()
    analysis_start_time = time.time()
    
    return logger_manager, analysis_start_time


def prepare_step_output_directory(
    formatted_symbol: str,
    analysis_date: str,
    analysis_id: Optional[str] = None,
    async_tracker: Optional[Any] = None,
    analysis_start_time: Optional[float] = None
) -> Path:
    """
    步骤8: 步骤输出目录准备
    
    Args:
        formatted_symbol: 格式化后的股票代码
        analysis_date: 分析日期
        analysis_id: 分析ID
        async_tracker: 异步进度跟踪器
        analysis_start_time: 分析开始时间
        
    Returns:
        步骤输出目录路径
    """
    from pathlib import Path
    
    step_output_base_dir = Path("eval_results") / formatted_symbol / "TradingAgentsStrategy_logs" / "step_outputs" / analysis_date
    step_output_base_dir.mkdir(parents=True, exist_ok=True)

    return step_output_base_dir


def execute_analysis(
    graph: Any,
    formatted_symbol: str,
    analysis_date: str,
    analysis_id: Optional[str],
    session_id: str,
    update_progress: Optional[Callable] = None,
    async_tracker: Optional[Any] = None,
    analysis_start_time: Optional[float] = None,
    check_task_control: Optional[Callable] = None
) -> tuple[Any, Any]:
    """
    步骤9: 执行分析
    
    Args:
        graph: TradingAgentsGraph实例
        formatted_symbol: 格式化后的股票代码
        analysis_date: 分析日期
        analysis_id: 分析ID
        session_id: 会话ID
        update_progress: 进度回调函数
        async_tracker: 异步进度跟踪器
        analysis_start_time: 分析开始时间
        check_task_control: 任务控制检查函数
        
    Returns:
        (state, decision)
    """
    from .message_utils import publish_progress_message, get_step_info, get_message_producer
    
    if update_progress:
        update_progress(f"📊 开始分析 {formatted_symbol} 股票，这可能需要几分钟时间...")
    
    # 发布步骤9开始消息
    message_producer = get_message_producer()
    current_step, total_steps = get_step_info(async_tracker, 8, 12)
    
    publish_progress_message(
        analysis_id=analysis_id,
        current_step=current_step,
        total_steps=total_steps,
        step_name="📊 执行分析",
        step_description="开始多智能体分析执行",
        last_message=f"📊 开始分析 {formatted_symbol} 股票",
        module_name="analysis_execution",
        node_status=NodeStatus.START.value,
        async_tracker=async_tracker,
        analysis_start_time=analysis_start_time,
        message_producer=message_producer
    )
    
    # 检查任务控制
    if check_task_control and not check_task_control():
        raise Exception('任务已被停止')
    
    logger.debug(f"🔍 [RUNNER DEBUG] ===== 调用graph.propagate =====")
    logger.debug(f"🔍 [RUNNER DEBUG] 传递给graph.propagate的参数:")
    logger.debug(f"🔍 [RUNNER DEBUG]   symbol: '{formatted_symbol}'")
    logger.debug(f"🔍 [RUNNER DEBUG]   date: '{analysis_date}'")
    logger.debug(f"🔍 [RUNNER DEBUG]   analysis_id: '{analysis_id}'")
    logger.debug(f"🔍 [RUNNER DEBUG]   session_id: '{session_id}'")
    
    state, decision = graph.propagate(formatted_symbol, analysis_date, analysis_id=analysis_id, session_id=session_id)
    
    # 再次检查任务控制
    if check_task_control and not check_task_control():
        logger.warning(f"⚠️ [任务控制] 分析完成后检测到停止信号")
        raise Exception('任务已被停止（分析已完成）')
    
    return state, decision


def process_analysis_results(
    state: Any,
    decision: Any,
    analysis_id: Optional[str] = None,
    llm_provider: Optional[str] = None,
    llm_model: Optional[str] = None,
    session_id: Optional[str] = None,
    analysts: Optional[list] = None,
    research_depth: Optional[int] = None,
    market_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    步骤10: 处理分析结果
    
    Args:
        state: 分析状态
        decision: 分析决策
        analysis_id: 分析ID
        ... (other optional params)
        
    Returns:
        处理后的结果字典
    """
    from tradingagents.tasks import get_task_manager
    
    task_manager = get_task_manager()
    
    # Fetch params from TaskManager if analysis_id is present
    if analysis_id and task_manager:
        task_status = task_manager.get_task_status(analysis_id)
        if task_status:
            params = task_status.get('params', {})
            extra_config = params.get('extra_config', {})
            
            if llm_provider is None:
                llm_provider = extra_config.get('llm_provider', 'dashscope')
            if llm_model is None:
                llm_model = extra_config.get('llm_model', 'qwen-max')
            if analysts is None:
                analysts = params.get('analysts', [])
            if research_depth is None:
                research_depth = params.get('research_depth', 2)
            if market_type is None:
                market_type = params.get('market_type', '美股')
            
            # session_id is typically analysis_id in this context
            if session_id is None:
                session_id = analysis_id

    # Fallback defaults if still None
    llm_provider = llm_provider or 'dashscope'
    llm_model = llm_model or 'qwen-max'
    analysts = analysts or []
    research_depth = research_depth or 2
    market_type = market_type or '美股'
    session_id = session_id or analysis_id or "unknown_session"

    # 延迟导入以避免循环依赖
    def extract_risk_assessment(state):
        """从分析状态中提取风险评估数据（延迟导入版本）"""
        try:
            from tradingagents.utils.analysis_runner import extract_risk_assessment as _extract
            return _extract(state)
        except ImportError:
            # 如果无法导入，返回None
            return None
    
    if task_manager and analysis_id:
        task_manager.update_task_progress(
            analysis_id, 
            "result_processing",
            "提取风险评估数据，记录Token使用情况，格式化分析结果用于显示", 
            'start'
        )
    
    # 提取风险评估数据
    risk_assessment = extract_risk_assessment(state)
    if risk_assessment:
        state['risk_assessment'] = risk_assessment
    
    # 记录Token使用
    track_token_usage(
        llm_provider, llm_model, session_id, analysts, 
        research_depth, market_type
    )
    
    if task_manager and analysis_id:
        task_manager.update_task_progress(
            analysis_id, 
            "result_processing", 
            "提取风险评估数据，记录Token使用情况，格式化分析结果用于显示", 
            'success'
        )
    
    return {
        'state': state,
        'decision': decision
    }


def log_analysis_completion(
    analysis_id: Optional[str] = None,
    # Optional parameters
    stock_symbol: Optional[str] = None,
    session_id: Optional[str] = None,
    analysis_start_time: Optional[float] = None,
    logger_manager: Optional[Any] = None
) -> float:
    """
    步骤11: 记录完成日志
    
    Args:
        analysis_id: 分析ID
        stock_symbol: 股票代码 (可选)
        session_id: 会话ID (可选)
        analysis_start_time: 分析开始时间 (可选)
        logger_manager: 日志管理器 (可选)
        
    Returns:
        总成本
    """
    import time
    from tradingagents.tasks import get_task_manager
    from tradingagents.utils.logging_manager import get_logger_manager
    
    if logger_manager is None:
        logger_manager = get_logger_manager()
        
    task_manager = get_task_manager()
    
    if analysis_id and task_manager:
        task_status = task_manager.get_task_status(analysis_id)
        if task_status:
            params = task_status.get('params', {})
            if stock_symbol is None:
                stock_symbol = params.get('stock_symbol')
            if session_id is None:
                session_id = params.get('session_id') or analysis_id
            if analysis_start_time is None:
                analysis_start_time = params.get('analysis_start_time') or params.get('start_time')
    
    stock_symbol = stock_symbol or "UNKNOWN"
    session_id = session_id or analysis_id or "unknown_session"
    analysis_start_time = analysis_start_time or time.time()
    
    step_info = {
        "step_index": 22, 
        "display_name": "✅ 记录完成日志", 
        "description": "记录分析完成时间，计算总耗时和总成本"
    }
    
    if task_manager and analysis_id:
        planned_steps = task_manager.get_task_planned_steps(analysis_id)
        if planned_steps:
            for step in planned_steps:
                if step['step_name'] == "completion_logging":
                    step_info = step
                    break
                    
        task_manager.update_task_progress(
            analysis_id, 
            "completion_logging", 
            step_info['description'], 
            'start'
        )
    
    analysis_duration = time.time() - analysis_start_time
    
    total_cost = 0.0
    try:
        from tradingagents.config.config_manager import token_tracker
        total_cost = token_tracker.get_session_cost(session_id)
    except:
        pass
    
    logger_manager.log_analysis_complete(
        logger, stock_symbol, "comprehensive_analysis", session_id,
        analysis_duration, total_cost
    )
    
    logger.info(f"✅ [分析完成] 股票分析成功完成",
               extra={
                   'stock_symbol': stock_symbol,
                   'session_id': session_id,
                   'duration': analysis_duration,
                   'total_cost': total_cost,
                   'success': True,
                   'event_type': 'web_analysis_complete'
               })
    
    if task_manager and analysis_id:
        task_manager.update_task_progress(
            analysis_id, 
            "completion_logging", 
            step_info['description'], 
            'success'
        )
    
    return total_cost


def post_process_analysis_steps(
    state: Dict[str, Any],
    decision: Any,
    analysis_id: Optional[str] = None,
    stock_symbol: Optional[str] = None,
    analysis_date: Optional[str] = None,
    analysts: Optional[list] = None,
    research_depth: Optional[int] = None,
    llm_provider: Optional[str] = None,
    llm_model: Optional[str] = None,
    market_type: Optional[str] = None,
    session_id: Optional[str] = None,
    analysis_start_time: Optional[float] = None
) -> Dict[str, Any]:
    """
    后处理步骤：执行所有分析后的处理工作
    
    后处理步骤包括：
    - 后处理步骤1: 📊 处理分析结果 (process_analysis_results)
    - 后处理步骤2: ✅ 记录完成日志 (log_analysis_completion)
    - 后处理步骤3: 💾 保存分析结果 (save_analysis_results)
    
    Args:
        state: 分析状态
        decision: 分析决策
        analysis_id: 分析ID
        stock_symbol: 股票代码（可选，会通过analysis_id自动补充）
        analysis_date: 分析日期（可选，会通过analysis_id自动补充）
        analysts: 分析师列表（可选，会通过analysis_id自动补充）
        research_depth: 研究深度（可选，会通过analysis_id自动补充）
        llm_provider: LLM提供商（可选，会通过analysis_id自动补充）
        llm_model: 模型名称（可选，会通过analysis_id自动补充）
        market_type: 市场类型（可选，会通过analysis_id自动补充）
        session_id: 会话ID（可选，会通过analysis_id自动补充）
        analysis_start_time: 分析开始时间
        
    Returns:
        最终的分析结果字典
    """
    # 导入必要的模块
    from tradingagents.utils.logging_manager import get_logger_manager
    from tradingagents.tasks import get_task_manager

    # 获取 logger_manager
    logger_manager = get_logger_manager()

    # 通过 analysis_id 尽量补充参数
    params: Dict[str, Any] = {}
    extra_config: Dict[str, Any] = {}
    task_manager = get_task_manager()
    if analysis_id and task_manager:
        task_status = task_manager.get_task_status(analysis_id) or {}
        params = task_status.get('params', {}) or {}
        extra_config = params.get('extra_config', {}) or {}
        if analysis_start_time is None:
            analysis_start_time = params.get('analysis_start_time') or params.get('start_time')
        if session_id is None:
            session_id = params.get('session_id') or analysis_id

    stock_symbol = stock_symbol or params.get('stock_symbol') or "UNKNOWN"
    analysis_date = analysis_date or params.get('analysis_date') or params.get('date') or ""
    analysts = analysts or params.get('analysts') or []
    research_depth = research_depth or params.get('research_depth') or 2
    llm_provider = llm_provider or extra_config.get('llm_provider') or 'dashscope'
    llm_model = llm_model or extra_config.get('llm_model') or 'qwen-max'
    market_type = market_type or params.get('market_type') or '美股'
    session_id = session_id or analysis_id or "unknown_session"

    # 检查 Token 跟踪是否启用
    token_tracking_enabled = False
    try:
        from tradingagents.config.config_manager import token_tracker
        token_tracking_enabled = True
    except ImportError:
        pass

    # ========== 后处理步骤1: 处理分析结果 ==========
    processed_results = process_analysis_results(
        state=state,
        decision=decision,
        llm_provider=llm_provider,
        llm_model=llm_model,
        session_id=session_id,
        analysts=analysts,
        research_depth=research_depth,
        market_type=market_type,
        analysis_id=analysis_id
    )

    results = {
        'stock_symbol': stock_symbol,
        'analysis_date': analysis_date,
        'analysts': analysts,
        'research_depth': research_depth,
        'llm_provider': llm_provider,
        'llm_model': llm_model,
        'state': processed_results['state'],
        'decision': processed_results['decision'],
        'success': True,
        'error': None,
        'session_id': session_id if token_tracking_enabled else None
    }

    # ========== 后处理步骤2: 记录完成日志 ==========
    log_analysis_completion(
        logger_manager=logger_manager,
        stock_symbol=stock_symbol,
        session_id=session_id,
        analysis_start_time=analysis_start_time if analysis_start_time else 0,
        analysis_id=analysis_id
    )

    # ========== 后处理步骤3: 保存分析结果 ==========
    save_analysis_results(
        results=results, 
        stock_symbol=stock_symbol, 
        analysis_id=analysis_id
    )

    return results
