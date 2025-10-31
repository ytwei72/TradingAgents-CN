"""
会话初始化工具
处理会话状态的初始化、恢复等功能
"""

import streamlit as st
import time
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def initialize_session_state():
    """
    初始化会话状态
    设置所有必需的session state变量
    """
    # 初始化认证相关状态
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'user_info' not in st.session_state:
        st.session_state.user_info = None
    if 'login_time' not in st.session_state:
        st.session_state.login_time = None
    
    # 初始化分析相关状态
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

    # 尝试从最新完成的分析中恢复结果
    _restore_latest_analysis_results()
    
    # 恢复分析ID和状态
    _restore_analysis_state()
    
    # 恢复表单配置
    _restore_form_config()


def _restore_latest_analysis_results():
    """从最新完成的分析中恢复结果"""
    if st.session_state.analysis_results:
        return  # 已经有结果，无需恢复
    
    try:
        from utils.async_progress_tracker import get_latest_analysis_id, get_progress_by_id
        from utils.analysis_runner import format_analysis_results

        latest_id = get_latest_analysis_id()
        if not latest_id:
            return
        
        progress_data = get_progress_by_id(latest_id)
        if (not progress_data or 
            progress_data.get('status') != 'completed' or
            'raw_results' not in progress_data):
            return

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


def _restore_analysis_state():
    """恢复分析ID和状态"""
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

        # 根据状态更新session state
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


def _restore_form_config():
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


def sync_auth_state(auth_manager):
    """
    同步认证状态
    确保session state和auth_manager的状态一致
    
    Args:
        auth_manager: 认证管理器实例
    """
    if not st.session_state.get('authenticated', False):
        return
    
    # 确保auth_manager也知道用户已认证
    if not auth_manager.is_authenticated() and st.session_state.get('user_info'):
        logger.debug("🔄 同步认证状态到auth_manager")
        try:
            auth_manager.login_user(
                st.session_state.user_info, 
                st.session_state.get('login_time', time.time())
            )
            logger.debug("✅ 认证状态同步成功")
        except Exception as e:
            logger.warning(f"⚠️ 认证状态同步失败: {e}")
    else:
        logger.debug("✅ 用户已认证，跳过缓存检查")


def restore_from_session_state(auth_manager):
    """
    最后一次尝试从session state恢复认证状态
    
    Args:
        auth_manager: 认证管理器实例
        
    Returns:
        是否成功恢复
    """
    if (st.session_state.get('authenticated', False) and 
        st.session_state.get('user_info') and 
        st.session_state.get('login_time')):
        
        logger.info("🔄 从session state恢复认证状态")
        try:
            auth_manager.login_user(
                st.session_state.user_info, 
                st.session_state.login_time
            )
            logger.info(f"✅ 成功从session state恢复用户 {st.session_state.user_info.get('username', 'Unknown')} 的认证状态")
            return True
        except Exception as e:
            logger.warning(f"⚠️ 从session state恢复认证状态失败: {e}")
            return False
    
    return False


def cleanup_zombie_analysis_state():
    """
    清理僵尸分析状态
    用于解决页面持续刷新等问题
    """
    # 清理session state
    st.session_state.analysis_running = False
    st.session_state.current_analysis_id = None
    st.session_state.analysis_results = None

    # 清理所有自动刷新状态
    keys_to_remove = []
    for key in st.session_state.keys():
        if 'auto_refresh' in key:
            keys_to_remove.append(key)

    for key in keys_to_remove:
        del st.session_state[key]

    # 清理死亡线程
    try:
        from utils.thread_tracker import cleanup_dead_analysis_threads
        cleanup_dead_analysis_threads()
        logger.info("✅ 分析状态已清理")
    except Exception as e:
        logger.warning(f"⚠️ 清理死亡线程失败: {e}")

