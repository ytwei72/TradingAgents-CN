"""
回测相关接口
当前实现：研报批量回测入口（占位实现）
"""

from datetime import date
from typing import Optional, List, Dict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from tradingagents.utils.logging_manager import get_logger
from app.services.backtest_service import backtest_service


router = APIRouter()
logger = get_logger("backtest_router")


class ReportBatchBacktestRequest(BaseModel):
    """研报批量回测请求参数"""

    analysis_ids: List[str] = Field(..., description="前端选中的研报 analysis_id 列表")


class SingleReportProfit(BaseModel):
    """单篇研报的收益序列"""
    analysis_id: str
    stock_symbol: str
    company_name: str
    analysis_date: str
    action: str
    profits: List[float]  # 收益序列（%），每个元素对应第1天到第N天的收益


class BatchBacktestStats(BaseModel):
    """批量回测统计信息"""
    weighted_avg: List[float]  # 加权平均收益序列


class ReportBatchBacktestResponse(BaseModel):
    """研报批量回测响应"""

    success: bool = Field(..., description="是否创建成功")
    message: str = Field(..., description="状态说明")
    data: Optional[Dict] = Field(
        default=None, description="回测结果数据，包含profits和stats"
    )


@router.post(
    "/batch/start-backtest",
    response_model=ReportBatchBacktestResponse,
    summary="研报批量回测",
    tags=["backtest"],
)
async def start_report_batch_backtest(request: ReportBatchBacktestRequest):
    """
    启动研报批量回测任务

    - **analysis_ids**: 前端选中的研报 analysis_id 列表
    
    回测配置参数（horizon_days、extend_days_before、extend_days_after、weight_mode、date_mode）
    从数据库的 backtest_config 中获取。
    """

    if not request.analysis_ids:
        raise HTTPException(
            status_code=400,
            detail="analysis_ids 不能为空",
        )

    logger.info(
        "收到研报批量回测请求 | analysis_ids_count=%s",
        len(request.analysis_ids),
    )

    # 调用回测服务，集中处理批量回测逻辑
    service_result = backtest_service.start_report_batch_backtest(
        analysis_ids=request.analysis_ids,
    )

    return ReportBatchBacktestResponse(
        success=True,
        message="研报批量回测完成",
        data=service_result.get("data"),
    )
