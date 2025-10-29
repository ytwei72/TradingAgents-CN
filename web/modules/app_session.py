"""
应用会话管理模块
从 app.py 中提取的会话管理相关代码
"""

import streamlit as st
import time
from tradingagents.utils.logging_manager import get_logger

logger = get_logger('web.session')


def initialize_basic_session():
    """初始化基础会话状态"""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'user_info' not in st.session_state:
        st.session_state.user_info = None
    if 'login_time' not in st.session_state:
        st.session_state.login_time = None


def initialize_analysis_session():
    """初始化分析相关会话状态"""
    if 'analysis_results' not in st.session_state:
        st.session_state.analysis_results = None
    if 'analysis_running' not in st.session_state:
        st.session_state.analysis_running = False
    if 'last_analysis_time' not in st.session_state:
        st.session_state.last_analysis_time = None
    if 'current_analysis_id' not in st.session_state:
        st.session_state.current_analysis_id = None
    if 'form_config' not in st.session_state:
        st.session_state.form_config = None


def restore_analysis_results():
    """从最新完成的分析中恢复结果"""
    if st.session_state.analysis_results:
        return  # 已有结果，无需恢复
    
    try:
        from utils.async_progress_tracker import get_latest_analysis_id, get_progress_by_id
        from utils.analysis_runner import format_analysis_results
        
        latest_id = get_latest_analysis_id()
        if not latest_id:
            return
        
        progress_data = get_progress_by_id(latest_id)
        if not progress_data:
            return
        
        if (progress_data.get('status') == 'completed' and 
            'raw_results' in progress_data):
            
            # 恢复分析结果
            raw_results = progress_data['raw_results']
            formatted_results = format_analysis_results(raw_results)
            
            if formatted_results:
                st.session_state.analysis_results = formatted_results
                st.session_state.current_analysis_id = latest_id
                
                # 检查分析状态
                analysis_status = progress_data.get('status', 'completed')
                st.session_state.analysis_running = (analysis_status == 'running')
                
                # 恢复股票信息
                if 'stock_symbol' in raw_results:
                    st.session_state.last_stock_symbol = raw_results.get('stock_symbol', '')
                if 'market_type' in raw_results:
                    st.session_state.last_market_type = raw_results.get('market_type', '')
                
                logger.info(f"📊 [结果恢复] 从分析 {latest_id} 恢复结果，状态: {analysis_status}")
    
    except Exception as e:
        logger.warning(f"⚠️ [结果恢复] 恢复失败: {e}")


def restore_analysis_state():
    """使用cookie管理器恢复分析ID"""
    try:
        from utils.smart_session_manager import get_persistent_analysis_id
        from utils.thread_tracker import check_analysis_status
        
        persistent_analysis_id = get_persistent_analysis_id()
        if not persistent_analysis_id:
            return
        
        # 使用线程检测来检查分析状态
        actual_status = check_analysis_status(persistent_analysis_id)
        
        # 只在状态变化时记录日志，避免重复
        current_session_status = st.session_state.get('last_logged_status')
        if current_session_status != actual_status:
            logger.info(f"📊 [状态检查] 分析 {persistent_analysis_id} 实际状态: {actual_status}")
            st.session_state.last_logged_status = actual_status
        
        if actual_status == 'running':
            st.session_state.analysis_running = True
            st.session_state.current_analysis_id = persistent_analysis_id
        elif actual_status == 'paused':
            # 暂停状态：保留analysis_id，但标记为运行中（线程仍活跃）
            st.session_state.analysis_running = True
            st.session_state.current_analysis_id = persistent_analysis_id
        elif actual_status == 'stopped':
            # 停止状态：保留analysis_id，但标记为未运行
            st.session_state.analysis_running = False
            st.session_state.current_analysis_id = persistent_analysis_id
        elif actual_status in ['completed', 'failed']:
            st.session_state.analysis_running = False
            st.session_state.current_analysis_id = persistent_analysis_id
        else:  # not_found
            logger.warning(f"📊 [状态检查] 分析 {persistent_analysis_id} 未找到，清理状态")
            st.session_state.analysis_running = False
            st.session_state.current_analysis_id = None
    
    except Exception as e:
        logger.warning(f"⚠️ [状态恢复] 恢复分析状态失败: {e}")
        st.session_state.analysis_running = False
        st.session_state.current_analysis_id = None


def restore_form_config():
    """恢复表单配置"""
    try:
        from utils.smart_session_manager import smart_session_manager
        
        session_data = smart_session_manager.load_analysis_state()
        
        if session_data and 'form_config' in session_data:
            st.session_state.form_config = session_data['form_config']
            
            # 只在没有分析运行时记录日志，避免重复
            if not st.session_state.get('analysis_running', False):
                logger.info("📊 [配置恢复] 表单配置已恢复")
    
    except Exception as e:
        logger.warning(f"⚠️ [配置恢复] 表单配置恢复失败: {e}")


def initialize_session_state():
    """
    初始化所有会话状态
    这是从 app.py 中提取的 initialize_session_state() 函数
    """
    # 初始化基础会话
    initialize_basic_session()
    
    # 初始化分析相关会话
    initialize_analysis_session()
    
    # 恢复分析结果
    restore_analysis_results()
    
    # 恢复分析状态
    restore_analysis_state()
    
    # 恢复表单配置
    restore_form_config()


def clear_session_state():
    """清除会话状态"""
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    logger.info("🧹 会话状态已清除")


def get_session_info() -> dict:
    """
    获取会话信息摘要
    
    Returns:
        会话信息字典
    """
    return {
        'authenticated': st.session_state.get('authenticated', False),
        'analysis_running': st.session_state.get('analysis_running', False),
        'current_analysis_id': st.session_state.get('current_analysis_id'),
        'has_results': st.session_state.get('analysis_results') is not None,
        'has_form_config': st.session_state.get('form_config') is not None,
    }

