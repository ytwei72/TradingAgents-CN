"""
缓存管理路由模块
提供Redis缓存记录的查询接口
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

from tradingagents.utils.logging_manager import get_logger
from tradingagents.storage.redis.connection import REDIS_AVAILABLE
from tradingagents.storage.redis.cache_manager import redis_cache_manager
from tradingagents.storage.mongodb.stock_dict_manager import stock_dict_manager

router = APIRouter()
logger = get_logger("cache_router")


class CacheCountResponse(BaseModel):
    """缓存记录总数响应"""
    success: bool
    total: int
    message: str


class CacheListItem(BaseModel):
    """缓存记录列表项"""
    task_id: str
    status: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    analysis_date: Optional[str] = None
    stock_symbol: Optional[str] = None
    company_name: Optional[str] = None


class CacheListResponse(BaseModel):
    """缓存记录列表响应"""
    success: bool
    data: List[CacheListItem]
    total: int
    page: int
    page_size: int
    pages: int
    message: str


class CacheDetailResponse(BaseModel):
    """缓存记录详细信息响应"""
    success: bool
    data: Dict[str, Any]
    message: str


@router.get("/count", response_model=CacheCountResponse)
async def get_cache_count():
    """
    获取所有缓存记录的总数
    
    返回Redis中所有task缓存记录的数量
    """
    try:
        if not REDIS_AVAILABLE:
            raise HTTPException(
                status_code=500,
                detail="Redis不可用，请检查Redis配置"
            )
        
        cache_manager = redis_cache_manager()
        if not cache_manager.is_available():
            raise HTTPException(
                status_code=500,
                detail="Redis连接失败"
            )
        
        task_ids = cache_manager.get_all_task_ids()
        total = len(task_ids)
        
        return CacheCountResponse(
            success=True,
            total=total,
            message="获取成功"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取缓存记录总数失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"获取缓存记录总数失败: {str(e)}"
        )


@router.get("/list", response_model=CacheListResponse)
async def get_cache_list(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量")
):
    """
    分页查询缓存记录的缩略信息
    
    返回包含task_id、status、created_at、updated_at、analysis_date、stock_symbol、company_name的列表
    """
    try:
        if not REDIS_AVAILABLE:
            raise HTTPException(
                status_code=500,
                detail="Redis不可用，请检查Redis配置"
            )
        
        cache_manager = redis_cache_manager()
        if not cache_manager.is_available():
            raise HTTPException(
                status_code=500,
                detail="Redis连接失败"
            )
        
        # 指定要提取的字段
        fields = ['status', 'created_at', 'updated_at', 'analysis_date', 'stock_symbol', 'company_of_interest']
        
        # 调用封装的方法获取缓存列表
        result = cache_manager.get_task_cache_list(
            sub_key="props",
            fields=fields,
            page=page,
            page_size=page_size
        )
        
        # 处理返回的数据，添加公司名称
        cache_list = []
        for item in result["items"]:
            task_id = item.get("task_id")
            stock_symbol = item.get('stock_symbol') or item.get('company_of_interest')
            company_name = None
            if stock_symbol:
                company_name = stock_dict_manager.get_company_name(stock_symbol)
            
            cache_list.append(CacheListItem(
                task_id=task_id,
                status=item.get('status', 'unknown'),
                created_at=item.get('created_at'),
                updated_at=item.get('updated_at'),
                analysis_date=item.get('analysis_date'),
                stock_symbol=stock_symbol,
                company_name=company_name
            ))
        
        return CacheListResponse(
            success=True,
            data=cache_list,
            total=result["total"],
            page=result["page"],
            page_size=result["page_size"],
            pages=result["pages"],
            message="获取成功"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取缓存记录列表失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"获取缓存记录列表失败: {str(e)}"
        )


@router.get("/{analysis_id}", response_model=CacheDetailResponse)
async def get_cache_detail(analysis_id: str):
    """
    根据analysis_id获取缓存记录的详细信息
    
    返回包含current_step、history、props的完整信息
    每个字段值最多显示50个字符，多余的用省略号表示
    """
    try:
        if not REDIS_AVAILABLE:
            raise HTTPException(
                status_code=500,
                detail="Redis不可用，请检查Redis配置"
            )
        
        cache_manager = redis_cache_manager()
        if not cache_manager.is_available():
            raise HTTPException(
                status_code=500,
                detail="Redis连接失败"
            )
        
        # 调用封装的方法获取缓存详情
        # 指定要获取的子键和截断长度
        result = cache_manager.get_task_cache_detail(
            task_id=analysis_id,
            sub_keys=["current_step", "history", "props"],
            truncate_length=50
        )
        
        # 如果所有数据都不存在，返回404
        if not any(v for v in result.values() if v is not None):
            raise HTTPException(
                status_code=404,
                detail=f"未找到analysis_id为{analysis_id}的缓存记录"
            )
        
        return CacheDetailResponse(
            success=True,
            data=result,
            message="获取成功"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取缓存记录详细信息失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"获取缓存记录详细信息失败: {str(e)}"
        )

