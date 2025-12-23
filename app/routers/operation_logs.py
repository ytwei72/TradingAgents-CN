"""
操作日志API路由
用于读取和查询系统日志（从MongoDB）
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel

router = APIRouter()

# 导入系统日志管理器
from tradingagents.storage.mongodb.system_logs_manager import get_system_logs_manager


class LogsResponse(BaseModel):
    success: bool
    data: List[Dict[str, Any]]
    total: int
    filtered_total: int
    message: str


@router.get("/query", response_model=LogsResponse)
async def get_operation_logs(
    start_date: Optional[str] = Query(None, description="开始日期 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="结束日期 (YYYY-MM-DD)"),
    days: Optional[int] = Query(None, description="近N天"),
    keyword: Optional[str] = Query(None, description="关键字搜索"),
    level: Optional[str] = Query(None, description="日志级别过滤 (INFO, WARNING, ERROR)"),
    logger: Optional[str] = Query(None, description="Logger名称过滤"),
    limit: Optional[int] = Query(1000, description="返回结果数量限制", ge=1, le=10000),
    skip: Optional[int] = Query(0, description="跳过的记录数（用于分页）", ge=0)
):
    """
    获取操作日志（从MongoDB）
    
    支持：
    - 日期区间筛选（start_date和end_date）
    - 近N天筛选（days参数）
    - 关键字搜索（在message, module, function, logger字段中搜索）
    - 日志级别过滤
    - Logger名称过滤
    - 分页支持（skip和limit）
    """
    try:
        # 获取系统日志管理器
        logs_manager = get_system_logs_manager()
        
        # 查询日志
        logs, total_count = logs_manager.query_logs(
            start_date=start_date,
            end_date=end_date,
            days=days,
            keyword=keyword,
            level=level,
            logger_name=logger,
            limit=limit,
            skip=skip
        )
        
        return LogsResponse(
            success=True,
            data=logs,
            total=total_count,
            filtered_total=len(logs),
            message="获取日志成功"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取日志失败: {str(e)}")


@router.get("/stats")
async def get_logs_stats():
    """获取日志统计信息（从MongoDB）"""
    try:
        # 获取系统日志管理器
        logs_manager = get_system_logs_manager()
        
        # 获取统计信息
        stats = logs_manager.get_logs_stats()
        
        return {
            "success": stats.get("success", True),
            "data": {
                "total_count": stats.get("total_count", 0),
                "by_level": stats.get("by_level", {}),
                "by_logger": stats.get("by_logger", {}),
                "latest_timestamp": stats.get("latest_timestamp"),
                "earliest_timestamp": stats.get("earliest_timestamp")
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取日志统计失败: {str(e)}")

