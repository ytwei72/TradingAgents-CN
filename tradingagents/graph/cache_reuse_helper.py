"""
缓存结果复用辅助工具
提供基于数据库缓存的结果复用功能，当分析任务参数相同时自动从缓存中读取结果
"""

import os
import time
import random
from typing import Dict, Any, Optional

from tradingagents.utils.logging_manager import get_logger
logger = get_logger('tools')  # 使用tools日志器，与正常节点执行保持一致，便于ProgressLogHandler统一捕获

from tradingagents.messaging.config import get_message_producer, is_message_mode_enabled
from tradingagents.messaging.decorators.message_decorators import _publish_step_message
from tradingagents.messaging.business.messages import NodeStatus

# 全局变量存储graph实例（用于访问结果复用功能）
_graph_instance = None


def set_graph_instance(graph_instance):
    """设置graph实例，以便节点可以访问结果复用功能"""
    global _graph_instance
    _graph_instance = graph_instance


def check_and_load_cached_result(node_name: str, state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """检查并加载缓存的节点结果（基于参数匹配的结果复用）

    当分析任务的参数（股票代码、分析日期、研究深度、分析师团队）都相同时，
    从数据库缓存中读取历史结果，避免重复计算。
    """
    global _graph_instance

    if not _graph_instance:
        return None

    # 获取股票代码和交易日期
    ticker = state.get('company_of_interest', '')
    trade_date = state.get('trade_date', '')

    if not ticker or not trade_date:
        logger.debug("🔍 [缓存查询] 无法获取股票代码或日期，跳过缓存查询")
        return None

    # 从graph实例中获取分析参数（用于匹配缓存）
    research_depth = getattr(_graph_instance, 'research_depth', None)
    analysts = getattr(_graph_instance, 'selected_analysts', None)
    market_type = getattr(_graph_instance, 'market_type', None)

    cache_reuse_config: Optional[Dict[str, bool]] = None
    cache_reuse_sleep_min: Optional[float] = None
    cache_reuse_sleep_max: Optional[float] = None

    # 提取分析ID（用于从任务状态读取配置及消息机制）
    analysis_id = state.get('analysis_id') or state.get('session_id')

    # 1. 优先从任务状态中读取结果复用配置
    if analysis_id:
        try:
            from tradingagents.tasks import get_task_manager
            task_manager = get_task_manager()
            if task_manager:
                task_status = task_manager.get_task_status(analysis_id)
                if task_status:
                    cfg = task_status.get('cache_reuse_config') or {}
                    mode = cfg.get('cache_reuse_mode')
                    sleep_min = cfg.get('cache_reuse_sleep_min')
                    sleep_max = cfg.get('cache_reuse_sleep_max')
                    if mode is not None:
                        cache_reuse_config, cache_reuse_sleep_min, cache_reuse_sleep_max = _load_cache_reuse_from_values(
                            mode, sleep_min, sleep_max
                        )
                        logger.debug(f"✅ [结果复用配置] 从任务状态读取: {cache_reuse_config}")
        except Exception as e:
            logger.debug(f"⚠️ [结果复用配置] 从任务状态读取失败，将回退到环境变量: {e}")

    # 2. 如果任务中没有配置，则从环境变量加载（全局默认）
    if cache_reuse_config is None:
        cache_reuse_config, cache_reuse_sleep_min, cache_reuse_sleep_max = _load_cache_reuse_from_env()

    # 如果消息模式启用，发送模块开始消息
    if is_message_mode_enabled():
        producer = get_message_producer()
        if producer and analysis_id:
            _publish_step_message(
                producer=producer,
                analysis_id=str(analysis_id),
                module_name=node_name,
                node_status=NodeStatus.START.value
            )

    # 记录模块开始（用于进度追踪）
    logger.info(f"📊 [模块开始] {node_name} - 股票: {ticker}")
    logger.info(f"🔍 [缓存查询] 查询缓存结果 - 股票: {ticker}, 日期: {trade_date}, 研究深度: {research_depth}, 分析师: {analysts}")

    # 尝试从数据库缓存中加载历史输出
    cached_state = _load_cached_step_output(
        node_name=node_name,
        ticker=ticker,
        trade_date=trade_date,
        research_depth=research_depth,
        analysts=analysts,
        market_type=market_type,
        current_state=state,
        cache_reuse_config=cache_reuse_config
    )

    # 记录开始时间（用于计算耗时）
    start_time = time.time()

    if cached_state:
        # 合并缓存状态到当前状态（保留当前状态的基础信息）
        merged_state = state.copy()
        # 保存analysis_id和session_id，避免被缓存数据覆盖
        preserved_analysis_id = state.get('analysis_id')
        preserved_session_id = state.get('session_id')
        merged_state.update(cached_state)
        # 恢复analysis_id和session_id
        if preserved_analysis_id is not None:
            merged_state['analysis_id'] = preserved_analysis_id
        if preserved_session_id is not None:
            merged_state['session_id'] = preserved_session_id

        # 对于研究员节点，更新计数
        if node_name in ['bull_researcher', 'bear_researcher']:
            if 'investment_debate_state' in merged_state and isinstance(merged_state['investment_debate_state'], dict):
                current_count = merged_state['investment_debate_state'].get('count', 0)
                merged_state['investment_debate_state']['count'] = current_count + 1

        # 对于风险分析师节点，更新计数
        if node_name in ['risky_analyst', 'safe_analyst', 'neutral_analyst']:
            if 'risk_debate_state' in merged_state and isinstance(merged_state['risk_debate_state'], dict):
                current_count = merged_state['risk_debate_state'].get('count', 0)
                merged_state['risk_debate_state']['count'] = current_count + 1

        # 模拟短暂延迟，模拟真实执行
        sleep_min = cache_reuse_sleep_min if cache_reuse_sleep_min is not None else 2.0
        sleep_max = cache_reuse_sleep_max if cache_reuse_sleep_max is not None else 10.0
        sleep_time = random.uniform(sleep_min, sleep_max)
        logger.info(f"✅ [缓存命中] 节点 {node_name} 使用缓存结果，模拟延迟 {sleep_time:.2f} 秒")

        time.sleep(sleep_time)
        duration = time.time() - start_time

        # 如果消息模式启用，发送模块完成消息
        if is_message_mode_enabled():
            producer = get_message_producer()
            if producer and analysis_id:
                _publish_step_message(
                    producer=producer,
                    analysis_id=str(analysis_id),
                    module_name=node_name,
                    node_status=NodeStatus.COMPLETE.value,
                    duration=duration
                )

        # 记录模块完成（用于进度追踪）
        logger.info(f"📊 [模块完成] {node_name} - 缓存复用完成 - 股票: {ticker}, 耗时: {duration:.2f}s")

        return merged_state
    else:
        # 如果没有找到缓存数据，继续正常执行
        duration = time.time() - start_time
        logger.debug(f"🔍 [缓存未命中] 节点 {node_name} 未找到匹配的缓存结果，使用正常执行模式")
        return None


def _load_cached_step_output(
    node_name: str,
    ticker: str,
    trade_date: str,
    research_depth: Optional[int],
    analysts: Optional[list],
    market_type: Optional[str],
    current_state: Optional[Dict[str, Any]] = None,
    cache_reuse_config: Optional[Dict[str, bool]] = None
) -> Optional[Dict[str, Any]]:
    """从数据库缓存中加载指定节点的历史输出"""
    global _graph_instance

    if not _graph_instance:
        return None

    # 检查是否应该使用结果复用（基于配置）
    should_use_cache_reuse = False
    if cache_reuse_config:
        if cache_reuse_config.get('all', False):
            should_use_cache_reuse = True
        else:
            should_use_cache_reuse = cache_reuse_config.get(node_name, False)

    if not should_use_cache_reuse:
        logger.debug(f"🔍 [结果复用] 节点 {node_name} 未启用结果复用，跳过缓存查询")
        return None

    # 优先从MongoDB读取缓存
    if _graph_instance.steps_status_manager.is_connected():
        try:
            doc = _graph_instance.steps_status_manager.find_cached_step_status(
                ticker=ticker,
                trade_date=trade_date,
                node_name=node_name,
            )

            if doc:
                if _graph_instance._match_node_output(node_name, doc):
                    logger.info(f"✅ [缓存命中] 从MongoDB找到匹配的缓存结果: {node_name} (股票: {ticker}, 日期: {trade_date})")
                    return _graph_instance._convert_historical_to_state(doc, node_name, current_state)
                else:
                    logger.debug(f"🔍 [缓存查询] MongoDB中找到记录但节点不匹配: {node_name}")
            else:
                logger.debug(f"🔍 [缓存查询] MongoDB中未找到匹配的缓存记录: {ticker} - {trade_date}")
        except Exception as e:
            logger.warning(f"⚠️ [缓存查询] 从MongoDB读取失败: {e}")

    logger.debug(f"🔍 [缓存查询] 未找到节点 {node_name} 的缓存结果")
    return None


def create_cache_reuse_wrapper(node_func, node_name: str):
    """创建节点包装器，自动添加缓存结果复用检查"""

    def wrapped_node(state: Dict[str, Any]) -> Dict[str, Any]:
        cached_result = check_and_load_cached_result(node_name, state)
        if cached_result is not None:
            return cached_result
        return node_func(state)

    return wrapped_node


def _load_cache_reuse_from_values(
    mode_value: Any,
    sleep_min_value: Any,
    sleep_max_value: Any,
) -> (Dict[str, bool], float, float):
    """从给定的值构建结果复用配置（供任务参数使用）"""
    mode_str = str(mode_value).strip().lower() if mode_value is not None else "false"

    # 解析模式
    if mode_str in ("false", ""):
        config: Dict[str, bool] = {}
    elif mode_str == "true":
        config = {"all": True}
    else:
        node_list = [node.strip() for node in mode_str.split(",") if node.strip()]
        config = {}
        node_mapping = {
            "market": "market_analyst",
            "market_analyst": "market_analyst",
            "fundamentals": "fundamentals_analyst",
            "fundamentals_analyst": "fundamentals_analyst",
            "news": "news_analyst",
            "news_analyst": "news_analyst",
            "social": "social_media_analyst",
            "social_media_analyst": "social_media_analyst",
            "bull": "bull_researcher",
            "bull_researcher": "bull_researcher",
            "bear": "bear_researcher",
            "bear_researcher": "bear_researcher",
            "research_manager": "research_manager",
            "trader": "trader",
            "risky": "risky_analyst",
            "risky_analyst": "risky_analyst",
            "safe": "safe_analyst",
            "safe_analyst": "safe_analyst",
            "neutral": "neutral_analyst",
            "neutral_analyst": "neutral_analyst",
            "risk_manager": "risk_manager",
            "risk_judge": "risk_manager",
        }
        for node in node_list:
            normalized_node = node_mapping.get(node, node)
            config[normalized_node] = True

    # 解析 sleep 配置
    try:
        sleep_min = float(sleep_min_value) if sleep_min_value is not None else 2.0
    except Exception:
        sleep_min = 2.0
    try:
        sleep_max = float(sleep_max_value) if sleep_max_value is not None else 10.0
    except Exception:
        sleep_max = 10.0

    return config, sleep_min, sleep_max


def _load_cache_reuse_from_env() -> (Dict[str, bool], float, float):
    """从环境变量加载结果复用配置（作为全局默认）"""
    mode_env = os.getenv("CACHE_REUSE_MODE", "false")
    sleep_min_env = os.getenv("CACHE_REUSE_SLEEP_MIN", "2")
    sleep_max_env = os.getenv("CACHE_REUSE_SLEEP_MAX", "10")

    return _load_cache_reuse_from_values(mode_env, sleep_min_env, sleep_max_env)


