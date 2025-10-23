import streamlit as st
from web2.utils.auth_manager import auth_manager

def render_login_form():
    st.markdown("""
    <style>
    .stApp {
        background-color: #111a22;
    }
    .login-container {
        width: 512px;
        margin: auto;
    }
    .stTextInput > div > div > input {
        background-color: #192633;
        color: white;
        border: 1px solid #324d67;
        border-radius: 0.5rem;
        height: 3rem;
    }
    .stButton > button {
        background-color: #1172d4;
        color: white;
        border-radius: 0.5rem;
        height: 2.5rem;
        width: 100%;
    }
    </style>
    """, unsafe_allow_html=True)

    with st.container():
        st.markdown('<div class="login-container">', unsafe_allow_html=True)

        st.markdown("""
        <header class="flex items-center justify-between whitespace-nowrap border-b border-solid border-b-[#233648] px-10 py-3">
          <div class="flex items-center gap-4 text-white" style="margin:auto;">
            <div class="size-4">
              <svg viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg" style="width: 1rem; height: 1rem;">
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
        """, unsafe_allow_html=True)

        st.markdown('<h3 style="text-align: center; color: white;">用户登录</h3>', unsafe_allow_html=True)

        username = st.text_input("Username", placeholder="admin", label_visibility="collapsed")
        password = st.text_input("Password", placeholder="••••••", type="password", label_visibility="collapsed")

        if st.button("立即登录"):
            if auth_manager.login(username, password):
                st.success("Logged in successfully!")
                st.rerun()
            else:
                st.error("Invalid username or password")

        st.markdown("---_", unsafe_allow_html=True)

        st.markdown("""
        <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 1rem; color: white;">
            <div style="text-align: center;">
                <p>智能分析</p>
                <p style="font-size: smaller; color: #92adc9;">AI驱动的投资分析</p>
            </div>
            <div style="text-align: center;">
                <p>深度研究</p>
                <p style="font-size: smaller; color: #92adc9;">全方位市场洞察</p>
            </div>
            <div style="text-align: center;">
                <p>实时数据</p>
                <p style="font-size: smaller; color: #92adc9;">最新市场信息</p>
            </div>
            <div style="text-align: center;">
                <p>风险控制</p>
                <p style="font-size: smaller; color: #92adc9;">智能风险评估</p>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)