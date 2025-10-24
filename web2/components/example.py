import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# 页面配置
st.set_page_config(
    page_title="Modern Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义 CSS 样式
st.markdown("""
<style>
    /* 隐藏默认的 Streamlit 元素 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* 全局字体和背景 */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* 卡片样式 */
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 1rem;
        box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        color: white;
        margin-bottom: 1rem;
        transition: transform 0.3s ease;
    }

    .metric-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 15px 40px rgba(0,0,0,0.15);
    }

    .metric-value {
        font-size: 2.5rem;
        font-weight: 700;
        margin: 0.5rem 0;
    }

    .metric-label {
        font-size: 0.9rem;
        opacity: 0.9;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    /* 不同颜色的卡片 */
    .card-blue {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }

    .card-green {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
    }

    .card-orange {
        background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
    }

    .card-purple {
        background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
    }

    /* 标题样式 */
    .main-title {
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }

    .subtitle {
        color: #64748b;
        font-size: 1.1rem;
        margin-bottom: 2rem;
    }

    /* 侧边栏样式 */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%);
    }

    /* 按钮样式 */
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 0.75rem 2rem;
        border-radius: 0.5rem;
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
    }

    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
    }

    /* 数据框样式 */
    .dataframe {
        border-radius: 0.5rem;
        overflow: hidden;
    }
</style>
""", unsafe_allow_html=True)

# 侧边栏
with st.sidebar:
    st.markdown("## 🎯 控制面板")
    st.markdown("---")

    date_range = st.date_input(
        "选择日期范围",
        value=(datetime.now() - timedelta(days=30), datetime.now()),
        max_value=datetime.now()
    )

    st.markdown("---")

    category = st.selectbox(
        "数据类别",
        ["销售数据", "用户增长", "营收分析", "产品表现"]
    )

    st.markdown("---")

    refresh = st.button("🔄 刷新数据")

# 主内容区域
st.markdown('<h1 class="main-title">📊 现代化数据仪表板</h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">实时监控您的业务指标和关键数据</p>', unsafe_allow_html=True)

# 指标卡片
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown("""
    <div class="metric-card card-blue">
        <div class="metric-label">总收入</div>
        <div class="metric-value">¥2.4M</div>
        <div style="font-size: 0.9rem; margin-top: 0.5rem;">
            ↑ 12.5% 较上月
        </div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="metric-card card-green">
        <div class="metric-label">新用户</div>
        <div class="metric-value">12,543</div>
        <div style="font-size: 0.9rem; margin-top: 0.5rem;">
            ↑ 8.3% 较上月
        </div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown("""
    <div class="metric-card card-orange">
        <div class="metric-label">转化率</div>
        <div class="metric-value">68.2%</div>
        <div style="font-size: 0.9rem; margin-top: 0.5rem;">
            ↑ 3.1% 较上月
        </div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    st.markdown("""
    <div class="metric-card card-purple">
        <div class="metric-label">活跃用户</div>
        <div class="metric-value">45.2K</div>
        <div style="font-size: 0.9rem; margin-top: 0.5rem;">
            ↑ 15.7% 较上月
        </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# 图表区域
col_left, col_right = st.columns([2, 1])

with col_left:
    st.markdown("### 📈 销售趋势分析")

    # 生成示例数据
    dates = pd.date_range(start='2024-01-01', end='2024-12-31', freq='D')
    df_sales = pd.DataFrame({
        'date': dates,
        'sales': (pd.Series(range(len(dates))) * 10 +
                  pd.Series(range(len(dates))).apply(lambda x: x % 30 * 50) +
                  50000)
    })

    fig = px.area(
        df_sales,
        x='date',
        y='sales',
        title='',
        labels={'sales': '销售额 (¥)', 'date': '日期'}
    )

    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(family='Inter', size=12),
        showlegend=False,
        hovermode='x unified',
        margin=dict(l=0, r=0, t=20, b=0)
    )

    fig.update_traces(
        fillcolor='rgba(102, 126, 234, 0.2)',
        line=dict(color='rgb(102, 126, 234)', width=3)
    )

    st.plotly_chart(fig, use_container_width=True)

with col_right:
    st.markdown("### 🎯 分类占比")

    df_category = pd.DataFrame({
        'category': ['电子产品', '服装', '食品', '图书', '其他'],
        'value': [35, 25, 20, 12, 8]
    })

    fig_pie = px.pie(
        df_category,
        values='value',
        names='category',
        hole=0.5,
        color_discrete_sequence=px.colors.sequential.Purples_r
    )

    fig_pie.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(family='Inter', size=12),
        showlegend=True,
        margin=dict(l=0, r=0, t=20, b=0)
    )

    st.plotly_chart(fig_pie, use_container_width=True)

# 数据表格
st.markdown("### 📋 最近交易记录")

df_transactions = pd.DataFrame({
    '订单号': ['#ORD-001', '#ORD-002', '#ORD-003', '#ORD-004', '#ORD-005'],
    '客户': ['张三', '李四', '王五', '赵六', '钱七'],
    '产品': ['iPhone 15', 'Nike 运动鞋', '咖啡机', 'Python 编程书', '蓝牙耳机'],
    '金额': ['¥7,999', '¥899', '¥1,299', '¥89', '¥599'],
    '状态': ['✅ 已完成', '✅ 已完成', '🚚 配送中', '📦 待发货', '✅ 已完成']
})

st.dataframe(
    df_transactions,
    use_container_width=True,
    hide_index=True,
    height=250
)

# 底部操作按钮
col1, col2, col3 = st.columns([1, 1, 4])

with col1:
    st.button("📥 导出数据")

with col2:
    st.button("📧 发送报告")

st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown("""
<div style='text-align: center; color: #94a3b8; font-size: 0.9rem;'>
    © 2024 Modern Dashboard | Powered by Streamlit
</div>
""", unsafe_allow_html=True)