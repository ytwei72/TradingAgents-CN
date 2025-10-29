/**
 * TradingAgents-CN 全局JavaScript脚本
 */

/**
 * 隐藏侧边栏按钮
 */
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

/**
 * 强制修改页面边距为8px
 */
function forceOptimalPadding() {
    const selectors = [
        '.main .block-container',
        '.stApp',
        '.stApp > div',
        '.main',
        '.main > div',
        'div[data-testid="stAppViewContainer"]',
        'section[data-testid="stMain"]',
        'div[data-testid="column"]'
    ];

    selectors.forEach(selector => {
        const elements = document.querySelectorAll(selector);
        elements.forEach(el => {
            el.style.paddingLeft = '8px';
            el.style.paddingRight = '8px';
            el.style.paddingTop = '0px';
            el.style.marginLeft = '0px';
            el.style.marginRight = '0px';
            el.style.marginTop = '0px';
        });
    });

    // 特别处理主容器宽度和边距
    const mainContainer = document.querySelector('.main .block-container');
    if (mainContainer) {
        mainContainer.style.width = 'calc(100vw - 336px)';
        mainContainer.style.maxWidth = 'calc(100vw - 336px)';
        mainContainer.style.paddingTop = '8px';
        mainContainer.style.paddingBottom = '8px';
        mainContainer.style.marginTop = '0px';
    }
    
    // 强制隐藏的 header 元素不占空间
    const headers = document.querySelectorAll('header, .stApp > header, header[data-testid="stHeader"]');
    headers.forEach(header => {
        header.style.display = 'none';
        header.style.height = '0';
        header.style.minHeight = '0';
        header.style.padding = '0';
        header.style.margin = '0';
    });
}

// 页面加载后执行
document.addEventListener('DOMContentLoaded', () => {
    hideSidebarButtons();
    forceOptimalPadding();
});

// 定期检查并隐藏按钮（防止动态生成）
setInterval(hideSidebarButtons, 1000);

// 定期强制应用样式
setInterval(forceOptimalPadding, 500);
