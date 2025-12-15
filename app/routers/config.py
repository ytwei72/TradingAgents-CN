from typing import Optional, Dict, Any, List

from fastapi import APIRouter, HTTPException, Query
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


class UpdateSystemConfigRequest(BaseModel):
    """
    更新系统配置请求
    可以包含 'models', 'pricing', 'settings' 中的任意几个键
    """
    models: Optional[List[Dict[str, Any]]] = Field(None, description="模型配置列表")
    pricing: Optional[List[Dict[str, Any]]] = Field(None, description="定价配置列表")
    settings: Optional[Dict[str, Any]] = Field(None, description="设置字典")
    
    model_config = ConfigDict(extra="forbid")  # 禁止额外字段


def _deep_merge(base: Dict[str, Any], overrides: Dict[str, Any]) -> Dict[str, Any]:
    """递归合并配置，嵌套字典按键覆盖"""
    merged = base.copy() if isinstance(base, dict) else {}
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _normalize_config_types(config_types: Optional[Any]) -> List[str]:
    """将传入的 config_types 规范化为去重有序列表"""
    valid_types = ['models', 'pricing', 'settings']

    def _split_str(val: str) -> List[str]:
        return [t.strip() for t in val.split(',') if t.strip()]

    parsed: List[str] = []
    if config_types is None:
        parsed = ['settings']
    elif isinstance(config_types, str):
        parsed = _split_str(config_types)
    elif isinstance(config_types, list):
        # 兼容误传多个同名 query 参数的情况
        for item in config_types:
            parsed.extend(_split_str(str(item)))
    else:
        parsed = ['settings']

    # 去重保持顺序
    seen = set()
    normalized = []
    for t in parsed or ['settings']:
        if t not in seen:
            seen.add(t)
            normalized.append(t)

    # 校验
    invalid = [t for t in normalized if t not in valid_types]
    if invalid:
        raise HTTPException(
            status_code=400,
            detail=f"无效的配置类型: {invalid}。有效类型: {valid_types}"
        )
    return normalized or ['settings']


@router.get("/system", response_model=SystemConfigResponse)
async def get_system_config(
    config_types: Optional[str] = Query(
        None,
        description="逗号分隔的配置类型，可选值：'models', 'pricing', 'settings'。不传默认只返回 'settings'"
    )
):
    """
    获取系统配置（持久化覆盖项）
    
    Args:
        config_types: 要获取的配置类型列表，可选值：'models', 'pricing', 'settings'
                     如果不指定，默认只返回 'settings'
    """
    try:
        # 规范化配置类型，支持逗号分隔的单参数或重复 query 参数
        config_type_list = _normalize_config_types(config_types)
        
        # 获取指定类型的配置
        config = config_manager.fetch_system_config(config_types=config_type_list)

        # 始终返回包含键名的对象（即使只请求单一类型）
        return SystemConfigResponse(success=True, data=config, message="系统配置获取成功")
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"获取系统配置失败: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取系统配置失败: {exc}")


@router.put("/system", response_model=SystemConfigResponse)
async def update_system_config(request: UpdateSystemConfigRequest):
    """
    更新系统配置并持久化
    
    请求体应该是一个 JSON 对象，可以包含以下键的任意几个：
    - 'models': List[Dict] - 模型配置列表
    - 'pricing': List[Dict] - 定价配置列表
    - 'settings': Dict - 设置字典
    
    根据请求中包含的键来更新对应的配置。
    对于 'settings'，会进行深度合并；对于其他配置，会完全替换。
    """
    try:
        # 获取请求数据，排除 None 值
        incoming = request.model_dump(exclude_none=True)
        
        # 验证至少包含一个配置类型
        valid_keys = ['models', 'pricing', 'settings']
        provided_keys = [key for key in incoming.keys() if key in valid_keys]
        
        if not provided_keys:
            raise HTTPException(
                status_code=400,
                detail=f"请求中必须包含至少一个配置类型。有效类型: {valid_keys}"
            )

        # 保存配置（save_system_config 会根据包含的键来更新对应的配置）
        config_manager.save_system_config(incoming)
        
        logger.info(f"✅ 系统配置已更新: {', '.join(provided_keys)}")
        # 不返回更新后的配置，保持响应精简
        return SystemConfigResponse(success=True, data={}, message="系统配置更新成功")
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"更新系统配置失败: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"更新系统配置失败: {exc}")

