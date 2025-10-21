import streamlit as st

def render_navigation():
    pages = [
        {"label": "股票分析", "icon": "📊"},
        {"label": "配置管理", "icon": "⚙️"},
        {"label": "缓存管理", "icon": "💾"},
        {"label": "Token统计", "icon": "💰"},
        {"label": "操作日志", "icon": "📋"},
        {"label": "分析结果", "icon": "📈"},
        {"label": "系统状态", "icon": "🔧"},
    ]

    if "current_page" not in st.session_state:
        st.session_state.current_page = pages[0]["label"]

    st.sidebar.markdown("<div class='sidebar-navigation'>", unsafe_allow_html=True)
    for p in pages:
        button_key = f"nav_button_{p['label']}"
        is_selected = st.session_state.current_page == p["label"]
        
        if st.sidebar.button(
            f"{p['icon']} {p['label']}", 
            key=button_key,
            use_container_width=True,
        ):
            st.session_state.current_page = p["label"]
            st.rerun()

        if is_selected:
            st.markdown(
                f'''
                <script>
                    var buttons = window.parent.document.querySelectorAll("button[data-testid='stButton']");
                    for (var i = 0; i < buttons.length; i++) {{
                        if (buttons[i].innerText.includes("{p['label']}")) {{
                            buttons[i].classList.add("selected");
                        }}
                    }}
                </script>
                ''',
                unsafe_allow_html=True
            )

    st.sidebar.markdown("</div>", unsafe_allow_html=True)


