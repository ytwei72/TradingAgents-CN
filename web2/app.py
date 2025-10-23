
import streamlit as st
from web2.utils.auth_manager import auth_manager
# from web2.components.login2 import render_login_form
from web2.components.login import render_login_form

def render_placeholder_page(page_name):
    st.title(page_name)
    st.header("计划建设中")
    if st.sidebar.button("Logout"):
        auth_manager.logout()

def main():
    # Try to login from query params
    params = st.query_params
    if "username" in params and "password" in params:
        username = params["username"]
        password = params["password"]
        if auth_manager.login(username, password):
            # Clear query params after login
            st.query_params.clear()
            st.rerun()
        else:
            st.error("Invalid username or password")

    if not auth_manager.is_authenticated():
        render_login_form()
    else:
        st.sidebar.title("Navigation")
        page = st.sidebar.radio("Go to", ["Home", "Dashboard", "Settings"])

        if page == "Home":
            render_placeholder_page("Home")
        elif page == "Dashboard":
            render_placeholder_page("Dashboard")
        elif page == "Settings":
            render_placeholder_page("Settings")

if __name__ == "__main__":
    main()
