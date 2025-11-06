#!/usr/bin/env python3
"""
工具调用日志装饰器
为所有工具调用添加统一的日志记录
"""

import time
import functools
from typing import Any, Dict, Optional, Callable
from datetime import datetime

from tradingagents.utils.logging_init import get_logger

# 导入日志模块
from tradingagents.utils.logging_manager import get_logger, get_logger_manager
logger = get_logger('agents')

# 工具调用日志器
tool_logger = get_logger("tools")


def log_tool_call(tool_name: Optional[str] = None, log_args: bool = True, log_result: bool = False):
    """
    工具调用日志装饰器
    
    Args:
        tool_name: 工具名称，如果不提供则使用函数名
        log_args: 是否记录参数
        log_result: 是否记录返回结果（注意：可能包含大量数据）
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 确定工具名称
            name = tool_name or getattr(func, '__name__', 'unknown_tool')
            
            # 记录开始时间
            start_time = time.time()
            
            # 准备参数信息
            args_info = {}
            if log_args:
                # 记录位置参数
                if args:
                    args_info['args'] = [str(arg)[:100] + '...' if len(str(arg)) > 100 else str(arg) for arg in args]
                
                # 记录关键字参数
                if kwargs:
                    args_info['kwargs'] = {
                        k: str(v)[:100] + '...' if len(str(v)) > 100 else str(v) 
                        for k, v in kwargs.items()
                    }
            
            # 记录工具调用开始
            tool_logger.info(
                f"🔧 [工具调用] {name} - 开始",
                extra={
                    'tool_name': name,
                    'event_type': 'tool_call_start',
                    'timestamp': datetime.now().isoformat(),
                    'args_info': args_info if log_args else None
                }
            )
            
            try:
                # 执行工具函数
                result = func(*args, **kwargs)
                
                # 计算执行时间
                duration = time.time() - start_time
                
                # 准备结果信息
                result_info = None
                if log_result and result is not None:
                    result_str = str(result)
                    result_info = result_str[:200] + '...' if len(result_str) > 200 else result_str
                
                # 记录工具调用成功
                tool_logger.info(
                    f"✅ [工具调用] {name} - 完成 (耗时: {duration:.2f}s)",
                    extra={
                        'tool_name': name,
                        'event_type': 'tool_call_success',
                        'duration': duration,
                        'result_info': result_info if log_result else None,
                        'timestamp': datetime.now().isoformat()
                    }
                )
                
                return result
                
            except Exception as e:
                # 计算执行时间
                duration = time.time() - start_time
                
                # 记录工具调用失败
                tool_logger.error(
                    f"❌ [工具调用] {name} - 失败 (耗时: {duration:.2f}s): {str(e)}",
                    extra={
                        'tool_name': name,
                        'event_type': 'tool_call_error',
                        'duration': duration,
                        'error': str(e),
                        'timestamp': datetime.now().isoformat()
                    },
                    exc_info=True
                )
                
                # 重新抛出异常
                raise
        
        return wrapper
    return decorator


def log_data_source_call(source_name: str):
    """
    数据源调用专用日志装饰器
    
    Args:
        source_name: 数据源名称（如：tushare、akshare、yfinance等）
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            # 提取股票代码（通常是第一个参数）
            symbol = args[0] if args else kwargs.get('symbol', kwargs.get('ticker', 'unknown'))
            
            # 记录数据源调用开始
            tool_logger.info(
                f"📊 [数据源] {source_name} - 获取 {symbol} 数据",
                extra={
                    'data_source': source_name,
                    'symbol': symbol,
                    'event_type': 'data_source_call',
                    'timestamp': datetime.now().isoformat()
                }
            )
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                # 检查结果是否成功
                success = result and "❌" not in str(result) and "错误" not in str(result)
                
                if success:
                    tool_logger.info(
                        f"✅ [数据源] {source_name} - {symbol} 数据获取成功 (耗时: {duration:.2f}s)",
                        extra={
                            'data_source': source_name,
                            'symbol': symbol,
                            'event_type': 'data_source_success',
                            'duration': duration,
                            'data_size': len(str(result)) if result else 0,
                            'timestamp': datetime.now().isoformat()
                        }
                    )
                else:
                    tool_logger.warning(
                        f"⚠️ [数据源] {source_name} - {symbol} 数据获取失败 (耗时: {duration:.2f}s)",
                        extra={
                            'data_source': source_name,
                            'symbol': symbol,
                            'event_type': 'data_source_failure',
                            'duration': duration,
                            'timestamp': datetime.now().isoformat()
                        }
                    )
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                
                tool_logger.error(
                    f"❌ [数据源] {source_name} - {symbol} 数据获取异常 (耗时: {duration:.2f}s): {str(e)}",
                    extra={
                        'data_source': source_name,
                        'symbol': symbol,
                        'event_type': 'data_source_error',
                        'duration': duration,
                        'error': str(e),
                        'timestamp': datetime.now().isoformat()
                    },
                    exc_info=True
                )
                
                raise
        
        return wrapper
    return decorator


def log_llm_call(provider: str, model: str):
    """
    LLM调用专用日志装饰器
    
    Args:
        provider: LLM提供商（如：openai、deepseek、tongyi等）
        model: 模型名称
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            # 记录LLM调用开始
            tool_logger.info(
                f"🤖 [LLM调用] {provider}/{model} - 开始",
                extra={
                    'llm_provider': provider,
                    'llm_model': model,
                    'event_type': 'llm_call_start',
                    'timestamp': datetime.now().isoformat()
                }
            )
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                tool_logger.info(
                    f"✅ [LLM调用] {provider}/{model} - 完成 (耗时: {duration:.2f}s)",
                    extra={
                        'llm_provider': provider,
                        'llm_model': model,
                        'event_type': 'llm_call_success',
                        'duration': duration,
                        'timestamp': datetime.now().isoformat()
                    }
                )
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                
                tool_logger.error(
                    f"❌ [LLM调用] {provider}/{model} - 失败 (耗时: {duration:.2f}s): {str(e)}",
                    extra={
                        'llm_provider': provider,
                        'llm_model': model,
                        'event_type': 'llm_call_error',
                        'duration': duration,
                        'error': str(e),
                        'timestamp': datetime.now().isoformat()
                    },
                    exc_info=True
                )
                
                raise
        
        return wrapper
    return decorator


# 便捷函数
def log_tool_usage(tool_name: str, symbol: str = None, **extra_data):
    """
    记录工具使用情况的便捷函数
    
    Args:
        tool_name: 工具名称
        symbol: 股票代码（可选）
        **extra_data: 额外的数据
    """
    extra = {
        'tool_name': tool_name,
        'event_type': 'tool_usage',
        'timestamp': datetime.now().isoformat(),
        **extra_data
    }
    
    if symbol:
        extra['symbol'] = symbol
    
    tool_logger.info(f"📋 [工具使用] {tool_name}", extra=extra)


def log_analysis_step(step_name: str, symbol: str, **extra_data):
    """
    记录分析步骤的便捷函数

    Args:
        step_name: 步骤名称
        symbol: 股票代码
        **extra_data: 额外的数据
    """
    extra = {
        'step_name': step_name,
        'symbol': symbol,
        'event_type': 'analysis_step',
        'timestamp': datetime.now().isoformat(),
        **extra_data
    }

    tool_logger.info(f"📈 [分析步骤] {step_name} - {symbol}", extra=extra)

