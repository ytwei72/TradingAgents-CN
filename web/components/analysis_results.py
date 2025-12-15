"""
分析结果管理组件
提供股票分析历史结果的查看和管理功能
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from typing import Dict, List, Any
import json
import os
from pathlib import Path
import hashlib
import logging

# MongoDB相关导入
try:
    from tradingagents.storage.mongodb.report_manager import MongoDBReportManager
    MONGODB_AVAILABLE = True
    print("✅ MongoDB模块导入成功")
except ImportError as e:
    MONGODB_AVAILABLE = False
    print(f"❌ MongoDB模块导入失败: {e}")

# 导入工具模块
from components.component_utils import safe_timestamp_to_datetime
from utils.favorites_tags_manager import (
    load_favorites, save_favorites, load_tags, save_tags,
    add_tag_to_analysis, remove_tag_from_analysis, get_analysis_tags,
    toggle_favorite as favorites_toggle_favorite
)
from config.report_constants import REPORT_DISPLAY_NAMES, get_report_display_name
from web.components.results_display import render_detailed_analysis as _render_detailed_analysis_ref

# 设置日志
logger = logging.getLogger(__name__)

# 从工具模块导入的函数，保留这里的get_analysis_results_dir用于向后兼容
def get_analysis_results_dir():
    """获取分析结果目录"""
    from utils.favorites_tags_manager import get_analysis_results_dir as _get_dir
    return _get_dir()

def load_analysis_results(start_date=None, end_date=None, stock_symbol=None, analyst_type=None,
                         limit=100, search_text=None, tags_filter=None, favorites_only=False):
    """加载分析结果 - 优先从MongoDB加载"""
    all_results = []
    favorites = load_favorites() if favorites_only else []
    tags_data = load_tags()
    mongodb_loaded = False

    # 优先从MongoDB加载数据
    if MONGODB_AVAILABLE:
        try:
            print("🔍 [数据加载] 从MongoDB加载分析结果")
            mongodb_manager = MongoDBReportManager()
            mongodb_results = mongodb_manager.get_all_reports()
            print(f"🔍 [数据加载] MongoDB返回 {len(mongodb_results)} 个结果")

            for mongo_result in mongodb_results:
                # 转换MongoDB结果格式
                result = {
                    'analysis_id': mongo_result.get('analysis_id', ''),
                    'timestamp': mongo_result.get('timestamp', 0),
                    'stock_symbol': mongo_result.get('stock_symbol', ''),
                    'analysts': mongo_result.get('analysts', []),
                    'research_depth': mongo_result.get('research_depth', 1),
                    'status': mongo_result.get('status', 'completed'),
                    'summary': mongo_result.get('summary', ''),
                    'performance': mongo_result.get('performance', {}),
                    'tags': tags_data.get(mongo_result.get('analysis_id', ''), []),
                    'is_favorite': mongo_result.get('analysis_id', '') in favorites,
                    'reports': mongo_result.get('reports', {}),
                    'source': 'mongodb'  # 标记数据来源
                }
                all_results.append(result)

            mongodb_loaded = True
            print(f"✅ 从MongoDB加载了 {len(mongodb_results)} 个分析结果")

        except Exception as e:
            print(f"❌ MongoDB加载失败: {e}")
            logger.error(f"MongoDB加载失败: {e}")
            mongodb_loaded = False
    else:
        print("⚠️ MongoDB不可用，将使用文件系统数据")

    # 只有在MongoDB加载失败或不可用时才从文件系统加载
    if not mongodb_loaded:
        print("🔄 [备用数据源] 从文件系统加载分析结果")

        # 首先尝试从Web界面的保存位置读取
        web_results_dir = get_analysis_results_dir()
        for result_file in web_results_dir.glob("*.json"):
            if result_file.name in ['favorites.json', 'tags.json']:
                continue

            try:
                with open(result_file, 'r', encoding='utf-8') as f:
                    result = json.load(f)

                    # 添加标签信息
                    result['tags'] = tags_data.get(result.get('analysis_id', ''), [])
                    result['is_favorite'] = result.get('analysis_id', '') in favorites
                    result['source'] = 'file_system'  # 标记数据来源

                    all_results.append(result)
            except Exception as e:
                st.warning(f"读取分析结果文件 {result_file.name} 失败: {e}")

        # 然后从实际的分析结果保存位置读取
        project_results_dir = Path(__file__).parent.parent.parent / "data" / "analysis_results" / "detailed"

        if project_results_dir.exists():
            # 遍历股票代码目录
            for stock_dir in project_results_dir.iterdir():
                if not stock_dir.is_dir():
                    continue

                stock_code = stock_dir.name

                # 遍历日期目录
                for date_dir in stock_dir.iterdir():
                    if not date_dir.is_dir():
                        continue

                    date_str = date_dir.name
                    reports_dir = date_dir / "reports"

                    if not reports_dir.exists():
                        continue

                    # 读取所有报告文件
                    reports = {}
                    summary_content = ""

                    for report_file in reports_dir.glob("*.md"):
                        try:
                            with open(report_file, 'r', encoding='utf-8') as f:
                                content = f.read()
                                report_name = report_file.stem
                                reports[report_name] = content

                                # 如果是最终决策报告，提取摘要
                                if report_name == "final_trade_decision":
                                    # 提取前200个字符作为摘要
                                    summary_content = content[:200].replace('#', '').replace('*', '').strip()
                                    if len(content) > 200:
                                        summary_content += "..."

                        except Exception as e:
                            continue

                    if reports:
                        # 解析日期
                        try:
                            analysis_date = datetime.strptime(date_str, '%Y-%m-%d')
                            timestamp = analysis_date.timestamp()
                        except:
                            timestamp = datetime.now().timestamp()

                        # 创建分析结果条目
                        analysis_id = f"{stock_code}_{date_str}_{int(timestamp)}"

                        # 尝试从元数据文件中读取真实的研究深度和分析师信息
                        research_depth = 1
                        analysts = ['market', 'fundamentals', 'trader']  # 默认值

                        metadata_file = date_dir / "analysis_metadata.json"
                        if metadata_file.exists():
                            try:
                                with open(metadata_file, 'r', encoding='utf-8') as f:
                                    metadata = json.load(f)
                                    research_depth = metadata.get('research_depth', 1)
                                    analysts = metadata.get('analysts', analysts)
                            except Exception as e:
                                # 如果读取元数据失败，使用推断逻辑
                                if len(reports) >= 5:
                                    research_depth = 3
                                elif len(reports) >= 3:
                                    research_depth = 2
                        else:
                            # 如果没有元数据文件，使用推断逻辑
                            if len(reports) >= 5:
                                research_depth = 3
                            elif len(reports) >= 3:
                                research_depth = 2

                        result = {
                            'analysis_id': analysis_id,
                            'timestamp': timestamp,
                            'stock_symbol': stock_code,
                            'analysts': analysts,
                            'research_depth': research_depth,
                            'status': 'completed',
                            'summary': summary_content,
                            'performance': {},
                            'tags': tags_data.get(analysis_id, []),
                            'is_favorite': analysis_id in favorites,
                            'reports': reports,  # 保存所有报告内容
                            'source': 'file_system'  # 标记数据来源
                        }

                        all_results.append(result)

        print(f"🔄 [备用数据源] 从文件系统加载了 {len(all_results)} 个分析结果")
    
    # 过滤结果
    filtered_results = []
    for result in all_results:
        # 收藏过滤
        if favorites_only and not result.get('is_favorite', False):
            continue
            
        # 时间过滤
        if start_date or end_date:
            result_time = safe_timestamp_to_datetime(result.get('timestamp', 0))
            if start_date and result_time.date() < start_date:
                continue
            if end_date and result_time.date() > end_date:
                continue
        
        # 股票代码过滤
        if stock_symbol and stock_symbol.upper() not in result.get('stock_symbol', '').upper():
            continue
        
        # 分析师类型过滤
        if analyst_type and analyst_type not in result.get('analysts', []):
            continue
            
        # 文本搜索过滤
        if search_text:
            search_text = search_text.lower()
            searchable_text = f"{result.get('stock_symbol', '')} {result.get('summary', '')} {' '.join(result.get('analysts', []))}".lower()
            if search_text not in searchable_text:
                continue
                
        # 标签过滤
        if tags_filter:
            result_tags = result.get('tags', [])
            if not any(tag in result_tags for tag in tags_filter):
                continue
        
        filtered_results.append(result)
    
    # 按时间倒序排列 - 使用安全的时间戳转换函数确保类型一致
    filtered_results.sort(key=lambda x: safe_timestamp_to_datetime(x.get('timestamp', 0)), reverse=True)
    
    # 限制数量
    return filtered_results[:limit]

def render_analysis_results():
    """渲染分析结果管理界面"""
    
    # 检查权限
    try:
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(__file__)))
        from utils.auth_manager import auth_manager
        
        if not auth_manager or not auth_manager.check_permission("analysis"):
            st.error("❌ 您没有权限访问分析结果")
            st.info("💡 提示：分析结果功能需要 'analysis' 权限")
            return
    except Exception as e:
        st.error(f"❌ 权限检查失败: {e}")
        return
    
    st.title("📊 分析结果历史记录")
    
    # 侧边栏过滤选项
    with st.sidebar:
        st.header("🔍 搜索与过滤")
        
        # 文本搜索
        search_text = st.text_input("🔍 关键词搜索", placeholder="搜索股票代码、摘要内容...")
        
        # 收藏过滤
        favorites_only = st.checkbox("⭐ 仅显示收藏")
        
        # 日期范围选择
        date_range = st.selectbox(
            "📅 时间范围",
            ["最近1天", "最近3天", "最近7天", "最近30天", "自定义"],
            index=2
        )
        
        if date_range == "自定义":
            start_date = st.date_input("开始日期", datetime.now() - timedelta(days=7))
            end_date = st.date_input("结束日期", datetime.now())
        else:
            days_map = {"最近1天": 1, "最近3天": 3, "最近7天": 7, "最近30天": 30}
            days = days_map[date_range]
            end_date = datetime.now().date()
            start_date = (datetime.now() - timedelta(days=days)).date()
        
        # 股票代码过滤
        stock_filter = st.text_input("📈 股票代码", placeholder="如: 000001, AAPL")
        
        # 分析师类型过滤
        analyst_filter = st.selectbox(
            "👥 分析师类型",
            ["全部", "market_analyst", "social_media_analyst", "news_analyst", "fundamental_analyst"],
            help="注意：社交媒体分析师仅适用于美股和港股，A股分析中不包含此类型"
        )
        
        if analyst_filter == "全部":
            analyst_filter = None
            
        # 标签过滤
        all_tags = set()
        tags_data = load_tags()
        for tag_list in tags_data.values():
            all_tags.update(tag_list)
        
        if all_tags:
            selected_tags = st.multiselect("🏷️ 标签过滤", sorted(all_tags))
        else:
            selected_tags = []
    
    # 加载分析结果
    results = load_analysis_results(
        start_date=start_date,
        end_date=end_date,
        stock_symbol=stock_filter if stock_filter else None,
        analyst_type=analyst_filter,
        limit=200,
        search_text=search_text if search_text else None,
        tags_filter=selected_tags if selected_tags else None,
        favorites_only=favorites_only
    )
    
    if not results:
        st.warning("📭 未找到符合条件的分析结果")
        return
    
    # 显示统计概览
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📊 总分析数", len(results))
    
    with col2:
        unique_stocks = len(set(result.get('stock_symbol', 'unknown') for result in results))
        st.metric("📈 分析股票", unique_stocks)
    
    with col3:
        successful_analyses = sum(1 for result in results if result.get('status') == 'completed')
        success_rate = (successful_analyses / len(results) * 100) if results else 0
        st.metric("✅ 成功率", f"{success_rate:.1f}%")
    
    with col4:
        favorites_count = sum(1 for result in results if result.get('is_favorite', False))
        st.metric("⭐ 收藏数", favorites_count)
    
    # 保留需要的功能按钮，移除不需要的功能
    tab1, tab2, tab3 = st.tabs([
        "📋 结果列表", "📈 统计图表", "📊 详细分析"
    ])
    
    with tab1:
        render_results_list(results)
    
    with tab2:
        render_results_charts(results)
    
    with tab3:
        render_analysis_result_selector(results)

def render_results_list(results: List[Dict[str, Any]]):
    """渲染分析结果列表"""
    
    st.subheader("📋 分析结果列表")
    
    # 排序选项
    col1, col2 = st.columns([2, 1])
    with col1:
        sort_by = st.selectbox("排序方式", ["时间倒序", "时间正序", "股票代码", "成功率"])
    with col2:
        view_mode = st.selectbox("显示模式", ["卡片视图", "表格视图"])
    
    # 排序结果
    if sort_by == "时间正序":
        results.sort(key=lambda x: safe_timestamp_to_datetime(x.get('timestamp', 0)))
    elif sort_by == "股票代码":
        results.sort(key=lambda x: x.get('stock_symbol', ''))
    elif sort_by == "成功率":
        results.sort(key=lambda x: 1 if x.get('status') == 'completed' else 0, reverse=True)
    
    if view_mode == "表格视图":
        render_results_table(results)
    else:
        render_results_cards(results)

def render_results_table(results: List[Dict[str, Any]]):
    """渲染表格视图"""
    
    # 准备表格数据
    table_data = []
    for result in results:
        table_data.append({
            '时间': safe_timestamp_to_datetime(result.get('timestamp', 0)).strftime('%m-%d %H:%M'),
            '股票': result.get('stock_symbol', 'unknown'),
            '分析师': ', '.join(result.get('analysts', [])[:2]) + ('...' if len(result.get('analysts', [])) > 2 else ''),
            '状态': '✅' if result.get('status') == 'completed' else '❌',
            '收藏': '⭐' if result.get('is_favorite', False) else '',
            '标签': ', '.join(result.get('tags', [])[:2]) + ('...' if len(result.get('tags', [])) > 2 else ''),
            '摘要': (result.get('summary', '')[:50] + '...') if len(result.get('summary', '')) > 50 else result.get('summary', '')
        })
    
    if table_data:
        df = pd.DataFrame(table_data)
        st.dataframe(df, use_container_width=True)

def render_results_cards(results: List[Dict[str, Any]]):
    """渲染卡片视图"""
    
    # 分页设置
    page_size = st.selectbox("每页显示", [5, 10, 20, 50], index=1)
    total_pages = (len(results) + page_size - 1) // page_size
    
    if total_pages > 1:
        page = st.number_input("页码", min_value=1, max_value=total_pages, value=1) - 1
    else:
        page = 0
    
    # 获取当前页数据
    start_idx = page * page_size
    end_idx = min(start_idx + page_size, len(results))
    page_results = results[start_idx:end_idx]
    
    # 显示结果卡片
    for i, result in enumerate(page_results):
        analysis_id = result.get('analysis_id', '')
        
        with st.container():
            # 卡片头部
            col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
            
            with col1:
                st.markdown(f"### 📊 {result.get('stock_symbol', 'unknown')}")
                st.caption(f"🕐 {safe_timestamp_to_datetime(result.get('timestamp', 0)).strftime('%Y-%m-%d %H:%M:%S')}")
            
            with col2:
                # 收藏按钮
                is_favorite = result.get('is_favorite', False)
                if st.button("⭐" if is_favorite else "☆", key=f"fav_{start_idx + i}"):
                    toggle_favorite(analysis_id)
                    st.rerun()
            
            with col3:
                # 查看详情按钮
                result_id = result.get('_id') or result.get('analysis_id') or f"result_{start_idx + i}"
                current_expanded = st.session_state.get('expanded_result_id') == result_id
                button_text = "🔼 收起" if current_expanded else "👁️ 详情"

                if st.button(button_text, key=f"view_{start_idx + i}"):
                    if current_expanded:
                        # 如果当前已展开，则收起
                        st.session_state['expanded_result_id'] = None
                    else:
                        # 展开当前结果的详情
                        st.session_state['expanded_result_id'] = result_id
                        st.session_state['selected_result_for_detail'] = result
                    st.rerun()
            
            with col4:
                # 状态显示
                status_icon = "✅" if result.get('status') == 'completed' else "❌"
                st.markdown(f"**状态**: {status_icon}")
            
            # 卡片内容
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.write(f"**分析师**: {', '.join(result.get('analysts', []))}")
                st.write(f"**研究深度**: {result.get('research_depth', 'unknown')}")

                # 显示分析摘要
                if result.get('summary'):
                    summary = result['summary'][:150] + "..." if len(result['summary']) > 150 else result['summary']
                    st.write(f"**摘要**: {summary}")
            
            with col2:
                # 显示标签
                tags = result.get('tags', [])
                if tags:
                    st.write("**标签**:")
                    for tag in tags[:3]:  # 最多显示3个标签
                        st.markdown(f"`{tag}`")
                    if len(tags) > 3:
                        st.caption(f"还有 {len(tags) - 3} 个标签...")

            # 显示折叠详情
            result_id = result.get('_id') or result.get('analysis_id') or f"result_{start_idx + i}"
            if st.session_state.get('expanded_result_id') == result_id:
                show_expanded_detail(result)

            st.divider()
    
    # 显示分页信息
    if total_pages > 1:
        st.info(f"第 {page + 1} 页，共 {total_pages} 页，总计 {len(results)} 条记录")
    
    # 注意：详情现在以折叠方式显示在每个结果下方

# 弹窗功能已移除，详情现在以折叠方式显示

def toggle_favorite(analysis_id):
    """切换收藏状态（向后兼容包装函数）"""
    return favorites_toggle_favorite(analysis_id)

def render_results_comparison(results: List[Dict[str, Any]]):
    """渲染结果对比功能"""
    
    st.subheader("🔄 分析结果对比")
    
    if len(results) < 2:
        st.warning("至少需要2个分析结果才能进行对比")
        return
    
    # 选择要对比的结果
    col1, col2 = st.columns(2)
    
    result_options = []
    for i, result in enumerate(results[:20]):  # 限制选项数量
        option = f"{result.get('stock_symbol', 'unknown')} - {safe_timestamp_to_datetime(result.get('timestamp', 0)).strftime('%m-%d %H:%M')}"
        result_options.append((option, i))
    
    with col1:
        st.write("**选择结果A**")
        selected_a = st.selectbox("结果A", result_options, format_func=lambda x: x[0], key="compare_a")
        result_a = results[selected_a[1]]
    
    with col2:
        st.write("**选择结果B**")
        selected_b = st.selectbox("结果B", result_options, format_func=lambda x: x[0], key="compare_b")
        result_b = results[selected_b[1]]
    
    if selected_a[1] == selected_b[1]:
        st.warning("请选择不同的分析结果进行对比")
        return
    
    # 对比显示
    st.markdown("---")
    
    # 基本信息对比
    st.subheader("📋 基本信息对比")
    
    comparison_data = {
        '项目': ['股票代码', '分析时间', '分析师', '研究深度', '状态'],
        '结果A': [
            result_a.get('stock_symbol', 'unknown'),
            safe_timestamp_to_datetime(result_a.get('timestamp', 0)).strftime('%Y-%m-%d %H:%M'),
            ', '.join(result_a.get('analysts', [])),
            str(result_a.get('research_depth', 'unknown')),
            '完成' if result_a.get('status') == 'completed' else '失败'
        ],
        '结果B': [
            result_b.get('stock_symbol', 'unknown'),
            safe_timestamp_to_datetime(result_b.get('timestamp', 0)).strftime('%Y-%m-%d %H:%M'),
            ', '.join(result_b.get('analysts', [])),
            str(result_b.get('research_depth', 'unknown')),
            '完成' if result_b.get('status') == 'completed' else '失败'
        ]
    }
    
    df_comparison = pd.DataFrame(comparison_data)
    st.dataframe(df_comparison, use_container_width=True)
    
    # 摘要对比
    if result_a.get('summary') or result_b.get('summary'):
        st.subheader("📝 分析摘要对比")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**结果A摘要**")
            st.text_area("", value=result_a.get('summary', '暂无摘要'), height=200, key="summary_a", disabled=True)
        
        with col2:
            st.write("**结果B摘要**")
            st.text_area("", value=result_b.get('summary', '暂无摘要'), height=200, key="summary_b", disabled=True)
    
    # 性能对比
    perf_a = result_a.get('performance', {})
    perf_b = result_b.get('performance', {})
    
    if perf_a or perf_b:
        st.subheader("⚡ 性能指标对比")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**结果A性能**")
            if perf_a:
                st.json(perf_a)
            else:
                st.info("暂无性能数据")
        
        with col2:
            st.write("**结果B性能**")
            if perf_b:
                st.json(perf_b)
            else:
                st.info("暂无性能数据")

def render_results_charts(results: List[Dict[str, Any]]):
    """渲染分析结果统计图表"""
    
    st.subheader("📈 统计图表")
    
    # 按股票统计
    st.subheader("📊 按股票统计")
    stock_counts = {}
    for result in results:
        stock = result.get('stock_symbol', 'unknown')
        stock_counts[stock] = stock_counts.get(stock, 0) + 1
    
    if stock_counts:
        # 只显示前10个最常分析的股票
        top_stocks = sorted(stock_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        stocks = [item[0] for item in top_stocks]
        counts = [item[1] for item in top_stocks]
        
        fig_bar = px.bar(
            x=stocks,
            y=counts,
            title="最常分析的股票 (前10名)",
            labels={'x': '股票代码', 'y': '分析次数'},
            color=counts,
            color_continuous_scale='viridis'
        )
        st.plotly_chart(fig_bar, use_container_width=True)
    
    # 按时间统计
    st.subheader("📅 每日分析趋势")
    daily_results = {}
    for result in results:
        date_str = safe_timestamp_to_datetime(result.get('timestamp', 0)).strftime('%Y-%m-%d')
        daily_results[date_str] = daily_results.get(date_str, 0) + 1
    
    if daily_results:
        dates = sorted(daily_results.keys())
        counts = [daily_results[date] for date in dates]
        
        fig_line = go.Figure()
        fig_line.add_trace(go.Scatter(
            x=dates,
            y=counts,
            mode='lines+markers',
            name='每日分析数',
            line=dict(color='#2E8B57', width=3),
            marker=dict(size=8, color='#FF6B6B'),
            fill='tonexty'
        ))
        fig_line.update_layout(
            title="每日分析趋势",
            xaxis_title="日期",
            yaxis_title="分析数量",
            hovermode='x unified'
        )
        st.plotly_chart(fig_line, use_container_width=True)
    
    # 按分析师类型统计
    st.subheader("👥 分析师使用分布")
    analyst_counts = {}
    for result in results:
        analysts = result.get('analysts', [])
        for analyst in analysts:
            analyst_counts[analyst] = analyst_counts.get(analyst, 0) + 1
    
    if analyst_counts:
        fig_pie = px.pie(
            values=list(analyst_counts.values()),
            names=list(analyst_counts.keys()),
            title="分析师使用分布",
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        st.plotly_chart(fig_pie, use_container_width=True)
    
    # 成功率统计
    st.subheader("✅ 分析成功率统计")
    success_data = {'成功': 0, '失败': 0}
    for result in results:
        if result.get('status') == 'completed':
            success_data['成功'] += 1
        else:
            success_data['失败'] += 1
    
    if success_data['成功'] + success_data['失败'] > 0:
        fig_success = px.pie(
            values=list(success_data.values()),
            names=list(success_data.keys()),
            title="分析成功率",
            color_discrete_map={'成功': '#4CAF50', '失败': '#F44336'}
        )
        st.plotly_chart(fig_success, use_container_width=True)
    
    # 标签使用统计
    tags_data = load_tags()
    if tags_data:
        st.subheader("🏷️ 标签使用统计")
        tag_counts = {}
        for tag_list in tags_data.values():
            for tag in tag_list:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        
        if tag_counts:
            # 只显示前10个最常用的标签
            top_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            tags = [item[0] for item in top_tags]
            counts = [item[1] for item in top_tags]
            
            fig_tags = px.bar(
                x=tags,
                y=counts,
                title="最常用标签 (前10名)",
                labels={'x': '标签', 'y': '使用次数'},
                color=counts,
                color_continuous_scale='plasma'
            )
            fig_tags.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig_tags, use_container_width=True)

def render_tags_management(results: List[Dict[str, Any]]):
    """渲染标签管理功能"""
    
    st.subheader("🏷️ 标签管理")
    
    # 获取所有标签
    all_tags = set()
    tags_data = load_tags()
    for tag_list in tags_data.values():
        all_tags.update(tag_list)
    
    # 标签统计
    if all_tags:
        st.write("**现有标签统计**")
        tag_counts = {}
        for tag_list in tags_data.values():
            for tag in tag_list:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        
        # 显示标签云
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # 创建标签云可视化
            if tag_counts:
                fig = px.bar(
                    x=list(tag_counts.keys()),
                    y=list(tag_counts.values()),
                    title="标签使用频率",
                    labels={'x': '标签', 'y': '使用次数'}
                )
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.write("**标签列表**")
            for tag, count in sorted(tag_counts.items(), key=lambda x: x[1], reverse=True):
                st.write(f"• {tag} ({count})")
    
    # 批量标签操作
    st.markdown("---")
    st.write("**批量标签操作**")
    
    # 选择要操作的结果
    if results:
        selected_results = st.multiselect(
            "选择分析结果",
            options=range(len(results)),
            format_func=lambda i: f"{results[i].get('stock_symbol', 'unknown')} - {safe_timestamp_to_datetime(results[i].get('timestamp', 0)).strftime('%m-%d %H:%M')}",
            max_selections=10
        )
        
        if selected_results:
            col1, col2 = st.columns(2)
            
            with col1:
                # 添加标签
                new_tag = st.text_input("新标签名称", placeholder="输入标签名称")
                if st.button("➕ 添加标签") and new_tag:
                    for idx in selected_results:
                        analysis_id = results[idx].get('analysis_id', '')
                        if analysis_id:
                            add_tag_to_analysis(analysis_id, new_tag)
                    st.success(f"已为 {len(selected_results)} 个结果添加标签: {new_tag}")
                    st.rerun()
            
            with col2:
                # 移除标签
                if all_tags:
                    remove_tag = st.selectbox("选择要移除的标签", sorted(all_tags))
                    if st.button("➖ 移除标签") and remove_tag:
                        for idx in selected_results:
                            analysis_id = results[idx].get('analysis_id', '')
                            if analysis_id:
                                remove_tag_from_analysis(analysis_id, remove_tag)
                        st.success(f"已从 {len(selected_results)} 个结果移除标签: {remove_tag}")
                        st.rerun()

def render_results_export(results: List[Dict[str, Any]]):
    """渲染分析结果导出功能"""
    
    st.subheader("📤 导出分析结果")
    
    if not results:
        st.warning("没有可导出的分析结果")
        return
    
    # 导出选项
    export_type = st.selectbox("选择导出内容", ["摘要信息", "完整数据"])
    export_format = st.selectbox("选择导出格式", ["CSV", "JSON", "Excel"])
    
    if st.button("📥 导出结果"):
        try:
            if export_type == "摘要信息":
                # 导出摘要信息
                summary_data = []
                for result in results:
                    summary_data.append({
                        '分析时间': safe_timestamp_to_datetime(result.get('timestamp', 0)).strftime('%Y-%m-%d %H:%M:%S'),
                        '股票代码': result.get('stock_symbol', 'unknown'),
                        '分析师': ', '.join(result.get('analysts', [])),
                        '研究深度': result.get('research_depth', 'unknown'),
                        '状态': result.get('status', 'unknown'),
                        '摘要': result.get('summary', '')[:100] + '...' if len(result.get('summary', '')) > 100 else result.get('summary', '')
                    })
                
                if export_format == "CSV":
                    df = pd.DataFrame(summary_data)
                    csv_data = df.to_csv(index=False, encoding='utf-8-sig')
                    
                    st.download_button(
                        label="下载 CSV 文件",
                        data=csv_data,
                        file_name=f"analysis_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
                
                elif export_format == "JSON":
                    json_data = json.dumps(summary_data, ensure_ascii=False, indent=2)
                    
                    st.download_button(
                        label="下载 JSON 文件",
                        data=json_data,
                        file_name=f"analysis_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json"
                    )
                
                elif export_format == "Excel":
                    df = pd.DataFrame(summary_data)
                    
                    from io import BytesIO
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        df.to_excel(writer, index=False, sheet_name='分析摘要')
                    
                    excel_data = output.getvalue()
                    
                    st.download_button(
                        label="下载 Excel 文件",
                        data=excel_data,
                        file_name=f"analysis_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
            
            else:  # 完整数据
                if export_format == "JSON":
                    json_data = json.dumps(results, ensure_ascii=False, indent=2)
                    
                    st.download_button(
                        label="下载完整数据 JSON 文件",
                        data=json_data,
                        file_name=f"analysis_full_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json"
                    )
                else:
                    st.warning("完整数据只支持 JSON 格式导出")
            
            st.success(f"✅ {export_format} 文件准备完成，请点击下载按钮")
            
        except Exception as e:
            st.error(f"❌ 导出失败: {e}")

def render_results_comparison(results: List[Dict[str, Any]]):
    """渲染分析结果对比"""
    
    st.subheader("🔍 分析结果对比")
    
    if len(results) < 2:
        st.info("至少需要2个分析结果才能进行对比")
        return
    
    # 选择要对比的分析结果
    st.write("**选择要对比的分析结果：**")
    
    col1, col2 = st.columns(2)
    
    # 准备选项
    result_options = []
    for i, result in enumerate(results[:20]):  # 限制前20个
        option = f"{result.get('stock_symbol', 'unknown')} - {safe_timestamp_to_datetime(result.get('timestamp', 0)).strftime('%m-%d %H:%M')}"
        result_options.append((option, i))
    
    with col1:
        st.write("**分析结果 A**")
        selected_a = st.selectbox(
            "选择第一个分析结果", 
            result_options, 
            format_func=lambda x: x[0],
            key="compare_a"
        )
        result_a = results[selected_a[1]]
    
    with col2:
        st.write("**分析结果 B**")
        selected_b = st.selectbox(
            "选择第二个分析结果", 
            result_options, 
            format_func=lambda x: x[0],
            key="compare_b"
        )
        result_b = results[selected_b[1]]
    
    if selected_a[1] == selected_b[1]:
        st.warning("请选择不同的分析结果进行对比")
        return
    
    # 基本信息对比
    st.subheader("📊 基本信息对比")
    
    comparison_data = {
        "项目": ["股票代码", "分析时间", "分析师数量", "研究深度", "状态", "标签数量"],
        "分析结果 A": [
            result_a.get('stock_symbol', 'unknown'),
            safe_timestamp_to_datetime(result_a.get('timestamp', 0)).strftime('%Y-%m-%d %H:%M'),
            len(result_a.get('analysts', [])),
            result_a.get('research_depth', 'unknown'),
            "✅ 完成" if result_a.get('status') == 'completed' else "❌ 失败",
            len(result_a.get('tags', []))
        ],
        "分析结果 B": [
            result_b.get('stock_symbol', 'unknown'),
            safe_timestamp_to_datetime(result_b.get('timestamp', 0)).strftime('%Y-%m-%d %H:%M'),
            len(result_b.get('analysts', [])),
            result_b.get('research_depth', 'unknown'),
            "✅ 完成" if result_b.get('status') == 'completed' else "❌ 失败",
            len(result_b.get('tags', []))
        ]
    }
    
    import pandas as pd
    df_comparison = pd.DataFrame(comparison_data)
    st.dataframe(df_comparison, use_container_width=True)
    
    # 性能指标对比
    perf_a = result_a.get('performance', {})
    perf_b = result_b.get('performance', {})
    
    if perf_a or perf_b:
        st.subheader("⚡ 性能指标对比")
        
        # 合并所有性能指标键
        all_perf_keys = set(perf_a.keys()) | set(perf_b.keys())
        
        if all_perf_keys:
            perf_comparison = {
                "指标": list(all_perf_keys),
                "分析结果 A": [perf_a.get(key, "N/A") for key in all_perf_keys],
                "分析结果 B": [perf_b.get(key, "N/A") for key in all_perf_keys]
            }
            
            df_perf = pd.DataFrame(perf_comparison)
            st.dataframe(df_perf, use_container_width=True)
    
    # 标签对比
    tags_a = set(result_a.get('tags', []))
    tags_b = set(result_b.get('tags', []))
    
    if tags_a or tags_b:
        st.subheader("🏷️ 标签对比")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.write("**共同标签**")
            common_tags = tags_a & tags_b
            if common_tags:
                for tag in common_tags:
                    st.markdown(f"✅ `{tag}`")
            else:
                st.write("无共同标签")
        
        with col2:
            st.write("**仅在结果A中**")
            only_a = tags_a - tags_b
            if only_a:
                for tag in only_a:
                    st.markdown(f"🔵 `{tag}`")
            else:
                st.write("无独有标签")
        
        with col3:
            st.write("**仅在结果B中**")
            only_b = tags_b - tags_a
            if only_b:
                for tag in only_b:
                    st.markdown(f"🔴 `{tag}`")
            else:
                st.write("无独有标签")
    
    # 摘要对比
    summary_a = result_a.get('summary', '')
    summary_b = result_b.get('summary', '')
    
    if summary_a or summary_b:
        st.subheader("📝 分析摘要对比")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**分析结果 A 摘要**")
            if summary_a:
                st.markdown(summary_a)
            else:
                st.write("无摘要")
        
        with col2:
            st.write("**分析结果 B 摘要**")
            if summary_b:
                st.markdown(summary_b)
            else:
                st.write("无摘要")
    
    # 详细内容对比
    st.subheader("📊 详细内容对比")
    
    # 定义要对比的关键字段
    comparison_fields = [
        ('market_report', '📈 市场技术分析'),
        ('fundamentals_report', '💰 基本面分析'),
        ('sentiment_report', '💭 市场情绪分析'),
        ('news_report', '📰 新闻事件分析'),
        ('risk_assessment', '⚠️ 风险评估'),
        ('investment_plan', '📋 投资建议'),
        ('final_trade_decision', '🎯 最终交易决策')
    ]
    
    # 创建对比标签页
    available_fields = []
    for field_key, field_name in comparison_fields:
        if (field_key in result_a and result_a[field_key]) or (field_key in result_b and result_b[field_key]):
            available_fields.append((field_key, field_name))
    
    if available_fields:
        tabs = st.tabs([field_name for _, field_name in available_fields])
        
        for i, (tab, (field_key, field_name)) in enumerate(zip(tabs, available_fields)):
            with tab:
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**分析结果 A**")
                    content_a = result_a.get(field_key, '')
                    if content_a:
                        if isinstance(content_a, str):
                            st.markdown(content_a)
                        else:
                            st.write(content_a)
                    else:
                        st.write("无此项分析")
                
                with col2:
                    st.write("**分析结果 B**")
                    content_b = result_b.get(field_key, '')
                    if content_b:
                        if isinstance(content_b, str):
                            st.markdown(content_b)
                        else:
                            st.write(content_b)
                    else:
                        st.write("无此项分析")

def render_analysis_result_selector(results: List[Dict[str, Any]]):
    """渲染分析结果选择器与详细信息
    
    这是一个完整的UI组件，包含：
    - 结果选择器（从多个分析结果中选择）
    - 基本信息展示（股票代码、分析师、时间、状态等）
    - 标签和摘要显示
    - 性能指标
    - 完整分析报告（通过复选框展开，调用 results_display.render_detailed_analysis）
    
    注意：此函数与 results_display.render_detailed_analysis 不同：
    - 此函数接收结果列表，提供选择功能
    - results_display.render_detailed_analysis 接收单个状态字典，只渲染报告内容
    """
    
    st.subheader("📊 详细分析")
    
    if not results:
        st.info("没有可分析的数据")
        return
    
    # 选择要查看的分析结果
    result_options = []
    for i, result in enumerate(results[:50]):  # 显示前50个
        option = f"{result.get('stock_symbol', 'unknown')} - {safe_timestamp_to_datetime(result.get('timestamp', 0)).strftime('%m-%d %H:%M')}"
        result_options.append((option, i))
    
    if result_options:
        selected_option = st.selectbox(
            "选择分析结果", 
            result_options, 
            format_func=lambda x: x[0]
        )
        selected_result = results[selected_option[1]]
        
        # 显示基本信息
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("股票代码", selected_result.get('stock_symbol', 'unknown'))
            st.metric("分析师数量", len(selected_result.get('analysts', [])))
        
        with col2:
            analysis_time = safe_timestamp_to_datetime(selected_result.get('timestamp', 0))
            st.metric("分析时间", analysis_time.strftime('%m-%d %H:%M'))
            status = "✅ 完成" if selected_result.get('status') == 'completed' else "❌ 失败"
            st.metric("状态", status)
        
        with col3:
            st.metric("研究深度", selected_result.get('research_depth', 'unknown'))
            tags = selected_result.get('tags', [])
            st.metric("标签数量", len(tags))
        
        # 显示标签
        if tags:
            st.write("**标签**:")
            tag_cols = st.columns(min(len(tags), 5))
            for i, tag in enumerate(tags):
                with tag_cols[i % 5]:
                    st.markdown(f"`{tag}`")
        
        # 显示分析摘要
        if selected_result.get('summary'):
            st.subheader("📝 分析摘要")
            st.markdown(selected_result['summary'])
        
        # 显示性能指标
        performance = selected_result.get('performance', {})
        if performance:
            st.subheader("⚡ 性能指标")
            perf_cols = st.columns(len(performance))
            for i, (key, value) in enumerate(performance.items()):
                with perf_cols[i]:
                    st.metric(key.replace('_', ' ').title(), f"{value:.2f}" if isinstance(value, (int, float)) else str(value))
        
        # 显示完整分析结果（复用 results_display.render_detailed_analysis 渲染详细报告）
        if st.checkbox("显示完整分析结果"):
            state: Dict[str, Any] = {}
            if isinstance(selected_result.get('reports'), dict) and selected_result['reports']:
                state = selected_result['reports']
            elif isinstance(selected_result.get('full_data'), dict) and selected_result['full_data']:
                state = selected_result['full_data']
            else:
                candidate_keys = [
                    'market_report', 'fundamentals_report', 'sentiment_report', 'news_report',
                    'risk_assessment', 'investment_plan', 'investment_debate_state',
                    'trader_investment_plan', 'risk_debate_state', 'final_trade_decision'
                ]
                for k in candidate_keys:
                    if k in selected_result and selected_result[k]:
                        state[k] = selected_result[k]

            if state:
                _render_detailed_analysis_ref(state)
            else:
                st.info("暂无详细分析报告")

def save_analysis_result(analysis_id: str, stock_symbol: str, analysts: List[str],
                        research_depth: int, result_data: Dict, status: str = "completed"):
    """保存分析结果
    仅保留：保存到文件系统，mongo数据库保存功能移除，在此前流程中已保存
    TODO： 需要合并两个保存结果的函数，避免重复代码
    """

    try:
        from tradingagents.utils.async_progress_tracker import safe_serialize

        # 创建结果条目，使用安全序列化
        result_entry = {
            'analysis_id': analysis_id,
            'timestamp': datetime.now().timestamp(),
            'stock_symbol': stock_symbol,
            'analysts': analysts,
            'research_depth': research_depth,
            'status': status,
            'summary': safe_serialize(result_data.get('summary', '')),
            'performance': safe_serialize(result_data.get('performance', {})),
            'full_data': safe_serialize(result_data)
        }

        # 1. 保存到文件系统（保持兼容性）
        results_dir = get_analysis_results_dir()
        result_file = results_dir / f"{analysis_id}.json"

        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(result_entry, f, ensure_ascii=False, indent=2)

        return True

    except Exception as e:
        print(f"❌ [保存分析结果] 保存失败: {e}")
        logger.error(f"保存分析结果异常: {e}")
        return False

def show_expanded_detail(result):
    """显示展开的详情内容"""

    # 创建详情容器
    with st.container():
        st.markdown("---")

        # 统一转换为 results_display.render_detailed_analysis 期望的 state 结构
        state: Dict[str, Any] = {}

        if isinstance(result.get('reports'), dict) and result['reports']:
            # 直接使用 reports 作为 state
            state = result['reports']
        elif isinstance(result.get('full_data'), dict) and result['full_data']:
            state = result['full_data']
        else:
            # 回退：将 result 自身可用的分析键收集为 state
            candidate_keys = [
                'market_report', 'fundamentals_report', 'sentiment_report', 'news_report',
                'risk_assessment', 'investment_plan', 'investment_debate_state',
                'trader_investment_plan', 'risk_debate_state', 'final_trade_decision'
            ]
            for k in candidate_keys:
                if k in result and result[k]:
                    state[k] = result[k]

        if not state:
            # 没有任何可展示的详细内容
            if result.get('summary'):
                st.subheader("📝 分析摘要")
                st.markdown(result['summary'])
            st.info("暂无详细分析报告")
            return

        # 使用标准的详细分析渲染方法，避免重复标题
        _render_detailed_analysis_ref(state)

        st.markdown("---")