"""
模拟模式辅助工具
提供节点级别的模拟模式检查和历史数据加载功能
"""

import os
import json
import time
import random
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

# 导入日志模块
from tradingagents.utils.logging_manager import get_logger
logger = get_logger('tools')  # 使用tools日志器，与正常节点执行保持一致，便于ProgressLogHandler统一捕获

# 导入消息机制
from tradingagents.messaging.config import get_message_producer, is_message_mode_enabled
from tradingagents.messaging.decorators.message_decorators import _publish_progress_message
from tradingagents.messaging.business.messages import NodeStatus

# 全局变量存储graph实例（用于访问模拟模式功能）
_graph_instance = None


def set_graph_instance(graph_instance):
    """设置graph实例，以便节点可以访问模拟模式功能"""
    global _graph_instance
    _graph_instance = graph_instance


def check_and_handle_mock_mode(node_name: str, state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """检查节点是否应该使用模拟模式，如果是则返回历史数据
    
    Args:
        node_name: 节点名称，如 'market_analyst', 'bull_researcher' 等
        state: 当前状态字典
        
    Returns:
        如果使用模拟模式，返回历史状态字典；否则返回None
    """
    global _graph_instance
    
    if not _graph_instance:
        return None
    
    # 检查是否应该使用模拟模式
    if not _graph_instance._should_use_mock_mode(node_name):
        return None
    
    # 获取股票代码和交易日期
    ticker = state.get('company_of_interest', '')
    trade_date = state.get('trade_date', '')
    
    if not ticker or not trade_date:
        logger.warning(f"⚠️ [模拟模式] 无法获取股票代码或日期，跳过模拟模式")
        return None
    
    # 提取分析ID（用于消息机制）
    analysis_id = state.get('analysis_id') or state.get('session_id')
    
    # 如果消息模式启用，发送模块开始消息
    if is_message_mode_enabled():
        producer = get_message_producer()
        if producer and analysis_id:
            _publish_progress_message(
                producer=producer,
                analysis_id=str(analysis_id),
                module_name=node_name,
                node_status=NodeStatus.START.value
            )
    
    # 记录模块开始（用于进度追踪）
    logger.info(f"📊 [模块开始] {node_name} - 股票: {ticker}")
    logger.info(f"🎭 [模拟模式] 节点 {node_name} 启用模拟模式")
    
    # 尝试加载历史输出
    historical_state = _graph_instance._load_historical_step_output(node_name, ticker, trade_date, state)
    
    # 记录开始时间（用于计算耗时）
    start_time = time.time()
    
    if historical_state:
        # 合并历史状态到当前状态（保留当前状态的基础信息）
        merged_state = state.copy()
        # 保存analysis_id和session_id，避免被历史数据覆盖
        preserved_analysis_id = state.get('analysis_id')
        preserved_session_id = state.get('session_id')
        merged_state.update(historical_state)
        # 恢复analysis_id和session_id
        if preserved_analysis_id is not None:
            merged_state['analysis_id'] = preserved_analysis_id
        if preserved_session_id is not None:
            merged_state['session_id'] = preserved_session_id
        
        # 模拟模式下也需要更新count值，以保持与真实执行一致的行为
        # 对于研究员节点（bull_researcher, bear_researcher），增加investment_debate_state的count
        if node_name in ['bull_researcher', 'bear_researcher']:
            if 'investment_debate_state' in merged_state and isinstance(merged_state['investment_debate_state'], dict):
                current_count = merged_state['investment_debate_state'].get('count', 0)
                merged_state['investment_debate_state']['count'] = current_count + 1
        
        # 对于风险分析师节点（risky_analyst, safe_analyst, neutral_analyst），增加risk_debate_state的count
        if node_name in ['risky_analyst', 'safe_analyst', 'neutral_analyst']:
            if 'risk_debate_state' in merged_state and isinstance(merged_state['risk_debate_state'], dict):
                current_count = merged_state['risk_debate_state'].get('count', 0)
                merged_state['risk_debate_state']['count'] = current_count + 1
        
        # 随机sleep 2-10秒
        sleep_time = random.uniform(
            _graph_instance.mock_sleep_min,
            _graph_instance.mock_sleep_max
        )
        logger.info(f"🎭 [模拟模式] 节点 {node_name} 使用历史数据，sleep {sleep_time:.2f} 秒")
        
        time.sleep(sleep_time)
        duration = time.time() - start_time
        
        # 如果消息模式启用，发送模块完成消息
        if is_message_mode_enabled():
            producer = get_message_producer()
            if producer and analysis_id:
                _publish_progress_message(
                    producer=producer,
                    analysis_id=str(analysis_id),
                    module_name=node_name,
                    node_status=NodeStatus.COMPLETE.value,
                    duration=duration
                )
        
        # 记录模块完成（用于进度追踪）
        logger.info(f"📊 [模块完成] {node_name} - 模拟模式完成 - 股票: {ticker}, 耗时: {duration:.2f}s")
        
        return merged_state
    else:
        # 如果没有找到历史数据，记录警告但继续正常执行
        # 注意：即使没有历史数据，也输出模块完成日志，确保进度追踪系统能检测到节点执行
        duration = time.time() - start_time
        
        # 如果消息模式启用，发送模块完成消息（即使没有历史数据）
        if is_message_mode_enabled():
            producer = get_message_producer()
            if producer and analysis_id:
                _publish_progress_message(
                    producer=producer,
                    analysis_id=str(analysis_id),
                    module_name=node_name,
                    node_status=NodeStatus.COMPLETE.value,
                    duration=duration
                )
        
        logger.warning(f"⚠️ [模拟模式] 节点 {node_name} 未找到历史数据，使用正常模式")
        logger.info(f"📊 [模块完成] {node_name} - 未找到历史数据，使用正常执行 - 股票: {ticker}")
        return None


def create_mock_mode_wrapper(node_func, node_name: str):
    """创建节点包装器，自动添加模拟模式检查
    
    Args:
        node_func: 原始节点函数
        node_name: 节点名称
        
    Returns:
        包装后的节点函数
    """
    def wrapped_node(state: Dict[str, Any]) -> Dict[str, Any]:
        # 检查模拟模式
        mock_result = check_and_handle_mock_mode(node_name, state)
        if mock_result is not None:
            return mock_result
        
        # 正常执行节点
        return node_func(state)
    
    return wrapped_node

