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
    from tradingagents.storage.mongodb.report_manager import MongoDBReportManager
    MONGODB_AVAILABLE = True
except ImportError:
    MONGODB_AVAILABLE = False
    MongoDBReportManager = None
    logger.warning("MongoDB模块不可用")


def _normalize_date_column(df: pd.DataFrame) -> pd.DataFrame:
    """
    标准化DataFrame的日期列
    
    Args:
        df: 输入的DataFrame
        
    Returns:
        标准化后的DataFrame，如果失败则返回空DataFrame
    """
    if df.empty:
        return df
    
    # 如果已经有date列，直接返回
    if 'date' in df.columns:
        return df
    
    # 如果有trade_date列，转换为date
    if 'trade_date' in df.columns:
        df['date'] = pd.to_datetime(df['trade_date'])
        return df
    
    # 如果索引是日期类型，重置为列
    if df.index.name == 'date':
        df = df.reset_index()
        if 'date' not in df.columns:
            logger.warning(f"重置索引后仍未找到date列，数据列: {list(df.columns)}")
            return pd.DataFrame()
        return df
    
    if hasattr(df.index, 'dtype') and pd.api.types.is_datetime64_any_dtype(df.index):
        index_name = df.index.name if df.index.name else 'index'
        df = df.reset_index()
        if index_name in df.columns:
            df['date'] = pd.to_datetime(df[index_name])
        elif 'index' in df.columns:
            df['date'] = pd.to_datetime(df['index'])
        else:
            logger.warning(f"重置日期索引后未找到日期列，数据列: {list(df.columns)}")
            return pd.DataFrame()
        return df
    
    logger.warning(f"无法从数据中提取日期列，数据列: {list(df.columns)}")
    return pd.DataFrame()


def _normalize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """
    标准化DataFrame的列名
    
    Args:
        df: 输入的DataFrame
        
    Returns:
        标准化后的DataFrame
    """
    column_mapping = {
        'close': 'close',
        'open': 'open',
        'high': 'high',
        'low': 'low',
        'vol': 'volume',
        'volume': 'volume',
        'amount': 'volume'
    }
    
    for old_col, new_col in column_mapping.items():
        if old_col in df.columns and new_col not in df.columns:
            df[new_col] = df[old_col]
    
    return df


def _timestamp_to_milliseconds(timestamp_obj) -> float:
    """
    将时间戳对象转换为毫秒时间戳
    
    Args:
        timestamp_obj: pandas Timestamp 或 datetime 对象
        
    Returns:
        毫秒时间戳（float）
    """
    try:
        return timestamp_obj.timestamp() * 1000
    except AttributeError:
        if hasattr(timestamp_obj, 'to_pydatetime'):
            return timestamp_obj.to_pydatetime().timestamp() * 1000
        return pd.to_datetime(timestamp_obj).timestamp() * 1000


def _merge_dataframes(df_pre: pd.DataFrame, df_post: pd.DataFrame) -> pd.DataFrame:
    """
    合并两个DataFrame，按日期排序
    
    Args:
        df_pre: 前一个DataFrame
        df_post: 后一个DataFrame
        
    Returns:
        合并后的DataFrame
    """
    if df_pre.empty:
        return df_post if not df_post.empty else df_pre
    if df_post.empty:
        return df_pre
    
    if 'date' not in df_pre.columns or 'date' not in df_post.columns:
        return df_post if not df_post.empty else df_pre
    
    df = pd.concat([df_pre, df_post], ignore_index=True)
    df = df.sort_values('date').reset_index(drop=True)
    df = df.drop_duplicates(subset=['date']).reset_index(drop=True)
    return df


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
                    df = adapter.provider.get_stock_daily(stock_code, start_date, end_date)
                    if df is not None and not df.empty:
                        df = _normalize_date_column(df)
                        if df.empty:
                            return pd.DataFrame()
                        
                        df = _normalize_column_names(df)
                        
                        if 'date' in df.columns and 'close' in df.columns:
                            df = df.sort_values('date').reset_index(drop=True)
                            return df
                        else:
                            logger.warning(f"数据缺少必要列，已有列: {list(df.columns)}，需要列: ['date', 'close']")
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
        index_code: 指数代码（如：000001、399001）
        start_date: 开始日期
        end_date: 结束日期
        
    Returns:
        DataFrame: 指数数据
    """
    try:
        # 使用指数数据接口
        try:
            from tradingagents.dataflows.tushare_utils import get_china_index_data_tushare
            from tradingagents.dataflows.tushare_adapter import get_tushare_adapter
            
            # 先尝试从Tushare适配器的Provider直接获取
            adapter = get_tushare_adapter()
            if adapter and adapter.provider and adapter.provider.connected:
                # 对于指数，需要转换为Tushare标准格式
                if index_code == "000001":
                    # 上证指数
                    index_symbols = ["000001.SH", "000001"]
                elif index_code == "399001":
                    # 深证成指
                    index_symbols = ["399001.SZ", "399001"]
                else:
                    # 尝试自动判断交易所
                    if index_code.startswith('39'):
                        index_symbols = [f"{index_code}.SZ", index_code]
                    elif index_code.startswith('00'):
                        index_symbols = [f"{index_code}.SH", index_code]
                    else:
                        index_symbols = [index_code]
                
                for symbol in index_symbols:
                    try:
                        df = adapter.provider.get_index_daily(symbol, start_date, end_date)
                        if df is not None and not df.empty:
                            df = _normalize_date_column(df)
                            if df.empty:
                                continue
                            
                            df = _normalize_column_names(df)
                            
                            if 'close' in df.columns and 'date' in df.columns:
                                df = df.sort_values('date').reset_index(drop=True)
                                logger.debug(f"✅ 成功获取指数数据: {index_code}, 数据条数: {len(df)}")
                                return df
                    except Exception as e:
                        logger.debug(f"尝试指数代码 {symbol} 失败: {e}")
                        continue
        except Exception as e:
            logger.debug(f"从Tushare适配器获取指数数据失败: {e}")
        
        # 降级方案：使用便捷函数
        try:
            from tradingagents.dataflows.tushare_utils import get_china_index_data_tushare
            
            # 转换指数代码格式
            if index_code == "000001":
                ts_code = "000001.SH"
            elif index_code == "399001":
                ts_code = "399001.SZ"
            elif index_code.startswith('39'):
                ts_code = f"{index_code}.SZ"
            elif index_code.startswith('00'):
                ts_code = f"{index_code}.SH"
            else:
                ts_code = index_code
            
            df = get_china_index_data_tushare(ts_code, start_date, end_date)
            if df is not None and not df.empty:
                df = _normalize_date_column(df)
                if df.empty:
                    return pd.DataFrame()
                
                df = _normalize_column_names(df)
                
                if 'close' in df.columns and 'date' in df.columns:
                    df = df.sort_values('date').reset_index(drop=True)
                    logger.debug(f"✅ 降级方案成功获取指数数据: {index_code}, 数据条数: {len(df)}")
                    return df
        except Exception as e:
            logger.warning(f"降级方案获取指数数据失败: {e}")
        
        # 最终降级方案：使用统一接口获取字符串数据并解析（不推荐，但作为最后手段）
        from tradingagents.dataflows.interface import get_china_stock_data_unified
        
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




def prepare_backtest_data(
    stock_code: str,
    analysis_date: str,
    target_price: Optional[float],
    min_points: int = 30
) -> Dict[str, Any]:
    """
    准备回测数据
    
    Args:
        stock_code: 股票代码
        analysis_date: 分析日期
        target_price: 目标价格
        min_points: 最少数据点数
        
    Returns:
        包含股票数据、指数数据和目标价格的字典
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
            
            # 合并数据
            stock_df = _merge_dataframes(stock_df_pre, stock_df_post)
            index_df = _merge_dataframes(index_df_pre, index_df_post)
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
            
            stock_df = _merge_dataframes(stock_df_pre, stock_df)
            index_df = _merge_dataframes(index_df_pre, index_df)
        
        # 标记分析日期（只在有数据时）
        analysis_date_dt = pd.to_datetime(analysis_date)
        
        for df_name, df in [('stock', stock_df), ('index', index_df)]:
            if df.empty:
                continue
            
            if 'date' not in df.columns:
                logger.warning(f"{df_name}数据缺少date列，尝试修复...")
                df = _normalize_date_column(df)
                if df_name == 'stock':
                    stock_df = df
                else:
                    index_df = df
                if df.empty:
                    continue
            
            if 'date' in df.columns:
                df['is_after_analysis'] = df['date'] >= analysis_date_dt
                if df_name == 'stock':
                    stock_df = df
                else:
                    index_df = df
        
        return {
            'stock_data': stock_df,
            'index_data': index_df,
            'target_price': target_price,
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
            'target_price': target_price,
            'analysis_date': analysis_date,
            'index_code': '',
            'index_name': ''
        }


def _get_stock_name(stock_code: str) -> str:
    """
    获取股票名称
    
    Args:
        stock_code: 股票代码
        
    Returns:
        股票名称，如果获取失败则返回股票代码
    """
    try:
        from tradingagents.dataflows.interface import get_china_stock_info_unified
        stock_info = get_china_stock_info_unified(stock_code)
        if "股票名称:" in stock_info:
            return stock_info.split("股票名称:")[1].split("\n")[0].strip()
    except Exception as e:
        logger.debug(f"获取股票名称失败: {e}")
    
    # 降级方案：尝试从数据源管理器获取
    try:
        from tradingagents.dataflows.data_source_manager import get_data_source_manager
        from tradingagents.utils.stock_utils import StockUtils
        
        manager = get_data_source_manager()
        market_info = StockUtils.get_market_info(stock_code)
        if market_info['is_china']:
            from tradingagents.dataflows.tushare_adapter import get_tushare_adapter
            adapter = get_tushare_adapter()
            if adapter and adapter.provider and adapter.provider.connected:
                try:
                    stock_basic = adapter.provider.get_stock_basic_info(stock_code)
                    if stock_basic and 'name' in stock_basic:
                        return stock_basic['name']
                except:
                    pass
    except Exception as e:
        logger.debug(f"从数据源管理器获取股票名称失败: {e}")
    
    return stock_code


def render_backtest_chart(backtest_data: Dict[str, Any], stock_code: str):
    """
    渲染回测图表
    
    Args:
        backtest_data: 回测数据字典
        stock_code: 股票代码
    """
    stock_df = backtest_data['stock_data']
    index_df = backtest_data['index_data']
    target_price = backtest_data['target_price']
    analysis_date = backtest_data['analysis_date']
    index_name = backtest_data['index_name']
    
    if stock_df.empty:
        st.warning("暂无股票数据，无法绘制图表")
        return
    
    # 获取股票名称
    stock_name = _get_stock_name(stock_code)
    
    # 创建子图
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=False,  # 不共享x轴，让两个图都能显示日期标签
        vertical_spacing=0.15,  # 增加间距，避免价格图的x轴标签被遮盖
        row_heights=[0.7, 0.3],
        subplot_titles=(f'{stock_name} ({stock_code}) 回测对比图', '成交量')
    )
    
    # 分析日期
    analysis_date_dt = pd.to_datetime(analysis_date)
    
    # 绘制股票收盘价（不拆分，合并为一条线）
    if not stock_df.empty:
        fig.add_trace(
            go.Scatter(
                x=stock_df['date'],
                y=stock_df['close'],
                mode='lines',
                name=f'{stock_name} 实际收盘价',
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
            stock_filtered = stock_df[stock_df['date'] <= analysis_date_dt]
            index_filtered = index_df[index_df['date'] <= analysis_date_dt]
            analysis_stock_price = stock_filtered['close'].iloc[-1] if not stock_filtered.empty else stock_df['close'].iloc[0]
            analysis_index_price = index_filtered['close'].iloc[-1] if not index_filtered.empty else index_df['close'].iloc[0]
            
            # 计算归一化系数
            scale_factor = analysis_stock_price / analysis_index_price if analysis_index_price > 0 else 1
            
            # 指数数据也不拆分，合并为一条线
            if not index_df.empty:
                index_normalized = index_df['close'] * scale_factor
                fig.add_trace(
                    go.Scatter(
                        x=index_df['date'],
                        y=index_normalized,
                        mode='lines',
                        name=f'{index_name}',
                        line=dict(color='green', width=2, dash='dash'),
                        legendgroup='index'
                    ),
                    row=1, col=1
                )
    
    # 绘制目标价格线（仅在分析日期之后）
    if target_price is not None:
        stock_after = stock_df[stock_df['date'] >= analysis_date_dt]
        if not stock_after.empty:
            fig.add_trace(
                go.Scatter(
                    x=stock_after['date'],
                    y=[target_price] * len(stock_after),
                    mode='lines',
                    name=f'目标价格: {target_price:.2f}',
                    line=dict(color='red', width=2, dash='dot'),
                    legendgroup='target'
                ),
                row=1, col=1
            )
    
    # 添加分析日期标记线（plotly 的 add_vline 需要 int/float 类型）
    analysis_date_timestamp = _timestamp_to_milliseconds(analysis_date_dt)
    fig.add_vline(
        x=analysis_date_timestamp,
        line_dash="dash",
        line_color="orange",
        annotation_text="分析日期",
        annotation_position="top",
        row=1, col=1
    )
    
    # 绘制成交量（不拆分，合并为一条）
    if 'volume' in stock_df.columns and not stock_df.empty:
        fig.add_trace(
            go.Bar(
                x=stock_df['date'],
                y=stock_df['volume'],
                name='成交量',
                marker_color='gray',
                legendgroup='volume',
                showlegend=False
            ),
            row=2, col=1
        )
    
    # 更新布局
    # 价格图的x轴：显示日期标签（仅月-日）
    fig.update_xaxes(
        title_text="日期",
        tickformat='%m-%d',
        type='date',
        tickangle=-45,
        showgrid=True,
        showticklabels=True,
        row=1, col=1
    )
    # 成交量图的x轴：显示日期标签（仅月-日）
    fig.update_xaxes(
        title_text="日期",
        tickformat='%m-%d',
        type='date',
        tickangle=-45,
        showgrid=True,
        showticklabels=True,
        row=2, col=1
    )
    fig.update_yaxes(title_text="价格", row=1, col=1)
    fig.update_yaxes(title_text="成交量", row=2, col=1)
    
    fig.update_layout(
        height=850,  # 稍微增加高度，为x轴标签留出空间
        title_text=f"{stock_name} ({stock_code}) 回测分析",
        hovermode='x unified',
        margin=dict(b=100)  # 增加底部边距，确保x轴标签可见
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
    target_price = backtest_data['target_price']
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
    
    # 添加目标价格
    if target_price is not None:
        analysis_date_dt = pd.to_datetime(analysis_date)
        result_df['目标价格'] = result_df.apply(
            lambda row: target_price if pd.to_datetime(row['日期']) >= analysis_date_dt else None,
            axis=1
        )
    
    # 添加分析日期标记
    analysis_date_dt = pd.to_datetime(analysis_date)
    result_df['是否分析后'] = result_df['日期'] >= analysis_date_dt
    
    # 计算目标价格误差（如果分析日期后）
    if target_price is not None:
        result_df['价格误差'] = result_df.apply(
            lambda row: abs(row[f'{stock_code}收盘价'] - target_price) if row['是否分析后'] and pd.notna(row[f'{stock_code}收盘价']) else None,
            axis=1
        )
        result_df['价格误差率(%)'] = result_df.apply(
            lambda row: abs((row[f'{stock_code}收盘价'] - target_price) / target_price * 100) if row['是否分析后'] and pd.notna(row[f'{stock_code}收盘价']) and target_price > 0 else None,
            axis=1
        )
    
    # 格式化日期
    result_df['日期'] = result_df['日期'].dt.strftime('%Y-%m-%d')
    
    # 重新排列列
    columns = ['日期', f'{stock_code}收盘价']
    if not index_df.empty:
        columns.append(f'{index_name}')
    if target_price is not None:
        columns.extend(['目标价格', '价格误差', '价格误差率(%)'])
    columns.append('是否分析后')
    
    result_df = result_df[columns]
    
    # 显示数据表
    st.subheader("📊 回测数据对比表")
    st.dataframe(result_df, use_container_width=True)
    
    # 显示统计信息
    if target_price is not None:
        after_analysis = result_df[result_df['是否分析后'] == True]
        if not after_analysis.empty and '价格误差' in after_analysis.columns:
            errors = after_analysis['价格误差'].dropna()
            if not errors.empty:
                st.subheader("📈 目标价格准确性统计")
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("平均误差", f"{errors.mean():.2f}")
                with col2:
                    st.metric("最大误差", f"{errors.max():.2f}")
                with col3:
                    st.metric("最小误差", f"{errors.min():.2f}")
                with col4:
                    if '价格误差率(%)' in after_analysis.columns:
                        error_rates = after_analysis['价格误差率(%)'].dropna()
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
    
    # 提取分析日期和目标价格
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
    
    # 提取formatted_decision信息
    formatted_decision = selected_report.get('formatted_decision', {})
    if not formatted_decision:
        st.warning("⚠️ 未找到决策信息，将仅显示实际价格和指数对比。")
    
    # 提取目标价格
    target_price = None
    if isinstance(formatted_decision, dict):
        target_price = formatted_decision.get('target_price')
        if target_price is not None:
            try:
                if isinstance(target_price, str):
                    # 清理字符串格式的价格
                    clean_price = target_price.replace('$', '').replace('¥', '').replace('￥', '').replace('元', '').strip()
                    target_price = float(clean_price) if clean_price and clean_price.lower() not in ['none', 'null', ''] else None
                elif isinstance(target_price, (int, float)):
                    target_price = float(target_price)
            except (ValueError, TypeError):
                target_price = None
    
    # 显示决策信息
    if formatted_decision:
        st.markdown("---")
        st.subheader("📋 交易决策信息")
        
        col1, col2 = st.columns(2)
        with col1:
            action = formatted_decision.get('action', 'N/A')
            action_color = 'red' if action == '卖出' else ('green' if action == '买入' else 'gray')
            st.markdown(f"**操作建议**: <span style='color:{action_color};font-weight:bold'>{action}</span>", unsafe_allow_html=True)
            
            target_price_str = f"{target_price:.2f}" if target_price is not None else "N/A"
            st.markdown(f"**目标价格**: {target_price_str}")
        
        with col2:
            confidence = formatted_decision.get('confidence', 0)
            confidence_str = f"{confidence:.1%}" if isinstance(confidence, (int, float)) else str(confidence)
            st.markdown(f"**置信度**: {confidence_str}")
            
            risk_score = formatted_decision.get('risk_score', 0)
            risk_score_str = f"{risk_score:.2f}" if isinstance(risk_score, (int, float)) else str(risk_score)
            st.markdown(f"**风险评分**: {risk_score_str}")
        
        # 显示决策理由
        reasoning = formatted_decision.get('reasoning', '')
        if reasoning:
            with st.expander("📝 决策理由", expanded=False):
                st.write(reasoning)
    
    # 准备回测数据
    try:
        with st.spinner("正在准备回测数据..."):
            backtest_data = prepare_backtest_data(
                stock_code=stock_code,
                analysis_date=analysis_date,
                target_price=target_price,
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

