"""
分析辅助函数模块
提供环境验证、股票代码格式化、成本估算等辅助功能
"""

import os
from typing import Dict, Any, Optional, Callable
from pathlib import Path

# 导入日志模块
from tradingagents.utils.logging_manager import get_logger, get_logger_manager
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
    results: Dict[str, Any],
    params: Dict[str, Any]
) -> Optional[float]:
    """
    记录Token使用情况
    
    Args:
        results: 分析结果字典，包含 llm_provider, llm_model, session_id, analysts, research_depth
        params: 参数字典，包含 market_type
        
    Returns:
        总成本（元），如果无法跟踪则返回None
    """
    try:
        from tradingagents.config.config_manager import token_tracker
    except ImportError:
        return None
    
    # 从 results 和 params 中提取所需信息
    analysts = results.get('analysts', [])
    research_depth = results.get('research_depth', 2)
    market_type = params.get('market_type', '美股')
    
    # 估算实际使用的token（基于分析师数量和研究深度）
    depth_token_map = {
        1: (1500, 800),
        2: (2000, 1000),
        3: (2500, 1200),
        4: (3000, 1500),
        5: (4000, 2000),
    }
    
    input_per_analyst, output_per_analyst = depth_token_map.get(research_depth, (2500, 1200))
    
    usage_record = token_tracker.track_usage(
        provider=results.get('llm_provider', 'dashscope'),
        model_name=results.get('llm_model', 'qwen-max'),
        input_tokens=len(analysts) * input_per_analyst,
        output_tokens=len(analysts) * output_per_analyst,
        session_id=results.get('session_id', ''),
        analysis_type=f"{market_type}_analysis"
    )

    return usage_record.cost if usage_record else None


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
    success, exec_msg, preparation_result = prepare_stock_data_for_analysis(
        stock_symbol, market_type, analysis_date, analysis_id, async_tracker
    )
    
    if not success:
        _update_step_error(exec_msg)
        return False, None, exec_msg
    _update_step_success(f"✅ 数据准备完成: {preparation_result.stock_name} ({preparation_result.market_type})")
    
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
    analysis_id: str,
    results: Dict[str, Any]
) -> tuple[bool, Dict[str, str]]:
    """
    后处理步骤3: 保存分析结果
    
    处理步骤包括：
    - 格式化分析结果
    - 保存分模块报告到本地目录
    - 保存分析报告到MongoDB
    
    Args:
        results: 分析结果字典
        analysis_id: 分析ID（必选）
        
    Returns:
        (是否成功, 保存的文件路径字典)
        文件路径字典包含各模块报告的本地保存路径
    """
    from tradingagents.tasks import get_task_manager

    task_manager = get_task_manager()

    # 从内部获取 stock_symbol：优先从 task_manager 获取，其次从 results 获取
    stock_symbol = None
    if analysis_id and task_manager:
        task_status = task_manager.get_task_status(analysis_id)
        if task_status:
            params = task_status.get('params', {})
            stock_symbol = params.get('stock_symbol')
    
    # 如果仍未获取到，从 results 中获取
    if stock_symbol is None:
        stock_symbol = results.get('stock_symbol', 'UNKNOWN')
    
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

        return save_success or bool(local_files), saved_files
        
    except Exception as save_error:
        logger.error(f"❌ [报告保存] 保存分析报告时发生错误: {str(save_error)}")
        return False, saved_files


# ========== 封装的步骤函数 ==========

def log_analysis_start(analysis_id: str) -> tuple[Any, float]:
    """
    步骤1: 记录分析开始日志
    
    Args:
        analysis_id: 分析ID（必选）
        
    Returns:
        (logger_manager, analysis_start_time)
    """
    from tradingagents.utils.logging_manager import get_logger_manager
    from tradingagents.tasks import get_task_manager
    import time
    
    logger_manager = get_logger_manager()
    analysis_start_time = time.time()
    
    # 将 analysis_start_time 保存到任务状态中
    task_manager = get_task_manager()
    if task_manager:
        try:
            state_machine = task_manager._get_task_state_machine(analysis_id)
            state_machine.update_state({'progress': {'analysis_start_time': analysis_start_time}})
        except Exception as e:
            logger.warning(f"⚠️ [分析启动] 保存analysis_start_time到任务状态失败: {e}")
    
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
    analysis_id: str,
    state: Any,
    decision: Any
) -> Dict[str, Any]:
    """
    后处理步骤1: 处理分析结果
    
    处理步骤包括：
    - 提取风险评估数据
    - 记录Token使用情况
    - 构建完整的结果字典
    
    Args:
        analysis_id: 分析ID（必选）
        state: 分析状态
        decision: 分析决策
        
    Returns:
        处理后的完整结果字典，包含所有需要的属性
    """
    # 获取并验证 task_manager、task_status、params、extra_config，如果无效则抛出异常
    task_manager = get_task_manager()
    
    task_status = task_manager.get_task_status(analysis_id)
    params = task_status.get('params') if task_status else None
    extra_config = params.get('extra_config') if params else None
    
    if not task_status or not params or not extra_config:
        raise ValueError(f"Task status data is abnormal for analysis_id: {analysis_id}")

    # 延迟导入以避免循环依赖
    def extract_risk_assessment(state):
        """从分析状态中提取风险评估数据（延迟导入版本）"""
        try:
            from tradingagents.utils.analysis_runner import extract_risk_assessment as _extract
            return _extract(state)
        except ImportError:
            # 如果无法导入，返回None
            return None
    
    # 提取风险评估数据
    risk_assessment = extract_risk_assessment(state)
    if risk_assessment:
        state['risk_assessment'] = risk_assessment
    
    # 检查 Token 跟踪是否启用
    token_tracking_enabled = False
    try:
        from tradingagents.config.config_manager import token_tracker
        token_tracking_enabled = True
    except ImportError:
        pass
    
    # 直接对 results 进行赋值，从 params 和 extra_config 中获取所有需要的值
    results = {}
    results['stock_symbol'] = params.get('stock_symbol', 'UNKNOWN')
    results['analysis_date'] = params.get('analysis_date') or params.get('date', '')
    results['analysts'] = params.get('analysts', [])
    results['research_depth'] = params.get('research_depth', 2)
    results['llm_provider'] = extra_config.get('llm_provider', 'dashscope')
    results['llm_model'] = extra_config.get('llm_model', 'qwen-max')
    results['state'] = state
    results['decision'] = decision
    results['success'] = True
    results['error'] = None
    results['session_id'] = params.get('session_id') or analysis_id
    
    # 记录Token使用
    track_token_usage(results, params)
    
    return results


def log_analysis_completion(
    analysis_id: str
) -> float:
    """
    后处理步骤2: 记录完成日志
    
    处理步骤包括：
    - 计算分析持续时间
    - 获取Token使用总成本
    - 记录分析完成日志
    - 保存分析完成信息到数据库
    
    Args:
        analysis_id: 分析ID（必选）
        
    Returns:
        总成本（元），如果无法跟踪则返回0.0
    """
    import time
    
    logger_manager = get_logger_manager()
    task_manager = get_task_manager()
    
    task_status = task_manager.get_task_status(analysis_id)
    params = task_status.get('params', {})
    progress = task_status.get('progress', {})
    # 股票代码
    stock_symbol = params.get('stock_symbol')
    # 会话ID
    session_id = params.get('session_id') or analysis_id
    # 分析开始时间
    analysis_start_time = progress.get('analysis_start_time')
        
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
    
    return total_cost


def post_process_analysis_steps(
    analysis_id: str,
    state: Dict[str, Any],
    decision: Any
) -> Dict[str, Any]:
    """
    后处理步骤：执行所有分析后的处理工作
    
    后处理步骤包括：
    - 后处理步骤1: 📊 处理分析结果 (process_analysis_results)
    - 后处理步骤2: ✅ 记录完成日志 (log_analysis_completion)
    - 后处理步骤3: 💾 保存分析结果 (save_analysis_results)
    
    Args:
        analysis_id: 分析ID
        state: 分析状态
        decision: 分析决策

    Returns:
        最终的分析结果字典
    """
    # 获取 task_manager
    task_manager = get_task_manager()
    
    # 验证 task_manager 和 analysis_id（提前验证，无效则抛出异常）
    if not task_manager or not analysis_id:
        raise ValueError(f"Task manager or analysis_id is not available: analysis_id={analysis_id}")
    
    # 初始化 step_name 变量
    step_name = ""
    
    def _update_step_start(message: str):
        task_manager.update_task_progress(analysis_id, step_name, message, 'start')

    def _update_step_success(message: str):
        task_manager.update_task_progress(analysis_id, step_name, message, 'success')
    
    def _update_step_error(message: str):
        task_manager.update_task_progress(analysis_id, step_name, message, 'error')

    # ========== 后处理步骤1: 处理分析结果 ==========
    step_name = "result_processing"
    _update_step_start("📊 开始处理分析结果...")
    try:
        results = process_analysis_results(analysis_id, state, decision)
        _update_step_success("✅ 分析结果处理完成")
    except Exception as e:
        error_msg = f"⚠️ 分析结果处理失败：{str(e)}"
        _update_step_error(error_msg)
        raise

    # ========== 后处理步骤2: 记录完成日志 ==========
    step_name = "completion_logging"
    _update_step_start("✅ 开始记录分析结束日志，并计算本次分析任务总成本...")
    try:
        log_analysis_completion(analysis_id=analysis_id)
        _update_step_success("✅ 完成分析任务结束日志记录和总成本计算，并保存到数据库")
    except Exception as e:
        error_msg = f"⚠️ 完成日志记录失败：{str(e)}"
        _update_step_error(error_msg)
        raise

    # ========== 后处理步骤3: 保存分析结果 ==========
    step_name = "save_results"
    _update_step_start("💾 开始保存分析结果...")
    try:
        save_analysis_results(analysis_id, results)
        _update_step_success("✅ 分析结果保存完成")
    except Exception as e:
        error_msg = f"⚠️ 分析结果保存失败：{str(e)}"
        _update_step_error(error_msg)
        raise

    return results
