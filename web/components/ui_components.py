"""
共用UI组件库
提供可复用的UI组件，避免重复代码
"""

import streamlit as st
from typing import Optional, Dict, Any, List, Tuple


def render_card(title: str, content: str, icon: str = "", card_type: str = "default"):
    """
    渲染卡片组件
    
    Args:
        title: 卡片标题
        content: 卡片内容
        icon: 图标emoji
        card_type: 卡片类型 (default, success, warning, error, info)
    """
    card_class = {
        "default": "metric-card",
        "success": "success-box",
        "warning": "warning-box",
        "error": "error-box",
        "info": "info-box"
    }.get(card_type, "metric-card")
    
    title_with_icon = f"{icon} {title}" if icon else title
    
    st.markdown(f"""
    <div class="{card_class}">
        <h4>{title_with_icon}</h4>
        <p>{content}</p>
    </div>
    """, unsafe_allow_html=True)


def render_metric_row(metrics: List[Dict[str, Any]], columns: int = 3):
    """
    渲染指标行
    
    Args:
        metrics: 指标列表，每个指标包含 label, value, delta, help
        columns: 列数
    """
    cols = st.columns(columns)
    for idx, metric in enumerate(metrics):
        with cols[idx % columns]:
            st.metric(
                label=metric.get('label', ''),
                value=metric.get('value', 'N/A'),
                delta=metric.get('delta'),
                help=metric.get('help')
            )


def render_section_header(title: str, icon: str = "", expanded: bool = True):
    """
    渲染带展开器的章节标题
    
    Args:
        title: 标题文本
        icon: 图标emoji
        expanded: 是否默认展开
        
    Returns:
        展开器上下文管理器
    """
    title_with_icon = f"{icon} {title}" if icon else title
    return st.expander(title_with_icon, expanded=expanded)


def render_info_box(message: str, box_type: str = "info", icon: str = ""):
    """
    渲染信息提示框
    
    Args:
        message: 提示信息
        box_type: 类型 (info, success, warning, error)
        icon: 图标emoji
    """
    icons = {
        "info": "ℹ️",
        "success": "✅",
        "warning": "⚠️",
        "error": "❌"
    }
    
    display_icon = icon if icon else icons.get(box_type, "ℹ️")
    message_with_icon = f"{display_icon} {message}"
    
    box_funcs = {
        "info": st.info,
        "success": st.success,
        "warning": st.warning,
        "error": st.error
    }
    
    box_func = box_funcs.get(box_type, st.info)
    box_func(message_with_icon)


def render_key_value_table(data: Dict[str, Any], title: str = "", columns: int = 2):
    """
    渲染键值对表格
    
    Args:
        data: 键值对数据
        title: 表格标题
        columns: 列数
    """
    if title:
        st.markdown(f"**{title}**")
    
    cols = st.columns(columns)
    items = list(data.items())
    
    for idx, (key, value) in enumerate(items):
        with cols[idx % columns]:
            st.markdown(f"**{key}:** {value}")


def render_progress_indicator(current: int, total: int, label: str = ""):
    """
    渲染进度指示器
    
    Args:
        current: 当前进度
        total: 总数
        label: 标签文本
    """
    progress = current / total if total > 0 else 0
    st.progress(progress)
    if label:
        st.caption(f"{label}: {current}/{total} ({progress*100:.1f}%)")


def render_status_badge(status: str, status_map: Optional[Dict[str, Tuple[str, str]]] = None):
    """
    渲染状态徽章
    
    Args:
        status: 状态值
        status_map: 状态映射 {status: (label, color)}
    """
    default_map = {
        "success": ("成功", "green"),
        "running": ("运行中", "blue"),
        "pending": ("等待中", "orange"),
        "failed": ("失败", "red"),
        "completed": ("已完成", "green"),
        "cancelled": ("已取消", "gray")
    }
    
    mapping = status_map if status_map else default_map
    label, color = mapping.get(status, (status, "gray"))
    
    st.markdown(f"""
    <span style="background-color: {color}; color: white; padding: 0.2rem 0.6rem; 
                 border-radius: 12px; font-size: 0.85rem; font-weight: 500;">
        {label}
    </span>
    """, unsafe_allow_html=True)


def render_divider(text: str = "", margin: str = "1rem 0"):
    """
    渲染分隔线
    
    Args:
        text: 分隔线文本
        margin: 外边距
    """
    if text:
        st.markdown(f"""
        <div style="margin: {margin}; text-align: center; position: relative;">
            <hr style="border: none; border-top: 1px solid #e0e0e0;"/>
            <span style="position: absolute; top: -0.6rem; left: 50%; transform: translateX(-50%);
                         background: white; padding: 0 1rem; color: #666; font-size: 0.9rem;">
                {text}
            </span>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("---")


def render_collapsible_code(code: str, language: str = "python", title: str = "查看代码"):
    """
    渲染可折叠的代码块
    
    Args:
        code: 代码内容
        language: 代码语言
        title: 标题
    """
    with st.expander(title, expanded=False):
        st.code(code, language=language)


def render_data_table(data: Any, title: str = "", use_container_width: bool = True):
    """
    渲染数据表格
    
    Args:
        data: 数据（DataFrame或字典）
        title: 表格标题
        use_container_width: 是否使用容器宽度
    """
    if title:
        st.markdown(f"**{title}**")
    
    st.dataframe(data, use_container_width=use_container_width)


def render_tabs(tab_config: List[Dict[str, Any]]):
    """
    渲染标签页组件
    
    Args:
        tab_config: 标签配置列表 [{"title": "标签1", "content": callable}, ...]
    """
    tab_titles = [config['title'] for config in tab_config]
    tabs = st.tabs(tab_titles)
    
    for idx, tab in enumerate(tabs):
        with tab:
            content_func = tab_config[idx].get('content')
            if callable(content_func):
                content_func()
            elif content_func is not None:
                st.write(content_func)


def render_empty_state(message: str, icon: str = "📭", action_button: Optional[Dict[str, Any]] = None):
    """
    渲染空状态页面
    
    Args:
        message: 提示消息
        icon: 图标emoji
        action_button: 操作按钮配置 {"label": "按钮文本", "callback": callable}
    """
    st.markdown(f"""
    <div style="text-align: center; padding: 3rem 1rem; color: #666;">
        <div style="font-size: 4rem; margin-bottom: 1rem;">{icon}</div>
        <div style="font-size: 1.2rem; margin-bottom: 2rem;">{message}</div>
    </div>
    """, unsafe_allow_html=True)
    
    if action_button:
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            if st.button(action_button['label'], use_container_width=True):
                if callable(action_button.get('callback')):
                    action_button['callback']()


def render_loading_spinner(text: str = "加载中..."):
    """
    渲染加载动画
    
    Args:
        text: 加载文本
        
    Returns:
        spinner上下文管理器
    """
    return st.spinner(text)

