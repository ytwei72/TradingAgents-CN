"""
消息装饰器 - 替代日志装饰器
"""

import functools
import time
from typing import Callable, Any, Dict, Optional

from tradingagents.utils.logging_manager import get_logger
from ..config import get_message_producer, is_message_mode_enabled
from ..business.messages import ModuleEvent

logger = get_logger('messaging.decorators')


def _extract_analysis_id(*args, **kwargs) -> Optional[str]:
    """从参数中提取分析ID"""
    # 尝试从state字典中获取
    if args:
        first_arg = args[0]
        if isinstance(first_arg, dict):
            # 可能包含analysis_id或session_id
            return first_arg.get('analysis_id') or first_arg.get('session_id')
    
    # 从kwargs中查找
    for key in ['analysis_id', 'session_id', 'task_id']:
        if key in kwargs:
            return str(kwargs[key])
    
    return None


def _extract_stock_symbol(*args, **kwargs) -> Optional[str]:
    """从参数中提取股票代码（与log_analysis_module保持一致的逻辑）"""
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


def message_analysis_module(module_name: str, session_id: str = None):
    """消息版分析模块装饰器
    
    自动发送模块开始/完成/错误消息，替代日志关键字识别方式。
    如果消息模式未启用，会回退到日志模式（兼容性）。
    
    Args:
        module_name: 模块名称（如：market_analyst、fundamentals_analyst等）
        session_id: 会话ID（可选）
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 提取分析ID和股票代码
            analysis_id = _extract_analysis_id(*args, **kwargs) or session_id
            stock_symbol = _extract_stock_symbol(*args, **kwargs)
            
            # 如果消息模式启用，使用消息机制
            if is_message_mode_enabled():
                producer = get_message_producer()
                if producer:
                    # 发送模块开始消息
                    producer.publish_module_start(
                        analysis_id=analysis_id or f"session_{int(time.time())}",
                        module_name=module_name,
                        stock_symbol=stock_symbol,
                        function_name=func.__name__
                    )
                    
                    start_time = time.time()
                    try:
                        # 执行分析函数
                        result = func(*args, **kwargs)
                        
                        # 计算执行时间
                        duration = time.time() - start_time
                        
                        # 发送模块完成消息
                        producer.publish_module_complete(
                            analysis_id=analysis_id or f"session_{int(time.time())}",
                            module_name=module_name,
                            duration=duration,
                            stock_symbol=stock_symbol,
                            function_name=func.__name__
                        )
                        
                        return result
                    except Exception as e:
                        # 计算执行时间
                        duration = time.time() - start_time
                        
                        # 发送模块错误消息
                        producer.publish_module_error(
                            analysis_id=analysis_id or f"session_{int(time.time())}",
                            module_name=module_name,
                            error_message=str(e),
                            stock_symbol=stock_symbol
                        )
                        
                        # 重新抛出异常
                        raise
                else:
                    logger.warning("消息生产者未初始化，回退到日志模式")
                    # 回退到日志模式
                    return _fallback_to_logging(func, module_name, session_id, *args, **kwargs)
            else:
                # 消息模式未启用，使用日志模式（兼容性）
                return _fallback_to_logging(func, module_name, session_id, *args, **kwargs)
        
        return wrapper
    return decorator


def _fallback_to_logging(func: Callable, module_name: str, session_id: Optional[str],
                        *args, **kwargs):
    """回退到日志模式（兼容性）"""
    # 导入日志装饰器
    from tradingagents.utils.tool_logging import log_analysis_module
    
    # 使用日志装饰器包装函数（临时）
    decorated_func = log_analysis_module(module_name, session_id)(func)
    return decorated_func(*args, **kwargs)

