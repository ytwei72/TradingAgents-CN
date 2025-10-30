"""
前端脚本管理工具
提供前端JavaScript脚本的注入和管理功能
"""

import streamlit as st
import logging

logger = logging.getLogger(__name__)


def inject_frontend_cache_check():
    """注入前端缓存检查脚本"""
    logger.info("📝 准备注入前端缓存检查脚本")
    
    # 如果已经注入过，不重复注入
    if st.session_state.get('cache_script_injected', False):
        logger.info("⚠️ 前端脚本已注入，跳过重复注入")
        return
    
    # 标记已注入
    st.session_state.cache_script_injected = True
    logger.info("✅ 标记前端脚本已注入")
    
    cache_check_js = """
    <script>
    // 前端缓存检查和恢复
    function checkAndRestoreAuth() {
        console.log('🚀 开始执行前端缓存检查');
        console.log('📍 当前URL:', window.location.href);
        
        try {
            // 检查URL中是否已经有restore_auth参数
            const currentUrl = new URL(window.location);
            if (currentUrl.searchParams.has('restore_auth')) {
                console.log('🔄 URL中已有restore_auth参数，跳过前端检查');
                return;
            }
            
            const authData = localStorage.getItem('tradingagents_auth');
            console.log('🔍 检查localStorage中的认证数据:', authData ? '存在' : '不存在');
            
            if (!authData) {
                console.log('🔍 前端缓存中没有登录状态');
                return;
            }
            
            const data = JSON.parse(authData);
            console.log('📊 解析的认证数据:', data);
            
            // 验证数据结构
            if (!data.userInfo || !data.userInfo.username) {
                console.log('❌ 认证数据结构无效，清除缓存');
                localStorage.removeItem('tradingagents_auth');
                return;
            }
            
            const now = Date.now();
            const timeout = 10 * 60 * 1000; // 10分钟
            const timeSinceLastActivity = now - data.lastActivity;
            
            console.log('⏰ 时间检查:', {
                now: new Date(now).toLocaleString(),
                lastActivity: new Date(data.lastActivity).toLocaleString(),
                timeSinceLastActivity: Math.round(timeSinceLastActivity / 1000) + '秒',
                timeout: Math.round(timeout / 1000) + '秒'
            });
            
            // 检查是否超时
            if (timeSinceLastActivity > timeout) {
                localStorage.removeItem('tradingagents_auth');
                console.log('⏰ 登录状态已过期，自动清除');
                return;
            }
            
            // 更新最后活动时间
            data.lastActivity = now;
            localStorage.setItem('tradingagents_auth', JSON.stringify(data));
            console.log('🔄 更新最后活动时间');
            
            console.log('✅ 从前端缓存恢复登录状态:', data.userInfo.username);
            
            // 保留现有的URL参数，只添加restore_auth参数
            // 传递完整的认证数据，包括原始登录时间
            const restoreData = {
                userInfo: data.userInfo,
                loginTime: data.loginTime
            };
            const restoreParam = btoa(JSON.stringify(restoreData));
            console.log('📦 生成恢复参数:', restoreParam);
            
            // 保留所有现有参数
            const existingParams = new URLSearchParams(currentUrl.search);
            existingParams.set('restore_auth', restoreParam);
            
            // 构建新URL，保留现有参数
            const newUrl = currentUrl.origin + currentUrl.pathname + '?' + existingParams.toString();
            console.log('🔗 准备跳转到:', newUrl);
            console.log('📋 保留的URL参数:', Object.fromEntries(existingParams));
            
            window.location.href = newUrl;
            
        } catch (e) {
            console.error('❌ 前端缓存恢复失败:', e);
            localStorage.removeItem('tradingagents_auth');
        }
    }
    
    // 延迟执行，确保页面完全加载
    console.log('⏱️ 设置1000ms延迟执行前端缓存检查');
    setTimeout(checkAndRestoreAuth, 1000);
    </script>
    """
    
    st.components.v1.html(cache_check_js, height=0)


def inject_stock_input_enhancer():
    """注入股票代码输入框增强脚本"""
    enhancer_js = """
    <script>
    // 监听输入框的变化，提供更好的用户反馈
    document.addEventListener('DOMContentLoaded', function() {
        const inputs = document.querySelectorAll('input[type="text"]');
        inputs.forEach(input => {
            input.addEventListener('input', function() {
                if (this.value.trim()) {
                    this.style.borderColor = '#00ff00';
                    this.title = '按回车键确认输入';
                } else {
                    this.style.borderColor = '';
                    this.title = '';
                }
            });
        });
    });
    </script>
    """
    
    st.markdown(enhancer_js, unsafe_allow_html=True)


def inject_custom_styles(style_content: str):
    """
    注入自定义CSS样式
    
    Args:
        style_content: CSS样式内容
    """
    st.markdown(f'<style>{style_content}</style>', unsafe_allow_html=True)


def inject_custom_script(script_content: str):
    """
    注入自定义JavaScript脚本
    
    Args:
        script_content: JavaScript脚本内容
    """
    st.markdown(f'<script>{script_content}</script>', unsafe_allow_html=True)


def load_static_file(file_type: str, file_name: str) -> str:
    """
    加载静态文件内容
    
    Args:
        file_type: 文件类型 ('css' 或 'js')
        file_name: 文件名
        
    Returns:
        文件内容，如果加载失败返回空字符串
    """
    from pathlib import Path
    
    file_path = Path(__file__).parent.parent / "static" / file_type / file_name
    
    if file_path.exists():
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.warning(f"加载静态文件失败 {file_path}: {e}")
            return ""
    else:
        logger.warning(f"静态文件不存在: {file_path}")
        return ""


def inject_page_refresh_script(delay_seconds: int = 5):
    """
    注入页面自动刷新脚本
    
    Args:
        delay_seconds: 延迟刷新的秒数
    """
    refresh_js = f"""
    <script>
    setTimeout(function() {{
        window.location.reload();
    }}, {delay_seconds * 1000});
    </script>
    """
    
    st.components.v1.html(refresh_js, height=0)

