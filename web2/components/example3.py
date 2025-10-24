import streamlit as st
from streamlit_option_menu import option_menu
import pandas as pd
import plotly.express as px

# 页面配置
st.set_page_config(
    page_title="数据分析平台",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 侧边栏导航菜单
with st.sidebar:
    st.image("https://streamlit.io/images/brand/streamlit-mark-color.png", width=100)
    st.title("数据分析平台")

    selected = option_menu(
        menu_title="主菜单",
        options=["首页", "数据分析", "图表展示", "数据表格", "设置"],
        icons=["house-fill", "graph-up", "bar-chart-fill", "table", "gear-fill"],
        menu_icon="cast",
        default_index=0,
        styles={
            "container": {"padding": "5!important", "background-color": "#fafafa"},
            "icon": {"color": "#CC785C", "font-size": "20px"},
            "nav-link": {
                "font-size": "16px",
                "text-align": "left",
                "margin": "0px",
                "--hover-color": "#F0E6DC",
            },
            "nav-link-selected": {"background-color": "#CC785C", "color": "white"},
        }
    )

    st.markdown("---")
    st.markdown("### 关于")
    st.info("这是一个使用 Anthropic 主题风格的 Streamlit 应用示例")

# 主页内容
if selected == "首页":
    st.title("🏠 欢迎来到数据分析平台")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            label="总用户数",
            value="1,234",
            delta="12%"
        )

    with col2:
        st.metric(
            label="活跃用户",
            value="856",
            delta="5%"
        )

    with col3:
        st.metric(
            label="转化率",
            value="68%",
            delta="-2%"
        )

    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📈 平台特点")
        st.write("""
        - 🎯 直观的数据可视化
        - 📊 实时数据分析
        - 🔒 安全可靠的数据处理
        - 🚀 快速响应的用户体验
        """)

    with col2:
        st.subheader("🎨 设计理念")
        st.write("""
        本应用采用 Anthropic 风格的主题设计：
        - 温暖的橙棕色调（#CC785C）
        - 简洁的浅色背景
        - 清晰的信息层次
        - 友好的用户界面
        """)

# 数据分析页面
elif selected == "数据分析":
    st.title("📊 数据分析")

    st.subheader("数据概览")

    # 创建示例数据
    df = pd.DataFrame({
        '月份': ['1月', '2月', '3月', '4月', '5月', '6月'],
        '销售额': [120, 145, 168, 192, 215, 238],
        '利润': [45, 58, 72, 85, 98, 112]
    })

    col1, col2 = st.columns([2, 1])

    with col1:
        # 创建折线图
        fig = px.line(df, x='月份', y=['销售额', '利润'],
                      title='销售趋势分析',
                      labels={'value': '金额 (万元)', 'variable': '指标'})
        fig.update_layout(
            plot_bgcolor='#fafafa',
            paper_bgcolor='#fafafa',
            font=dict(color='#191919')
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("### 数据洞察")
        st.success("✅ 销售额持续增长")
        st.info("📈 6个月增长率: 98%")
        st.warning("⚠️ 需关注成本控制")

        if st.button("生成详细报告", type="primary"):
            st.balloons()
            st.success("报告生成成功！")

# 图表展示页面
elif selected == "图表展示":
    st.title("📈 图表展示")

    tab1, tab2, tab3 = st.tabs(["柱状图", "饼图", "散点图"])

    with tab1:
        df_bar = pd.DataFrame({
            '产品': ['产品A', '产品B', '产品C', '产品D', '产品E'],
            '销量': [230, 180, 290, 150, 200]
        })
        fig = px.bar(df_bar, x='产品', y='销量', title='产品销量对比',
                     color='销量', color_continuous_scale='Oranges')
        fig.update_layout(plot_bgcolor='#fafafa', paper_bgcolor='#fafafa')
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        df_pie = pd.DataFrame({
            '类别': ['电子产品', '服装', '食品', '图书', '其他'],
            '占比': [35, 25, 20, 12, 8]
        })
        fig = px.pie(df_pie, values='占比', names='类别', title='销售类别分布',
                     color_discrete_sequence=px.colors.sequential.Oranges)
        fig.update_layout(paper_bgcolor='#fafafa')
        st.plotly_chart(fig, use_container_width=True)

    with tab3:
        df_scatter = pd.DataFrame({
            'X值': [10, 20, 30, 40, 50, 60],
            'Y值': [15, 35, 45, 55, 70, 85],
            '分类': ['A', 'A', 'B', 'B', 'C', 'C']
        })
        fig = px.scatter(df_scatter, x='X值', y='Y值', color='分类',
                         title='数据分布图',
                         color_discrete_sequence=['#CC785C', '#9B5C47', '#7A4638'])
        fig.update_layout(plot_bgcolor='#fafafa', paper_bgcolor='#fafafa')
        st.plotly_chart(fig, use_container_width=True)

# 数据表格页面
elif selected == "数据表格":
    st.title("📋 数据表格")

    # 创建示例数据表
    df_table = pd.DataFrame({
        '编号': range(1, 11),
        '姓名': [f'用户{i}' for i in range(1, 11)],
        '年龄': [25, 32, 28, 45, 35, 29, 41, 33, 27, 38],
        '城市': ['北京', '上海', '广州', '深圳', '杭州', '成都', '西安', '南京', '武汉', '重庆'],
        '消费金额': [1200, 1800, 1500, 2200, 1900, 1400, 2100, 1600, 1700, 2000]
    })

    st.subheader("用户数据总览")
    st.dataframe(df_table, use_container_width=True, height=400)

    col1, col2 = st.columns(2)

    with col1:
        st.metric("平均消费", f"¥{df_table['消费金额'].mean():.0f}")

    with col2:
        st.metric("总用户数", len(df_table))

    if st.button("下载数据"):
        csv = df_table.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 下载CSV文件",
            data=csv,
            file_name="user_data.csv",
            mime="text/csv"
        )

# 设置页面
elif selected == "设置":
    st.title("⚙️ 系统设置")

    st.subheader("主题配置")

    with st.expander("🎨 Anthropic 主题配置", expanded=True):
        st.code("""
[theme]
primaryColor = "#CC785C"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F0E6DC"
textColor = "#191919"
font = "sans serif"
        """, language="toml")

        st.info("💡 将上述配置保存到 `.streamlit/config.toml` 文件中")

    st.subheader("用户偏好设置")

    col1, col2 = st.columns(2)

    with col1:
        st.checkbox("启用暗色模式", value=False)
        st.checkbox("显示数据网格线", value=True)
        st.checkbox("启用动画效果", value=True)

    with col2:
        st.selectbox("语言选择", ["中文", "English", "日本語"])
        st.slider("图表默认高度", 300, 800, 500)
        st.selectbox("数据刷新频率", ["实时", "5秒", "30秒", "1分钟"])

    if st.button("保存设置", type="primary"):
        st.success("✅ 设置已保存！")
        st.balloons()

# 页脚
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666;'>
        <p>© 2024 数据分析平台 | Powered by Streamlit & Anthropic Theme</p>
    </div>
    """,
    unsafe_allow_html=True
)