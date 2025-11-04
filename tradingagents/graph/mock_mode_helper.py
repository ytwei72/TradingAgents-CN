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
logger = get_logger('agents')

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
    
    logger.info(f"🎭 [模拟模式] 节点 {node_name} 启用模拟模式")
    
    # 获取股票代码和交易日期
    ticker = state.get('company_of_interest', '')
    trade_date = state.get('trade_date', '')
    
    if not ticker or not trade_date:
        logger.warning(f"⚠️ [模拟模式] 无法获取股票代码或日期，跳过模拟模式")
        return None
    
    # 尝试加载历史输出
    historical_state = _graph_instance._load_historical_step_output(node_name, ticker, trade_date)
    
    if historical_state:
        # 合并历史状态到当前状态（保留当前状态的基础信息）
        merged_state = state.copy()
        merged_state.update(historical_state)
        
        # 随机sleep 2-10秒
        sleep_time = random.uniform(
            _graph_instance.mock_sleep_min,
            _graph_instance.mock_sleep_max
        )
        logger.info(f"🎭 [模拟模式] 节点 {node_name} 使用历史数据，sleep {sleep_time:.2f} 秒")
        time.sleep(sleep_time)
        
        return merged_state
    else:
        # 如果没有找到历史数据，记录警告但继续正常执行
        logger.warning(f"⚠️ [模拟模式] 节点 {node_name} 未找到历史数据，使用正常模式")
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

