"""
任务状态显示组件
提供统一的任务状态卡片显示功能
"""

import streamlit as st
from typing import Optional


def render_task_status_card(status: str, analysis_id: Optional[str] = None, message: Optional[str] = None):
    """
    渲染任务状态卡片
    
    Args:
        status: 任务状态 ('running', 'paused', 'stopped', 'completed', 'failed')
        analysis_id: 分析ID（可选）
        message: 自定义消息（可选）
    """
    # 导入配置
    try:
        from config.report_constants import get_task_status_config
        config = get_task_status_config(status)
    except ImportError:
        # 如果导入失败，使用默认配置
        config = {
            'icon': '📊',
            'title': status.upper(),
            'gradient': 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            'message': message or ''
        }
    
    # 如果提供了analysis_id，格式化消息
    if analysis_id and '{}'in config.get('message', ''):
        display_message = config['message'].format(analysis_id[:16] + "...")
    elif message:
        display_message = message
    else:
        display_message = config.get('message', '')
    
    # 渲染状态卡片
    status_html = f"""
    <div style="background: {config['gradient']}; 
                padding: 1rem; border-radius: 10px; color: white; text-align: center;">
        <h4 style="margin: 0; color: white;">{config['icon']} {config['title']}</h4>
        <p style="margin: 0.5rem 0 0 0; font-size: 0.9rem;">{display_message}</p>
    </div>
    """
    
    st.markdown(status_html, unsafe_allow_html=True)


def render_progress_hint(status: str):
    """
    根据状态显示进度提示信息
    
    Args:
        status: 任务状态
    """
    hints = {
        'running': "⏱️ 分析正在进行中，可以使用下方的自动刷新功能查看进度更新...",
        'paused': "⏸️ 分析已暂停，点击【继续】按钮恢复分析...",
        'stopped': "⏹️ 分析已被停止",
        'completed': "✅ 分析完成，请查看下方报告",
        'failed': "❌ 分析失败，请查看错误信息"
    }
    
    hint = hints.get(status, f"📊 当前状态: {status}")
    
    if status == 'running':
        st.info(hint)
    elif status in ['paused', 'stopped', 'failed']:
        st.warning(hint) if status == 'paused' else st.error(hint)
    elif status == 'completed':
        st.success(hint)
    else:
        st.info(hint)


def render_task_control_buttons(analysis_id: str, actual_status: str, 
                                pause_callback, resume_callback, stop_callback):
    """
    渲染任务控制按钮
    
    Args:
        analysis_id: 分析ID
        actual_status: 实际任务状态
        pause_callback: 暂停回调函数
        resume_callback: 恢复回调函数
        stop_callback: 停止回调函数
    """
    if actual_status not in ['running', 'paused']:
        return
    
    st.markdown("---")
    st.markdown("### 🎮 任务控制")
    
    # 创建按钮列
    btn_col1, btn_col2, btn_col3 = st.columns(3)
    
    with btn_col1:
        if actual_status == 'running':
            if st.button("⏸️ 暂停分析", key=f"pause_btn_{analysis_id}", use_container_width=True):
                if pause_callback(analysis_id):
                    st.success("✅ 任务已暂停")
                    st.rerun()
                else:
                    st.error("❌ 暂停失败")
        elif actual_status == 'paused':
            if st.button("▶️ 继续分析", key=f"resume_btn_{analysis_id}", use_container_width=True):
                if resume_callback(analysis_id):
                    st.success("✅ 任务已恢复")
                    st.rerun()
                else:
                    st.error("❌ 恢复失败")
    
    with btn_col2:
        if st.button("⏹️ 停止分析", key=f"stop_btn_{analysis_id}", use_container_width=True):
            if stop_callback(analysis_id):
                st.success("✅ 任务已停止")
                st.rerun()
            else:
                st.error("❌ 停止失败")
    
    with btn_col3:
        # 预留空间或添加其他控制按钮
        pass

