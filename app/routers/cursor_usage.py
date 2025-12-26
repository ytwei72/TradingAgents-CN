"""
Cursor Usage API 接口
用于查询和分析 Cursor 使用情况
"""

from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from tradingagents.utils.logging_manager import get_logger
from tradingagents.storage.toolkits.cursor_usage import CursorUsageAnalyzer

logger = get_logger("api_cursor_usage")
router = APIRouter()

def get_analyzer(account_name: Optional[str] = None) -> CursorUsageAnalyzer:
    """获取 CursorUsageAnalyzer 实例（每次创建新实例以支持不同的 account_name）"""
    try:
        return CursorUsageAnalyzer(account_name=account_name)
    except Exception as e:
        logger.error(f"初始化 CursorUsageAnalyzer 失败: {e}")
        raise HTTPException(status_code=503, detail=f"Cursor 使用分析服务不可用: {e}")


# ==================== 响应模型 ====================

class DateListResponse(BaseModel):
    """日期列表响应"""
    success: bool
    dates: list[str]
    count: int
    message: str


class StatisticsResponse(BaseModel):
    """统计信息响应"""
    success: bool
    data: Dict[str, Any]
    message: str


# ==================== API 接口 ====================

@router.get("/dates", response_model=DateListResponse)
async def get_available_dates(
    account_name: Optional[str] = Query(None, description="账户名称"),
    start_date: Optional[str] = Query(None, description="开始日期 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="结束日期 (YYYY-MM-DD)")
):
    """
    获取所有可用的日期列表
    
    可选参数：
    - account_name: 账户名称过滤
    - start_date + end_date: 过滤指定日期范围内的文件
    
    返回所有可用的日期列表
    """
    try:
        from tradingagents.storage.mongodb.cursor_usage_manager import CursorUsageManager
        manager = CursorUsageManager()
        
        dates = manager.get_available_dates(
            account_name=account_name,
            start_date=start_date,
            end_date=end_date
        )
        
        count = len(dates)
        
        return DateListResponse(
            success=True,
            dates=dates,
            count=count,
            message=f"找到 {count} 个可用日期"
        )
    except Exception as e:
        logger.error(f"获取日期列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取日期列表失败: {e}")


@router.get("/statistics/total", response_model=StatisticsResponse)
async def get_total_statistics(
    account_name: Optional[str] = Query(None, description="账户名称"),
    start_date: Optional[str] = Query(None, description="开始日期 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="结束日期 (YYYY-MM-DD)")
):
    """
    获取总体统计信息
    
    可选参数：
    - account_name: 账户名称过滤
    - start_date + end_date: 指定日期区间
    - 如果不提供，则统计所有数据
    
    返回总体统计数据，包括：
    - 总请求数
    - 总成本
    - 总 tokens
    - 平均成本/请求
    """
    try:
        analyzer = get_analyzer(account_name=account_name)
        
        stats = analyzer.get_total_statistics(
            start_date=start_date,
            end_date=end_date
        )
        
        return StatisticsResponse(
            success=True,
            data=stats,
            message="统计查询成功"
        )
    except Exception as e:
        logger.error(f"获取总体统计失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取总体统计失败: {e}")


@router.get("/statistics/daily", response_model=StatisticsResponse)
async def get_daily_statistics(
    account_name: Optional[str] = Query(None, description="账户名称"),
    start_date: Optional[str] = Query(None, description="开始日期 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="结束日期 (YYYY-MM-DD)")
):
    """
    获取按日期分组的统计信息
    
    时间范围（可选）：
    - start_date + end_date: 指定日期区间
    - 如果不提供，则统计所有数据
    
    返回按日期分组的统计数据
    """
    try:
        analyzer = get_analyzer(account_name=account_name)
        
        stats = analyzer.get_daily_statistics(
            start_date=start_date,
            end_date=end_date
        )
        
        return StatisticsResponse(
            success=True,
            data=stats,
            message="按日期统计查询成功"
        )
    except Exception as e:
        logger.error(f"获取按日期统计失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取按日期统计失败: {e}")


@router.get("/statistics/kind", response_model=StatisticsResponse)
async def get_kind_statistics(
    account_name: Optional[str] = Query(None, description="账户名称"),
    start_date: Optional[str] = Query(None, description="开始日期 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="结束日期 (YYYY-MM-DD)")
):
    """
    按 Kind（免费/包含）分类统计
    
    时间范围（可选）：
    - start_date + end_date: 指定日期区间
    - 如果不提供，则统计所有数据
    
    返回按 Kind 分组的统计数据
    """
    try:
        analyzer = get_analyzer(account_name=account_name)
        
        stats = analyzer.get_kind_statistics(
            start_date=start_date,
            end_date=end_date
        )
        
        return StatisticsResponse(
            success=True,
            data=stats,
            message="按 Kind 统计查询成功"
        )
    except Exception as e:
        logger.error(f"获取按 Kind 统计失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取按 Kind 统计失败: {e}")


@router.get("/statistics/model", response_model=StatisticsResponse)
async def get_model_statistics(
    account_name: Optional[str] = Query(None, description="账户名称"),
    start_date: Optional[str] = Query(None, description="开始日期 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="结束日期 (YYYY-MM-DD)")
):
    """
    按模型分类统计
    
    时间范围（可选）：
    - start_date + end_date: 指定日期区间
    - 如果不提供，则统计所有数据
    
    返回按模型分组的统计数据
    """
    try:
        analyzer = get_analyzer(account_name=account_name)
        
        stats = analyzer.get_model_statistics(
            start_date=start_date,
            end_date=end_date
        )
        
        return StatisticsResponse(
            success=True,
            data=stats,
            message="按模型统计查询成功"
        )
    except Exception as e:
        logger.error(f"获取按模型统计失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取按模型统计失败: {e}")


@router.get("/statistics/cost", response_model=StatisticsResponse)
async def get_cost_statistics(
    account_name: Optional[str] = Query(None, description="账户名称"),
    start_date: Optional[str] = Query(None, description="开始日期 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="结束日期 (YYYY-MM-DD)")
):
    """
    获取费用统计（区分free和Included，auto仅作参考，其他模型单独累计）
    
    时间范围（可选）：
    - start_date + end_date: 指定日期区间
    - 如果不提供，则统计所有数据
    
    返回费用统计信息，包括：
    - free: 免费使用统计
    - Included: 套餐内使用统计
    - 每个类型下，auto的费用仅作参考，其他模型单独累计
    """
    try:
        analyzer = get_analyzer(account_name=account_name)
        
        stats = analyzer.get_cost_statistics(
            start_date=start_date,
            end_date=end_date
        )
        
        return StatisticsResponse(
            success=True,
            data=stats,
            message="费用统计查询成功"
        )
    except Exception as e:
        logger.error(f"获取费用统计失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取费用统计失败: {e}")


@router.get("/statistics/hourly", response_model=StatisticsResponse)
async def get_hourly_statistics(
    account_name: Optional[str] = Query(None, description="账户名称"),
    start_date: Optional[str] = Query(None, description="开始日期 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="结束日期 (YYYY-MM-DD)")
):
    """
    按小时统计
    
    时间范围（可选）：
    - start_date + end_date: 指定日期区间
    - 如果不提供，则统计所有数据
    
    返回按小时分组的统计数据（0-23）
    """
    try:
        analyzer = get_analyzer(account_name=account_name)
        
        stats = analyzer.get_hourly_statistics(
            start_date=start_date,
            end_date=end_date
        )
        
        # 将整数键转换为字符串键，以符合 JSON/Pydantic 规范
        stats_with_string_keys = {str(k): v for k, v in stats.items()}
        
        return StatisticsResponse(
            success=True,
            data=stats_with_string_keys,
            message="按小时统计查询成功"
        )
    except Exception as e:
        logger.error(f"获取按小时统计失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取按小时统计失败: {e}")

