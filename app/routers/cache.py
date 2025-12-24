"""
缓存管理路由模块
提供Redis缓存记录的查询接口
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import time

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
    page_size: int = Query(10, ge=1, le=100, description="每页数量"),
    task_id: Optional[str] = Query(None, description="任务ID筛选（支持部分匹配）"),
    analysis_date: Optional[str] = Query(None, description="分析日期筛选（精确匹配）"),
    status: Optional[str] = Query(None, description="运行状态筛选（精确匹配）"),
    stock_symbol: Optional[str] = Query(None, description="股票代码筛选（支持部分匹配）"),
    company_name: Optional[str] = Query(None, description="公司名称筛选（支持部分匹配）")
):
    """
    分页查询缓存记录的缩略信息（支持筛选）
    
    返回包含task_id、status、created_at、updated_at、analysis_date、stock_symbol、company_name的列表
    
    筛选参数说明：
    - task_id: 任务ID筛选，支持部分匹配（不区分大小写）
    - analysis_date: 分析日期筛选，精确匹配
    - status: 运行状态筛选，精确匹配（如：completed, running, pending, failed等）
    - stock_symbol: 股票代码筛选，支持部分匹配（不区分大小写）
    - company_name: 公司名称筛选，支持部分匹配（不区分大小写）
    """
    start_time = time.time()
    logger.info(f"[缓存列表查询] 开始处理请求 - page={page}, page_size={page_size}, "
                f"filters={{task_id={task_id}, analysis_date={analysis_date}, status={status}, "
                f"stock_symbol={stock_symbol}, company_name={company_name}}}")
    
    try:
        step_start = time.time()
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
        logger.info(f"[缓存列表查询] Redis连接检查完成，耗时: {time.time() - step_start:.3f}秒")
        
        # 指定要提取的字段
        fields = ['status', 'created_at', 'updated_at', 'analysis_date', 'stock_symbol', 'company_of_interest']
        
        # 如果使用company_name筛选，需要先获取所有数据（不分页），然后筛选后再分页
        # 否则可以直接使用分页
        if company_name:
            # 获取所有数据（使用一个很大的page_size来获取所有数据）
            # 或者我们可以先获取总数，然后获取所有数据
            # 为了效率，我们使用一个合理的page_size，比如10000
            step_start = time.time()
            result = cache_manager.get_task_cache_list(
                sub_key="props",
                fields=fields,
                page=1,
                page_size=10000,  # 获取所有数据
                task_id=task_id,
                analysis_date=analysis_date,
                status=status,
                stock_symbol=stock_symbol,
                company_name=None  # company_name筛选在路由层处理
            )
            logger.info(f"[缓存列表查询] 从Redis获取缓存列表完成，获取到 {len(result['items'])} 条记录，耗时: {time.time() - step_start:.3f}秒")
            
            # 处理返回的数据，添加公司名称，并应用company_name筛选
            step_start = time.time()
            cache_list = []
            company_name_lookup_count = 0
            for item in result["items"]:
                task_id_item = item.get("task_id")
                stock_symbol_item = item.get('stock_symbol') or item.get('company_of_interest')
                company_name_item = None
                if stock_symbol_item:
                    company_name_item = stock_dict_manager.get_company_name(stock_symbol_item)
                    company_name_lookup_count += 1
                
                # 应用company_name筛选
                if not company_name_item or company_name.lower() not in company_name_item.lower():
                    continue
                
                cache_list.append(CacheListItem(
                    task_id=task_id_item,
                    status=item.get('status', 'unknown'),
                    created_at=item.get('created_at'),
                    updated_at=item.get('updated_at'),
                    analysis_date=item.get('analysis_date'),
                    stock_symbol=stock_symbol_item,
                    company_name=company_name_item
                ))
            logger.info(f"[缓存列表查询] 公司名称查询和筛选完成，查询了 {company_name_lookup_count} 次，筛选后剩余 {len(cache_list)} 条，耗时: {time.time() - step_start:.3f}秒")
            
            # 应用company_name筛选后，重新计算分页
            step_start = time.time()
            total_filtered = len(cache_list)
            pages_filtered = (total_filtered + page_size - 1) // page_size if total_filtered > 0 else 0
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            cache_list = cache_list[start_idx:end_idx]
            logger.info(f"[缓存列表查询] 分页处理完成，总记录数: {total_filtered}, 当前页: {page}/{pages_filtered}, 耗时: {time.time() - step_start:.3f}秒")
            
            total_time = time.time() - start_time
            logger.info(f"[缓存列表查询] 请求处理完成，总耗时: {total_time:.3f}秒，返回 {len(cache_list)} 条记录")
            
            return CacheListResponse(
                success=True,
                data=cache_list,
                total=total_filtered,
                page=page,
                page_size=page_size,
                pages=pages_filtered,
                message="获取成功"
            )
        else:
            # 没有company_name筛选，可以直接使用分页
            step_start = time.time()
            result = cache_manager.get_task_cache_list(
                sub_key="props",
                fields=fields,
                page=page,
                page_size=page_size,
                task_id=task_id,
                analysis_date=analysis_date,
                status=status,
                stock_symbol=stock_symbol,
                company_name=None
            )
            logger.info(f"[缓存列表查询] 从Redis获取缓存列表完成，获取到 {len(result['items'])} 条记录，总记录数: {result['total']}，耗时: {time.time() - step_start:.3f}秒")
            
            # 处理返回的数据，添加公司名称
            step_start = time.time()
            cache_list = []
            company_name_lookup_count = 0
            for item in result["items"]:
                task_id_item = item.get("task_id")
                stock_symbol_item = item.get('stock_symbol') or item.get('company_of_interest')
                company_name_item = None
                if stock_symbol_item:
                    company_name_item = stock_dict_manager.get_company_name(stock_symbol_item)
                    company_name_lookup_count += 1
                
                cache_list.append(CacheListItem(
                    task_id=task_id_item,
                    status=item.get('status', 'unknown'),
                    created_at=item.get('created_at'),
                    updated_at=item.get('updated_at'),
                    analysis_date=item.get('analysis_date'),
                    stock_symbol=stock_symbol_item,
                    company_name=company_name_item
                ))
            logger.info(f"[缓存列表查询] 公司名称查询完成，查询了 {company_name_lookup_count} 次，耗时: {time.time() - step_start:.3f}秒")
            
            total_time = time.time() - start_time
            logger.info(f"[缓存列表查询] 请求处理完成，总耗时: {total_time:.3f}秒，返回 {len(cache_list)} 条记录")
            
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
        total_time = time.time() - start_time
        logger.error(f"[缓存列表查询] 请求处理失败，总耗时: {total_time:.3f}秒，错误: {e}", exc_info=True)
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

