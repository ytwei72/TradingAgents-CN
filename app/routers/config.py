from typing import Optional, Dict, Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, ConfigDict

from tradingagents.config.config_manager import config_manager
from tradingagents.utils.logging_manager import get_logger


logger = get_logger("api_config")
router = APIRouter()


class MongoConfig(BaseModel):
    """Mongo 配置"""
    mongo_host: Optional[str] = Field(None, description="MongoDB 主机")
    mongo_port: Optional[int] = Field(None, description="MongoDB 端口")
    mongo_username: Optional[str] = Field(None, description="MongoDB 用户名")
    mongo_password: Optional[str] = Field(None, description="MongoDB 密码")
    mongo_database: Optional[str] = Field(None, description="MongoDB 数据库")
    mongo_auth_source: Optional[str] = Field(None, description="认证数据库")
    mongo_max_connections: Optional[int] = Field(None, description="最大连接数")
    mongo_min_connections: Optional[int] = Field(None, description="最小连接数")
    mongo_connect_timeout_ms: Optional[int] = Field(None, description="连接超时(毫秒)")
    mongo_socket_timeout_ms: Optional[int] = Field(None, description="Socket超时(毫秒)")
    mongo_server_selection_timeout_ms: Optional[int] = Field(None, description="Server选择超时(毫秒)")
    mongo_uri: Optional[str] = Field(None, description="连接URI")
    mongo_db: Optional[str] = Field(None, description="数据库名称")

    model_config = ConfigDict(extra="allow")


class DBConfig(BaseModel):
    """数据库配置"""
    mongo: Optional[MongoConfig] = None
    model_config = ConfigDict(extra="allow")


class SystemConfig(BaseModel):
    """系统配置（与 analysis_config 覆盖项一致）"""
    llm_provider: Optional[str] = Field(None, description="LLM 提供商")
    deep_think_llm: Optional[str] = Field(None, description="深度思考模型")
    quick_think_llm: Optional[str] = Field(None, description="快速思考模型")
    research_depth_default: Optional[int] = Field(None, ge=1, le=5, description="默认研究深度")
    market_type_default: Optional[str] = Field(None, description="默认市场类型")
    memory_enabled: Optional[bool] = Field(None, description="是否启用记忆")
    online_tools: Optional[bool] = Field(None, description="是否启用在线工具")
    online_news: Optional[bool] = Field(None, description="是否启用在线新闻")
    realtime_data: Optional[bool] = Field(None, description="是否启用实时数据")
    max_recur_limit: Optional[int] = Field(None, ge=1, description="最大递归限制")
    backend_url: Optional[str] = Field(None, description="LLM 后端地址")
    custom_openai_base_url: Optional[str] = Field(None, description="自定义 OpenAI Base URL")
    data_dir: Optional[str] = Field(None, description="数据目录")
    results_dir: Optional[str] = Field(None, description="结果目录")
    data_cache_dir: Optional[str] = Field(None, description="数据缓存目录")
    db: Optional[DBConfig] = Field(None, description="数据库配置")

    model_config = ConfigDict(extra="allow")


class SystemConfigResponse(BaseModel):
    success: bool
    data: Dict[str, Any]
    message: str


class UpdateSystemConfigRequest(SystemConfig):
    """更新系统配置请求"""
    pass


def _deep_merge(base: Dict[str, Any], overrides: Dict[str, Any]) -> Dict[str, Any]:
    """递归合并配置，嵌套字典按键覆盖"""
    merged = base.copy() if isinstance(base, dict) else {}
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


@router.get("/system", response_model=SystemConfigResponse)
async def get_system_config():
    """获取系统配置（持久化覆盖项）"""
    try:
        config = config_manager.load_system_config()
        return SystemConfigResponse(success=True, data=config, message="系统配置获取成功")
    except Exception as exc:
        logger.error(f"获取系统配置失败: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取系统配置失败: {exc}")


@router.put("/system", response_model=SystemConfigResponse)
async def update_system_config(request: UpdateSystemConfigRequest):
    """更新系统配置并持久化"""
    try:
        incoming = request.model_dump(exclude_none=True)
        current = config_manager.load_system_config()
        merged = _deep_merge(current, incoming)
        config_manager.save_system_config(merged)
        logger.info("✅ 系统配置已更新")
        return SystemConfigResponse(success=True, data=merged, message="系统配置更新成功")
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"更新系统配置失败: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"更新系统配置失败: {exc}")

