"""
回测相关接口
当前实现：研报批量回测入口（占位实现）
"""

from datetime import date
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from tradingagents.utils.logging_manager import get_logger
from app.services.backtest_service import backtest_service


router = APIRouter()
logger = get_logger("backtest_router")


class ReportBatchBacktestRequest(BaseModel):
    """研报批量回测请求参数"""

    policy: int = Field(..., description="回测策略类型，当前仅支持 1")
    research_start_date: date = Field(..., description="研究分析起始日期")
    research_end_date: date = Field(..., description="研究分析结束日期")
    backtest_start_date: date = Field(..., description="回测历史数据起始日期")
    backtest_end_date: date = Field(..., description="回测历史数据结束日期")


class ReportBatchBacktestResponse(BaseModel):
    """研报批量回测响应"""

    success: bool = Field(..., description="是否创建成功")
    message: str = Field(..., description="状态说明")
    policy: int = Field(..., description="使用的回测策略")
    task_id: Optional[str] = Field(
        default=None, description="批量回测任务ID（预留字段，后续接入任务系统）"
    )


@router.post(
    "/analysis/batch-backtest",
    response_model=ReportBatchBacktestResponse,
    summary="研报批量回测",
    tags=["backtest"],
)
async def start_report_batch_backtest(request: ReportBatchBacktestRequest):
    """
    启动研报批量回测任务（占位实现）

    - **policy**: 回测策略，当前仅支持值为 `1`
    - **research_start_date / research_end_date**: 研究分析时间段
    - **backtest_start_date / backtest_end_date**: 回测历史数据时间段
    """

    # 目前仅支持策略 1
    if request.policy != 1:
        raise HTTPException(
            status_code=400,
            detail="当前仅支持 policy=1 的回测策略",
        )

    # 基本时间区间校验
    if request.research_start_date > request.research_end_date:
        raise HTTPException(
            status_code=400,
            detail="研究分析时间段的起始日期不能晚于结束日期",
        )

    if request.backtest_start_date > request.backtest_end_date:
        raise HTTPException(
            status_code=400,
            detail="回测历史数据时间段的起始日期不能晚于结束日期",
    )

    logger.info(
        "收到研报批量回测请求 | policy=%s research=[%s,%s] backtest=[%s,%s]",
        request.policy,
        request.research_start_date,
        request.research_end_date,
        request.backtest_start_date,
        request.backtest_end_date,
    )

    # 调用回测服务，集中处理批量回测逻辑（当前为占位实现）
    service_result = backtest_service.start_report_batch_backtest(
        policy=request.policy,
        research_start_date=request.research_start_date,
        research_end_date=request.research_end_date,
        backtest_start_date=request.backtest_start_date,
        backtest_end_date=request.backtest_end_date,
    )

    return ReportBatchBacktestResponse(
        success=True,
        message="研报批量回测任务创建成功（占位实现，尚未接入实际回测引擎）",
        policy=service_result.get("policy", request.policy),
        task_id=service_result.get("task_id"),
    )
