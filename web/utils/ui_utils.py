#!/usr/bin/env python3
"""
UI工具函数
提供通用的UI辅助功能（样式已迁移到 static/css/styles.css）
"""

import streamlit as st
from pathlib import Path


def load_external_css(css_file: str = "styles.css"):
    """
    加载外部CSS文件
    
    Args:
        css_file: CSS文件名（位于 web/static/css/ 目录下）
    """
    css_path = Path(__file__).parent.parent / "static" / "css" / css_file
    if css_path.exists():
        with open(css_path, 'r', encoding='utf-8') as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    else:
        st.warning(f"CSS文件不存在: {css_path}")


def load_external_js(js_file: str = "scripts.js"):
    """
    加载外部JavaScript文件
    
    Args:
        js_file: JS文件名（位于 web/static/js/ 目录下）
    """
    js_path = Path(__file__).parent.parent / "static" / "js" / js_file
    if js_path.exists():
        with open(js_path, 'r', encoding='utf-8') as f:
            st.markdown(f'<script>{f.read()}</script>', unsafe_allow_html=True)
    else:
        st.warning(f"JavaScript文件不存在: {js_path}")


def apply_common_styles():
    """
    应用通用样式（加载外部CSS和JS文件）
    注意：样式定义已迁移到 web/static/css/styles.css
    """
    load_external_css("styles.css")
    load_external_js("scripts.js")


def apply_hide_deploy_button_css():
    """
    应用隐藏Deploy按钮和工具栏的CSS样式
    注意：此功能已集成到 styles.css 中，调用此函数仅为向后兼容
    """
    # 为了向后兼容，保留此函数，但实际样式已在 styles.css 中定义
    pass
