"""
分析结果显示模块
将大段代码拆分为可复用的小模块
"""

import streamlit as st
from typing import Dict, Any, List, Optional
from components.ui_components import render_metric_row, render_section_header
from components.component_utils import safe_get, get_display_name


def get_model_display_name(model: str) -> str:
    """
    获取模型显示名称
    
    Args:
        model: 模型ID
        
    Returns:
        显示名称
    """
    model_map = {
        'qwen-turbo': 'Qwen Turbo',
        'qwen-plus': 'Qwen Plus',
        'qwen-max': 'Qwen Max',
        'gemini-2.0-flash': 'Gemini 2.0 Flash',
        'gemini-1.5-pro': 'Gemini 1.5 Pro',
        'gemini-1.5-flash': 'Gemini 1.5 Flash',
        'ERNIE-Speed-8K': 'ERNIE Speed 8K',
        'ERNIE-Lite-8K': 'ERNIE Lite 8K'
    }
    return model_map.get(model, model)


def get_analyst_display_name(analyst: str) -> str:
    """
    获取分析师显示名称
    
    Args:
        analyst: 分析师ID
        
    Returns:
        显示名称
    """
    analyst_map = {
        'market': '📈 市场技术分析师',
        'fundamentals': '💰 基本面分析师',
        'news': '📰 新闻分析师',
        'social_media': '💭 社交媒体分析师',
        'risk': '⚠️ 风险评估师'
    }
    return analyst_map.get(analyst, analyst)


def get_action_display(action: str) -> tuple[str, str]:
    """
    获取投资建议显示信息
    
    Args:
        action: 建议动作
        
    Returns:
        (中文名称, 颜色)
    """
    action_map = {
        'BUY': ('买入', 'green'),
        'SELL': ('卖出', 'red'),
        'HOLD': ('持有', 'orange'),
        '买入': ('买入', 'green'),
        '卖出': ('卖出', 'red'),
        '持有': ('持有', 'orange')
    }
    return action_map.get(action, (action, 'gray'))


def render_analysis_config(results: Dict[str, Any]):
    """
    渲染分析配置信息（简化版）
    
    Args:
        results: 分析结果
    """
    with render_section_header("分析配置信息", icon="📋", expanded=False):
        llm_provider = safe_get(results, 'llm_provider', 'dashscope')
        llm_model = safe_get(results, 'llm_model')
        analysts = safe_get(results, 'analysts', [])
        
        metrics = [
            {
                'label': 'LLM提供商',
                'value': get_display_name(llm_provider),
                'help': '使用的AI模型提供商'
            },
            {
                'label': 'AI模型',
                'value': get_model_display_name(llm_model),
                'help': '使用的具体AI模型'
            },
            {
                'label': '分析师数量',
                'value': f"{len(analysts)}个" if analysts else "0个",
                'help': '参与分析的AI分析师数量'
            }
        ]
        
        render_metric_row(metrics, columns=3)
        
        # 显示分析师列表
        if analysts:
            st.write("**参与的分析师:**")
            analyst_list = [get_analyst_display_name(a) for a in analysts]
            st.write(" • ".join(analyst_list))


def render_decision_metrics(decision: Dict[str, Any]):
    """
    渲染投资决策指标
    
    Args:
        decision: 决策数据
    """
    action = safe_get(decision, 'action')
    action_cn, action_color = get_action_display(action)
    
    target_price = safe_get(decision, 'target_price')
    risk_level = safe_get(decision, 'risk_level')
    confidence = safe_get(decision, 'confidence')
    
    # 准备指标数据
    metrics = [
        {
            'label': '投资建议',
            'value': action_cn,
            'help': '基于AI分析的投资建议'
        },
        {
            'label': '目标价位',
            'value': f"¥{target_price}" if target_price != 'N/A' else 'N/A',
            'help': '预期的目标价格'
        },
        {
            'label': '风险评级',
            'value': risk_level,
            'help': '投资风险等级'
        },
        {
            'label': '置信度',
            'value': f"{confidence}%" if confidence != 'N/A' else 'N/A',
            'help': 'AI对决策的置信度'
        }
    ]
    
    render_metric_row(metrics, columns=4)


def render_empty_decision_placeholder():
    """渲染空投资决策占位符"""
    st.markdown("""
    <div style="background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
                padding: 30px; border-radius: 15px; text-align: center;
                border: 2px dashed #dee2e6; margin: 20px 0;">
        <h4 style="color: #6c757d; margin-bottom: 15px;">📊 等待投资决策</h4>
        <p style="color: #6c757d; font-size: 16px; margin-bottom: 20px;">
            分析完成后，投资决策将在此处显示
        </p>
        <div style="display: flex; justify-content: center; gap: 15px; flex-wrap: wrap;">
            <span style="background: white; padding: 8px 16px; border-radius: 20px;
                       color: #6c757d; font-size: 14px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                📊 投资建议
            </span>
            <span style="background: white; padding: 8px 16px; border-radius: 20px;
                       color: #6c757d; font-size: 14px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                💰 目标价位
            </span>
            <span style="background: white; padding: 8px 16px; border-radius: 20px;
                       color: #6c757d; font-size: 14px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                ⚖️ 风险评级
            </span>
            <span style="background: white; padding: 8px 16px; border-radius: 20px;
                       color: #6c757d; font-size: 14px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                🎯 置信度
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_risk_warning_box():
    """渲染风险提示框"""
    st.markdown("""
    <div class="warning-box">
        <h4>⚠️ 风险提示</h4>
        <p>本分析结果仅供参考，不构成投资建议。投资有风险，入市需谨慎。</p>
        <ul>
            <li>AI分析可能存在偏差，请结合实际情况判断</li>
            <li>过去的表现不代表未来的收益</li>
            <li>请根据自身风险承受能力做出投资决策</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)


def extract_analyst_reports(state: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """
    提取分析师报告
    
    Args:
        state: 状态数据
        
    Returns:
        分析师报告字典
    """
    reports = {}
    
    # 从state中提取各类分析
    if 'market_data' in state:
        reports['market'] = {
            'title': '市场技术分析',
            'icon': '📈',
            'data': state['market_data']
        }
    
    if 'fundamentals' in state:
        reports['fundamentals'] = {
            'title': '基本面分析',
            'icon': '💰',
            'data': state['fundamentals']
        }
    
    if 'news_analysis' in state:
        reports['news'] = {
            'title': '新闻分析',
            'icon': '📰',
            'data': state['news_analysis']
        }
    
    if 'risk_assessment' in state:
        reports['risk'] = {
            'title': '风险评估',
            'icon': '⚠️',
            'data': state['risk_assessment']
        }
    
    return reports


def format_report_content(content: Any) -> str:
    """
    格式化报告内容
    
    Args:
        content: 内容数据
        
    Returns:
        格式化后的字符串
    """
    if isinstance(content, dict):
        lines = []
        for key, value in content.items():
            if isinstance(value, (dict, list)):
                continue  # 跳过复杂对象
            lines.append(f"**{key}**: {value}")
        return "\n\n".join(lines)
    elif isinstance(content, str):
        return content
    else:
        return str(content)

