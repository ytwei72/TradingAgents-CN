"""
分析辅助函数模块
提供环境验证、股票代码格式化、成本估算等辅助功能
"""

import os
from typing import Dict, Any, Optional, Callable
from pathlib import Path

# 导入日志模块
from tradingagents.utils.logging_manager import get_logger
logger = get_logger('web')


def validate_environment(update_progress: Optional[Callable] = None) -> tuple[bool, Optional[str]]:
    """
    验证环境变量配置
    
    Args:
        update_progress: 进度回调函数
        
    Returns:
        (是否通过验证, 错误信息)
    """
    if update_progress:
        update_progress("检查环境变量配置...")
    
    dashscope_key = os.getenv("DASHSCOPE_API_KEY")
    finnhub_key = os.getenv("FINNHUB_API_KEY")
    
    logger.info(f"环境变量检查:")
    logger.info(f"  DASHSCOPE_API_KEY: {'已设置' if dashscope_key else '未设置'}")
    logger.info(f"  FINNHUB_API_KEY: {'已设置' if finnhub_key else '未设置'}")
    
    if not dashscope_key:
        error_msg = "DASHSCOPE_API_KEY 环境变量未设置"
        if update_progress:
            update_progress(f"❌ {error_msg}")
        return False, error_msg
    
    if not finnhub_key:
        error_msg = "FINNHUB_API_KEY 环境变量未设置"
        if update_progress:
            update_progress(f"❌ {error_msg}")
        return False, error_msg
    
    if update_progress:
        update_progress("✅ 环境变量验证通过")
    
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
    update_progress: Optional[Callable] = None
) -> Optional[float]:
    """
    估算分析成本
    
    Args:
        llm_provider: LLM提供商
        llm_model: 模型名称
        analysts: 分析师列表
        research_depth: 研究深度
        update_progress: 进度回调函数
        
    Returns:
        估算的成本（元），如果无法估算则返回None
    """
    try:
        from tradingagents.config.config_manager import token_tracker
    except ImportError:
        if update_progress:
            update_progress("⚠️ Token跟踪功能未启用，无法估算成本")
        return None
    
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
    
    if update_progress:
        update_progress(f"💰 预估分析成本: ¥{estimated_cost:.4f}")
    
    return estimated_cost


def prepare_stock_data_for_analysis(
    stock_symbol: str,
    market_type: str,
    analysis_date: str,
    update_progress: Optional[Callable] = None
) -> tuple[bool, Optional[str], Optional[Any]]:
    """
    预获取和验证股票数据
    
    Args:
        stock_symbol: 股票代码
        market_type: 市场类型
        analysis_date: 分析日期
        update_progress: 进度回调函数
        
    Returns:
        (是否成功, 错误信息, 准备结果)
    """
    if update_progress:
        update_progress("🔍 验证股票代码并预获取数据...")
    
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
            if update_progress:
                update_progress(error_msg)
            logger.error(error_msg)
            return False, preparation_result.error_message, preparation_result
        
        # 数据预获取成功
        success_msg = f"✅ 数据准备完成: {preparation_result.stock_name} ({preparation_result.market_type})"
        if update_progress:
            update_progress(success_msg)
        logger.info(success_msg)
        logger.info(f"缓存状态: {preparation_result.cache_status}")
        
        return True, None, preparation_result
        
    except Exception as e:
        error_msg = f"❌ 数据预获取过程中发生错误: {str(e)}"
        if update_progress:
            update_progress(error_msg)
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
        from .task_control_manager import should_stop, should_pause, wait_if_paused
        
        # 检查停止信号
        if should_stop(analysis_id):
            logger.info(f"⏹️ [任务控制] 收到停止信号: {analysis_id}")
            if async_tracker:
                async_tracker.mark_stopped("用户停止了分析任务")
            return False
        
        # 检查暂停信号
        if should_pause(analysis_id):
            logger.info(f"⏸️ [任务控制] 收到暂停信号: {analysis_id}")
            if async_tracker:
                async_tracker.mark_paused()
            
            # 等待直到恢复或停止
            wait_if_paused(analysis_id)
            
            # 检查是否在暂停期间被停止
            if should_stop(analysis_id):
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
    market_type: str,
    update_progress: Optional[Callable] = None
) -> Optional[float]:
    """
    记录Token使用情况
    
    Args:
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
    
    if usage_record and update_progress:
        update_progress(f"💰 记录使用成本: ¥{usage_record.cost:.4f}")
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
    async_tracker: Optional[Any],
    update_progress: Optional[Callable] = None
) -> tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
    """
    准备分析步骤：执行所有前期准备工作
    
    准备步骤包括：
    - 准备步骤1: 任务控制检查
    - 准备步骤2: 数据预获取和验证
    - 准备步骤3: 环境验证
    - 准备步骤4: 构建配置
    - 准备步骤5: 格式化股票代码
    - 准备步骤6: 初始化分析引擎
    
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
        update_progress: 进度回调函数
        
    Returns:
        (是否成功, 准备结果字典, 错误信息)
        准备结果字典包含: config, formatted_symbol, graph, session_id
    """
    from .analysis_config import AnalysisConfigBuilder
    
    # 生成会话ID
    import uuid
    from datetime import datetime
    session_id = f"analysis_{uuid.uuid4().hex[:8]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # ========== 准备步骤1: 任务控制检查 ==========
    if not check_task_control(analysis_id, async_tracker):
        error_msg = '任务已被停止'
        return False, None, error_msg
    
    # ========== 准备步骤2: 数据预获取和验证 ==========
    success, error_msg, preparation_result = prepare_stock_data_for_analysis(
        stock_symbol, market_type, analysis_date, update_progress
    )
    
    if not success:
        suggestion = getattr(preparation_result, 'suggestion', "请检查网络连接或稍后重试") if preparation_result else "请检查网络连接或稍后重试"
        return False, None, f"{error_msg} ({suggestion})"
    
    # ========== 准备步骤3: 环境验证 ==========
    env_valid, env_error = validate_environment(update_progress)
    if not env_valid:
        return False, None, env_error
    
    # ========== 准备步骤4: 构建配置 ==========
    if update_progress:
        update_progress("⚙️ 构建配置...")
    config_builder = AnalysisConfigBuilder()
    config = config_builder.build_config(
        llm_provider=llm_provider,
        llm_model=llm_model,
        research_depth=research_depth,
        market_type=market_type
    )
    
    logger.info(f"使用配置: {config}")
    logger.info(f"分析师列表: {analysts}")
    logger.info(f"股票代码: {stock_symbol}")
    logger.info(f"分析日期: {analysis_date}")
    
    if update_progress:
        update_progress("✅ 配置构建完成")
    
    # ========== 准备步骤5: 格式化股票代码 ==========
    if update_progress:
        update_progress("📝 格式化股票代码...")
    formatted_symbol = format_stock_symbol(stock_symbol, market_type)
    
    # 显示市场类型提示
    market_icons = {"A股": "🇨🇳", "港股": "🇭🇰", "美股": "🇺🇸"}
    market_icon = market_icons.get(market_type, "📊")
    if update_progress:
        update_progress(f"✅ {market_icon} 股票代码格式化完成: {formatted_symbol}")
    
    # ========== 准备步骤6: 初始化分析引擎 ==========
    if update_progress:
        update_progress("🔧 初始化分析引擎...")
    
    if not check_task_control(analysis_id, async_tracker):
        error_msg = '任务已被停止'
        return False, None, error_msg
    
    from tradingagents.graph.trading_graph import TradingAgentsGraph
    graph = TradingAgentsGraph(analysts, config=config, debug=False)
    
    # 返回准备结果
    preparation_result_dict = {
        'config': config,
        'formatted_symbol': formatted_symbol,
        'graph': graph,
        'session_id': session_id,
        'preparation_result': preparation_result
    }
    
    return True, preparation_result_dict, None


def save_analysis_results(
    results: Dict[str, Any],
    stock_symbol: str,
    analysis_id: Optional[str],
    update_progress: Optional[Callable] = None
) -> tuple[bool, Dict[str, str]]:
    """
    保存分析结果到本地和MongoDB
    
    Args:
        results: 分析结果
        stock_symbol: 股票代码
        analysis_id: 分析ID
        update_progress: 进度回调函数
        
    Returns:
        (是否成功, 保存的文件路径字典)
    """
    if update_progress:
        update_progress("💾 正在保存分析报告...")
    
    saved_files = {}
    
    try:
        from .report_exporter import save_analysis_report, save_modular_reports_to_results_dir
        from .analysis_runner import format_analysis_results
        
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
            if update_progress:
                update_progress("✅ 分析报告已保存到数据库和本地文件")
        else:
            logger.warning(f"⚠️ [MongoDB保存] MongoDB报告保存失败")
            if update_progress:
                if local_files:
                    update_progress("✅ 本地报告已保存，但数据库保存失败")
                else:
                    update_progress("⚠️ 报告保存失败，但分析已完成")
        
        return save_success or bool(local_files), saved_files
        
    except Exception as save_error:
        logger.error(f"❌ [报告保存] 保存分析报告时发生错误: {str(save_error)}")
        if update_progress:
            update_progress("⚠️ 报告保存出错，但分析已完成")
        return False, saved_files

