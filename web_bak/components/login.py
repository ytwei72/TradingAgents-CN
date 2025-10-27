"""
登录组件
提供用户登录界面
"""

import streamlit as st
import time
import sys
from pathlib import Path
import base64

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# 导入认证管理器 - 使用全局变量确保在整个模块中可用
auth_manager = None

# 尝试多种导入路径
try:
    # 尝试相对导入（从 web 目录运行时）
    from ..utils.auth_manager import AuthManager, auth_manager as imported_auth_manager
    auth_manager = imported_auth_manager
except ImportError:
    try:
        # 尝试从 web.utils 导入（从项目根目录运行时）
        from web.utils.auth_manager import AuthManager, auth_manager as imported_auth_manager
        auth_manager = imported_auth_manager
    except ImportError:
        try:
            # 尝试直接从 utils 导入
            from utils.auth_manager import AuthManager, auth_manager as imported_auth_manager
            auth_manager = imported_auth_manager
        except ImportError:
            try:
                # 尝试绝对路径导入
                import sys
                from pathlib import Path
                web_utils_path = Path(__file__).parent.parent / "utils"
                sys.path.insert(0, str(web_utils_path))
                from auth_manager import AuthManager, auth_manager as imported_auth_manager
                auth_manager = imported_auth_manager
            except ImportError:
                # 如果都失败了，创建一个简单的认证管理器
                class SimpleAuthManager:
                    def __init__(self):
                        self.authenticated = False
                        self.current_user = None
                    
                    def is_authenticated(self):
                        return st.session_state.get('authenticated', False)
                    
                    def authenticate(self, username, password):
                        # 简单的认证逻辑
                        if username == "admin" and password == "admin123":
                            return True, {"username": username, "role": "admin"}
                        elif username == "user" and password == "user123":
                            return True, {"username": username, "role": "user"}
                        return False, None
                    
                    def logout(self):
                        st.session_state.authenticated = False
                        st.session_state.user_info = None
                    
                    def get_current_user(self):
                        return st.session_state.get('user_info')
                    
                    def require_permission(self, permission):
                        return self.is_authenticated()
                
                auth_manager = SimpleAuthManager()

def get_base64_image(image_path):
    """将图片转换为base64编码"""
    try:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except:
        return None

def render_login_form():
    """渲染登录表单"""
    params = st.query_params
    if "username" in params and "password" in params:
        username = params.get("username")
        password = params.get("password")
        if auth_manager.login(username, password):
            st.success("Logged in successfully!")
            st.query_params.clear()
            st.rerun()
        else:
            st.error("Invalid username or password")
            # Clear the params to avoid login loop
            st.query_params.clear()
            time.sleep(1)
            st.rerun()

    html_content = """
    <html>
      <head>
        <link rel="preconnect" href="https://fonts.gstatic.com/" crossorigin="" />
        <link
          rel="stylesheet"
          as="style"
          onload="this.rel='stylesheet'"
          href="https://fonts.googleapis.com/css2?display=swap&amp;family=Inter%3Awght%40400%3B500%3B700%3B900&amp;family=Noto+Sans%3Awght%40400%3B500%3B700%3B900"
        />
        <script src="https://cdn.tailwindcss.com?plugins=forms,container-queries"></script>
      </head>
      <body>
        <div class="relative flex h-auto min-h-screen w-full flex-col bg-[#111a22] dark group/design-root overflow-x-hidden" style='font-family: Inter, "Noto Sans", sans-serif;'>
          <div class="layout-container flex h-full grow flex-col">
            <div class="px-40 flex flex-1 justify-center py-5">
              <div class="layout-content-container flex flex-col w-[512px] max-w-[512px] py-5 max-w-[960px] flex-1">
                <header class="flex items-center justify-between whitespace-nowrap border-b border-solid border-b-[#233648] px-10 py-3">
                  <div class="flex items-center gap-4 text-white">
                    <div class="size-4">
                      <svg viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path
                          fill-rule="evenodd"
                          clip-rule="evenodd"
                          d="M24 18.4228L42 11.475V34.3663C42 34.7796 41.7457 35.1504 41.3601 35.2992L24 42V18.4228Z"
                          fill="currentColor"
                        ></path>
                        <path
                          fill-rule="evenodd"
                          clip-rule="evenodd"
                          d="M24 8.18819L33.4123 11.574L24 15.2071L14.5877 11.574L24 8.18819ZM9 15.8487L21 20.4805V37.6263L9 32.9945V15.8487ZM27 37.6263V20.4805L39 15.8487V32.9945L27 37.6263ZM25.354 2.29885C24.4788 1.98402 23.5212 1.98402 22.646 2.29885L4.98454 8.65208C3.7939 9.08038 3 10.2097 3 11.475V34.3663C3 36.0196 4.01719 37.5026 5.55962 38.098L22.9197 44.7987C23.6149 45.0671 24.3851 45.0671 25.0803 44.7987L42.4404 38.098C43.9828 37.5026 45 36.0196 45 34.3663V11.475C45 10.2097 44.2061 9.08038 43.0155 8.65208L25.354 2.29885Z"
                          fill="currentColor"
                        ></path>
                      </svg>
                    </div>
                    <h2 class="text-white text-lg font-bold leading-tight tracking-[-0.015em]">TradingAgents-CN</h2>
                  </div>
                </header>
                <h3 class="text-white tracking-light text-2xl font-bold leading-tight px-4 text-center pb-2 pt-5">用户登录</h3>
                <div class="flex flex-col items-center w-full px-4 py-3 gap-y-4">
                  <div class="w-full max-w-[480px]">
                    <label class="flex flex-col w-full">
                      <input
                        id="username"
                        placeholder="admin"
                        class="form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-lg text-white focus:outline-0 focus:ring-0 border border-[#324d67] bg-[#192633] focus:border-[#324d67] h-14 placeholder:text-[#92adc9] p-[15px] text-base font-normal leading-normal"
                        value=""
                      />
                    </label>
                  </div>
                  <div class="w-full max-w-[480px]">
                    <label class="flex flex-col w-full">
                      <input
                        id="password"
                        type="password"
                        placeholder="••••••"
                        class="form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-lg text-white focus:outline-0 focus:ring-0 border border-[#324d67] bg-[#192633] focus:border-[#324d67] h-14 placeholder:text-[#92adc9] p-[15px] text-base font-normal leading-normal"
                        value=""
                      />
                    </label>
                  </div>
                  <div class="w-full max-w-[480px]">
                    <button
                      id="login-button"
                      class="flex min-w-[84px] w-full cursor-pointer items-center justify-center overflow-hidden rounded-lg h-10 px-4 bg-[#1172d4] text-white text-sm font-bold leading-normal tracking-[0.015em]"
                    >
                      <span class="truncate">立即登录</span>
                    </button>
                  </div>
                </div>
                <div class="grid grid-cols-[repeat(auto-fit,minmax(158px,1fr))] gap-3 p-4">
                  <div class="flex flex-col gap-3 pb-3">
                    <div class="w-1/2 mx-auto">
                    <div
                      class="w-full bg-center bg-no-repeat aspect-square bg-cover rounded-lg"
                      style='background-image: url("https://lh3.googleusercontent.com/aida-public/AB6AXuCqsqBasbK5vq-kj21xvaI9Dry3wOJQZU-Z5eIGMnp-YVtrjDxiQN27yP3F0Y6hNNNNZ_JjG2bKbTIyX87W3yICfvf2PLuoAdWOD44AWTbIpaTMWHLl3gQKpdEQUpbcn4VtL2NWgHYXQo9Wf7vA4fRoHlzQWFJU5BVrnIcVu4N-MjJkslfJqaXMkoB0KcsMGSnrlF3JHEf3vjV6oLNCMeYoKw69tkhBZT3cW8BG3_W1nPExsLaMgbSbhEfiDB88Lzb7KU3ih3WVP7w");'></div>
                    </div>
                    <div class="text-center">
                      <p class="text-white text-base font-medium leading-normal">智能分析</p>
                      <p class="text-[#92adc9] text-sm font-normal leading-normal">AI驱动的投资分析</p>
                    </div>
                  </div>
                  <div class="flex flex-col gap-3 pb-3">
                    <div class="w-1/2 mx-auto">
                    <div
                      class="w-full bg-center bg-no-repeat aspect-square bg-cover rounded-lg"
                      style='background-image: url("https://lh3.googleusercontent.com/aida-public/AB6AXuA4K0CROyxil-3U9G4zGoFNF-FP4pdx3wdTWqm86HWP1-7GAoqmDkjl8EIdRDPPbSI4UmfsH5iJyFz21q7zKXY-UJmWjQ4iK6g6BWut5RfWw8vbh0cKyJP1m1KrroUJQYn4D1DAA8WEiASO2tHf6bMmNRPm6XFF9hR9tTGNwuThB4gtVi_AnPrF3cwVoJYgogYYBRIb9MPLBr2BTnn2CSlxRLValLptG44Anb2vVKH0tZusS5m9-0KCAFXRuGAAHvTZHmHevCys4Ps");'></div>
                    </div>
                    <div class="text-center">
                      <p class="text-white text-base font-medium leading-normal">深度研究</p>
                      <p class="text-[#92adc9] text-sm font-normal leading-normal">全方位市场洞察</p>
                    </div>
                  </div>
                  <div class="flex flex-col gap-3 pb-3">
                    <div class="w-1/2 mx-auto">
                    <div
                      class="w-full bg-center bg-no-repeat aspect-square bg-cover rounded-lg"
                      style='background-image: url("https://lh3.googleusercontent.com/aida-public/AB6AXuBkHkcHZDB3JEIEXQCpYmQ9o4gJ6MvnqG9SxygMNLa__lfLZqmlVEsayO1f2S54ylQvNOwKq6pgRnhRQ2ouoKVWHS6IwksIZ_JiTsx4m6hfdbAMSPfTRXO5RCaRc8HyCtD5YrBZCgQ5AerHwJgnJkSloVWFrr0bjrnBtoOfiT0hw7tnE9c0E0-klmjTT31mJlirPVdwdaWhiv-rhdoUDgJZL13HJiK9C6wP3kCC_kD9YIOd1PLGlnE2D-vZh0dpdRcIOiYOJX8FSps");'></div>
                    </div>
                    <div class="text-center">
                      <p class="text-white text-base font-medium leading-normal">实时数据</p>
                      <p class="text-[#92adc9] text-sm font-normal leading-normal">最新市场信息</p>
                    </div>
                  </div>
                  <div class="flex flex-col gap-3 pb-3">
                    <div class="w-1/2 mx-auto">
                    <div
                      class="w-full bg-center bg-no-repeat aspect-square bg-cover rounded-lg"
                      style='background-image: url("https://lh3.googleusercontent.com/aida-public/AB6AXuDiGRSWXHvS6Nk9iLYfpfj7fVwYWz6LfO-INL7W_OR15IMTd1s7yo3q0S_WBiw54TT8gsQ4qg3XXcfl5P5gQLqJM8HZhYws8ydz8E_kzLpgYn5RHuQRMuNyeyWoFfK1QaPOsYm6VaWDIriYPsmX1Nxy551yJ4bbx8lq0dBqHQsFc6ix3qfSWNAq9l2JN-9SPNeVJtulHTTqNG8TZ892EX7nbUIjUUDQWvAlsq7pljrYzp0BXpYsGrJtFrefb6uG0ST9ZlVKVxLkRkk");'></div>
                    </div>
                    <div class="text-center">
                      <p class="text-white text-base font-medium leading-normal">风险控制</p>
                      <p class="text-[#92adc9] text-sm font-normal leading-normal">智能风险评估</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
        <script>
            const usernameInput = document.getElementById('username');
            const passwordInput = document.getElementById('password');
            const loginButton = document.getElementById('login-button');

            loginButton.addEventListener('click', () => {
                const username = usernameInput.value;
                const password = passwordInput.value;
                window.location.href = `?username=${username}&password=${password}`;
            });
        </script>
      </body>
    </html>
    """
    st.components.v1.html(html_content, height=800)

def render_sidebar_user_info():
    """在侧边栏渲染用户信息"""
    
    if not auth_manager.is_authenticated():
        return
    
    user_info = auth_manager.get_current_user()
    if not user_info:
        return
    
    # 侧边栏用户信息样式
    st.sidebar.markdown("""
    <style>
    .sidebar-user-info {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem;
        border-radius: 12px;
        margin-bottom: 1rem;
        box-shadow: 0 4px 20px rgba(102, 126, 234, 0.3);
        border: 1px solid rgba(255, 255, 255, 0.2);
    }
    
    .sidebar-user-name {
        font-size: 1.1rem;
        font-weight: 600;
        margin-bottom: 0.3rem;
        text-align: center;
    }
    
    .sidebar-user-role {
        background: rgba(255, 255, 255, 0.2);
        padding: 0.2rem 0.6rem;
        border-radius: 15px;
        font-size: 0.8rem;
        font-weight: 500;
        text-align: center;
        margin-bottom: 0.5rem;
        backdrop-filter: blur(10px);
    }
    
    .sidebar-user-status {
        font-size: 0.8rem;
        opacity: 0.9;
        text-align: center;
        margin-bottom: 0.8rem;
    }
    
    .sidebar-logout-btn {
        width: 100% !important;
        background: rgba(255, 255, 255, 0.2) !important;
        color: white !important;
        border: 1px solid rgba(255, 255, 255, 0.3) !important;
        border-radius: 8px !important;
        padding: 0.4rem 0.8rem !important;
        font-size: 0.85rem !important;
        font-weight: 500 !important;
        transition: all 0.3s ease !important;
        backdrop-filter: blur(10px) !important;
    }
    
    .sidebar-logout-btn:hover {
        background: rgba(255, 255, 255, 0.3) !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.2) !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # 获取用户角色的中文显示
    role_display = {
        'admin': '管理员',
        'user': '普通用户'
    }.get(user_info.get('role', 'user'), '用户')
    
    # 获取登录时间
    login_time = st.session_state.get('login_time')
    login_time_str = ""
    if login_time:
        import datetime
        login_dt = datetime.datetime.fromtimestamp(login_time)
        login_time_str = login_dt.strftime("%H:%M")
    
    # 渲染用户信息
    st.sidebar.markdown(f"""
    <div class="sidebar-user-info">
        <div class="sidebar-user-name">👋 {user_info['username']}</div>
        <div class="sidebar-user-role">{role_display}</div>
        <div class="sidebar-user-status">
            🌟 在线中 {f'· {login_time_str}登录' if login_time_str else ''}
        </div>
    </div>
    """, unsafe_allow_html=True)

def render_sidebar_logout():
    """在侧边栏底部渲染退出按钮"""
    
    if not auth_manager.is_authenticated():
        return
    
    # 退出按钮样式
    st.sidebar.markdown("""
    <style>
    .sidebar-logout-container {
        margin-top: 2rem;
        padding-top: 1rem;
        border-top: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    .sidebar-logout-btn {
        width: 100% !important;
        background: linear-gradient(135deg, #ff6b6b 0%, #ee5a52 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 0.6rem 1rem !important;
        font-size: 0.9rem !important;
        font-weight: 600 !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 2px 10px rgba(255, 107, 107, 0.3) !important;
    }
    
    .sidebar-logout-btn:hover {
        background: linear-gradient(135deg, #ff5252 0%, #d32f2f 100%) !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 15px rgba(255, 107, 107, 0.4) !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # 添加分隔线和退出按钮
    st.sidebar.markdown('<div class="sidebar-logout-container">', unsafe_allow_html=True)
    if st.sidebar.button("🚪 安全退出", use_container_width=True, key="sidebar_logout_btn"):
        auth_manager.logout()
        st.sidebar.success("✅ 已安全退出，感谢使用！")
        time.sleep(1)
        st.rerun()
    st.sidebar.markdown('</div>', unsafe_allow_html=True)

def render_user_info():
    """渲染用户信息栏"""
    
    if not auth_manager.is_authenticated():
        return
    
    user_info = auth_manager.get_current_user()
    if not user_info:
        return
    
    # 现代化用户信息栏样式
    st.markdown("""
    <style>
    .user-info-container {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 15px;
        margin-bottom: 1.5rem;
        box-shadow: 0 8px 32px rgba(102, 126, 234, 0.3);
        border: 1px solid rgba(255, 255, 255, 0.2);
    }
    
    .user-welcome {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 0.5rem;
    }
    
    .user-name {
        font-size: 1.4rem;
        font-weight: 600;
        margin: 0;
    }
    
    .user-role {
        background: rgba(255, 255, 255, 0.2);
        padding: 0.3rem 0.8rem;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 500;
        backdrop-filter: blur(10px);
    }
    
    .user-details {
        display: flex;
        align-items: center;
        gap: 1rem;
        opacity: 0.9;
        font-size: 0.95rem;
    }
    
    .logout-btn {
        background: rgba(255, 255, 255, 0.2) !important;
        color: white !important;
        border: 1px solid rgba(255, 255, 255, 0.3) !important;
        border-radius: 10px !important;
        padding: 0.5rem 1rem !important;
        font-weight: 500 !important;
        transition: all 0.3s ease !important;
        backdrop-filter: blur(10px) !important;
    }
    
    .logout-btn:hover {
        background: rgba(255, 255, 255, 0.3) !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2) !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # 获取用户角色的中文显示
    role_display = {
        'admin': '管理员',
        'user': '普通用户'
    }.get(user_info.get('role', 'user'), '用户')
    
    # 获取登录时间
    login_time = st.session_state.get('login_time')
    login_time_str = ""
    if login_time:
        import datetime
        login_dt = datetime.datetime.fromtimestamp(login_time)
        login_time_str = login_dt.strftime("%H:%M")
    
    col1, col2 = st.columns([4, 1])
    
    with col1:
        st.markdown(f"""
        <div class="user-info-container">
            <div class="user-welcome">
                <div>
                    <h3 class="user-name">👋 欢迎回来，{user_info['username']}</h3>
                    <div class="user-details">
                        <span>🎯 {role_display}</span>
                        {f'<span>🕐 {login_time_str} 登录</span>' if login_time_str else ''}
                        <span>🌟 在线中</span>
                    </div>
                </div>
                <div class="user-role">{role_display}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        if st.button("🚪 安全退出", use_container_width=True, type="secondary", key="logout_btn"):
            auth_manager.logout()
            st.success("✅ 已安全退出，感谢使用！")
            time.sleep(1)
            st.rerun()

def check_authentication():
    """检查用户认证状态"""
    global auth_manager
    if auth_manager is None:
        return False
    return auth_manager.is_authenticated()

def require_permission(permission: str):
    """要求特定权限"""
    global auth_manager
    if auth_manager is None:
        return False
    return auth_manager.require_permission(permission)