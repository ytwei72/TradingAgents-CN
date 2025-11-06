#!/usr/bin/env python3
"""
异步进度显示组件
支持定时刷新，从Redis或文件获取进度状态
支持消息驱动的实时更新（如果消息模式启用）
"""

import streamlit as st
import time
import html
from typing import Optional, Dict, Any
from web.utils.async_progress_tracker import get_progress_by_id, format_time

# 导入日志模块
from tradingagents.utils.logging_manager import get_logger
logger = get_logger('async_display')

# 导入消息订阅组件
try:
    from web.components.message_subscriber import (
        is_message_subscription_enabled,
        get_message_subscriber_manager
    )
    MESSAGE_SUBSCRIPTION_AVAILABLE = True
except ImportError:
    MESSAGE_SUBSCRIPTION_AVAILABLE = False

class AsyncProgressDisplay:
    """异步进度显示组件"""
    
    def __init__(self, container, analysis_id: str, refresh_interval: float = 1.0):
        self.container = container
        self.analysis_id = analysis_id
        self.refresh_interval = refresh_interval
        
        # 创建显示组件
        with self.container:
            self.progress_bar = st.progress(0)
            self.status_text = st.empty()
            self.step_info = st.empty()
            self.time_info = st.empty()
            self.refresh_button = st.empty()
        
        # 初始化状态
        self.last_update = 0
        self.is_completed = False
        
        logger.info(f"📊 [异步显示] 初始化: {analysis_id}, 刷新间隔: {refresh_interval}s")
    
    def update_display(self) -> bool:
        """更新显示，返回是否需要继续刷新"""
        current_time = time.time()
        
        # 检查是否需要刷新
        if current_time - self.last_update < self.refresh_interval and not self.is_completed:
            return not self.is_completed
        
        # 获取进度数据
        progress_data = get_progress_by_id(self.analysis_id)
        
        if not progress_data:
            self.status_text.error("❌ 无法获取分析进度，请检查分析是否正在运行")
            return False
        
        # 更新显示
        self._render_progress(progress_data)
        self.last_update = current_time
        
        # 检查是否完成
        status = progress_data.get('status', 'running')
        self.is_completed = status in ['completed', 'failed']
        
        return not self.is_completed
    
    def _render_progress(self, progress_data: Dict[str, Any]):
        """渲染进度显示"""
        try:
            # 基本信息
            current_step = progress_data.get('current_step', 0)
            total_steps = progress_data.get('total_steps', 8)
            progress_percentage = progress_data.get('progress_percentage', 0.0)
            status = progress_data.get('status', 'running')
            
            # 更新进度条
            self.progress_bar.progress(min(progress_percentage / 100, 1.0))
            
            # 状态信息
            step_name = progress_data.get('current_step_name', '未知')
            step_description = progress_data.get('current_step_description', '')
            last_message = progress_data.get('last_message', '')
            
            # 状态图标
            status_icon = {
                'running': '🔄',
                'completed': '✅',
                'failed': '❌'
            }.get(status, '🔄')
            
            # 显示当前状态
            self.status_text.info(f"{status_icon} **当前状态**: {last_message}")
            
            # 显示步骤信息
            if status == 'failed':
                self.step_info.error(f"❌ **分析失败**: {last_message}")
            elif status == 'completed':
                self.step_info.success(f"🎉 **分析完成**: 所有步骤已完成")

                # 添加查看报告按钮
                with self.step_info:
                    if st.button("📊 查看分析报告", key=f"view_report_{progress_data.get('analysis_id', 'unknown')}", type="primary"):
                        analysis_id = progress_data.get('analysis_id')
                        # 尝试恢复分析结果（如果还没有的话）
                        if not st.session_state.get('analysis_results'):
                            try:
                                from web.utils.analysis_runner import format_analysis_results
                                raw_results = progress_data.get('raw_results')
                                if raw_results:
                                    formatted_results = format_analysis_results(raw_results)
                                    if formatted_results:
                                        st.session_state.analysis_results = formatted_results
                                        st.session_state.analysis_running = False
                            except Exception as e:
                                st.error(f"恢复分析结果失败: {e}")

                        # 触发显示报告
                        st.session_state.show_analysis_results = True
                        st.session_state.current_analysis_id = analysis_id
                        st.rerun()
            else:
                self.step_info.info(f"📊 **进度**: 第 {current_step + 1} 步，共 {total_steps} 步 ({progress_percentage:.1f}%)\n\n"
                                  f"**当前步骤**: {step_name}\n\n"
                                  f"**步骤说明**: {step_description}")
            
            # 时间信息 - 实时计算已用时间
            start_time = progress_data.get('start_time', 0)
            estimated_total_time = progress_data.get('estimated_total_time', 0)

            # 计算已用时间
            import time
            if status == 'completed':
                # 已完成的分析使用存储的最终耗时
                real_elapsed_time = progress_data.get('elapsed_time', 0)
            elif start_time > 0:
                # 进行中的分析使用实时计算
                real_elapsed_time = time.time() - start_time
            else:
                # 备用方案
                real_elapsed_time = progress_data.get('elapsed_time', 0)

            # 重新计算剩余时间
            remaining_time = max(estimated_total_time - real_elapsed_time, 0)
            
            if status == 'completed':
                self.time_info.success(f"⏱️ **已用时间**: {format_time(real_elapsed_time)} | **总耗时**: {format_time(real_elapsed_time)}")
            elif status == 'failed':
                self.time_info.error(f"⏱️ **已用时间**: {format_time(real_elapsed_time)} | **分析中断**")
            else:
                self.time_info.info(f"⏱️ **已用时间**: {format_time(real_elapsed_time)} | **预计剩余**: {format_time(remaining_time)}")
            
            # 刷新按钮（仅在运行时显示）
            if status == 'running':
                with self.refresh_button:
                    col1, col2, col3 = st.columns([1, 1, 1])
                    with col2:
                        if st.button("🔄 手动刷新", key=f"refresh_{self.analysis_id}"):
                            st.rerun()
            else:
                self.refresh_button.empty()
                
        except Exception as e:
            logger.error(f"📊 [异步显示] 渲染失败: {e}")
            self.status_text.error(f"❌ 显示更新失败: {str(e)}")

def create_async_progress_display(container, analysis_id: str, refresh_interval: float = 1.0) -> AsyncProgressDisplay:
    """创建异步进度显示组件"""
    return AsyncProgressDisplay(container, analysis_id, refresh_interval)

def auto_refresh_progress(display: AsyncProgressDisplay, max_duration: float = 1800):
    """自动刷新进度显示"""
    start_time = time.time()
    
    # 使用Streamlit的自动刷新机制
    placeholder = st.empty()
    
    while True:
        # 检查超时
        if time.time() - start_time > max_duration:
            with placeholder:
                st.warning("⚠️ 分析时间过长，已停止自动刷新。请手动刷新页面查看最新状态。")
            break
        
        # 更新显示
        should_continue = display.update_display()
        
        if not should_continue:
            # 分析完成或失败，停止刷新
            break
        
        # 等待刷新间隔
        time.sleep(display.refresh_interval)
    
    logger.info(f"📊 [异步显示] 自动刷新结束: {display.analysis_id}")

# Streamlit专用的自动刷新组件
def streamlit_auto_refresh_progress(analysis_id: str, refresh_interval: int = 2):
    """Streamlit专用的自动刷新进度显示
    支持消息驱动的实时更新（如果消息模式启用）
    """

    # 检查消息订阅是否启用并已注册
    use_message_subscription = False
    if MESSAGE_SUBSCRIPTION_AVAILABLE and is_message_subscription_enabled():
        try:
            manager = get_message_subscriber_manager()
            if manager.is_registered(analysis_id):
                use_message_subscription = True
                logger.debug(f"📡 [消息订阅] 使用消息驱动更新: {analysis_id}")
        except Exception as e:
            logger.debug(f"检查消息订阅状态失败: {e}")

    # 获取进度数据（消息订阅模式下，数据已通过消息更新，这里获取最新状态）
    progress_data = get_progress_by_id(analysis_id)

    if not progress_data:
        st.error("❌ 无法获取分析进度，请检查分析是否正在运行")
        return False

    status = progress_data.get('status', 'running')

    # 基本信息
    current_step = progress_data.get('current_step', 0)
    total_steps = progress_data.get('total_steps', 8)
    progress_percentage = progress_data.get('progress_percentage', 0.0)

    # 进度条
    st.progress(min(progress_percentage / 100, 1.0))

    # 状态信息
    step_name = progress_data.get('current_step_name', '未知')
    step_description = progress_data.get('current_step_description', '')
    last_message = progress_data.get('last_message', '')

    # 状态图标
    status_icon = {
        'running': '🔄',
        'completed': '✅',
        'failed': '❌'
    }.get(status, '🔄')

    # 显示信息
    st.info(f"{status_icon} **当前状态**: {last_message}")

    if status == 'failed':
        st.error(f"❌ **分析失败**: {last_message}")
    elif status == 'completed':
        st.success(f"🎉 **分析完成**: 所有步骤已完成")

        # 添加查看报告按钮
        if st.button("📊 查看分析报告", key=f"view_report_streamlit_{progress_data.get('analysis_id', 'unknown')}", type="primary"):
            analysis_id = progress_data.get('analysis_id')
            # 尝试恢复分析结果（如果还没有的话）
            if not st.session_state.get('analysis_results'):
                try:
                    from web.utils.analysis_runner import format_analysis_results
                    raw_results = progress_data.get('raw_results')
                    if raw_results:
                        formatted_results = format_analysis_results(raw_results)
                        if formatted_results:
                            st.session_state.analysis_results = formatted_results
                            st.session_state.analysis_running = False
                except Exception as e:
                    st.error(f"恢复分析结果失败: {e}")

            # 触发显示报告
            st.session_state.show_analysis_results = True
            st.session_state.current_analysis_id = analysis_id
            st.rerun()
    else:
        st.info(f"📊 **进度**: 第 {current_step + 1} 步，共 {total_steps} 步 ({progress_percentage:.1f}%)\n\n"
               f"**当前步骤**: {step_name}\n\n"
               f"**步骤说明**: {step_description}")
    
    # 添加步骤日志记录 - 可展开/收缩的容器
    _render_step_log(progress_data, analysis_id)

    # 时间信息 - 实时计算已用时间
    start_time = progress_data.get('start_time', 0)
    estimated_total_time = progress_data.get('estimated_total_time', 0)

    # 计算已用时间
    import time
    if status == 'completed':
        # 已完成的分析使用存储的最终耗时
        elapsed_time = progress_data.get('elapsed_time', 0)
    elif start_time > 0:
        # 进行中的分析使用实时计算
        elapsed_time = time.time() - start_time
    else:
        # 备用方案
        elapsed_time = progress_data.get('elapsed_time', 0)

    # 重新计算剩余时间
    remaining_time = max(estimated_total_time - elapsed_time, 0)

    if status == 'completed':
        st.success(f"⏱️ **总耗时**: {format_time(elapsed_time)}")
    elif status == 'failed':
        st.error(f"⏱️ **已用时间**: {format_time(elapsed_time)} | **分析中断**")
    else:
        st.info(f"⏱️ **已用时间**: {format_time(elapsed_time)} | **预计剩余**: {format_time(remaining_time)}")

    # 添加刷新控制（仅在运行时显示）
    if status == 'running':
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("🔄 刷新进度", key=f"refresh_streamlit_{analysis_id}"):
                st.rerun()
        with col2:
            auto_refresh_key = f"auto_refresh_streamlit_{analysis_id}"
            # 获取默认值，如果是新分析则默认为True
            default_value = st.session_state.get(auto_refresh_key, True)  # 默认为True
            auto_refresh = st.checkbox("🔄 自动刷新", value=default_value, key=auto_refresh_key)
            if auto_refresh and status == 'running':  # 只在运行时自动刷新
                import time
                time.sleep(3)  # 等待3秒
                st.rerun()
            elif auto_refresh and status in ['completed', 'failed']:
                # 分析完成后自动关闭自动刷新
                st.session_state[auto_refresh_key] = False

    return status in ['completed', 'failed']

# 新增：静态进度显示（不会触发页面刷新）
def display_static_progress(analysis_id: str) -> bool:
    """
    显示静态进度（不自动刷新）
    支持消息驱动的实时更新（如果消息模式启用）
    返回是否已完成
    """
    import streamlit as st

    # 使用session state避免重复创建组件
    progress_key = f"progress_display_{analysis_id}"
    if progress_key not in st.session_state:
        st.session_state[progress_key] = True
    
    # 检查消息订阅是否启用并已注册
    if MESSAGE_SUBSCRIPTION_AVAILABLE and is_message_subscription_enabled():
        try:
            manager = get_message_subscriber_manager()
            if manager.is_registered(analysis_id):
                logger.debug(f"📡 [消息订阅] 使用消息驱动更新显示: {analysis_id}")
        except Exception as e:
            logger.debug(f"检查消息订阅状态失败: {e}")

    # 获取进度数据（消息订阅模式下，数据已通过消息更新，这里获取最新状态）
    progress_data = get_progress_by_id(analysis_id)

    if not progress_data:
        st.error("❌ 无法获取分析进度，请检查分析是否正在运行")
        return False

    status = progress_data.get('status', 'running')

    # 调试信息（可以在生产环境中移除）
    import datetime
    current_time = datetime.datetime.now().strftime('%H:%M:%S')
    logger.debug(f"📊 [进度显示] {current_time} - 状态: {status}, 进度: {progress_data.get('progress_percentage', 0):.1f}%")

    # 显示基本信息（移除分析ID显示）
    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])

    with col1:
        step_name = progress_data.get('current_step_name', '未知')
        st.write(f"**当前步骤**: {step_name}")

    with col2:
        progress_percentage = progress_data.get('progress_percentage', 0.0)
        st.metric("进度", f"{progress_percentage:.1f}%")

    with col3:
        # 计算已用时间
        start_time = progress_data.get('start_time', 0)
        import time
        if status == 'completed':
            # 已完成的分析使用存储的最终耗时
            elapsed_time = progress_data.get('elapsed_time', 0)
        elif start_time > 0:
            # 进行中的分析使用实时计算
            elapsed_time = time.time() - start_time
        else:
            # 备用方案
            elapsed_time = progress_data.get('elapsed_time', 0)
        st.metric("已用时间", format_time(elapsed_time))

    with col4:
        remaining_time = progress_data.get('remaining_time', 0)
        if status == 'completed':
            st.metric("预计剩余", "已完成")
        elif status == 'failed':
            st.metric("预计剩余", "已中断")
        elif remaining_time > 0 and status == 'running':
            st.metric("预计剩余", format_time(remaining_time))
        else:
            st.metric("预计剩余", "计算中...")

    # 进度条
    st.progress(min(progress_percentage / 100, 1.0))

    # 步骤详情
    step_description = progress_data.get('current_step_description', '正在处理...')
    st.write(f"**当前任务**: {step_description}")
    
    # 添加步骤日志记录 - 可展开/收缩的容器
    _render_step_log(progress_data, analysis_id)

    # 状态信息
    last_message = progress_data.get('last_message', '')

    # 状态图标
    status_icon = {
        'running': '🔄',
        'completed': '✅',
        'failed': '❌'
    }.get(status, '🔄')

    # 显示状态
    if status == 'failed':
        st.error(f"❌ **分析失败**: {last_message}")
    elif status == 'completed':
        st.success(f"🎉 **分析完成**: {last_message}")

        # 添加查看报告按钮
        if st.button("📊 查看分析报告", key=f"view_report_static_{analysis_id}", type="primary"):
            # 尝试恢复分析结果（如果还没有的话）
            if not st.session_state.get('analysis_results'):
                try:
                    from web.utils.async_progress_tracker import get_progress_by_id
                    from web.utils.analysis_runner import format_analysis_results
                    progress_data = get_progress_by_id(analysis_id)
                    if progress_data and progress_data.get('raw_results'):
                        formatted_results = format_analysis_results(progress_data['raw_results'])
                        if formatted_results:
                            st.session_state.analysis_results = formatted_results
                            st.session_state.analysis_running = False
                except Exception as e:
                    st.error(f"恢复分析结果失败: {e}")

            # 触发显示报告
            st.session_state.show_analysis_results = True
            st.session_state.current_analysis_id = analysis_id
            st.rerun()
    else:
        st.info(f"{status_icon} **当前状态**: {last_message}")

        # 添加刷新控制（仅在运行时显示）
        if status == 'running':
            # 使用唯一的容器避免重复
            refresh_container_key = f"refresh_container_{analysis_id}"
            if refresh_container_key not in st.session_state:
                st.session_state[refresh_container_key] = True

            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button("🔄 刷新进度", key=f"refresh_static_{analysis_id}"):
                    st.rerun()
            with col2:
                auto_refresh_key = f"auto_refresh_static_{analysis_id}"
                # 获取默认值，如果是新分析则默认为True
                default_value = st.session_state.get(auto_refresh_key, True)  # 默认为True
                auto_refresh = st.checkbox("🔄 自动刷新", value=default_value, key=auto_refresh_key)
                if auto_refresh and status == 'running':  # 只在运行时自动刷新
                    import time
                    time.sleep(3)  # 等待3秒
                    st.rerun()
                elif auto_refresh and status in ['completed', 'failed']:
                    # 分析完成后自动关闭自动刷新
                    st.session_state[auto_refresh_key] = False

    # 清理session state（分析完成后）
    if status in ['completed', 'failed']:
        progress_key = f"progress_display_{analysis_id}"
        refresh_container_key = f"refresh_container_{analysis_id}"
        if progress_key in st.session_state:
            del st.session_state[progress_key]
        if refresh_container_key in st.session_state:
            del st.session_state[refresh_container_key]

    return status in ['completed', 'failed']


def display_unified_progress(analysis_id: str, show_refresh_controls: bool = True) -> bool:
    """
    统一的进度显示函数，避免重复元素
    返回是否已完成
    """
    import streamlit as st

    # 简化逻辑：直接调用显示函数，通过参数控制是否显示刷新按钮
    # 调用方负责确保只在需要的地方传入show_refresh_controls=True
    return display_static_progress_with_controls(analysis_id, show_refresh_controls)


def display_static_progress_with_controls(analysis_id: str, show_refresh_controls: bool = True) -> bool:
    """
    显示静态进度，可控制是否显示刷新控件
    支持消息驱动的实时更新（如果消息模式启用）
    """
    import streamlit as st
    from web.utils.async_progress_tracker import get_progress_by_id
    
    # 检查消息订阅状态
    use_message_subscription = False
    if MESSAGE_SUBSCRIPTION_AVAILABLE and is_message_subscription_enabled():
        try:
            manager = get_message_subscriber_manager()
            if manager.is_registered(analysis_id):
                use_message_subscription = True
                logger.debug(f"📡 [消息订阅] 使用消息驱动更新: {analysis_id}")
        except Exception as e:
            logger.debug(f"检查消息订阅状态失败: {e}")

    # 获取进度数据（消息订阅模式下，数据已通过消息更新，这里获取最新状态）
    progress_data = get_progress_by_id(analysis_id)

    if not progress_data:
        # 如果没有进度数据，显示默认的准备状态
        st.info("🔄 **当前状态**: 准备开始分析...")
        
        # 设置默认状态为initializing
        status = 'initializing'

        # 如果需要显示刷新控件，仍然显示
        if show_refresh_controls:
            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button("🔄 刷新进度", key=f"refresh_unified_default_{analysis_id}"):
                    st.rerun()
            with col2:
                auto_refresh_key = f"auto_refresh_unified_default_{analysis_id}"
                # 获取默认值，如果是新分析则默认为True
                default_value = st.session_state.get(auto_refresh_key, True)  # 默认为True
                auto_refresh = st.checkbox("🔄 自动刷新", value=default_value, key=auto_refresh_key)
                if auto_refresh and status == 'running':  # 只在运行时自动刷新
                    import time
                    time.sleep(3)  # 等待3秒
                    st.rerun()
                elif auto_refresh and status in ['completed', 'failed']:
                    # 分析完成后自动关闭自动刷新
                    st.session_state[auto_refresh_key] = False

        return False  # 返回False表示还未完成

    # 解析进度数据（修复字段名称匹配）
    status = progress_data.get('status', 'running')
    current_step = progress_data.get('current_step', 0)
    current_step_name = progress_data.get('current_step_name', '准备阶段')
    progress_percentage = progress_data.get('progress_percentage', 0.0)

    # 计算已用时间
    start_time = progress_data.get('start_time', 0)
    estimated_total_time = progress_data.get('estimated_total_time', 0)
    import time
    if status == 'completed':
        # 已完成的分析使用存储的最终耗时
        elapsed_time = progress_data.get('elapsed_time', 0)
    elif start_time > 0:
        # 进行中的分析使用实时计算
        elapsed_time = time.time() - start_time
    else:
        # 备用方案
        elapsed_time = progress_data.get('elapsed_time', 0)

    # 重新计算剩余时间
    remaining_time = max(estimated_total_time - elapsed_time, 0)
    current_step_description = progress_data.get('current_step_description', '初始化分析引擎')
    last_message = progress_data.get('last_message', '准备开始分析')

    # 显示当前步骤
    st.write(f"**当前步骤**: {current_step_name}")

    # 显示进度条和统计信息
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("进度", f"{progress_percentage:.1f}%")

    with col2:
        st.metric("已用时间", format_time(elapsed_time))

    with col3:
        if status == 'completed':
            st.metric("预计剩余", "已完成")
        elif status == 'failed':
            st.metric("预计剩余", "已中断")
        else:
            st.metric("预计剩余", format_time(remaining_time))

    # 显示进度条
    st.progress(min(progress_percentage / 100.0, 1.0))

    # 显示当前任务
    st.write(f"**当前任务**: {current_step_description}")
    
    # 添加步骤日志记录 - 可展开/收缩的容器
    _render_step_log(progress_data, analysis_id)

    # 显示当前状态
    status_icon = {
        'running': '🔄',
        'completed': '✅',
        'failed': '❌'
    }.get(status, '🔄')

    if status == 'completed':
        st.success(f"{status_icon} **当前状态**: {last_message}")

        # 添加查看报告按钮
        if st.button("📊 查看分析报告", key=f"view_report_unified_{analysis_id}", type="primary"):
            # 尝试恢复分析结果（如果还没有的话）
            if not st.session_state.get('analysis_results'):
                try:
                    from web.utils.async_progress_tracker import get_progress_by_id
                    from web.utils.analysis_runner import format_analysis_results
                    progress_data = get_progress_by_id(analysis_id)
                    if progress_data and progress_data.get('raw_results'):
                        formatted_results = format_analysis_results(progress_data['raw_results'])
                        if formatted_results:
                            st.session_state.analysis_results = formatted_results
                            st.session_state.analysis_running = False
                except Exception as e:
                    st.error(f"恢复分析结果失败: {e}")

            # 触发显示报告
            st.session_state.show_analysis_results = True
            st.session_state.current_analysis_id = analysis_id
            st.rerun()
    elif status == 'failed':
        st.error(f"{status_icon} **当前状态**: {last_message}")
    else:
        st.info(f"{status_icon} **当前状态**: {last_message}")

    # 显示刷新控制的条件：
    # 1. 需要显示刷新控件 AND
    # 2. (分析正在运行 OR 分析刚开始还没有状态)
    if show_refresh_controls and (status == 'running' or status == 'initializing'):
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("🔄 刷新进度", key=f"refresh_unified_{analysis_id}"):
                st.rerun()
        with col2:
            auto_refresh_key = f"auto_refresh_unified_{analysis_id}"
            # 获取默认值，如果是新分析则默认为True
            default_value = st.session_state.get(auto_refresh_key, True)  # 默认为True
            auto_refresh = st.checkbox("🔄 自动刷新", value=default_value, key=auto_refresh_key)
            if auto_refresh and status == 'running':  # 只在运行时自动刷新
                import time
                time.sleep(3)  # 等待3秒
                st.rerun()
            elif auto_refresh and status in ['completed', 'failed']:
                # 分析完成后自动关闭自动刷新
                st.session_state[auto_refresh_key] = False

    # 不需要清理session state，因为我们通过参数控制显示

    return status in ['completed', 'failed']


def _render_step_log(progress_data: Dict[str, Any], analysis_id: str):
    """
    渲染分析步骤日志记录
    显示每个阶段的状态信息和时间戳
    """
    from datetime import datetime
    
    # 从 progress_data 中提取步骤历史信息
    steps_history = []
    
    # 获取分析步骤定义
    analysis_steps = progress_data.get('steps', [])
    current_step = progress_data.get('current_step', 0)
    start_time = progress_data.get('start_time', time.time())
    step_history = progress_data.get('step_history', [])  # 获取实际的步骤执行历史
    
    # 创建步骤索引到历史记录的映射
    step_history_map = {h['step_index']: h for h in step_history}
    
    # 构建步骤日志
    # 1. 首先添加初始化步骤
    steps_history.append({
        'phase': '系统初始化',
        'message': '分析系统启动，准备数据源和分析引擎',
        'timestamp': start_time,
        'step_duration': 0,  # 初始化没有步骤用时
        'total_elapsed': 0,  # 从开始到现在的总用时
        'status': 'completed',
        'icon': '✅'
    })
    
    # 2. 根据当前进度添加已完成和进行中的步骤
    for i, step_info in enumerate(analysis_steps):
        step_name = step_info.get('name', f'步骤 {i+1}')
        step_description = step_info.get('description', '')
        
        # 使用实际的步骤历史记录
        if i in step_history_map:
            # 已完成的步骤，使用实际记录的时间
            history = step_history_map[i]
            # 从消息中获取节点信息和状态（确保与消息处理时保存的状态信息对应）
            module_name = history.get('module_name', '')
            node_status = history.get('node_status', '')
            
            # 调试日志：检查状态信息
            logger.debug(f"步骤 {i+1} ({step_name}) 状态信息: module_name={module_name}, node_status={node_status}, end_time={history.get('end_time', 'N/A')}")
            
            # 如果步骤在step_history中且有end_time，确保状态为完成
            if 'end_time' in history and history['end_time'] > 0:
                # 如果node_status缺失或为start，但步骤已完成，强制设置为complete
                if not node_status or node_status == 'start':
                    node_status = 'complete'
                    logger.debug(f"步骤 {i+1} 已完成但状态为 {history.get('node_status')}，更新为 complete")
            
            # 根据节点状态确定显示状态（确保完成状态正确显示）
            # 状态值映射：complete -> completed, start -> running, error -> error
            if node_status == 'error':
                status = 'error'
                icon = '❌'
                status_text = '❌ 执行失败'
            elif node_status in ['complete', 'completed']:  # 支持两种完成状态值
                status = 'completed'
                icon = '✅'
                status_text = '✅ 已完成'
            elif node_status == 'start':
                status = 'running'
                icon = '🔄'
                status_text = '🔄 执行中'
            elif node_status == 'paused':
                status = 'paused'
                icon = '⏸️'
                status_text = '⏸️ 已暂停'
            else:
                # 默认情况下，如果步骤在step_history中且有end_time，视为已完成
                status = 'completed'
                icon = '✅'
                status_text = '✅ 已完成'
            
            # 构建消息，包含节点信息和状态
            if module_name:
                message_text = f'{step_description}\n{status_text} - 节点: {module_name} (状态: {node_status or "complete"})'
            else:
                message_text = f'{step_description} - {status_text}'
            
            steps_history.append({
                'phase': f'阶段 {i+1}: {step_name}',
                'message': message_text,
                'timestamp': history['end_time'],  # 使用实际完成时间
                'step_duration': history['duration'],  # 步骤执行时长
                'total_elapsed': history['end_time'] - start_time,  # 从开始到完成该步骤的总用时
                'status': status,
                'icon': icon,
                'module_name': module_name,  # 任务节点名称
                'node_status': node_status  # 任务节点状态
            })
        elif i == current_step:
            # 当前进行中的步骤
            current_message = progress_data.get('last_message', '')
            current_module_name = progress_data.get('current_module_name', '')
            current_node_status = progress_data.get('current_node_status', 'start')
            current_time = time.time()
            
            # 计算当前步骤已运行时长
            if i in step_history_map:
                step_start = step_history_map[i]['start_time']
            else:
                # 如果没有记录，尝试从上一步的结束时间推算
                prev_step = i - 1
                if prev_step in step_history_map:
                    step_start = step_history_map[prev_step]['end_time']
                else:
                    step_start = start_time
            step_duration = current_time - step_start
            
            # 根据节点状态确定显示状态和图标
            if current_node_status == 'error':
                status = 'error'
                icon = '❌'
            elif current_node_status == 'paused':
                status = 'paused'
                icon = '⏸️'
            else:
                status = 'running'
                icon = '🔄'
            
            # 构建消息，包含节点信息
            if current_module_name:
                message_text = f'{step_description}\n💬 {current_message}\n📦 节点: {current_module_name} ({current_node_status})'
            else:
                message_text = f'{step_description}\n💬 {current_message}'
            
            steps_history.append({
                'phase': f'阶段 {i+1}: {step_name}',
                'message': message_text,
                'timestamp': current_time,  # 使用当前时间
                'step_duration': step_duration,  # 当前步骤已运行时长
                'total_elapsed': current_time - start_time,  # 从开始到现在的总用时
                'status': status,
                'icon': icon,
                'module_name': current_module_name,  # 任务节点名称
                'node_status': current_node_status  # 任务节点状态
            })
        else:
            # 待执行的步骤
            steps_history.append({
                'phase': f'阶段 {i+1}: {step_name}',
                'message': f'{step_description} - 等待执行',
                'timestamp': None,
                'step_duration': 0,
                'total_elapsed': 0,
                'status': 'pending',
                'icon': '⏳'
            })
    
    # 如果分析完成，添加完成记录
    if progress_data.get('status') == 'completed':
        completion_time = progress_data.get('last_update', time.time())
        total_duration = completion_time - start_time
        steps_history.append({
            'phase': '分析完成',
            'message': '所有分析步骤已完成，报告生成成功',
            'timestamp': completion_time,
            'step_duration': 0,  # 完成标记没有步骤用时
            'total_elapsed': total_duration,  # 总用时
            'status': 'completed',
            'icon': '🎉'
        })
    
    # 使用 expander 创建可展开/收缩的容器
    with st.expander("📋 查看详细分析步骤日志", expanded=False):
        st.markdown("### 📊 分析流程追踪")
        st.markdown("以下是本次分析的完整步骤记录，包含每个阶段的状态和执行时间：")
        st.markdown("---")
        
        # 显示步骤日志
        for idx, step in enumerate(steps_history):
            # 根据状态设置样式（支持错误和暂停状态）
            if step['status'] == 'completed':
                bg_color = '#e8f5e9'  # 淡绿色
                border_color = '#4caf50'
            elif step['status'] == 'running':
                bg_color = '#e3f2fd'  # 淡蓝色
                border_color = '#2196f3'
            elif step['status'] == 'error':
                bg_color = '#ffebee'  # 淡红色
                border_color = '#f44336'
            elif step['status'] == 'paused':
                bg_color = '#fff3e0'  # 淡橙色
                border_color = '#ff9800'
            else:  # pending
                bg_color = '#f5f5f5'  # 灰色
                border_color = '#9e9e9e'
            
            # 格式化时间戳
            if step['timestamp']:
                time_str = datetime.fromtimestamp(step['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
                # 步骤用时
                step_duration_str = format_time(step.get('step_duration', 0))
                # 总用时
                total_elapsed_str = format_time(step.get('total_elapsed', 0))
                # 步骤标题包含用时（注意：转义phase内容，然后添加HTML标签）
                escaped_phase = html.escape(str(step['phase']))
                if step.get('step_duration', 0) > 0:
                    phase_with_duration = f"{escaped_phase} <span style='color: #2196f3; font-weight: normal;'>(用时: {step_duration_str})</span>"
                else:
                    phase_with_duration = escaped_phase
            else:
                time_str = '未开始'
                total_elapsed_str = '-'
                phase_with_duration = html.escape(str(step['phase']))
            
            # 显示状态标签
            node_status = step.get('node_status', '')
            module_name = step.get('module_name', '')
            status_badge = ""
            if node_status:
                status_colors = {
                    'complete': '#4caf50',
                    'completed': '#4caf50',
                    'start': '#2196f3',
                    'error': '#f44336',
                    'paused': '#ff9800'
                }
                status_labels = {
                    'complete': '已完成',
                    'completed': '已完成',
                    'start': '执行中',
                    'error': '失败',
                    'paused': '已暂停'
                }
                status_color = status_colors.get(node_status, '#9e9e9e')
                status_label = status_labels.get(node_status, node_status)
                status_badge = f'<span style="background-color: {status_color}; color: white; padding: 2px 8px; border-radius: 12px; font-size: 11px; margin-left: 8px;">{status_label}</span>'
            
            # 转义消息内容中的HTML特殊字符，避免破坏HTML结构
            # 注意：phase_with_duration 和 status_badge 已经包含HTML标签，不需要转义
            escaped_message = html.escape(str(step['message']))
            escaped_module_name = html.escape(str(module_name)) if module_name else ''
            escaped_time_str = html.escape(str(time_str))
            escaped_total_elapsed_str = html.escape(str(total_elapsed_str))
            
            # 使用HTML渲染美化的步骤卡片
            step_html = f"""
            <div style="background-color: {bg_color}; 
                        border-left: 4px solid {border_color}; 
                        padding: 12px; 
                        margin-bottom: 10px; 
                        border-radius: 5px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div style="flex: 1;">
                        <strong style="font-size: 16px;">{step['icon']} {phase_with_duration}{status_badge}</strong>
                        <p style="margin: 5px 0; color: #555; white-space: pre-wrap;">{escaped_message}</p>
                    </div>
                    <div style="text-align: right; margin-left: 15px; min-width: 180px;">
                        <div style="font-size: 12px; color: #666;">🕐 {escaped_time_str}</div>
                        <div style="font-size: 12px; color: #666;">📊 总用时: {escaped_total_elapsed_str}</div>
                    </div>
                </div>
            </div>
            """
            st.markdown(step_html, unsafe_allow_html=True)
        
        # 添加统计信息
        completed_count = sum(1 for s in steps_history if s['status'] == 'completed')
        total_count = len(steps_history)
        
        st.markdown("---")
        st.markdown(f"**📈 进度统计**: 已完成 {completed_count}/{total_count} 个步骤")
        
        # 显示总耗时
        if progress_data.get('status') == 'completed':
            total_time = progress_data.get('elapsed_time', 0)
            st.markdown(f"**⏱️ 总耗时**: {format_time(total_time)}")
        else:
            current_time = time.time()
            elapsed = current_time - start_time
            st.markdown(f"**⏱️ 当前用时**: {format_time(elapsed)}")
