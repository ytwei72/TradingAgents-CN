"""
组件工具函数库
提供数据处理、格式化等共用工具函数
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, date
import logging

logger = logging.getLogger(__name__)


def format_number(value: Any, decimal_places: int = 2, suffix: str = "", prefix: str = "") -> str:
    """
    格式化数字显示
    
    Args:
        value: 数值
        decimal_places: 小数位数
        suffix: 后缀
        prefix: 前缀
        
    Returns:
        格式化后的字符串
    """
    try:
        num = float(value)
        formatted = f"{num:,.{decimal_places}f}"
        return f"{prefix}{formatted}{suffix}"
    except (ValueError, TypeError):
        return str(value)


def format_percentage(value: Any, decimal_places: int = 2) -> str:
    """
    格式化百分比
    
    Args:
        value: 数值
        decimal_places: 小数位数
        
    Returns:
        百分比字符串
    """
    return format_number(value, decimal_places, suffix="%")


def format_currency(value: Any, currency: str = "¥", decimal_places: int = 2) -> str:
    """
    格式化货币
    
    Args:
        value: 数值
        currency: 货币符号
        decimal_places: 小数位数
        
    Returns:
        货币字符串
    """
    return format_number(value, decimal_places, prefix=currency)


def format_date(value: Any, format_str: str = "%Y-%m-%d") -> str:
    """
    格式化日期
    
    Args:
        value: 日期值
        format_str: 格式字符串
        
    Returns:
        格式化后的日期字符串
    """
    try:
        if isinstance(value, str):
            dt = datetime.fromisoformat(value)
        elif isinstance(value, (datetime, date)):
            dt = value
        else:
            return str(value)
        return dt.strftime(format_str)
    except (ValueError, AttributeError):
        return str(value)


def safe_get(data: Dict, key: str, default: Any = "N/A") -> Any:
    """
    安全获取字典值
    
    Args:
        data: 字典数据
        key: 键名
        default: 默认值
        
    Returns:
        值或默认值
    """
    return data.get(key, default) if data else default


def safe_get_nested(data: Dict, keys: List[str], default: Any = "N/A") -> Any:
    """
    安全获取嵌套字典值
    
    Args:
        data: 字典数据
        keys: 键名列表，按嵌套顺序
        default: 默认值
        
    Returns:
        值或默认值
    """
    try:
        result = data
        for key in keys:
            result = result[key]
        return result
    except (KeyError, TypeError, AttributeError):
        return default


def get_display_name(key: str, name_map: Optional[Dict[str, str]] = None) -> str:
    """
    获取显示名称
    
    Args:
        key: 键名
        name_map: 名称映射字典
        
    Returns:
        显示名称
    """
    if name_map and key in name_map:
        return name_map[key]
    
    # 默认映射
    default_map = {
        'dashscope': '阿里百炼',
        'google': 'Google AI',
        'qianfan': '文心一言（千帆）',
        'openai': 'OpenAI',
        'anthropic': 'Anthropic',
        '美股': 'US Stock',
        'A股': 'A-Share',
        '港股': 'HK Stock',
    }
    
    return default_map.get(key, key)


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    截断文本
    
    Args:
        text: 文本内容
        max_length: 最大长度
        suffix: 后缀
        
    Returns:
        截断后的文本
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def extract_config_from_results(results: Dict[str, Any]) -> Dict[str, Any]:
    """
    从结果中提取配置信息
    
    Args:
        results: 分析结果
        
    Returns:
        配置字典
    """
    return {
        'stock_symbol': safe_get(results, 'stock_symbol'),
        'market_type': safe_get(results, 'market_type'),
        'llm_provider': safe_get(results, 'llm_provider'),
        'llm_model': safe_get(results, 'llm_model'),
        'research_depth': safe_get(results, 'research_depth'),
        'analysis_date': safe_get(results, 'analysis_date'),
    }


def parse_decision_recommendation(decision: Dict[str, Any]) -> str:
    """
    解析投资决策建议
    
    Args:
        decision: 决策字典
        
    Returns:
        决策建议文本
    """
    recommendation = safe_get(decision, 'recommendation', '暂无建议')
    confidence = safe_get(decision, 'confidence', 'N/A')
    
    if confidence != 'N/A':
        return f"{recommendation} (置信度: {confidence})"
    return recommendation


def get_risk_level_color(risk_level: str) -> str:
    """
    获取风险等级对应的颜色
    
    Args:
        risk_level: 风险等级
        
    Returns:
        颜色代码
    """
    color_map = {
        '低': 'green',
        '中': 'orange',
        '高': 'red',
        'low': 'green',
        'medium': 'orange',
        'high': 'red',
    }
    return color_map.get(risk_level.lower(), 'gray')


def validate_stock_symbol(symbol: str, market_type: str) -> tuple[bool, str]:
    """
    验证股票代码格式
    
    Args:
        symbol: 股票代码
        market_type: 市场类型
        
    Returns:
        (是否有效, 错误消息)
    """
    if not symbol or not symbol.strip():
        return False, "股票代码不能为空"
    
    symbol = symbol.strip()
    
    if market_type == "A股":
        if not (len(symbol) == 6 and symbol.isdigit()):
            return False, "A股代码应为6位数字"
    elif market_type == "美股":
        if not symbol.replace('.', '').isalnum():
            return False, "美股代码格式不正确"
    elif market_type == "港股":
        if not (symbol.endswith('.HK') or symbol.endswith('.hk')):
            return False, "港股代码应以.HK结尾"
    
    return True, ""


def calculate_metrics_delta(current: float, previous: float) -> Optional[float]:
    """
    计算指标变化
    
    Args:
        current: 当前值
        previous: 之前值
        
    Returns:
        变化百分比
    """
    try:
        if previous == 0:
            return None
        return ((current - previous) / previous) * 100
    except (TypeError, ZeroDivisionError):
        return None


def group_by_category(items: List[Dict], category_key: str) -> Dict[str, List[Dict]]:
    """
    按类别分组
    
    Args:
        items: 项目列表
        category_key: 类别键名
        
    Returns:
        分组后的字典
    """
    grouped = {}
    for item in items:
        category = item.get(category_key, '未分类')
        if category not in grouped:
            grouped[category] = []
        grouped[category].append(item)
    return grouped


def filter_empty_values(data: Dict) -> Dict:
    """
    过滤空值
    
    Args:
        data: 数据字典
        
    Returns:
        过滤后的字典
    """
    return {k: v for k, v in data.items() if v not in (None, '', 'N/A', [])}


def merge_configs(*configs: Dict) -> Dict:
    """
    合并多个配置字典
    
    Args:
        configs: 配置字典列表
        
    Returns:
        合并后的配置
    """
    result = {}
    for config in configs:
        if config:
            result.update(config)
    return result


def log_component_action(component: str, action: str, details: Optional[Dict] = None):
    """
    记录组件操作日志
    
    Args:
        component: 组件名称
        action: 操作类型
        details: 详细信息
    """
    log_msg = f"[{component}] {action}"
    if details:
        log_msg += f" - {details}"
    logger.info(log_msg)

