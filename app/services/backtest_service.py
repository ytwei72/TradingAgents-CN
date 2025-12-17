"""
回测服务模块

当前实现：研报批量回测服务占位，用于接收 API 参数并统一调度后续回测引擎。
"""

from __future__ import annotations

from datetime import date
from typing import Optional
import logging


logger = logging.getLogger(__name__)


class BacktestService:
    """回测服务类

    负责接收批量回测请求参数，并在后续接入真实回测引擎或任务系统时，作为统一入口。
    """

    def __init__(self) -> None:
        # 这里可以预留一些初始化配置，例如结果目录、任务管理器等
        self._initialized = True

    def start_report_batch_backtest(
        self,
        *,
        policy: int,
        research_start_date: date,
        research_end_date: date,
        backtest_start_date: date,
        backtest_end_date: date,
    ) -> dict:
        """启动研报批量回测任务（占位实现）

        Args:
            policy: 回测策略类型，当前仅支持 1
            research_start_date: 研究分析起始日期
            research_end_date: 研究分析结束日期
            backtest_start_date: 回测历史数据起始日期
            backtest_end_date: 回测历史数据结束日期

        Returns:
            dict: 包含占位 task_id 等信息的结果对象
        """
        logger.info(
            "BacktestService.start_report_batch_backtest | policy=%s research=[%s,%s] backtest=[%s,%s]",
            policy,
            research_start_date,
            research_end_date,
            backtest_start_date,
            backtest_end_date,
        )

        # TODO: 在此处对接真实的任务管理器 / 回测引擎，例如：
        # task_id = task_manager.start_backtest_task(...)
        # 目前返回占位 task_id，方便前后端联调。
        task_id: Optional[str] = None

        return {
            "task_id": task_id,
            "policy": policy,
            "research_start_date": research_start_date,
            "research_end_date": research_end_date,
            "backtest_start_date": backtest_start_date,
            "backtest_end_date": backtest_end_date,
        }


backtest_service = BacktestService()


