"""
分析表单模块
将表单相关的大段代码拆分为可复用的小模块
"""

import streamlit as st
import datetime
from typing import Dict, Any, List, Tuple
from components.component_utils import safe_get, validate_stock_symbol
from components.ui_components import render_info_box


def get_market_stock_input_config(market_type: str) -> Dict[str, str]:
    """
    获取不同市场的股票输入配置
    
    Args:
        market_type: 市场类型
        
    Returns:
        配置字典 {placeholder, help, key}
    """
    configs = {
        "美股": {
            "placeholder": "输入美股代码，如 AAPL, TSLA, MSFT，然后按回车确认",
            "help": "输入要分析的美股代码，输入完成后请按回车键确认",
            "key": "us_stock_input",
            "transform": lambda x: x.upper().strip()
        },
        "港股": {
            "placeholder": "输入港股代码，如 0700.HK, 9988.HK, 3690.HK，然后按回车确认",
            "help": "输入要分析的港股代码，如 0700.HK(腾讯控股), 9988.HK(阿里巴巴), 3690.HK(美团)，输入完成后请按回车键确认",
            "key": "hk_stock_input",
            "transform": lambda x: x.upper().strip()
        },
        "A股": {
            "placeholder": "输入A股代码，如 000001, 600519，然后按回车确认",
            "help": "输入要分析的A股代码，如 000001(平安银行), 600519(贵州茅台)，输入完成后请按回车键确认",
            "key": "cn_stock_input",
            "transform": lambda x: x.strip()
        }
    }
    return configs.get(market_type, configs["A股"])


def render_stock_input(market_type: str, cached_value: str = "", cached_market: str = "") -> str:
    """
    渲染股票代码输入框
    
    Args:
        market_type: 当前市场类型
        cached_value: 缓存的股票代码
        cached_market: 缓存的市场类型
        
    Returns:
        输入的股票代码
    """
    config = get_market_stock_input_config(market_type)
    
    # 只有当前市场类型与缓存市场类型一致时才使用缓存值
    value = cached_value if cached_market == market_type else ''
    
    stock_symbol = st.text_input(
        "股票代码 📈",
        value=value,
        placeholder=config['placeholder'],
        help=config['help'],
        key=config['key'],
        autocomplete="off"
    )
    
    # 应用转换（大写/去空格等）
    return config['transform'](stock_symbol)


def get_research_depth_label(depth: int) -> str:
    """
    获取研究深度标签
    
    Args:
        depth: 深度级别
        
    Returns:
        标签文本
    """
    labels = {
        1: "1级 - 快速分析",
        2: "2级 - 基础分析",
        3: "3级 - 标准分析",
        4: "4级 - 深度分析",
        5: "5级 - 全面分析"
    }
    return labels.get(depth, f"{depth}级")


def get_default_analysts(market_type: str) -> List[str]:
    """
    获取默认的分析师列表
    
    Args:
        market_type: 市场类型
        
    Returns:
        分析师ID列表
    """
    # A股市场默认不包含社交媒体分析师
    base_analysts = ['market', 'fundamentals']
    
    if market_type != "A股":
        base_analysts.append('social')
    
    return base_analysts


def adjust_analysts_for_market(analysts: List[str], market_type: str) -> List[str]:
    """
    根据市场类型调整分析师列表
    
    Args:
        analysts: 当前分析师列表
        market_type: 市场类型
        
    Returns:
        调整后的分析师列表
    """
    if market_type == "A股":
        # A股市场：移除社交媒体分析师
        adjusted = [a for a in analysts if a != 'social']
    else:
        # 非A股市场：保留所有分析师
        adjusted = analysts.copy()
    
    # 确保至少有默认分析师
    if len(adjusted) == 0:
        adjusted = get_default_analysts(market_type)
    
    return adjusted


def get_analyst_info() -> Dict[str, Dict[str, str]]:
    """
    获取分析师信息
    
    Returns:
        分析师信息字典 {id: {name, icon, help}}
    """
    return {
        'market': {
            'name': '市场分析师',
            'icon': '📈',
            'help': '专注于技术面分析、价格趋势、技术指标'
        },
        'fundamentals': {
            'name': '基本面分析师',
            'icon': '💰',
            'help': '分析财务数据、公司基本面、估值指标'
        },
        'news': {
            'name': '新闻分析师',
            'icon': '📰',
            'help': '分析新闻事件、市场情绪、舆论影响'
        },
        'social': {
            'name': '社交媒体分析师',
            'icon': '💭',
            'help': '分析社交媒体讨论、投资者情绪（仅美股/港股）'
        },
        'risk': {
            'name': '风险评估师',
            'icon': '⚠️',
            'help': '评估投资风险、给出风险提示'
        }
    }


def render_analyst_selection(
    cached_analysts: List[str],
    market_type: str,
    cached_market_type: str
) -> List[str]:
    """
    渲染分析师选择组件
    
    Args:
        cached_analysts: 缓存的分析师列表
        market_type: 当前市场类型
        cached_market_type: 缓存的市场类型
        
    Returns:
        选中的分析师列表
    """
    st.markdown("### 👥 选择分析师团队")
    
    # 如果市场类型改变，调整分析师列表
    if cached_market_type != market_type:
        cached_analysts = adjust_analysts_for_market(cached_analysts, market_type)
    
    analyst_info = get_analyst_info()
    selected_analysts = []
    
    col1, col2 = st.columns(2)
    
    # 第一列
    with col1:
        for analyst_id in ['market', 'fundamentals', 'news']:
            info = analyst_info[analyst_id]
            if st.checkbox(
                f"{info['icon']} {info['name']}",
                value=analyst_id in cached_analysts,
                help=info['help']
            ):
                selected_analysts.append(analyst_id)
    
    # 第二列
    with col2:
        # 社交媒体分析师（仅非A股市场）
        if market_type != "A股":
            info = analyst_info['social']
            if st.checkbox(
                f"{info['icon']} {info['name']}",
                value='social' in cached_analysts,
                help=info['help']
            ):
                selected_analysts.append('social')
        else:
            st.info("💡 社交媒体分析师仅支持美股和港股")
        
        # 风险评估师
        info = analyst_info['risk']
        if st.checkbox(
            f"{info['icon']} {info['name']}",
            value='risk' in cached_analysts,
            help=info['help']
        ):
            selected_analysts.append('risk')
    
    return selected_analysts


def validate_form_inputs(
    stock_symbol: str,
    market_type: str,
    selected_analysts: List[str]
) -> Tuple[bool, str]:
    """
    验证表单输入
    
    Args:
        stock_symbol: 股票代码
        market_type: 市场类型
        selected_analysts: 选中的分析师
        
    Returns:
        (是否有效, 错误消息)
    """
    # 验证股票代码
    if not stock_symbol:
        return False, "请输入股票代码"
    
    is_valid, error_msg = validate_stock_symbol(stock_symbol, market_type)
    if not is_valid:
        return False, error_msg
    
    # 验证分析师选择
    if not selected_analysts:
        return False, "请至少选择一位分析师"
    
    return True, ""


def build_form_config(
    stock_symbol: str,
    market_type: str,
    analysis_date: datetime.date,
    research_depth: int,
    selected_analysts: List[str]
) -> Dict[str, Any]:
    """
    构建表单配置字典
    
    Args:
        stock_symbol: 股票代码
        market_type: 市场类型
        analysis_date: 分析日期
        research_depth: 研究深度
        selected_analysts: 选中的分析师
        
    Returns:
        配置字典
    """
    return {
        'stock_symbol': stock_symbol,
        'market_type': market_type,
        'analysis_date': analysis_date.strftime('%Y-%m-%d'),
        'research_depth': research_depth,
        'selected_analysts': selected_analysts
    }


def show_form_validation_error(error_msg: str):
    """
    显示表单验证错误
    
    Args:
        error_msg: 错误消息
    """
    render_info_box(f"⚠️ {error_msg}", box_type="warning")


def show_analysis_running_message():
    """显示分析正在运行的消息"""
    render_info_box(
        "📊 分析正在进行中，请在下方查看进度...",
        box_type="info"
    )


def show_form_tips():
    """显示表单使用提示"""
    with st.expander("💡 使用提示", expanded=False):
        st.markdown("""
        **如何使用分析表单：**
        
        1. **选择市场**：选择要分析的股票市场（美股、A股或港股）
        2. **输入代码**：输入股票代码，不同市场格式不同
           - 美股：如 AAPL, TSLA, MSFT
           - A股：如 000001, 600519（6位数字）
           - 港股：如 0700.HK, 9988.HK
        3. **选择深度**：选择分析深度，级别越高分析越详细
        4. **选择分析师**：选择需要的分析师，建议至少选择2位
        5. **开始分析**：点击"开始分析"按钮
        
        **注意事项：**
        - 分析可能需要几分钟时间
        - 更高的分析深度需要更长时间
        - 社交媒体分析师仅支持美股和港股
        """)

