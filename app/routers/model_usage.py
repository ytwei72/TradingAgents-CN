"""
模型使用记录 API 接口
包含 model usage 相关的读写、统计、查询等接口
"""

from typing import Optional, Dict, Any, List
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from tradingagents.utils.logging_manager import get_logger


logger = get_logger("api_usage")
router = APIRouter()

# 延迟加载 ModelUsageManager 避免启动时连接问题
_usage_manager = None


def get_usage_manager():
    """获取 ModelUsageManager 实例（延迟初始化）"""
    global _usage_manager
    if _usage_manager is None:
        try:
            from tradingagents.storage.mongodb.model_usage_manager import ModelUsageManager
            _usage_manager = ModelUsageManager()
        except Exception as e:
            logger.error(f"初始化 ModelUsageManager 失败: {e}")
            raise HTTPException(status_code=503, detail=f"使用记录服务不可用: {e}")
    return _usage_manager


# ==================== 请求/响应模型 ====================

class UsageRecordCreate(BaseModel):
    """创建使用记录请求"""
    timestamp: Optional[str] = Field(None, description="时间戳 (ISO格式)，不传则使用当前时间")
    provider: str = Field(..., description="供应商名称")
    model_name: str = Field(..., description="模型名称")
    input_tokens: int = Field(..., ge=0, description="输入token数")
    output_tokens: int = Field(..., ge=0, description="输出token数")
    cost: float = Field(..., ge=0, description="成本")
    session_id: str = Field(..., description="会话ID")
    analysis_type: str = Field("", description="分析类型")


class UsageRecordResponse(BaseModel):
    """使用记录响应"""
    timestamp: str
    provider: str
    model_name: str
    input_tokens: int
    output_tokens: int
    cost: float
    session_id: str
    analysis_type: str


class UsageRecordsListResponse(BaseModel):
    """使用记录列表响应"""
    success: bool
    data: List[UsageRecordResponse]
    total: int
    message: str


class UsageStatisticsResponse(BaseModel):
    """使用统计响应"""
    success: bool
    data: Dict[str, Any]
    message: str


class UsageCountResponse(BaseModel):
    """记录数量响应"""
    success: bool
    count: int
    message: str


class InsertRecordResponse(BaseModel):
    """插入记录响应"""
    success: bool
    record_id: Optional[str] = None
    message: str


class BatchInsertResponse(BaseModel):
    """批量插入响应"""
    success: bool
    inserted_count: int
    message: str


class CleanupResponse(BaseModel):
    """清理响应"""
    success: bool
    deleted_count: int
    message: str


# ==================== API 接口 ====================

@router.get("/records", response_model=UsageRecordsListResponse)
async def get_usage_records(
    limit: int = Query(100, ge=1, le=10000, description="返回记录数限制"),
    days: Optional[int] = Query(None, ge=1, description="最近N天的记录"),
    provider: Optional[str] = Query(None, description="按供应商过滤"),
    model_name: Optional[str] = Query(None, description="按模型名称过滤"),
    session_id: Optional[str] = Query(None, description="按会话ID过滤"),
    analysis_type: Optional[str] = Query(None, description="按分析类型过滤"),
    start_date: Optional[str] = Query(None, description="开始日期 (ISO格式)"),
    end_date: Optional[str] = Query(None, description="结束日期 (ISO格式)")
):
    """
    查询模型使用记录
    
    支持多种过滤条件：
    - limit: 返回记录数限制（默认100，最大10000）
    - days: 最近N天的记录
    - provider: 按供应商过滤
    - model_name: 按模型名称过滤
    - session_id: 按会话ID过滤
    - analysis_type: 按分析类型过滤
    - start_date/end_date: 时间范围过滤
    """
    try:
        manager = get_usage_manager()
        
        if not manager.is_connected():
            raise HTTPException(status_code=503, detail="MongoDB 连接不可用")
        
        records = manager.query_usage_records(
            limit=limit,
            days=days,
            provider=provider,
            model_name=model_name,
            session_id=session_id,
            analysis_type=analysis_type,
            start_date=start_date,
            end_date=end_date
        )
        
        # 转换为响应格式
        records_data = [
            UsageRecordResponse(
                timestamp=r.timestamp,
                provider=r.provider,
                model_name=r.model_name,
                input_tokens=r.input_tokens,
                output_tokens=r.output_tokens,
                cost=r.cost,
                session_id=r.session_id,
                analysis_type=r.analysis_type
            )
            for r in records
        ]
        
        return UsageRecordsListResponse(
            success=True,
            data=records_data,
            total=len(records_data),
            message="查询成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询使用记录失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"查询使用记录失败: {e}")


@router.get("/statistics", response_model=UsageStatisticsResponse)
async def get_usage_statistics(
    days: int = Query(30, ge=1, le=365, description="统计最近N天的数据"),
    provider: Optional[str] = Query(None, description="按供应商过滤"),
    model_name: Optional[str] = Query(None, description="按模型名称过滤")
):
    """
    获取模型使用统计信息
    
    返回指定时间范围内的总体统计数据，包括：
    - 总成本
    - 总输入/输出 tokens
    - 总请求数
    - 平均成本
    - 平均 tokens
    """
    try:
        manager = get_usage_manager()
        
        if not manager.is_connected():
            raise HTTPException(status_code=503, detail="MongoDB 连接不可用")
        
        stats = manager.get_usage_statistics(
            days=days,
            provider=provider,
            model_name=model_name
        )
        
        return UsageStatisticsResponse(
            success=True,
            data=stats,
            message="统计查询成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取使用统计失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取使用统计失败: {e}")


@router.get("/statistics/providers", response_model=UsageStatisticsResponse)
async def get_provider_statistics(
    days: int = Query(30, ge=1, le=365, description="统计最近N天的数据")
):
    """
    按供应商获取统计信息
    
    返回按供应商分组的统计数据，每个供应商包括：
    - 总成本
    - 总输入/输出 tokens
    - 请求数
    - 平均成本
    """
    try:
        manager = get_usage_manager()
        
        if not manager.is_connected():
            raise HTTPException(status_code=503, detail="MongoDB 连接不可用")
        
        stats = manager.get_provider_statistics(days=days)
        
        return UsageStatisticsResponse(
            success=True,
            data=stats,
            message="供应商统计查询成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取供应商统计失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取供应商统计失败: {e}")


@router.get("/statistics/models", response_model=UsageStatisticsResponse)
async def get_model_statistics(
    days: int = Query(30, ge=1, le=365, description="统计最近N天的数据"),
    provider: Optional[str] = Query(None, description="按供应商过滤")
):
    """
    按模型获取统计信息
    
    返回按模型分组的统计数据，每个模型包括：
    - 供应商
    - 模型名称
    - 总成本
    - 总输入/输出 tokens
    - 请求数
    - 平均成本
    """
    try:
        manager = get_usage_manager()
        
        if not manager.is_connected():
            raise HTTPException(status_code=503, detail="MongoDB 连接不可用")
        
        stats = manager.get_model_statistics(days=days, provider=provider)
        
        return UsageStatisticsResponse(
            success=True,
            data=stats,
            message="模型统计查询成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取模型统计失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取模型统计失败: {e}")


@router.get("/count", response_model=UsageCountResponse)
async def get_records_count(
    days: Optional[int] = Query(None, ge=1, description="统计最近N天的记录"),
    provider: Optional[str] = Query(None, description="按供应商过滤"),
    model_name: Optional[str] = Query(None, description="按模型名称过滤")
):
    """
    统计记录数量
    
    返回符合条件的记录总数
    """
    try:
        manager = get_usage_manager()
        
        if not manager.is_connected():
            raise HTTPException(status_code=503, detail="MongoDB 连接不可用")
        
        count = manager.count_records(
            days=days,
            provider=provider,
            model_name=model_name
        )
        
        return UsageCountResponse(
            success=True,
            count=count,
            message="统计成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"统计记录数量失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"统计记录数量失败: {e}")


@router.post("/records", response_model=InsertRecordResponse)
async def create_usage_record(record: UsageRecordCreate):
    """
    添加单个使用记录
    
    创建一条新的模型使用记录
    """
    try:
        manager = get_usage_manager()
        
        if not manager.is_connected():
            raise HTTPException(status_code=503, detail="MongoDB 连接不可用")
        
        from tradingagents.storage.mongodb.model_usage_manager import UsageRecord
        
        # 如果没有提供时间戳，使用当前时间
        timestamp = record.timestamp or datetime.now().isoformat()
        
        usage_record = UsageRecord(
            timestamp=timestamp,
            provider=record.provider,
            model_name=record.model_name,
            input_tokens=record.input_tokens,
            output_tokens=record.output_tokens,
            cost=record.cost,
            session_id=record.session_id,
            analysis_type=record.analysis_type
        )
        
        record_id = manager.insert_usage_record(usage_record)
        
        if record_id:
            return InsertRecordResponse(
                success=True,
                record_id=record_id,
                message="记录添加成功"
            )
        else:
            return InsertRecordResponse(
                success=False,
                record_id=None,
                message="记录添加失败"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"添加使用记录失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"添加使用记录失败: {e}")


@router.post("/records/batch", response_model=BatchInsertResponse)
async def create_usage_records_batch(records: List[UsageRecordCreate]):
    """
    批量添加使用记录
    
    一次性创建多条模型使用记录
    """
    try:
        manager = get_usage_manager()
        
        if not manager.is_connected():
            raise HTTPException(status_code=503, detail="MongoDB 连接不可用")
        
        if not records:
            return BatchInsertResponse(
                success=True,
                inserted_count=0,
                message="没有要插入的记录"
            )
        
        from tradingagents.storage.mongodb.model_usage_manager import UsageRecord
        
        usage_records = []
        for r in records:
            timestamp = r.timestamp or datetime.now().isoformat()
            usage_records.append(UsageRecord(
                timestamp=timestamp,
                provider=r.provider,
                model_name=r.model_name,
                input_tokens=r.input_tokens,
                output_tokens=r.output_tokens,
                cost=r.cost,
                session_id=r.session_id,
                analysis_type=r.analysis_type
            ))
        
        inserted_count = manager.insert_many_usage_records(usage_records)
        
        return BatchInsertResponse(
            success=inserted_count > 0,
            inserted_count=inserted_count,
            message=f"成功插入 {inserted_count} 条记录"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量添加使用记录失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"批量添加使用记录失败: {e}")


@router.delete("/records/cleanup", response_model=CleanupResponse)
async def cleanup_old_records(
    days: int = Query(90, ge=1, le=365, description="删除N天前的记录")
):
    """
    清理旧记录
    
    删除指定天数之前的历史记录，用于数据清理和空间管理
    
    注意：此操作不可逆，请谨慎使用
    """
    try:
        manager = get_usage_manager()
        
        if not manager.is_connected():
            raise HTTPException(status_code=503, detail="MongoDB 连接不可用")
        
        deleted_count = manager.cleanup_old_records(days=days)
        
        return CleanupResponse(
            success=True,
            deleted_count=deleted_count,
            message=f"成功清理 {deleted_count} 条超过 {days} 天的记录"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"清理旧记录失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"清理旧记录失败: {e}")


@router.get("/health", response_model=Dict[str, Any])
async def check_usage_service_health():
    """
    检查使用记录服务健康状态
    
    返回服务连接状态和基本信息
    """
    try:
        manager = get_usage_manager()
        
        connected = manager.is_connected()
        
        result = {
            "success": True,
            "connected": connected,
            "collection": manager.collection_name if connected else None,
            "message": "服务正常" if connected else "MongoDB 连接不可用"
        }
        
        # 如果连接正常，获取记录数量
        if connected:
            result["total_records"] = manager.count_records()
        
        return result
        
    except Exception as e:
        logger.error(f"检查服务健康状态失败: {e}", exc_info=True)
        return {
            "success": False,
            "connected": False,
            "collection": None,
            "message": f"服务检查失败: {e}"
        }

