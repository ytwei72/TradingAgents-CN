#!/usr/bin/env python3
"""
Token使用统计页面

展示Token使用情况、成本分析和统计图表
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import json
import os
from typing import Dict, List, Any

# 添加项目根目录到路径
import sys
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 导入UI工具函数
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from utils.ui_utils import apply_hide_deploy_button_css

from tradingagents.config.config_manager import config_manager, token_tracker
from tradingagents.storage.mongodb.model_usage_manager import UsageRecord

def render_token_statistics():
    """渲染Token统计页面"""
    # 应用隐藏Deploy按钮的CSS样式
    apply_hide_deploy_button_css()
    
    st.markdown("**💰 Token使用统计与成本分析**")
    
    # 侧边栏控制
    with st.sidebar:
        st.subheader("📊 统计设置")
        
        # 时间范围选择
        time_range = st.selectbox(
            "统计时间范围",
            ["今天", "最近7天", "最近30天", "最近90天", "全部"],
            index=2
        )
        
        # 转换为天数
        days_map = {
            "今天": 1,
            "最近7天": 7,
            "最近30天": 30,
            "最近90天": 90,
            "全部": 365  # 使用一年作为"全部"
        }
        days = days_map[time_range]
        
        # 刷新按钮
        if st.button("🔄 刷新数据", use_container_width=True):
            st.rerun()
        
        # 导出数据按钮
        if st.button("📥 导出统计数据", use_container_width=True):
            export_statistics_data(days)
    
    # 获取统计数据
    try:
        stats = config_manager.get_usage_statistics(days)
        records = load_detailed_records(days)
        
        if not stats or stats.get('total_requests', 0) == 0:
            st.info(f"📊 {time_range}内暂无Token使用记录")
            st.markdown("""
            ### 💡 如何开始记录Token使用？
            
            1. **进行股票分析**: 使用主页面的股票分析功能
            2. **确保API配置**: 检查DashScope API密钥是否正确配置
            3. **启用成本跟踪**: 在配置管理中启用Token成本跟踪
            
            系统会自动记录所有LLM调用的Token使用情况。
            """)
            return
        
        # 显示概览统计
        render_overview_metrics(stats, time_range)
        
        # 显示详细图表
        if records:
            render_detailed_charts(records, stats)
        
        # 显示供应商统计
        render_provider_statistics(stats)
        
        # 显示成本趋势
        if records:
            render_cost_trends(records)
        
        # 显示详细记录表
        render_detailed_records_table(records)
        
    except Exception as e:
        st.error(f"❌ 获取统计数据失败: {str(e)}")
        st.info("请检查配置文件和数据存储是否正常")

def render_overview_metrics(stats: Dict[str, Any], time_range: str):
    """渲染概览指标"""
    st.markdown(f"**📈 {time_range}概览**")
    
    # 创建指标卡片：总输入、总输出、请求数和总费用
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="📥 总输入",
            value=f"{stats['total_input_tokens']:,}",
            delta=f"{stats['total_input_tokens']/(stats['total_input_tokens']+stats['total_output_tokens'])*100:.1f}%" if (stats['total_input_tokens']+stats['total_output_tokens']) > 0 else None
        )
    
    with col2:
        st.metric(
            label="📤 总输出",
            value=f"{stats['total_output_tokens']:,}",
            delta=f"{stats['total_output_tokens']/(stats['total_input_tokens']+stats['total_output_tokens'])*100:.1f}%" if (stats['total_input_tokens']+stats['total_output_tokens']) > 0 else None
        )
    
    with col3:
        st.metric(
            label="🔢 请求数",
            value=f"{stats['total_requests']:,}",
            delta=None
        )
    
    with col4:
        st.metric(
            label="💰 总费用",
            value=f"¥{stats['total_cost']:.4f}",
            delta=None
        )

# 定义多种配色方案
COLOR_SCHEMES = {
    "经典红蓝": {
        "colors": ['#FF6B6B', '#4ECDC4'],
        "description": "经典对比色，清晰明了"
    },
    "渐变紫粉": {
        "colors": ['#A78BFA', '#EC4899'],
        "description": "优雅浪漫，现代感强"
    },
    "深邃蓝绿": {
        "colors": ['#3B82F6', '#10B981'],
        "description": "专业稳重，商务风格"
    },
    "活力橙黄": {
        "colors": ['#F59E0B', '#EF4444'],
        "description": "活力四射，引人注目"
    },
    "清新绿松": {
        "colors": ['#34D399', '#06B6D4'],
        "description": "清新自然，舒适护眼"
    },
    "典雅紫蓝": {
        "colors": ['#8B5CF6', '#3B82F6'],
        "description": "典雅高贵，科技感十足"
    },
    "温暖粉橙": {
        "colors": ['#FB923C', '#F472B6'],
        "description": "温暖柔和，亲和力强"
    },
    "稳重灰蓝": {
        "colors": ['#64748B', '#0EA5E9'],
        "description": "稳重大气，专业可靠"
    },
    "自然绿黄": {
        "colors": ['#84CC16', '#FACC15'],
        "description": "自然清新，充满活力"
    },
    "科技青紫": {
        "colors": ['#14B8A6', '#A855F7'],
        "description": "科技未来，富有创意"
    }
}

def render_detailed_charts(records: List[UsageRecord], stats: Dict[str, Any]):
    """渲染详细图表"""
    st.markdown("**📊 详细分析图表**")
    
    # Token使用分布饼图
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**🥧 Token使用分布**")
        
        # 创建饼图数据
        token_data = {
            'Token类型': ['输入Token', '输出Token'],
            '数量': [stats['total_input_tokens'], stats['total_output_tokens']]
        }
        
        # 获取当前选中的配色方案
        selected_scheme = st.session_state.get('color_scheme', '经典红蓝')
        colors = COLOR_SCHEMES[selected_scheme]['colors']
        
        # 计算总数和百分比
        total = stats['total_input_tokens'] + stats['total_output_tokens']
        input_percent = (stats['total_input_tokens'] / total * 100) if total > 0 else 0
        output_percent = (stats['total_output_tokens'] / total * 100) if total > 0 else 0
        
        fig_pie = px.pie(
            values=token_data['数量'],
            names=token_data['Token类型'],
            title="Token使用分布",
            color_discrete_sequence=colors
        )
        
        # 自定义显示：同时显示绝对值和百分比
        fig_pie.update_traces(
            textposition='inside',
            texttemplate='%{label}<br>%{value:,}<br>(%{percent})',
            hovertemplate='<b>%{label}</b><br>数量: %{value:,}<br>占比: %{percent}<extra></extra>'
        )
        
        st.plotly_chart(fig_pie, use_container_width=True)
    
    with col2:
        st.markdown("**📈 成本vs Token关系**")
        
        # 创建散点图
        df_records = pd.DataFrame([
            {
                'total_tokens': record.input_tokens + record.output_tokens,
                'cost': record.cost,
                'provider': record.provider,
                'model': record.model_name
            }
            for record in records
        ])
        
        if not df_records.empty:
            fig_scatter = px.scatter(
                df_records,
                x='total_tokens',
                y='cost',
                color='provider',
                hover_data=['model'],
                title="成本与Token使用量关系",
                labels={'total_tokens': 'Token总数', 'cost': '成本(¥)'}
            )
            st.plotly_chart(fig_scatter, use_container_width=True)
    
    # 配色方案选择器 - 放在图表下方
    st.markdown("---")
    st.markdown("**🎨 图表配色方案选择**")
    
    # 创建配色方案选择器
    col_select, col_preview = st.columns([2, 2])
    
    with col_select:
        scheme_options = list(COLOR_SCHEMES.keys())
        current_scheme = st.session_state.get('color_scheme', '经典红蓝')
        
        selected = st.selectbox(
            "选择配色方案",
            options=scheme_options,
            index=scheme_options.index(current_scheme),
            format_func=lambda x: f"{x} - {COLOR_SCHEMES[x]['description']}",
            key='color_scheme_selector'
        )
        
        # 更新session state
        if selected != current_scheme:
            st.session_state['color_scheme'] = selected
            st.rerun()
    
    with col_preview:
        # 显示当前配色预览
        st.markdown("**当前配色预览**")
        preview_colors = COLOR_SCHEMES[st.session_state.get('color_scheme', '经典红蓝')]['colors']
        preview_html = """
        <div style='display: flex; gap: 10px; align-items: center; padding: 10px; background-color: #f8f9fa; border-radius: 8px;'>
        """
        for idx, color in enumerate(preview_colors):
            preview_html += f"""
            <div style='display: flex; flex-direction: column; align-items: center;'>
                <div style='width: 60px; height: 60px; background-color: {color}; border-radius: 8px; border: 2px solid #dee2e6; box-shadow: 0 2px 4px rgba(0,0,0,0.1);'></div>
                <span style='margin-top: 5px; font-size: 11px; color: #6c757d;'>{['输入', '输出'][idx]}</span>
            </div>
            """
        preview_html += "</div>"
        st.markdown(preview_html, unsafe_allow_html=True)
    
    # 展示所有配色方案对比
    with st.expander("🌈 查看所有配色方案对比", expanded=False):
        st.markdown("**所有可用配色方案预览**")
        
        # 使用网格布局展示所有配色方案
        cols_per_row = 3
        scheme_list = list(COLOR_SCHEMES.items())
        
        for i in range(0, len(scheme_list), cols_per_row):
            cols = st.columns(cols_per_row)
            for j, col in enumerate(cols):
                if i + j < len(scheme_list):
                    scheme_name, scheme_data = scheme_list[i + j]
                    with col:
                        # 创建精美的配色卡片
                        card_html = f"""
                        <div style='padding: 15px; background-color: #ffffff; border-radius: 10px; border: 1px solid #e0e0e0; margin-bottom: 10px; box-shadow: 0 2px 6px rgba(0,0,0,0.05);'>
                            <h4 style='margin: 0 0 8px 0; font-size: 16px; color: #2c3e50;'>{scheme_name}</h4>
                            <p style='margin: 0 0 10px 0; font-size: 12px; color: #7f8c8d;'>{scheme_data['description']}</p>
                            <div style='display: flex; gap: 8px;'>
                        """
                        for idx, color in enumerate(scheme_data['colors']):
                            card_html += f"""
                            <div style='flex: 1; display: flex; flex-direction: column; align-items: center;'>
                                <div style='width: 100%; height: 50px; background-color: {color}; border-radius: 6px; border: 1px solid #dee2e6;'></div>
                                <span style='margin-top: 4px; font-size: 10px; color: #95a5a6;'>{color}</span>
                            </div>
                            """
                        card_html += """
                            </div>
                        </div>
                        """
                        st.markdown(card_html, unsafe_allow_html=True)

def render_provider_statistics(stats: Dict[str, Any]):
    """渲染供应商统计"""
    st.markdown("**🏢 供应商统计**")
    
    provider_stats = stats.get('provider_stats', {})
    
    if not provider_stats:
        st.info("暂无供应商统计数据")
        return
    
    # 创建供应商对比表
    provider_df = pd.DataFrame([
        {
            '供应商': provider,
            '成本(¥)': f"{data['cost']:.4f}",
            '调用次数': data['requests'],
            '输入Token': f"{data['input_tokens']:,}",
            '输出Token': f"{data['output_tokens']:,}",
            '平均成本(¥)': f"{data['cost']/data['requests']:.4f}" if data['requests'] > 0 else "0.0000"
        }
        for provider, data in provider_stats.items()
    ])
    
    st.dataframe(provider_df, use_container_width=True)
    
    # 供应商成本对比图
    col1, col2 = st.columns(2)
    
    with col1:
        # 成本对比柱状图
        cost_data = {provider: data['cost'] for provider, data in provider_stats.items()}
        fig_bar = px.bar(
            x=list(cost_data.keys()),
            y=list(cost_data.values()),
            title="各供应商成本对比",
            labels={'x': '供应商', 'y': '成本(¥)'},
            color=list(cost_data.values()),
            color_continuous_scale='Viridis'
        )
        st.plotly_chart(fig_bar, use_container_width=True)
    
    with col2:
        # 调用次数对比
        requests_data = {provider: data['requests'] for provider, data in provider_stats.items()}
        fig_requests = px.bar(
            x=list(requests_data.keys()),
            y=list(requests_data.values()),
            title="各供应商调用次数对比",
            labels={'x': '供应商', 'y': '调用次数'},
            color=list(requests_data.values()),
            color_continuous_scale='Plasma'
        )
        st.plotly_chart(fig_requests, use_container_width=True)

def render_cost_trends(records: List[UsageRecord]):
    """渲染成本趋势图"""
    st.markdown("**📈 成本趋势分析**")
    
    # 按日期聚合数据
    df_records = pd.DataFrame([
        {
            'date': datetime.fromisoformat(record.timestamp).date(),
            'cost': record.cost,
            'tokens': record.input_tokens + record.output_tokens,
            'provider': record.provider
        }
        for record in records
    ])
    
    if df_records.empty:
        st.info("暂无趋势数据")
        return
    
    # 按日期聚合
    daily_stats = df_records.groupby('date').agg({
        'cost': 'sum',
        'tokens': 'sum'
    }).reset_index()
    
    # 创建双轴图表
    fig = make_subplots(
        specs=[[{"secondary_y": True}]],
        subplot_titles=["每日成本和Token使用趋势"]
    )
    
    # 添加成本趋势线
    fig.add_trace(
        go.Scatter(
            x=daily_stats['date'],
            y=daily_stats['cost'],
            mode='lines+markers',
            name='每日成本(¥)',
            line=dict(color='#FF6B6B', width=3)
        ),
        secondary_y=False,
    )
    
    # 添加Token使用趋势线
    fig.add_trace(
        go.Scatter(
            x=daily_stats['date'],
            y=daily_stats['tokens'],
            mode='lines+markers',
            name='每日Token数',
            line=dict(color='#4ECDC4', width=3)
        ),
        secondary_y=True,
    )
    
    # 设置轴标签
    fig.update_xaxes(title_text="日期")
    fig.update_yaxes(title_text="成本(¥)", secondary_y=False)
    fig.update_yaxes(title_text="Token数量", secondary_y=True)
    
    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)

def render_detailed_records_table(records: List[UsageRecord]):
    """渲染详细记录表"""
    st.markdown("**📋 详细使用记录**")
    
    if not records:
        st.info("暂无详细记录")
        return
    
    # 创建记录表格
    records_df = pd.DataFrame([
        {
            '时间': datetime.fromisoformat(record.timestamp).strftime('%Y-%m-%d %H:%M:%S'),
            '供应商': record.provider,
            '模型': record.model_name,
            '输入Token': record.input_tokens,
            '输出Token': record.output_tokens,
            '总Token': record.input_tokens + record.output_tokens,
            '成本(¥)': f"{record.cost:.4f}",
            '会话ID': record.session_id[:12] + '...' if len(record.session_id) > 12 else record.session_id,
            '分析类型': record.analysis_type
        }
        for record in sorted(records, key=lambda x: x.timestamp, reverse=True)
    ])
    
    # 分页显示
    page_size = 20
    total_records = len(records_df)
    total_pages = (total_records + page_size - 1) // page_size
    
    if total_pages > 1:
        page = st.selectbox(f"页面 (共{total_pages}页, {total_records}条记录)", range(1, total_pages + 1))
        start_idx = (page - 1) * page_size
        end_idx = min(start_idx + page_size, total_records)
        display_df = records_df.iloc[start_idx:end_idx]
    else:
        display_df = records_df
    
    st.dataframe(display_df, use_container_width=True)

def load_detailed_records(days: int) -> List[UsageRecord]:
    """加载详细记录"""
    try:
        all_records = config_manager.load_usage_records()
        
        # 过滤时间范围
        cutoff_date = datetime.now() - timedelta(days=days)
        filtered_records = []
        
        for record in all_records:
            try:
                record_date = datetime.fromisoformat(record.timestamp)
                if record_date >= cutoff_date:
                    filtered_records.append(record)
            except:
                continue
        
        return filtered_records
    except Exception as e:
        st.error(f"加载记录失败: {e}")
        return []

def export_statistics_data(days: int):
    """导出统计数据"""
    try:
        stats = config_manager.get_usage_statistics(days)
        records = load_detailed_records(days)
        
        # 创建导出数据
        export_data = {
            'summary': stats,
            'detailed_records': [
                {
                    'timestamp': record.timestamp,
                    'provider': record.provider,
                    'model_name': record.model_name,
                    'input_tokens': record.input_tokens,
                    'output_tokens': record.output_tokens,
                    'cost': record.cost,
                    'session_id': record.session_id,
                    'analysis_type': record.analysis_type
                }
                for record in records
            ]
        }
        
        # 生成文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"token_statistics_{timestamp}.json"
        
        # 提供下载
        st.download_button(
            label="📥 下载统计数据",
            data=json.dumps(export_data, ensure_ascii=False, indent=2),
            file_name=filename,
            mime="application/json"
        )
        
        st.success(f"✅ 统计数据已准备好下载: {filename}")
        
    except Exception as e:
        st.error(f"❌ 导出失败: {str(e)}")

def main():
    """主函数"""
    st.set_page_config(
        page_title="Token统计 - TradingAgents",
        page_icon="💰",
        layout="wide"
    )
    
    render_token_statistics()

if __name__ == "__main__":
    main()