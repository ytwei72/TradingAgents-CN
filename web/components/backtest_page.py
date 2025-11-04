#!/usr/bin/env python3
"""
回测页面组件
用于展示股票分析结果的回测效果
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging
import re

logger = logging.getLogger(__name__)

try:
    from web.utils.mongodb_report_manager import MongoDBReportManager, MONGODB_AVAILABLE
except ImportError:
    MONGODB_AVAILABLE = False
    logger.warning("MongoDB模块不可用")


def get_market_index_code(stock_code: str) -> tuple[str, str]:
    """
    根据股票代码确定对应的大盘指数代码
    
    Args:
        stock_code: 股票代码
        
    Returns:
        (index_code, index_name): 指数代码和名称
    """
    # A股：根据代码前缀判断市场
    if stock_code.startswith(('60', '68', '90')):
        # 上海市场 - 使用上证指数
        return "000001", "上证指数"
    elif stock_code.startswith(('00', '30', '20')):
        # 深圳市场 - 使用深证成指
        return "399001", "深证成指"
    else:
        # 默认使用上证指数
        return "000001", "上证指数"


def parse_stock_data(data_str: str) -> pd.DataFrame:
    """
    解析股票数据字符串为DataFrame
    
    Args:
        data_str: 股票数据字符串（通常包含日期、收盘价等信息）
        
    Returns:
        DataFrame: 包含日期和收盘价的DataFrame
    """
    try:
        # 尝试从字符串中提取数据
        # 数据格式可能是多种，需要灵活处理
        lines = data_str.strip().split('\n')
        
        dates = []
        closes = []
        opens = []
        highs = []
        lows = []
        volumes = []
        
        for line in lines:
            # 跳过空行和标题行
            if not line.strip() or '日期' in line or 'Date' in line or line.startswith('#'):
                continue
            
            # 尝试解析数据行
            # 可能的格式：日期,开盘,最高,最低,收盘,成交量
            parts = [p.strip() for p in line.split(',')]
            if len(parts) < 5:
                parts = [p.strip() for p in line.split('\t')]
            
            if len(parts) >= 5:
                try:
                    date_str = parts[0]
                    # 尝试解析日期
                    try:
                        date = pd.to_datetime(date_str)
                    except:
                        # 如果解析失败，尝试其他格式
                        date = pd.to_datetime(date_str, errors='coerce')
                    
                    if pd.isna(date):
                        continue
                    
                    # 尝试解析数值
                    try:
                        open_price = float(parts[1])
                        high = float(parts[2])
                        low = float(parts[3])
                        close = float(parts[4])
                        volume = float(parts[5]) if len(parts) > 5 else 0
                        
                        dates.append(date)
                        opens.append(open_price)
                        highs.append(high)
                        lows.append(low)
                        closes.append(close)
                        volumes.append(volume)
                    except (ValueError, IndexError):
                        continue
                except Exception:
                    continue
        
        if not dates:
            # 如果解析失败，返回空DataFrame
            return pd.DataFrame()
        
        df = pd.DataFrame({
            'date': dates,
            'open': opens,
            'high': highs,
            'low': lows,
            'close': closes,
            'volume': volumes
        })
        
        df = df.sort_values('date').reset_index(drop=True)
        return df
        
    except Exception as e:
        logger.error(f"解析股票数据失败: {e}")
        return pd.DataFrame()


def get_stock_data_from_api(stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
    """
    从API获取股票数据
    
    Args:
        stock_code: 股票代码
        start_date: 开始日期
        end_date: 结束日期
        
    Returns:
        DataFrame: 股票数据
    """
    try:
        # 尝试直接从数据源管理器获取DataFrame
        from tradingagents.dataflows.data_source_manager import get_data_source_manager
        from tradingagents.utils.stock_utils import StockUtils
        
        manager = get_data_source_manager()
        market_info = StockUtils.get_market_info(stock_code)
        
        if market_info['is_china']:
            # A股：尝试从Tushare适配器直接获取DataFrame
            try:
                from tradingagents.dataflows.tushare_adapter import get_tushare_adapter
                adapter = get_tushare_adapter()
                if adapter and adapter.provider and adapter.provider.connected:
                    df = adapter.provider.get_stock_data(stock_code, start_date, end_date)
                    if df is not None and not df.empty:
                        # 确保列名标准化
                        if 'trade_date' in df.columns:
                            df['date'] = pd.to_datetime(df['trade_date'])
                        elif 'date' not in df.columns:
                            if df.index.name == 'date':
                                df = df.reset_index()
                            elif hasattr(df.index, 'dtype') and pd.api.types.is_datetime64_any_dtype(df.index):
                                # 如果索引是日期类型，重置为列
                                df = df.reset_index()
                                df['date'] = pd.to_datetime(df.index) if 'date' not in df.columns else df['date']
                            else:
                                logger.warning(f"无法从数据中提取日期列，数据列: {list(df.columns)}")
                                return pd.DataFrame()
                        
                        # 标准化列名
                        column_mapping = {
                            'close': 'close',
                            'open': 'open',
                            'high': 'high',
                            'low': 'low',
                            'vol': 'volume',
                            'volume': 'volume',
                            'amount': 'volume'  # 如果只有amount，使用它作为volume
                        }
                        
                        for old_col, new_col in column_mapping.items():
                            if old_col in df.columns and new_col not in df.columns:
                                df[new_col] = df[old_col]
                        
                        # 确保必要的列存在
                        required_cols = ['date', 'close']
                        if all(col in df.columns for col in required_cols):
                            df = df.sort_values('date').reset_index(drop=True)
                            return df
                        else:
                            logger.warning(f"数据缺少必要列，已有列: {list(df.columns)}，需要列: {required_cols}")
                            return pd.DataFrame()
            except Exception as e:
                logger.debug(f"从Tushare适配器获取数据失败: {e}")
        
        # 降级方案：使用统一接口获取字符串数据并解析
        try:
            from tradingagents.dataflows.interface import get_stock_data_by_market
            
            # 获取股票数据字符串
            data_str = get_stock_data_by_market(stock_code, start_date, end_date)
            
            if not data_str or "失败" in data_str or "错误" in data_str:
                logger.warning(f"获取股票数据失败: {data_str}")
                return pd.DataFrame()
            
            # 解析数据
            df = parse_stock_data(data_str)
            return df
        except ImportError as e:
            logger.error(f"导入模块失败: {e}")
            return pd.DataFrame()
        
    except Exception as e:
        logger.error(f"从API获取股票数据失败: {e}")
        return pd.DataFrame()


def get_index_data_from_api(index_code: str, start_date: str, end_date: str) -> pd.DataFrame:
    """
    从API获取指数数据
    
    Args:
        index_code: 指数代码
        start_date: 开始日期
        end_date: 结束日期
        
    Returns:
        DataFrame: 指数数据
    """
    try:
        # 尝试从Tushare适配器直接获取DataFrame
        try:
            from tradingagents.dataflows.tushare_adapter import get_tushare_adapter
            adapter = get_tushare_adapter()
            if adapter and adapter.provider and adapter.provider.connected:
                # 对于指数，可能需要特殊处理
                # 尝试使用指数的标准格式
                if index_code == "000001":
                    # 上证指数：可能需要使用 "000001.SH" 或其他格式
                    index_symbols = ["000001.SH", "000001"]
                elif index_code == "399001":
                    # 深证成指
                    index_symbols = ["399001.SZ", "399001"]
                else:
                    index_symbols = [index_code]
                
                for symbol in index_symbols:
                    try:
                        df = adapter.provider.get_stock_data(symbol, start_date, end_date)
                        if df is not None and not df.empty:
                            # 确保列名标准化
                            if 'trade_date' in df.columns:
                                df['date'] = pd.to_datetime(df['trade_date'])
                            elif 'date' not in df.columns and df.index.name == 'date':
                                df = df.reset_index()
                            
                            # 标准化列名
                            if 'close' in df.columns:
                                df = df.sort_values('date').reset_index(drop=True)
                                return df
                    except Exception:
                        continue
        except Exception as e:
            logger.debug(f"从Tushare适配器获取指数数据失败: {e}")
        
        # 降级方案：使用统一接口获取字符串数据并解析
        from tradingagents.dataflows.interface import get_china_stock_data_unified
        
        # 尝试获取指数数据（使用与股票相同的接口）
        data_str = get_china_stock_data_unified(index_code, start_date, end_date)
        
        if not data_str or "失败" in data_str or "错误" in data_str:
            logger.warning(f"获取指数数据失败: {data_str}")
            return pd.DataFrame()
        
        # 解析数据
        df = parse_stock_data(data_str)
        return df
        
    except Exception as e:
        logger.error(f"从API获取指数数据失败: {e}")
        return pd.DataFrame()


def extract_predicted_price(analysis_result: Dict[str, Any]) -> Optional[float]:
    """
    从分析结果中提取预测价格
    
    Args:
        analysis_result: 分析结果字典
        
    Returns:
        预测价格，如果无法提取则返回None
    """
    try:
        # 尝试从formatted_decision中提取
        formatted_decision = analysis_result.get('formatted_decision', {})
        if isinstance(formatted_decision, dict):
            target_price = formatted_decision.get('target_price')
            if target_price is not None:
                try:
                    if isinstance(target_price, str):
                        # 清理字符串格式的价格
                        clean_price = target_price.replace('$', '').replace('¥', '').replace('￥', '').replace('元', '').strip()
                        return float(clean_price) if clean_price and clean_price.lower() not in ['none', 'null', ''] else None
                    elif isinstance(target_price, (int, float)):
                        return float(target_price)
                except (ValueError, TypeError):
                    pass
        
        # 尝试从reports中提取
        reports = analysis_result.get('reports', {})
        if isinstance(reports, dict):
            # 搜索所有报告中的目标价格
            for report_key, report_content in reports.items():
                if isinstance(report_content, str):
                    # 使用正则表达式提取价格
                    patterns = [
                        r'目标[价位格]*[：:]\s*[¥$￥]?(\d+\.?\d*)',
                        r'目标[价位格]*[：:]\s*(\d+\.?\d*)[元]?',
                        r'target\s*price[：:]\s*[¥$￥]?(\d+\.?\d*)',
                    ]
                    for pattern in patterns:
                        match = re.search(pattern, report_content, re.IGNORECASE)
                        if match:
                            try:
                                return float(match.group(1))
                            except (ValueError, TypeError):
                                continue
        
        return None
        
    except Exception as e:
        logger.error(f"提取预测价格失败: {e}")
        return None


def prepare_backtest_data(
    stock_code: str,
    analysis_date: str,
    predicted_price: Optional[float],
    min_points: int = 30
) -> Dict[str, Any]:
    """
    准备回测数据
    
    Args:
        stock_code: 股票代码
        analysis_date: 分析日期
        predicted_price: 预测价格
        min_points: 最少数据点数
        
    Returns:
        包含股票数据、指数数据和预测数据的字典
    """
    try:
        # 计算日期范围
        analysis_dt = pd.to_datetime(analysis_date)
        today = datetime.now()
        
        # 首先获取分析日期之后的数据
        end_date = today.strftime('%Y-%m-%d')
        start_date_post = (analysis_dt + timedelta(days=1)).strftime('%Y-%m-%d')
        
        # 获取分析日期之后的股票数据
        stock_df_post = get_stock_data_from_api(stock_code, start_date_post, end_date)
        
        # 获取对应的大盘指数代码
        index_code, index_name = get_market_index_code(stock_code)
        index_df_post = get_index_data_from_api(index_code, start_date_post, end_date)
        
        # 如果分析日期后的数据点少于min_points，需要获取分析日期前的数据
        total_points = len(stock_df_post)
        if total_points < min_points:
            # 计算需要获取多少天前的数据
            days_before = (min_points - total_points) + 10  # 多获取一些，以防有缺失数据
            start_date_pre = (analysis_dt - timedelta(days=days_before)).strftime('%Y-%m-%d')
            end_date_pre = analysis_date
            
            # 获取分析日期前的数据
            stock_df_pre = get_stock_data_from_api(stock_code, start_date_pre, end_date_pre)
            index_df_pre = get_index_data_from_api(index_code, start_date_pre, end_date_pre)
            
            # 合并数据（检查是否有date列）
            if not stock_df_pre.empty and 'date' in stock_df_pre.columns:
                if not stock_df_post.empty and 'date' in stock_df_post.columns:
                    stock_df = pd.concat([stock_df_pre, stock_df_post], ignore_index=True)
                    stock_df = stock_df.sort_values('date').reset_index(drop=True)
                else:
                    stock_df = stock_df_pre
            else:
                stock_df = stock_df_post if not stock_df_post.empty else stock_df_pre
            
            if not index_df_pre.empty and 'date' in index_df_pre.columns:
                if not index_df_post.empty and 'date' in index_df_post.columns:
                    index_df = pd.concat([index_df_pre, index_df_post], ignore_index=True)
                    index_df = index_df.sort_values('date').reset_index(drop=True)
                else:
                    index_df = index_df_pre
            else:
                index_df = index_df_post if not index_df_post.empty else index_df_pre
        else:
            stock_df = stock_df_post
            index_df = index_df_post
        
        # 确保数据点不少于min_points（如果数据不足，至少返回现有数据）
        if len(stock_df) < min_points and len(stock_df) > 0:
            # 如果数据仍然不足，尝试获取更多历史数据
            days_before = min_points * 2
            start_date_pre = (analysis_dt - timedelta(days=days_before)).strftime('%Y-%m-%d')
            end_date_pre = analysis_date
            
            stock_df_pre = get_stock_data_from_api(stock_code, start_date_pre, end_date_pre)
            index_df_pre = get_index_data_from_api(index_code, start_date_pre, end_date_pre)
            
            if not stock_df_pre.empty and 'date' in stock_df_pre.columns:
                if not stock_df.empty and 'date' in stock_df.columns:
                    stock_df = pd.concat([stock_df_pre, stock_df], ignore_index=True)
                    stock_df = stock_df.sort_values('date').reset_index(drop=True)
                    stock_df = stock_df.drop_duplicates(subset=['date']).reset_index(drop=True)
                else:
                    stock_df = stock_df_pre
            
            if not index_df_pre.empty and 'date' in index_df_pre.columns:
                if not index_df.empty and 'date' in index_df.columns:
                    index_df = pd.concat([index_df_pre, index_df], ignore_index=True)
                    index_df = index_df.sort_values('date').reset_index(drop=True)
                    index_df = index_df.drop_duplicates(subset=['date']).reset_index(drop=True)
                else:
                    index_df = index_df_pre
        
        # 标记分析日期（只在有数据时）
        analysis_date_dt = pd.to_datetime(analysis_date)
        if not stock_df.empty and 'date' in stock_df.columns:
            stock_df['is_after_analysis'] = stock_df['date'] >= analysis_date_dt
        elif not stock_df.empty:
            # 如果没有date列，尝试创建
            logger.warning(f"股票数据缺少date列，尝试修复...")
            if 'trade_date' in stock_df.columns:
                stock_df['date'] = pd.to_datetime(stock_df['trade_date'])
                stock_df['is_after_analysis'] = stock_df['date'] >= analysis_date_dt
            else:
                logger.error(f"股票数据格式异常，缺少date和trade_date列")
                stock_df = pd.DataFrame()
        
        if not index_df.empty and 'date' in index_df.columns:
            index_df['is_after_analysis'] = index_df['date'] >= analysis_date_dt
        elif not index_df.empty:
            # 如果没有date列，尝试创建
            logger.warning(f"指数数据缺少date列，尝试修复...")
            if 'trade_date' in index_df.columns:
                index_df['date'] = pd.to_datetime(index_df['trade_date'])
                index_df['is_after_analysis'] = index_df['date'] >= analysis_date_dt
            else:
                logger.error(f"指数数据格式异常，缺少date和trade_date列")
                index_df = pd.DataFrame()
        
        return {
            'stock_data': stock_df,
            'index_data': index_df,
            'predicted_price': predicted_price,
            'analysis_date': analysis_date,
            'index_code': index_code,
            'index_name': index_name
        }
        
    except Exception as e:
        logger.error(f"准备回测数据失败: {e}")
        import traceback
        logger.error(f"详细错误信息: {traceback.format_exc()}")
        return {
            'stock_data': pd.DataFrame(),
            'index_data': pd.DataFrame(),
            'predicted_price': predicted_price,
            'analysis_date': analysis_date,
            'index_code': '',
            'index_name': ''
        }


def render_backtest_chart(backtest_data: Dict[str, Any], stock_code: str):
    """
    渲染回测图表
    
    Args:
        backtest_data: 回测数据字典
        stock_code: 股票代码
    """
    stock_df = backtest_data['stock_data']
    index_df = backtest_data['index_data']
    predicted_price = backtest_data['predicted_price']
    analysis_date = backtest_data['analysis_date']
    index_name = backtest_data['index_name']
    
    if stock_df.empty:
        st.warning("暂无股票数据，无法绘制图表")
        return
    
    # 创建子图
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.1,
        row_heights=[0.7, 0.3],
        subplot_titles=(f'{stock_code} 回测对比图', '成交量')
    )
    
    # 分析日期
    analysis_date_dt = pd.to_datetime(analysis_date)
    
    # 分离分析日期前后的数据
    stock_before = stock_df[stock_df['date'] < analysis_date_dt]
    stock_after = stock_df[stock_df['date'] >= analysis_date_dt]
    
    # 绘制股票收盘价
    if not stock_before.empty:
        fig.add_trace(
            go.Scatter(
                x=stock_before['date'],
                y=stock_before['close'],
                mode='lines',
                name=f'{stock_code} 实际收盘价（分析前）',
                line=dict(color='lightblue', width=2),
                legendgroup='stock'
            ),
            row=1, col=1
        )
    
    if not stock_after.empty:
        fig.add_trace(
            go.Scatter(
                x=stock_after['date'],
                y=stock_after['close'],
                mode='lines',
                name=f'{stock_code} 实际收盘价（分析后）',
                line=dict(color='blue', width=2),
                legendgroup='stock'
            ),
            row=1, col=1
        )
    
    # 绘制指数数据（归一化到股票价格范围）
    if not index_df.empty:
        # 计算归一化系数（使指数与股票价格在同一量级）
        stock_price_range = stock_df['close'].max() - stock_df['close'].min()
        index_price_range = index_df['close'].max() - index_df['close'].min()
        
        if index_price_range > 0 and stock_price_range > 0:
            # 找到分析日期当天的股票价格和指数，用于对齐
            analysis_stock_price = stock_df[stock_df['date'] <= analysis_date_dt]['close'].iloc[-1] if not stock_df[stock_df['date'] <= analysis_date_dt].empty else stock_df['close'].iloc[0]
            analysis_index_price = index_df[index_df['date'] <= analysis_date_dt]['close'].iloc[-1] if not index_df[index_df['date'] <= analysis_date_dt].empty else index_df['close'].iloc[0]
            
            # 计算归一化系数
            scale_factor = analysis_stock_price / analysis_index_price if analysis_index_price > 0 else 1
            index_normalized = index_df['close'] * scale_factor
            
            index_before = index_df[index_df['date'] < analysis_date_dt]
            index_after = index_df[index_df['date'] >= analysis_date_dt]
            
            if not index_before.empty:
                fig.add_trace(
                    go.Scatter(
                        x=index_before['date'],
                        y=index_normalized[index_before.index],
                        mode='lines',
                        name=f'{index_name}（分析前）',
                        line=dict(color='lightgreen', width=2, dash='dash'),
                        legendgroup='index'
                    ),
                    row=1, col=1
                )
            
            if not index_after.empty:
                fig.add_trace(
                    go.Scatter(
                        x=index_after['date'],
                        y=index_normalized[index_after.index],
                        mode='lines',
                        name=f'{index_name}（分析后）',
                        line=dict(color='green', width=2, dash='dash'),
                        legendgroup='index'
                    ),
                    row=1, col=1
                )
    
    # 绘制预测价格线
    if predicted_price is not None:
        # 在分析日期之后绘制预测价格线
        if not stock_after.empty:
            predicted_dates = stock_after['date'].tolist()
            predicted_prices = [predicted_price] * len(predicted_dates)
            
            fig.add_trace(
                go.Scatter(
                    x=predicted_dates,
                    y=predicted_prices,
                    mode='lines',
                    name=f'预测价格: {predicted_price:.2f}',
                    line=dict(color='red', width=2, dash='dot'),
                    legendgroup='predicted'
                ),
                row=1, col=1
            )
    
    # 添加分析日期标记线
    fig.add_vline(
        x=analysis_date_dt,
        line_dash="dash",
        line_color="orange",
        annotation_text="分析日期",
        annotation_position="top",
        row=1, col=1
    )
    
    # 绘制成交量
    if 'volume' in stock_df.columns:
        volume_before = stock_before['volume'] if not stock_before.empty else pd.Series()
        volume_after = stock_after['volume'] if not stock_after.empty else pd.Series()
        
        if not stock_before.empty:
            fig.add_trace(
                go.Bar(
                    x=stock_before['date'],
                    y=stock_before['volume'],
                    name='成交量（分析前）',
                    marker_color='lightgray',
                    legendgroup='volume',
                    showlegend=False
                ),
                row=2, col=1
            )
        
        if not stock_after.empty:
            fig.add_trace(
                go.Bar(
                    x=stock_after['date'],
                    y=stock_after['volume'],
                    name='成交量（分析后）',
                    marker_color='gray',
                    legendgroup='volume',
                    showlegend=False
                ),
                row=2, col=1
            )
    
    # 更新布局
    fig.update_xaxes(title_text="日期", row=2, col=1)
    fig.update_yaxes(title_text="价格", row=1, col=1)
    fig.update_yaxes(title_text="成交量", row=2, col=1)
    
    fig.update_layout(
        height=800,
        title_text=f"{stock_code} 回测分析",
        hovermode='x unified'
    )
    
    st.plotly_chart(fig, use_container_width=True)


def render_backtest_table(backtest_data: Dict[str, Any], stock_code: str):
    """
    渲染回测数据表
    
    Args:
        backtest_data: 回测数据字典
        stock_code: 股票代码
    """
    stock_df = backtest_data['stock_data']
    index_df = backtest_data['index_data']
    predicted_price = backtest_data['predicted_price']
    analysis_date = backtest_data['analysis_date']
    index_name = backtest_data['index_name']
    
    if stock_df.empty:
        st.warning("暂无股票数据，无法显示数据表")
        return
    
    # 合并数据
    result_df = stock_df[['date', 'close']].copy()
    result_df.columns = ['日期', f'{stock_code}收盘价']
    
    # 添加指数数据
    if not index_df.empty:
        index_data_dict = dict(zip(index_df['date'], index_df['close']))
        result_df[f'{index_name}'] = result_df['日期'].map(index_data_dict)
    
    # 添加预测价格
    if predicted_price is not None:
        analysis_date_dt = pd.to_datetime(analysis_date)
        result_df['预测价格'] = result_df.apply(
            lambda row: predicted_price if pd.to_datetime(row['日期']) >= analysis_date_dt else None,
            axis=1
        )
    
    # 添加分析日期标记
    analysis_date_dt = pd.to_datetime(analysis_date)
    result_df['是否分析后'] = result_df['日期'] >= analysis_date_dt
    
    # 计算预测误差（如果分析日期后）
    if predicted_price is not None:
        result_df['预测误差'] = result_df.apply(
            lambda row: abs(row[f'{stock_code}收盘价'] - predicted_price) if row['是否分析后'] and pd.notna(row[f'{stock_code}收盘价']) else None,
            axis=1
        )
        result_df['预测误差率(%)'] = result_df.apply(
            lambda row: abs((row[f'{stock_code}收盘价'] - predicted_price) / predicted_price * 100) if row['是否分析后'] and pd.notna(row[f'{stock_code}收盘价']) and predicted_price > 0 else None,
            axis=1
        )
    
    # 格式化日期
    result_df['日期'] = result_df['日期'].dt.strftime('%Y-%m-%d')
    
    # 重新排列列
    columns = ['日期', f'{stock_code}收盘价']
    if not index_df.empty:
        columns.append(f'{index_name}')
    if predicted_price is not None:
        columns.extend(['预测价格', '预测误差', '预测误差率(%)'])
    columns.append('是否分析后')
    
    result_df = result_df[columns]
    
    # 显示数据表
    st.subheader("📊 回测数据对比表")
    st.dataframe(result_df, use_container_width=True)
    
    # 显示统计信息
    if predicted_price is not None:
        after_analysis = result_df[result_df['是否分析后'] == True]
        if not after_analysis.empty and '预测误差' in after_analysis.columns:
            errors = after_analysis['预测误差'].dropna()
            if not errors.empty:
                st.subheader("📈 预测准确性统计")
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("平均误差", f"{errors.mean():.2f}")
                with col2:
                    st.metric("最大误差", f"{errors.max():.2f}")
                with col3:
                    st.metric("最小误差", f"{errors.min():.2f}")
                with col4:
                    if '预测误差率(%)' in after_analysis.columns:
                        error_rates = after_analysis['预测误差率(%)'].dropna()
                        if not error_rates.empty:
                            st.metric("平均误差率", f"{error_rates.mean():.2f}%")


def render_backtest_page():
    """渲染回测页面"""
    st.header("📈 分析结果回测")
    
    # 检查MongoDB连接
    if not MONGODB_AVAILABLE:
        st.error("❌ MongoDB未连接，无法读取分析结果。请检查MongoDB配置。")
        return
    
    # 输入股票代码
    stock_code = st.text_input(
        "请输入股票代码",
        value="",
        help="例如：000001（平安银行）、600036（招商银行）",
        key="backtest_stock_code"
    )
    
    if not stock_code:
        st.info("👆 请输入股票代码以开始回测")
        return
    
    # 查询按钮
    col1, col2 = st.columns([1, 4])
    with col1:
        query_button = st.button("🔍 查询分析结果", key="query_analysis_results", type="primary")
    
    # 初始化session state
    if 'backtest_analysis_reports' not in st.session_state:
        st.session_state.backtest_analysis_reports = None
    if 'backtest_selected_report' not in st.session_state:
        st.session_state.backtest_selected_report = None
    
    # 点击查询按钮
    if query_button:
        try:
            mongodb_manager = MongoDBReportManager()
            if not mongodb_manager.connected:
                st.error("❌ 无法连接到MongoDB，请检查数据库配置。")
                st.session_state.backtest_analysis_reports = None
                return
            
            # 根据股票代码查询分析结果
            with st.spinner("正在查询分析结果..."):
                analysis_reports = mongodb_manager.get_analysis_reports(
                    limit=100,
                    stock_symbol=stock_code
                )
            
            if not analysis_reports:
                st.warning(f"⚠️ 未找到股票 {stock_code} 的分析结果。请先进行股票分析。")
                st.session_state.backtest_analysis_reports = None
            else:
                # 按时间倒序排列
                analysis_reports = sorted(analysis_reports, key=lambda x: x.get('timestamp', 0), reverse=True)
                st.session_state.backtest_analysis_reports = analysis_reports
                st.success(f"✅ 找到 {len(analysis_reports)} 条分析结果")
        
        except Exception as e:
            logger.error(f"查询分析结果失败: {e}")
            st.error(f"❌ 查询分析结果失败: {str(e)}")
            st.session_state.backtest_analysis_reports = None
    
    # 显示分析结果列表
    analysis_reports = st.session_state.backtest_analysis_reports
    
    if analysis_reports is None:
        if not query_button:
            st.info("👆 请输入股票代码后，点击「查询分析结果」按钮")
        return
    
    if not analysis_reports:
        st.warning(f"⚠️ 未找到股票 {stock_code} 的分析结果。请先进行股票分析。")
        return
    
    # 显示分析结果列表
    st.subheader("📋 分析结果列表")
    
    # 创建选择框
    report_options = []
    for report in analysis_reports:
        timestamp = report.get('timestamp', 0)
        if isinstance(timestamp, (int, float)):
            date_str = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
        else:
            date_str = str(timestamp)
        
        analysis_date = report.get('analysis_date', '')
        if not analysis_date:
            # 尝试从timestamp提取
            if isinstance(timestamp, (int, float)):
                analysis_date = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d')
            else:
                analysis_date = date_str
        
        option_text = f"{analysis_date} - {report.get('analysis_id', 'N/A')}"
        report_options.append((option_text, report))
    
    if not report_options:
        st.warning("⚠️ 未找到有效的分析结果。")
        return
    
    # 显示分析结果选择框
    selected_option = st.selectbox(
        "选择要回测的分析结果",
        options=[opt[0] for opt in report_options],
        key="backtest_report_select",
        help="选择一条分析结果进行回测"
    )
    
    selected_index = [opt[0] for opt in report_options].index(selected_option)
    selected_report = report_options[selected_index][1]
    
    # 保存选中的报告
    st.session_state.backtest_selected_report = selected_report
        
    # 显示分析结果信息
    st.markdown("---")
    st.subheader("📊 选中的分析结果信息")
    
    col1, col2 = st.columns(2)
    with col1:
        st.info(f"""
        **分析ID**: {selected_report.get('analysis_id', 'N/A')}  
        **分析日期**: {selected_report.get('analysis_date', 'N/A')}  
        """)
    with col2:
        st.info(f"""
        **分析师**: {', '.join(selected_report.get('analysts', []))}  
        **研究深度**: {selected_report.get('research_depth', 'N/A')}
        """)
    
    # 开始回测按钮
    st.markdown("---")
    start_backtest = st.button("🚀 开始回测", key="start_backtest", type="primary")
    
    if not start_backtest:
        st.info("👆 确认分析结果后，点击「开始回测」按钮进行回测")
        return
    
    # 提取分析日期和预测价格
    analysis_date = selected_report.get('analysis_date', '')
    if not analysis_date:
        # 从timestamp提取
        timestamp = selected_report.get('timestamp', 0)
        if isinstance(timestamp, (int, float)):
            analysis_date = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d')
        elif hasattr(timestamp, 'strftime'):
            # 如果是datetime对象
            analysis_date = timestamp.strftime('%Y-%m-%d')
        else:
            st.error("无法确定分析日期")
            return
    
    # 提取预测价格
    predicted_price = extract_predicted_price(selected_report)
    
    if predicted_price is None:
        st.warning("⚠️ 未找到预测价格信息，将仅显示实际价格和指数对比。")
    
    # 准备回测数据
    try:
        with st.spinner("正在准备回测数据..."):
            backtest_data = prepare_backtest_data(
                stock_code=stock_code,
                analysis_date=analysis_date,
                predicted_price=predicted_price,
                min_points=30
            )
        
        # 检查数据是否准备成功
        if backtest_data['stock_data'].empty:
            st.error("❌ 无法获取股票交易数据，请检查股票代码是否正确。")
            return
        
        # 显示回测图表
        st.markdown("---")
        st.subheader("📈 回测图表")
        render_backtest_chart(backtest_data, stock_code)
        
        # 显示回测数据表
        st.markdown("---")
        render_backtest_table(backtest_data, stock_code)
        
    except Exception as e:
        logger.error(f"回测数据处理失败: {e}")
        st.error(f"❌ 回测数据处理失败: {str(e)}")

