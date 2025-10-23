
import streamlit as st
import time

class AuthManager:
    def __init__(self):
        if 'authenticated' not in st.session_state:
            st.session_state.authenticated = False
        if 'user_info' not in st.session_state:
            st.session_state.user_info = None

    def is_authenticated(self):
        return st.session_state.authenticated

    def login(self, username, password):
        # Simplified authentication
        if username == "admin" and password == "password":
            st.session_state.authenticated = True
            st.session_state.user_info = {"username": username}
            return True
        return False

    def logout(self):
        st.session_state.authenticated = False
        st.session_state.user_info = None
        st.rerun()

auth_manager = AuthManager()
