// JavaScript来强制隐藏侧边栏按钮
function hideSidebarButtons() {
    // 隐藏所有可能的侧边栏控制按钮
    const selectors = [
        'button[kind="header"]',
        'button[data-testid="collapsedControl"]',
        'button[aria-label="Close sidebar"]',
        'button[aria-label="Open sidebar"]',
        '[data-testid="collapsedControl"]',
        '.css-1d391kg',
        '.css-1rs6os',
        '.css-17eq0hr',
        '.css-1lcbmhc button',
        '.css-1y4p8pa button'
    ];

    selectors.forEach(selector => {
        const elements = document.querySelectorAll(selector);
        elements.forEach(el => {
            el.style.display = 'none';
            el.style.visibility = 'hidden';
            el.style.opacity = '0';
            el.style.pointerEvents = 'none';
        });
    });
}

// 页面加载后执行
document.addEventListener('DOMContentLoaded', hideSidebarButtons);

// 定期检查并隐藏按钮（防止动态生成）
setInterval(hideSidebarButtons, 1000);

// 强制修改页面边距为8px
function forceOptimalPadding() {
    const selectors = [
        '.main .block-container',
        '.stApp',
        '.stApp > div',
        '.main',
        '.main > div',
        'div[data-testid="stAppViewContainer"]',
        'section[data-testid="stMain"]',
        'div[data-testid="column"]',
        'div[data-testid="stAppViewContainer"] > div',
        'section[data-testid="stMain"] > div'
    ];

    selectors.forEach(selector => {
        const elements = document.querySelectorAll(selector);
        elements.forEach(el => {
            el.style.paddingLeft = '8px';
            el.style.paddingRight = '8px';
            el.style.marginLeft = '0px';
            el.style.marginRight = '0px';
        });
    });

    // 特别处理主容器宽度
    const mainContainer = document.querySelector('.main .block-container');
    if (mainContainer) {
        mainContainer.style.width = 'calc(100vw - 336px)';
        mainContainer.style.maxWidth = 'calc(100vw - 336px)';
    }
}

// 页面加载后执行
document.addEventListener('DOMContentLoaded', forceOptimalPadding);

// 定期强制应用样式
setInterval(forceOptimalPadding, 500);

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
