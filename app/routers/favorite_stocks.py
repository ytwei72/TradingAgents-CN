"""
自选股管理路由模块
提供自选股的增删改查、统计等功能接口
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

from tradingagents.utils.logging_manager import get_logger
from tradingagents.storage.mongodb.favorite_stocks_manager import favorite_stocks_manager

router = APIRouter()
logger = get_logger("favorite_stocks_router")


# ==================== 请求/响应模型 ====================

class FavoriteStockCreate(BaseModel):
    """创建自选股请求"""
    stock_code: str = Field(..., description="股票代码")
    user_id: Optional[str] = Field("default", description="用户ID")
    stock_name: Optional[str] = Field(None, description="股票名称（如不提供，将从股票字典自动查询）")
    market_type: Optional[str] = Field(None, description="市场类型")
    category: Optional[str] = Field("default", description="分类")
    tags: Optional[List[str]] = Field(default_factory=list, description="标签列表")
    themes: Optional[List[str]] = Field(default_factory=list, description="概念板块（Theme）列表")
    sectors: Optional[List[str]] = Field(default_factory=list, description="行业板块（Sector）列表")
    notes: Optional[str] = Field("无", description="备注")


class FavoriteStockUpdate(BaseModel):
    """更新自选股请求"""
    stock_name: Optional[str] = Field(None, description="股票名称")
    market_type: Optional[str] = Field(None, description="市场类型")
    category: Optional[str] = Field(None, description="分类")
    tags: Optional[List[str]] = Field(None, description="标签列表")
    themes: Optional[List[str]] = Field(None, description="概念板块（Theme）列表")
    sectors: Optional[List[str]] = Field(None, description="行业板块（Sector）列表")
    notes: Optional[str] = Field(None, description="备注")


class FavoriteStockResponse(BaseModel):
    """自选股响应"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    message: str


class FavoriteStockListResponse(BaseModel):
    """自选股列表响应"""
    success: bool
    data: Optional[List[Dict[str, Any]]] = None
    total: int = 0
    message: str


class FavoriteStockStatisticsResponse(BaseModel):
    """自选股统计响应"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    message: str


# ==================== API接口 ====================

@router.post("", response_model=FavoriteStockResponse)
async def create_favorite_stock(stock_data: FavoriteStockCreate):
    """
    创建自选股记录
    
    - **stock_code**: 股票代码（必填）
    - **user_id**: 用户ID（可选，默认"default"）
    - **stock_name**: 股票名称（可选）
    - **market_type**: 市场类型（可选）
    - **category**: 分类（可选，默认"default"）
    - **tags**: 标签列表（可选）
    - **notes**: 备注（可选）
    """
    try:
        if not favorite_stocks_manager.connected:
            raise HTTPException(
                status_code=500,
                detail="MongoDB自选股服务不可用，请检查数据库配置"
            )
        
        # 转换为字典
        stock_dict = stock_data.model_dump(exclude_unset=True)
        
        # 插入记录
        success = favorite_stocks_manager.insert(stock_dict)
        
        if not success:
            raise HTTPException(
                status_code=400,
                detail="创建自选股失败，可能已存在相同的记录"
            )
        
        # 查询刚创建的记录
        result = favorite_stocks_manager.get_by_stock_code(
            stock_data.stock_code,
            stock_data.user_id
        )
        
        return FavoriteStockResponse(
            success=True,
            data=result,
            message="创建成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建自选股失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"创建自选股失败: {str(e)}"
        )


@router.get("", response_model=FavoriteStockListResponse)
async def get_favorite_stocks(
    user_id: Optional[str] = Query("default", description="用户ID"),
    stock_code: Optional[str] = Query(None, description="股票代码（可选，用于精确查询）"),
    category: Optional[str] = Query(None, description="分类（可选）"),
    tag: Optional[str] = Query(None, description="标签（可选）"),
    limit: int = Query(100, ge=1, le=1000, description="最大返回数量"),
    skip: int = Query(0, ge=0, description="跳过记录数（用于分页）"),
    sort_by: str = Query("created_at", description="排序字段"),
    sort_order: str = Query("desc", description="排序方向（asc/desc）")
):
    """
    查询自选股列表
    
    - **user_id**: 用户ID（默认"default"）
    - **stock_code**: 股票代码（可选）
    - **category**: 分类（可选）
    - **tag**: 标签（可选）
    - **limit**: 最大返回数量
    - **skip**: 跳过记录数（用于分页）
    - **sort_by**: 排序字段
    - **sort_order**: 排序方向（asc/desc）
    """
    try:
        if not favorite_stocks_manager.connected:
            raise HTTPException(
                status_code=500,
                detail="MongoDB自选股服务不可用，请检查数据库配置"
            )
        
        # 构建查询条件
        filter_dict = {"user_id": user_id}
        
        if stock_code:
            filter_dict["stock_code"] = stock_code
        
        if category:
            filter_dict["category"] = category
        
        if tag:
            filter_dict["tags"] = tag
        
        # 构建排序规则
        from pymongo import ASCENDING, DESCENDING
        sort_order_pymongo = DESCENDING if sort_order.lower() == "desc" else ASCENDING
        sort = [(sort_by, sort_order_pymongo)]
        
        # 查询记录
        results = favorite_stocks_manager.find(
            filter_dict=filter_dict,
            sort=sort,
            limit=limit,
            skip=skip
        )
        
        # 统计总数
        total = favorite_stocks_manager.count(filter_dict)
        
        return FavoriteStockListResponse(
            success=True,
            data=results,
            total=total,
            message=f"查询成功，共{total}条记录"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询自选股列表失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"查询自选股列表失败: {str(e)}"
        )


@router.get("/{stock_code}", response_model=FavoriteStockResponse)
async def get_favorite_stock(
    stock_code: str,
    user_id: Optional[str] = Query("default", description="用户ID")
):
    """
    根据股票代码查询自选股详情
    
    - **stock_code**: 股票代码
    - **user_id**: 用户ID（默认"default"）
    """
    try:
        if not favorite_stocks_manager.connected:
            raise HTTPException(
                status_code=500,
                detail="MongoDB自选股服务不可用，请检查数据库配置"
            )
        
        result = favorite_stocks_manager.get_by_stock_code(stock_code, user_id)
        
        if result is None:
            raise HTTPException(
                status_code=404,
                detail=f"未找到股票{stock_code}的自选股记录"
            )
        
        return FavoriteStockResponse(
            success=True,
            data=result,
            message="查询成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询自选股详情失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"查询自选股详情失败: {str(e)}"
        )


@router.put("/{stock_code}", response_model=FavoriteStockResponse)
async def update_favorite_stock(
    stock_code: str,
    update_data: FavoriteStockUpdate,
    user_id: Optional[str] = Query("default", description="用户ID")
):
    """
    更新自选股记录
    
    - **stock_code**: 股票代码
    - **user_id**: 用户ID（默认"default"）
    - **update_data**: 要更新的数据
    """
    try:
        if not favorite_stocks_manager.connected:
            raise HTTPException(
                status_code=500,
                detail="MongoDB自选股服务不可用，请检查数据库配置"
            )
        
        # 构建查询条件
        filter_dict = {
            "stock_code": stock_code,
            "user_id": user_id
        }
        
        # 转换为字典，排除未设置的字段
        update_dict = update_data.model_dump(exclude_unset=True)
        
        # 确保数组字段的类型正确
        if 'tags' in update_dict and not isinstance(update_dict['tags'], list):
            update_dict['tags'] = [update_dict['tags']] if update_dict['tags'] else []
        if 'themes' in update_dict and not isinstance(update_dict['themes'], list):
            update_dict['themes'] = [update_dict['themes']] if update_dict['themes'] else []
        if 'sectors' in update_dict and not isinstance(update_dict['sectors'], list):
            update_dict['sectors'] = [update_dict['sectors']] if update_dict['sectors'] else []
        
        if not update_dict:
            raise HTTPException(
                status_code=400,
                detail="没有提供要更新的字段"
            )
        
        # 更新记录
        success = favorite_stocks_manager.update(filter_dict, update_dict)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"未找到股票{stock_code}的自选股记录"
            )
        
        # 查询更新后的记录
        result = favorite_stocks_manager.get_by_stock_code(stock_code, user_id)
        
        return FavoriteStockResponse(
            success=True,
            data=result,
            message="更新成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新自选股失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"更新自选股失败: {str(e)}"
        )


@router.delete("/{stock_code}", response_model=FavoriteStockResponse)
async def delete_favorite_stock(
    stock_code: str,
    user_id: Optional[str] = Query("default", description="用户ID")
):
    """
    删除自选股记录
    
    - **stock_code**: 股票代码
    - **user_id**: 用户ID（默认"default"）
    """
    try:
        if not favorite_stocks_manager.connected:
            raise HTTPException(
                status_code=500,
                detail="MongoDB自选股服务不可用，请检查数据库配置"
            )
        
        # 构建查询条件
        filter_dict = {
            "stock_code": stock_code,
            "user_id": user_id
        }
        
        # 先查询记录（用于返回）
        result = favorite_stocks_manager.get_by_stock_code(stock_code, user_id)
        
        if result is None:
            raise HTTPException(
                status_code=404,
                detail=f"未找到股票{stock_code}的自选股记录"
            )
        
        # 删除记录
        success = favorite_stocks_manager.delete(filter_dict)
        
        if not success:
            raise HTTPException(
                status_code=500,
                detail="删除失败"
            )
        
        return FavoriteStockResponse(
            success=True,
            data=result,
            message="删除成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除自选股失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"删除自选股失败: {str(e)}"
        )


@router.get("/statistics/summary", response_model=FavoriteStockStatisticsResponse)
async def get_favorite_stocks_statistics(
    user_id: Optional[str] = Query("default", description="用户ID")
):
    """
    获取自选股统计信息
    
    - **user_id**: 用户ID（默认"default"）
    """
    try:
        if not favorite_stocks_manager.connected:
            raise HTTPException(
                status_code=500,
                detail="MongoDB自选股服务不可用，请检查数据库配置"
            )
        
        statistics = favorite_stocks_manager.get_statistics(user_id)
        
        return FavoriteStockStatisticsResponse(
            success=True,
            data=statistics,
            message="统计成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取自选股统计失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"获取自选股统计失败: {str(e)}"
        )

