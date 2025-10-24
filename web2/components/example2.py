import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from streamlit_option_menu import option_menu

# 页面配置
st.set_page_config(
    page_title="现代化仪表板",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义CSS样式
st.markdown('''
<style>
    /* 隐藏默认元素 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* 主背景 */
    .main {
        background: #FFFFFF;
        padding: 2rem;
    }

    /* 标题样式 */
    .title {
        font-size: 3rem;
        font-weight: bold;
        color: #262730;
        text-align: center;
        margin-bottom: 2rem;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
    }

    /* 卡片容器 */
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 15px;
        box-shadow: 0 8px 16px rgba(0,0,0,0.1);
        margin: 1rem 0;
        transition: transform 0.3s ease;
    }

    .metric-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 12px 24px rgba(0,0,0,0.15);
    }

    /* 指标数字 */
    .metric-value {
        font-size: 2.5rem;
        font-weight: bold;
        color: #262730;
        margin: 0;
    }

    .metric-label {
        font-size: 1rem;
        color: #666;
        margin-top: 0.5rem;
    }

    /* 侧边栏样式 */
    [data-testid="stSidebar"] {
        background-color: #F0F2F6;
    }

    /* 按钮美化 */
    .stButton>button {
        background: #202123;
        color: white;
        border-radius: 25px;
        border: none;
        padding: 0.75rem 2rem;
        font-size: 1rem;
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }

    .stButton>button:hover {
        transform: scale(1.05);
        box-shadow: 0 6px 12px rgba(0,0,0,0.3);
    }

    /* 图表容器 */
    .chart-container {
        background: white;
        padding: 1.5rem;
        border-radius: 15px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        margin: 1rem 0;
    }
</style>
''', unsafe_allow_html=True)

# 主标题
st.markdown('<h1 class="title">📊 现代化数据仪表板</h1>', unsafe_allow_html=True)

# 侧边栏
with st.sidebar:
    selected = option_menu(
        menu_title="控制面板",  # required
        options=["概览", "详细分析", "趋势预测"],  # required
        icons=["house", "clipboard-data", "graph-up-arrow"],  # optional
        menu_icon="cast",  # optional
        default_index=0,  # optional
        styles={
            "container": {"padding": "0!important", "background-color": "#EFEFEF"},
            "icon": {"color": "#333333", "font-size": "25px"}, 
            "nav-link": {"font-size": "16px", "text-align": "left", "margin":"0px", "--hover-color": "#DCDCDC"},
            "nav-link-selected": {"background-color": "#DCDCDC"},
        }
    )

    date_range = st.date_input(
        "选择日期范围",
        value=(pd.Timestamp('2024-01-01'), pd.Timestamp('2024-12-31'))
    )

    st.markdown("---")
    if st.button("🔄 刷新数据"):
        st.success("数据已刷新!")

# 主内容区域
# KPI指标卡片
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown('''
    <div class="metric-card">
        <p class="metric-value">$125K</p>
        <p class="metric-label">📈 总收入</p>
    </div>
    ''', unsafe_allow_html=True)

with col2:
    st.markdown('''
    <div class="metric-card">
        <p class="metric-value">1,234</p>
        <p class="metric-label">👥 活跃用户</p>
    </div>
    ''', unsafe_allow_html=True)

with col3:
    st.markdown('''
    <div class="metric-card">
        <p class="metric-value">89%</p>
        <p class="metric-label">✅ 满意度</p>
    </div>
    ''', unsafe_allow_html=True)

with col4:
    st.markdown('''
    <div class="metric-card">
        <p class="metric-value">+23%</p>
        <p class="metric-label">📊 增长率</p>
    </div>
    ''', unsafe_allow_html=True)

# 图表区域
st.markdown("<br>", unsafe_allow_html=True)

if selected == "概览":
    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        st.subheader("📈 月度销售趋势")

        # 创建示例数据
        months = ['1月', '2月', '3月', '4月', '5月', '6月']
        sales = [45000, 52000, 48000, 61000, 58000, 67000]

        fig1 = go.Figure()
        fig1.add_trace(go.Scatter(
            x=months, y=sales,
            mode='lines+markers',
            line=dict(color='#202123', width=3),
            marker=dict(size=10, color='#202123'),
            fill='tozeroy',
            fillcolor='rgba(32, 33, 35, 0.1)'
        ))
        fig1.update_layout(
            height=300,
            margin=dict(l=0, r=0, t=0, b=0),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=True, gridcolor='rgba(0,0,0,0.1)')
        )
        st.plotly_chart(fig1, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col_right:
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        st.subheader("🎯 产品分布")

        # 饼图数据
        products = ['产品A', '产品B', '产品C', '产品D']
        values = [35, 25, 25, 15]

        fig2 = go.Figure(data=[go.Pie(
            labels=products,
            values=values,
            hole=0.4,
            marker=dict(colors=['#202123', '#6B7280', '#9CA3AF', '#D1D5DB'])
        )])
        fig2.update_layout(
            height=300,
            margin=dict(l=0, r=0, t=0, b=0),
            paper_bgcolor='rgba(0,0,0,0)',
            showlegend=True
        )
        st.plotly_chart(fig2, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # 数据表格
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    st.subheader("📋 最新订单")

    # 示例数据表
    df = pd.DataFrame({
        '订单ID': ['#1001', '#1002', '#1003', '#1004', '#1005'],
        '客户': ['张三', '李四', '王五', '赵六', '钱七'],
        '金额': ['$1,200', '$850', '$2,100', '$950', '$1,500'],
        '状态': ['✅ 已完成', '⏳ 处理中', '✅ 已完成', '📦 已发货', '⏳ 处理中']
    })

    st.dataframe(df, use_container_width=True, hide_index=True)
    st.markdown('</div>', unsafe_allow_html=True)

elif selected == "详细分析":
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    st.subheader("详细分析页面")
    st.write("这里是详细分析的内容。")
    # 在这里可以添加更多的图表和数据
    st.markdown('</div>', unsafe_allow_html=True)

elif selected == "趋势预测":
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    st.subheader("趋势预测页面")
    st.write("这里是趋势预测的内容。")
    # 在这里可以添加预测模型和图表
    st.markdown('</div>', unsafe_allow_html=True)


# 底部操作按钮
st.markdown("<br>", unsafe_allow_html=True)
col_btn1, col_btn2, col_btn3, col_btn4 = st.columns(4)

with col_btn1:
    if st.button("📥 导出报告", use_container_width=True):
        st.success("报告已导出!")

with col_btn2:
    if st.button("📧 发送邮件", use_container_width=True):
        st.success("邮件已发送!")

with col_btn3:
    if st.button("⚙️ 设置", use_container_width=True):
        st.info("打开设置...")

with col_btn4:
    if st.button("❓ 帮助", use_container_width=True):
        st.info("显示帮助文档...")
