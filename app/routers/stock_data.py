"""
股票数据管理路由模块
提供股票基本信息、历史交易数据等接口
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import pandas as pd
import json

from tradingagents.utils.logging_manager import get_logger
from tradingagents.dataflows.stock_data_service import get_stock_data_service
from tradingagents.storage.mongodb.stock_history_manager import stock_history_manager
from tradingagents.storage.mongodb.stock_dict_manager import stock_dict_manager
from tradingagents.utils.stock_utils import StockUtils

router = APIRouter()
logger = get_logger("stock_data_router")


class StockBasicInfoResponse(BaseModel):
    """股票基本信息响应"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    message: str


class StockHistoricalDataResponse(BaseModel):
    """股票历史数据响应"""
    success: bool
    data: Optional[List[Dict[str, Any]]] = None
    total: int = 0
    message: str


class StockListResponse(BaseModel):
    """股票列表响应"""
    success: bool
    data: Optional[List[Dict[str, Any]]] = None
    total: int = 0
    message: str


def _dataframe_to_dict(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """将DataFrame转换为字典列表"""
    if df.empty:
        return []
    
    # 处理日期列
    df = df.copy()
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            df[col] = df[col].dt.strftime('%Y-%m-%d')
        elif pd.api.types.is_numeric_dtype(df[col]):
            # 将NaN转换为None
            df[col] = df[col].fillna(0)
    
    # 转换为字典列表
    records = df.to_dict('records')
    # 将NaN值转换为None（JSON序列化需要）
    for record in records:
        for key, value in record.items():
            if pd.isna(value) if hasattr(pd, 'isna') else (value != value):
                record[key] = None
    
    return records


def _normalize_date_column(df: pd.DataFrame) -> pd.DataFrame:
    """标准化DataFrame的日期列"""
    if df.empty:
        return df
    
    # 如果已经有date列，直接返回
    if 'date' in df.columns:
        return df
    
    # 如果有trade_date列，转换为date
    if 'trade_date' in df.columns:
        df = df.copy()
        df['date'] = pd.to_datetime(df['trade_date'])
        return df
    
    # 如果索引是日期类型，重置为列
    if df.index.name == 'date' or (hasattr(df.index, 'dtype') and pd.api.types.is_datetime64_any_dtype(df.index)):
        df = df.reset_index()
        if 'date' not in df.columns and len(df.columns) > 0:
            # 尝试使用第一列作为日期
            first_col = df.columns[0]
            if pd.api.types.is_datetime64_any_dtype(df[first_col]):
                df['date'] = df[first_col]
            else:
                df['date'] = pd.to_datetime(df[first_col], errors='coerce')
        return df
    
    return df


def _normalize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """标准化DataFrame的列名"""
    column_mapping = {
        'close': 'close',
        'open': 'open',
        'high': 'high',
        'low': 'low',
        'vol': 'volume',
        'volume': 'volume',
        'amount': 'volume'
    }
    
    df = df.copy()
    for old_col, new_col in column_mapping.items():
        if old_col in df.columns and new_col not in df.columns:
            df[new_col] = df[old_col]
    
    return df


@router.get("/basic-info/{stock_code}", response_model=StockBasicInfoResponse)
async def get_stock_basic_info(stock_code: str):
    """
    从MongoDB的 stock_dict 集合中获取股票基本信息
    
    - **stock_code**: 股票代码（如：000001）
    """
    try:
        # 检查MongoDB连接
        if not stock_dict_manager or not stock_dict_manager.connected:
            raise HTTPException(
                status_code=500,
                detail="MongoDB股票基础信息服务不可用，请检查数据库配置"
            )

        # stock_dict 中使用的是不带交易所后缀的 6 位代码
        stock_symbol = stock_code
        if "." in stock_code:
            stock_symbol = stock_code.split(".")[0]

        result = stock_dict_manager.get_by_symbol(stock_symbol)

        if result is None:
            raise HTTPException(
                status_code=404,
                detail=f"未找到股票{stock_code}的基础信息"
            )

        # stock_dict_manager 已经在查询时去掉了 _id 字段，这里直接返回即可
        return StockBasicInfoResponse(
            success=True,
            data=result,
            message="获取成功"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取股票基本信息失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"获取股票基本信息失败: {str(e)}"
        )


@router.get("/list", response_model=StockListResponse)
async def get_all_stocks():
    """
    获取所有股票列表
    """
    try:
        service = get_stock_data_service()
        result = service.get_stock_basic_info(None)  # None表示获取所有股票
        
        if result is None:
            result = []
        
        # 处理_id字段
        if isinstance(result, list):
            for item in result:
                if isinstance(item, dict) and '_id' in item:
                    item['_id'] = str(item['_id'])
        elif isinstance(result, dict):
            if '_id' in result:
                result['_id'] = str(result['_id'])
            result = [result]
        
        return StockListResponse(
            success=True,
            data=result if isinstance(result, list) else [result],
            total=len(result) if isinstance(result, list) else 1,
            message="获取成功"
        )
        
    except Exception as e:
        logger.error(f"获取股票列表失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"获取股票列表失败: {str(e)}"
        )


@router.get("/historical-data/{stock_code}", response_model=StockHistoricalDataResponse)
async def get_stock_historical_data(
    stock_code: str,
    start_date: str = Query(..., description="开始日期 (YYYY-MM-DD)"),
    end_date: str = Query(..., description="结束日期 (YYYY-MM-DD)"),
    analysis_date: Optional[str] = Query(None, description="分析日期 (YYYY-MM-DD)，用于智能调整数据范围"),
    expected_points: int = Query(60, ge=1, le=500, description="期望的数据点总数（用于智能调整日期范围）")
):
    """
    获取股票指定日期区间的历史交易数据
    
    - **stock_code**: 股票代码（如：000001）
    - **start_date**: 开始日期 (YYYY-MM-DD)
    - **end_date**: 结束日期 (YYYY-MM-DD)
    - **analysis_date**: 分析日期 (YYYY-MM-DD)，如果提供，将优先保留分析日期之后的数据
    - **expected_points**: 期望的数据点总数（默认60）
    """
    try:
        # 解析日期
        try:
            start_dt = pd.to_datetime(start_date)
            end_dt = pd.to_datetime(end_date)
            analysis_dt = pd.to_datetime(analysis_date) if analysis_date else None
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"日期格式错误: {str(e)}，请使用YYYY-MM-DD格式"
            )
        
        if start_dt > end_dt:
            raise HTTPException(
                status_code=400,
                detail="开始日期不能晚于结束日期"
            )
        
        # 获取市场信息
        market_info = StockUtils.get_market_info(stock_code)
        
        if not market_info.get('is_china', False):
            raise HTTPException(
                status_code=400,
                detail=f"当前接口仅支持A股，股票代码{stock_code}不属于A股"
            )
        
        # 检查MongoDB连接
        if not stock_history_manager.connected:
            raise HTTPException(
                status_code=500,
                detail="MongoDB历史交易数据服务不可用，请检查数据库配置"
            )
        
        # 从MongoDB获取指定日期范围的数据
        df = stock_history_manager.get_stock_history(stock_code, start_date, end_date)
        
        if df.empty:
            raise HTTPException(
                status_code=404,
                detail=f"未找到股票{stock_code}在{start_date}至{end_date}期间的历史数据"
            )
        
        # 标准化日期列和列名（MongoDB返回的数据可能已经包含date列）
        if 'date' not in df.columns:
            df = _normalize_date_column(df)
        
        df = _normalize_column_names(df)
        
        if 'date' not in df.columns:
            raise HTTPException(
                status_code=500,
                detail="数据格式错误：缺少日期列"
            )
        
        # 确保日期列是datetime类型（MongoDB返回的date可能是字符串）
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        # 过滤掉无效的日期
        df = df[df['date'].notna()].reset_index(drop=True)
        df = df.sort_values('date').reset_index(drop=True)
        
        # 检查数据量，如果不足 expected_points，尝试扩展日期范围（向前扩展）
        #
        # 注意：根据业务需求，expected_points 表示**期望的最少数据量**，
        # 如果区间内数据量多于 expected_points，不做截断，直接返回完整区间数据。
        # 这样可以保证：
        # 1. 一定包含「分析日期前一个月 ~ 页面设置的结束日期」这个区间；
        # 2. 当分析日期之后的交易日较少时，尽量向前补足到 ~expected_points 条。
        if len(df) < expected_points:
            # 计算需要向前扩展多少天（乘以 2 以覆盖非交易日）
            days_needed = (expected_points - len(df)) * 2
            extended_start_date = (start_dt - timedelta(days=days_needed)).strftime('%Y-%m-%d')

            # 从 MongoDB 获取扩展的数据（主要是分析日期之前的数据）
            extended_df = stock_history_manager.get_stock_history(stock_code, extended_start_date, start_date)
            if not extended_df.empty:
                # MongoDB 返回的数据已经基本标准化，这里只确保有 date 列
                if 'date' not in extended_df.columns:
                    extended_df = _normalize_date_column(extended_df)

                extended_df = _normalize_column_names(extended_df)

                if 'date' in extended_df.columns and 'date' in df.columns:
                    # 确保 date 列为 datetime 类型
                    extended_df['date'] = pd.to_datetime(extended_df['date'], errors='coerce')
                    df['date'] = pd.to_datetime(df['date'], errors='coerce')

                    # 过滤无效日期
                    extended_df = extended_df[extended_df['date'].notna()]
                    df = df[df['date'].notna()]

                    # 去重并合并：扩展数据在前，原始数据在后
                    extended_df = extended_df[~extended_df['date'].isin(df['date'])]
                    df = pd.concat([extended_df, df], ignore_index=True)
                    df = df.sort_values('date').reset_index(drop=True)
                    df = df.drop_duplicates(subset=['date']).reset_index(drop=True)
        
        # 转换为字典列表（日期格式化为字符串）
        df['date'] = df['date'].dt.strftime('%Y-%m-%d')
        records = _dataframe_to_dict(df)
        
        return StockHistoricalDataResponse(
            success=True,
            data=records,
            total=len(records),
            message=f"获取成功，共{len(records)}条数据"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取股票历史数据失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"获取股票历史数据失败: {str(e)}"
        )


@router.get("/analysis-reports/{stock_code}")
async def get_analysis_reports_by_stock(
    stock_code: str,
    limit: int = Query(100, ge=1, le=1000, description="最大返回数量")
):
    """
    根据股票代码获取分析结果列表
    
    - **stock_code**: 股票代码（如：000001）
    - **limit**: 最大返回数量
    """
    try:
        from tradingagents.storage.mongodb.report_manager import mongodb_report_manager
        
        if not mongodb_report_manager or not mongodb_report_manager.connected:
            raise HTTPException(
                status_code=500,
                detail="报告数据库未连接"
            )
        
        # 查询分析结果
        reports = mongodb_report_manager.get_analysis_reports(
            limit=limit,
            stock_symbol=stock_code
        )
        
        # 按时间倒序排列
        reports = sorted(reports, key=lambda x: x.get('timestamp', 0), reverse=True)
        
        # 处理ObjectId
        for report in reports:
            if '_id' in report:
                report['_id'] = str(report['_id'])
        
        return {
            "success": True,
            "data": reports,
            "total": len(reports),
            "message": "获取成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取分析结果失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"获取分析结果失败: {str(e)}"
        )

