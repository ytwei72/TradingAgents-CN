"""
股票数据管理路由模块
提供股票基本信息、历史交易数据等接口
"""

from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import pandas as pd
import json

from tradingagents.utils.logging_manager import get_logger
from tradingagents.dataflows.stock_data_service import get_stock_data_service
from tradingagents.storage.mongodb.stock_history_manager import stock_history_manager
from tradingagents.storage.mongodb.stock_dict_manager import stock_dict_manager
from tradingagents.storage.mongodb.sector_manager import sector_manager
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


class StockSectorsResponse(BaseModel):
    """股票所属板块响应"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    message: str


class SectorStocksResponse(BaseModel):
    """板块股票列表响应"""
    success: bool
    data: Optional[Dict[str, List[Dict[str, Any]]]] = None
    message: str


class SectorUpdateResponse(BaseModel):
    """板块更新响应"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    message: str


class SectorListResponse(BaseModel):
    """板块列表响应"""
    success: bool
    data: Optional[List[Dict[str, Any]]] = None
    total: int = 0
    message: str


class ConceptNamesUpdateRequest(BaseModel):
    """概念板块名称列表更新请求"""
    concept_names: List[str] = Field(..., description="概念板块名称列表")


class IndustryNamesUpdateRequest(BaseModel):
    """行业板块名称列表更新请求"""
    industry_names: List[str] = Field(..., description="行业板块名称列表")


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
    limit: int = Query(100, ge=1, le=1000, description="最大返回数量"),
    start_date: Optional[str] = Query(
        default=None, description="分析开始日期（可选，格式：YYYY-MM-DD）"
    ),
    end_date: Optional[str] = Query(
        default=None, description="分析结束日期（可选，格式：YYYY-MM-DD）"
    ),
):
    """
    根据股票代码获取分析结果列表
    
    - **stock_code**: 股票代码（如：000001），特殊值 `all` 表示不过滤股票代码
    - **limit**: 最大返回数量
    - **start_date**: 分析开始日期，可选
    - **end_date**: 分析结束日期，可选
    """
    try:
        from tradingagents.storage.mongodb.report_manager import mongodb_report_manager

        if not mongodb_report_manager or not mongodb_report_manager.connected:
            raise HTTPException(
                status_code=500,
                detail="报告数据库未连接"
            )

        # 处理特殊股票代码：all / * 表示不过滤股票代码
        stock_symbol: Optional[str]
        if stock_code and stock_code.lower() not in {"all", "*"}:
            stock_symbol = stock_code
        else:
            stock_symbol = None

        # 查询分析结果（底层会根据是否提供 stock_symbol / start_date / end_date 构建查询条件）
        reports = mongodb_report_manager.get_analysis_reports(
            limit=limit,
            stock_symbol=stock_symbol,
            start_date=start_date,
            end_date=end_date,
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


def _get_stock_sectors_data(stock_code: str) -> Dict[str, Any]:
    """
    内部辅助函数：根据股票代码获取所属板块数据
    
    Args:
        stock_code: 股票代码
    
    Returns:
        包含股票板块信息的字典
    """
    # 获取股票基本信息
    stock_info = None
    if stock_dict_manager and stock_dict_manager.connected:
        stock_info = stock_dict_manager.get_by_symbol(stock_code)
    
    # 获取所属概念板块
    concepts = sector_manager.get_concepts_by_stock(stock_code)
    
    # 获取所属行业板块
    industries = sector_manager.get_industries_by_stock(stock_code)
    
    # 构建响应数据
    result = {
        "stock_code": stock_code,
        "stock_name": stock_info.get('name') if stock_info else None,
        "concepts": concepts,
        "industries": industries,
        "concept_count": len(concepts),
        "industry_count": len(industries)
    }
    
    # 如果股票信息存在，添加更多字段
    if stock_info:
        result.update({
            "market": stock_info.get('market'),
            "exchange": stock_info.get('exchange'),
            "industry": stock_info.get('industry')
        })
    
    return result


@router.get("/sectors_by_id/{stock_id}", response_model=StockSectorsResponse)
async def get_stock_sectors_by_id(stock_id: str):
    """
    根据股票代码查询所属板块
    
    - **stock_id**: 股票代码（如：000001）
    """
    try:
        # 检查板块管理器连接
        if not sector_manager or not sector_manager.is_connected():
            raise HTTPException(
                status_code=500,
                detail="板块数据服务不可用，请检查数据库配置"
            )
        
        # 处理股票代码格式（去掉交易所后缀）
        stock_code = stock_id
        if "." in stock_code:
            stock_code = stock_code.split(".")[0]
        
        # 验证股票代码格式
        if not stock_code.isdigit() or len(stock_code) != 6:
            raise HTTPException(
                status_code=400,
                detail=f"股票代码格式错误，应为6位数字，如：000001"
            )
        
        # 获取板块数据
        result = _get_stock_sectors_data(stock_code)
        
        return StockSectorsResponse(
            success=True,
            data=result,
            message="查询成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询股票所属板块失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"查询股票所属板块失败: {str(e)}"
        )


@router.get("/sectors_by_name/{company_name}", response_model=StockSectorsResponse)
async def get_stock_sectors_by_name(company_name: str):
    """
    根据上市公司名称查询所属板块
    
    - **company_name**: 上市公司名称（如：平安银行）
    """
    try:
        # 检查板块管理器连接
        if not sector_manager or not sector_manager.is_connected():
            raise HTTPException(
                status_code=500,
                detail="板块数据服务不可用，请检查数据库配置"
            )
        
        if not stock_dict_manager or not stock_dict_manager.connected:
            raise HTTPException(
                status_code=500,
                detail="股票基础信息服务不可用，无法通过名称查询"
            )
        
        # 通过名称查询股票代码（精确匹配）
        matched_stocks = stock_dict_manager.get_by_name(company_name, exact=True)
        
        if not matched_stocks:
            raise HTTPException(
                status_code=404,
                detail=f"未找到名称为 '{company_name}' 的股票"
            )
        
        # 取第一个匹配的股票
        matched_stock = matched_stocks[0]
        stock_code = matched_stock.get('symbol')
        if not stock_code:
            raise HTTPException(
                status_code=404,
                detail=f"股票 '{company_name}' 缺少股票代码信息"
            )
        
        # 获取板块数据
        result = _get_stock_sectors_data(stock_code)
        
        return StockSectorsResponse(
            success=True,
            data=result,
            message="查询成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询股票所属板块失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"查询股票所属板块失败: {str(e)}"
        )


class IndustryNamesRequest(BaseModel):
    """行业板块名称列表请求"""
    industry_names: List[str] = Field(..., description="行业板块名称列表")


@router.post("/sectors/industry/stocks", response_model=SectorStocksResponse)
async def get_stocks_by_industries(request: IndustryNamesRequest = Body(...)):
    """
    根据指定的行业板块名称列表，返回每个行业板块的股票列表
    
    - **industry_names**: 行业板块名称列表（支持多个）
    """
    try:
        # 检查板块管理器连接
        if not sector_manager or not sector_manager.is_connected():
            raise HTTPException(
                status_code=500,
                detail="板块数据服务不可用，请检查数据库配置"
            )
        
        if not request.industry_names:
            raise HTTPException(
                status_code=400,
                detail="行业板块名称列表不能为空"
            )
        
        # 确保 industry_names 是列表
        if not isinstance(request.industry_names, list):
            raise HTTPException(
                status_code=400,
                detail=f"industry_names 必须是列表类型，当前类型: {type(request.industry_names)}"
            )
        
        industry_names = request.industry_names
        result = {}
        
        for industry_name in industry_names:
            if not isinstance(industry_name, str):
                logger.warning(f"跳过非字符串类型的行业板块名称: {industry_name} (类型: {type(industry_name)})")
                continue
            stocks = sector_manager.get_stocks_by_industry(industry_name)
            result[industry_name] = stocks
        
        return SectorStocksResponse(
            success=True,
            data=result,
            message=f"查询成功，共 {len(industry_names)} 个行业板块"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询行业板块股票列表失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"查询行业板块股票列表失败: {str(e)}"
        )


class ConceptNamesRequest(BaseModel):
    """概念板块名称列表请求"""
    concept_names: List[str] = Field(..., description="概念板块名称列表")


@router.post("/sectors/concept/stocks", response_model=SectorStocksResponse)
async def get_stocks_by_concepts(request: ConceptNamesRequest = Body(...)):
    """
    根据指定的概念板块名称列表，返回每个概念板块的股票列表
    
    - **concept_names**: 概念板块名称列表（支持多个）
    """
    try:
        # 检查板块管理器连接
        if not sector_manager or not sector_manager.is_connected():
            raise HTTPException(
                status_code=500,
                detail="板块数据服务不可用，请检查数据库配置"
            )
        
        if not request.concept_names:
            raise HTTPException(
                status_code=400,
                detail="概念板块名称列表不能为空"
            )
        
        # 确保 concept_names 是列表
        if not isinstance(request.concept_names, list):
            raise HTTPException(
                status_code=400,
                detail=f"concept_names 必须是列表类型，当前类型: {type(request.concept_names)}"
            )
        
        concept_names = request.concept_names
        result = {}
        
        for concept_name in concept_names:
            if not isinstance(concept_name, str):
                logger.warning(f"跳过非字符串类型的概念板块名称: {concept_name} (类型: {type(concept_name)})")
                continue
            stocks = sector_manager.get_stocks_by_concept(concept_name)
            result[concept_name] = stocks
        
        return SectorStocksResponse(
            success=True,
            data=result,
            message=f"查询成功，共 {len(concept_names)} 个概念板块"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询概念板块股票列表失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"查询概念板块股票列表失败: {str(e)}"
        )


@router.post("/sectors/update", response_model=SectorUpdateResponse)
async def update_sectors(
    update_concept: bool = Query(True, description="是否更新概念板块"),
    update_industry: bool = Query(True, description="是否更新行业板块")
):
    """
    更新板块数据（概念板块和/或行业板块）
    
    - **update_concept**: 是否更新概念板块（默认：true）
    - **update_industry**: 是否更新行业板块（默认：true）
    """
    try:
        # 检查板块管理器连接
        if not sector_manager or not sector_manager.is_connected():
            raise HTTPException(
                status_code=500,
                detail="板块数据服务不可用，请检查数据库配置"
            )
        
        result = {}
        
        # 更新概念板块
        if update_concept:
            try:
                concept_result = sector_manager.update_concept_sectors()
                result["concept"] = concept_result
                result["concept"]["updated"] = concept_result.get("failed_count", 0) == 0
            except Exception as e:
                logger.error(f"更新概念板块失败: {e}", exc_info=True)
                result["concept"] = {
                    "success": [],
                    "failed": {"整体更新": str(e)},
                    "total": 0,
                    "success_count": 0,
                    "failed_count": 1,
                    "updated": False
                }
        else:
            result["concept"] = {
                "success": [],
                "failed": {},
                "total": 0,
                "success_count": 0,
                "failed_count": 0,
                "updated": False,
                "message": "跳过概念板块更新"
            }
        
        # 更新行业板块
        if update_industry:
            try:
                industry_result = sector_manager.update_industry_sectors()
                result["industry"] = industry_result
                result["industry"]["updated"] = industry_result.get("failed_count", 0) == 0
            except Exception as e:
                logger.error(f"更新行业板块失败: {e}", exc_info=True)
                result["industry"] = {
                    "success": [],
                    "failed": {"整体更新": str(e)},
                    "total": 0,
                    "success_count": 0,
                    "failed_count": 1,
                    "updated": False
                }
        else:
            result["industry"] = {
                "success": [],
                "failed": {},
                "total": 0,
                "success_count": 0,
                "failed_count": 0,
                "updated": False,
                "message": "跳过行业板块更新"
            }
        
        # 判断整体是否成功
        all_success = (
            (not update_concept or result["concept"].get("updated", False)) and
            (not update_industry or result["industry"].get("updated", False))
        )
        
        return SectorUpdateResponse(
            success=all_success,
            data=result,
            message="板块更新完成" if all_success else "板块更新部分失败，请查看详细信息"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新板块数据失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"更新板块数据失败: {str(e)}"
        )


@router.post("/sectors/concept/update", response_model=SectorUpdateResponse)
async def update_specific_concept_sectors(request: ConceptNamesUpdateRequest):
    """
    更新指定的概念板块列表
    
    - **concept_names**: 概念板块名称列表
    """
    try:
        # 检查板块管理器连接
        if not sector_manager or not sector_manager.is_connected():
            raise HTTPException(
                status_code=500,
                detail="板块数据服务不可用，请检查数据库配置"
            )
        
        if not request.concept_names:
            raise HTTPException(
                status_code=400,
                detail="概念板块名称列表不能为空"
            )
        
        # 更新指定的概念板块
        result = sector_manager.update_specific_concept_sectors(request.concept_names)
        result["updated"] = result.get("failed_count", 0) == 0
        
        return SectorUpdateResponse(
            success=result["updated"],
            data={"concept": result},
            message=f"概念板块更新完成，成功 {result.get('success_count', 0)} 个，失败 {result.get('failed_count', 0)} 个"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新指定概念板块失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"更新指定概念板块失败: {str(e)}"
        )


@router.post("/sectors/industry/update", response_model=SectorUpdateResponse)
async def update_specific_industry_sectors(request: IndustryNamesUpdateRequest):
    """
    更新指定的行业板块列表
    
    - **industry_names**: 行业板块名称列表
    """
    try:
        # 检查板块管理器连接
        if not sector_manager or not sector_manager.is_connected():
            raise HTTPException(
                status_code=500,
                detail="板块数据服务不可用，请检查数据库配置"
            )
        
        if not request.industry_names:
            raise HTTPException(
                status_code=400,
                detail="行业板块名称列表不能为空"
            )
        
        # 更新指定的行业板块
        result = sector_manager.update_specific_industry_sectors(request.industry_names)
        result["updated"] = result.get("failed_count", 0) == 0
        
        return SectorUpdateResponse(
            success=result["updated"],
            data={"industry": result},
            message=f"行业板块更新完成，成功 {result.get('success_count', 0)} 个，失败 {result.get('failed_count', 0)} 个"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新指定行业板块失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"更新指定行业板块失败: {str(e)}"
        )


@router.get("/sectors/concept/list", response_model=SectorListResponse)
async def get_concept_list(
    limit: Optional[int] = Query(None, ge=1, le=10000, description="最大返回数量"),
    skip: Optional[int] = Query(0, ge=0, description="跳过记录数（用于分页）")
):
    """
    获取所有概念板块列表
    
    - **limit**: 最大返回数量（可选）
    - **skip**: 跳过记录数（可选，用于分页）
    """
    try:
        # 检查板块管理器连接
        if not sector_manager or not sector_manager.is_connected():
            raise HTTPException(
                status_code=500,
                detail="板块数据服务不可用，请检查数据库配置"
            )
        
        # 获取概念板块列表
        concepts = sector_manager.get_concept_list(limit=limit, skip=skip)
        
        return SectorListResponse(
            success=True,
            data=concepts,
            total=len(concepts),
            message=f"查询成功，共 {len(concepts)} 个概念板块"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询概念板块列表失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"查询概念板块列表失败: {str(e)}"
        )


@router.get("/sectors/industry/list", response_model=SectorListResponse)
async def get_industry_list(
    limit: Optional[int] = Query(None, ge=1, le=10000, description="最大返回数量"),
    skip: Optional[int] = Query(0, ge=0, description="跳过记录数（用于分页）")
):
    """
    获取所有行业板块列表
    
    - **limit**: 最大返回数量（可选）
    - **skip**: 跳过记录数（可选，用于分页）
    """
    try:
        # 检查板块管理器连接
        if not sector_manager or not sector_manager.is_connected():
            raise HTTPException(
                status_code=500,
                detail="板块数据服务不可用，请检查数据库配置"
            )
        
        # 获取行业板块列表
        industries = sector_manager.get_industry_list(limit=limit, skip=skip)
        
        return SectorListResponse(
            success=True,
            data=industries,
            total=len(industries),
            message=f"查询成功，共 {len(industries)} 个行业板块"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询行业板块列表失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"查询行业板块列表失败: {str(e)}"
        )

