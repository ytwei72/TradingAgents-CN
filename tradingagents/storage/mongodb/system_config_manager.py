#!/usr/bin/env python3
"""
系统配置 MongoDB 管理器
管理 models、pricing、settings 三类系统配置
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

from tradingagents.utils.logging_manager import get_logger
logger = get_logger('storage')

try:
    from pymongo import MongoClient
    from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
    MONGODB_AVAILABLE = True
except ImportError:
    MONGODB_AVAILABLE = False
    MongoClient = None
    logger.warning("pymongo未安装，MongoDB功能不可用")


class SystemConfigManager:
    """系统配置 MongoDB 管理器"""
    
    def __init__(self, config_dir: str = "config"):
        """
        初始化系统配置管理器
        
        Args:
            config_dir: 配置文件目录（保留用于兼容性，不再用于读取JSON文件）
        """
        self.config_dir = Path(config_dir)
        
        # 集合名称
        self.collection_models = "dict_models"
        self.collection_pricing = "dict_pricing"
        self.collection_settings = "dict_settings"
        
        # MongoDB 集合对象
        self.models_collection = None
        self.pricing_collection = None
        self.settings_collection = None
        
        self._connected = False
        
        # 尝试连接 MongoDB
        self._connect()
    
    def _connect(self):
        """连接到 MongoDB"""
        if not MONGODB_AVAILABLE:
            logger.warning("⚠️ pymongo未安装，系统配置将使用JSON文件存储")
            self._connected = False
            return
        
        try:
            # 使用统一的连接管理
            from tradingagents.storage.manager import get_mongo_collection
            
            self.models_collection = get_mongo_collection(self.collection_models)
            self.pricing_collection = get_mongo_collection(self.collection_pricing)
            self.settings_collection = get_mongo_collection(self.collection_settings)
            
            if self.models_collection is None:
                logger.warning("⚠️ MongoDB连接失败，系统配置将使用JSON文件存储")
                self._connected = False
                return
            
            # 创建索引
            self._create_indexes()
            
            self._connected = True
            logger.info("✅ 系统配置管理器已连接MongoDB")
            
        except Exception as e:
            logger.warning(f"⚠️ MongoDB连接失败: {e}，系统配置将使用JSON文件存储")
            self._connected = False
    
    def _cleanup_duplicates(self, collection, key_fields: List[str], collection_name: str):
        """
        清理集合中的重复数据
        
        Args:
            collection: MongoDB 集合对象
            key_fields: 用于判断重复的字段列表
            collection_name: 集合名称（用于日志）
        """
        if collection is None:
            return
        
        try:
            # 查找所有重复的记录
            pipeline = [
                {
                    "$group": {
                        "_id": {field: f"${field}" for field in key_fields},
                        "count": {"$sum": 1},
                        "docs": {"$push": "$$ROOT"}
                    }
                },
                {
                    "$match": {
                        "count": {"$gt": 1}  # 只保留重复的记录
                    }
                }
            ]
            
            duplicates = list(collection.aggregate(pipeline))
            
            if duplicates:
                logger.warning(f"⚠️ [系统配置] 在 {collection_name} 中发现 {len(duplicates)} 组重复数据，开始清理...")
                
                deleted_count = 0
                for dup_group in duplicates:
                    docs = dup_group["docs"]
                    # 按 updated_at 降序排序，保留最新的记录
                    # 如果没有 updated_at，按 _id 排序（ObjectId 包含时间戳）
                    docs.sort(key=lambda x: (
                        x.get("updated_at", datetime.min) if isinstance(x.get("updated_at"), datetime) else datetime.min,
                        str(x.get("_id", ""))
                    ), reverse=True)
                    
                    # 保留第一条（最新的），删除其余的
                    for doc in docs[1:]:
                        collection.delete_one({"_id": doc["_id"]})
                        deleted_count += 1
                
                logger.info(f"✅ [系统配置] {collection_name} 清理完成，删除了 {deleted_count} 条重复记录")
            else:
                logger.debug(f"✅ [系统配置] {collection_name} 无重复数据")
                
        except Exception as e:
            logger.warning(f"⚠️ [系统配置] 清理 {collection_name} 重复数据时出错: {e}")
    
    def _create_indexes(self):
        """创建数据库索引"""
        try:
            # models 集合索引：按 provider 和 model_name
            if self.models_collection is not None:
                # 先清理重复数据
                self._cleanup_duplicates(
                    self.models_collection,
                    ["provider", "model_name"],
                    "dict_models"
                )
                
                try:
                    self.models_collection.create_index([("provider", 1), ("model_name", 1)], unique=True)
                    logger.debug("✅ [系统配置] models 索引创建成功")
                except Exception as e:
                    error_str = str(e).lower()
                    error_code = getattr(e, 'code', None)
                    if "already exists" in error_str or "indexoptionsconflict" in error_str or error_code == 85:
                        logger.debug("✅ [系统配置] models 索引已存在")
                    elif "duplicate key" in error_str or error_code == 11000:
                        # 如果清理后仍有重复，记录详细错误
                        logger.error(f"❌ [系统配置] models 索引创建失败，仍有重复数据: {e}")
                        logger.error("❌ [系统配置] 请手动清理 dict_models 集合中的重复数据后重试")
                    else:
                        logger.warning(f"⚠️ [系统配置] 创建 models 索引时出错: {e}")
            
            # pricing 集合索引：按 provider 和 model_name
            if self.pricing_collection is not None:
                # 先清理重复数据
                self._cleanup_duplicates(
                    self.pricing_collection,
                    ["provider", "model_name"],
                    "dict_pricing"
                )
                
                try:
                    self.pricing_collection.create_index([("provider", 1), ("model_name", 1)], unique=True)
                    logger.debug("✅ [系统配置] pricing 索引创建成功")
                except Exception as e:
                    error_str = str(e).lower()
                    error_code = getattr(e, 'code', None)
                    if "already exists" in error_str or "indexoptionsconflict" in error_str or error_code == 85:
                        logger.debug("✅ [系统配置] pricing 索引已存在")
                    elif "duplicate key" in error_str or error_code == 11000:
                        # 如果清理后仍有重复，记录详细错误
                        logger.error(f"❌ [系统配置] pricing 索引创建失败，仍有重复数据: {e}")
                        logger.error("❌ [系统配置] 请手动清理 dict_pricing 集合中的重复数据后重试")
                    else:
                        logger.warning(f"⚠️ [系统配置] 创建 pricing 索引时出错: {e}")
            
            # settings 集合只有一个文档，使用 _id 索引即可
            
        except Exception as e:
            logger.warning(f"⚠️ 创建索引失败: {e}")
    
    def is_connected(self) -> bool:
        """检查是否已连接到MongoDB"""
        return self._connected
    
    def _get_default_configs(self) -> Dict[str, Any]:
        """
        获取所有默认配置
        
        Returns:
            包含 models, pricing, settings 的字典
        """
        return {
            'models': self._get_default_models(),
            'pricing': self._get_default_pricing(),
            'settings': self._get_default_settings()
        }
    
    def _get_default_models(self) -> List[Dict]:
        """获取默认模型配置"""
        from tradingagents.config.config_manager import ModelConfig
        
        default_models = [
            ModelConfig(
                provider="dashscope",
                model_name="qwen-turbo",
                api_key="",
                max_tokens=4000,
                temperature=0.7
            ),
            ModelConfig(
                provider="dashscope",
                model_name="qwen-plus-latest",
                api_key="",
                max_tokens=8000,
                temperature=0.7
            ),
            ModelConfig(
                provider="openai",
                model_name="gpt-3.5-turbo",
                api_key="",
                max_tokens=4000,
                temperature=0.7,
                enabled=False
            ),
            ModelConfig(
                provider="openai",
                model_name="gpt-4",
                api_key="",
                max_tokens=8000,
                temperature=0.7,
                enabled=False
            ),
            ModelConfig(
                provider="google",
                model_name="gemini-2.5-pro",
                api_key="",
                max_tokens=4000,
                temperature=0.7,
                enabled=False
            ),
            ModelConfig(
                provider="deepseek",
                model_name="deepseek-chat",
                api_key="",
                max_tokens=8000,
                temperature=0.7,
                enabled=False
            )
        ]
        return [asdict(model) for model in default_models]
    
    def _get_default_pricing(self) -> List[Dict]:
        """获取默认定价配置"""
        from tradingagents.config.config_manager import PricingConfig
        
        default_pricing = [
            PricingConfig("dashscope", "qwen-turbo", 0.002, 0.006, "CNY"),
            PricingConfig("dashscope", "qwen-plus-latest", 0.004, 0.012, "CNY"),
            PricingConfig("dashscope", "qwen-max", 0.02, 0.06, "CNY"),
            PricingConfig("deepseek", "deepseek-chat", 0.0014, 0.0028, "CNY"),
            PricingConfig("deepseek", "deepseek-coder", 0.0014, 0.0028, "CNY"),
            PricingConfig("openai", "gpt-3.5-turbo", 0.0015, 0.002, "USD"),
            PricingConfig("openai", "gpt-4", 0.03, 0.06, "USD"),
            PricingConfig("openai", "gpt-4-turbo", 0.01, 0.03, "USD"),
            PricingConfig("google", "gemini-2.5-pro", 0.00025, 0.0005, "USD"),
            PricingConfig("google", "gemini-2.5-flash", 0.00025, 0.0005, "USD"),
            PricingConfig("google", "gemini-2.0-flash", 0.00025, 0.0005, "USD"),
            PricingConfig("google", "gemini-1.5-pro", 0.00025, 0.0005, "USD"),
            PricingConfig("google", "gemini-1.5-flash", 0.00025, 0.0005, "USD"),
            PricingConfig("google", "gemini-2.5-flash-lite-preview-06-17", 0.00025, 0.0005, "USD"),
            PricingConfig("google", "gemini-pro", 0.00025, 0.0005, "USD"),
            PricingConfig("google", "gemini-pro-vision", 0.00025, 0.0005, "USD"),
        ]
        return [asdict(price) for price in default_pricing]
    
    def _get_default_settings(self) -> Dict:
        """获取默认设置配置"""
        import os
        default_data_dir = os.path.join(os.path.expanduser("~"), "Documents", "TradingAgents", "data")
        default_results_dir = os.path.join(os.path.expanduser("~"), "Documents", "TradingAgents", "results")
        
        # 规范化路径：统一使用正斜杠（跨平台兼容）
        normalized_data_dir = default_data_dir.replace("\\", "/")
        normalized_results_dir = default_results_dir.replace("\\", "/")
        
        return {
            "default_provider": "dashscope",
            "default_model": "qwen-turbo",
            "enable_cost_tracking": True,
            "cost_alert_threshold": 100.0,
            "currency_preference": "CNY",
            "auto_save_usage": True,
            "max_usage_records": 10000,
            "data_dir": normalized_data_dir,
            "cache_dir": f"{normalized_data_dir}/cache",
            "results_dir": normalized_results_dir,
            "auto_create_dirs": True,
            "openai_enabled": False,
        }
    
    def _ensure_config_exists(self, config_type: str):
        """
        确保配置存在于数据库中，如果不存在则使用代码中的默认配置初始化
        
        Args:
            config_type: 配置类型，'models', 'pricing', 或 'settings'
        
        Raises:
            RuntimeError: 如果数据库未连接或操作失败
        """
        if not self._connected:
            raise RuntimeError(f"MongoDB未连接，无法确保配置存在: {config_type}")
        
        try:
            if config_type == 'models':
                if self.models_collection.count_documents({}) == 0:
                    # 使用代码中的默认配置初始化
                    default_config = self._get_default_models()
                    self.save_models(default_config)
                    logger.info("✅ 已从代码默认配置初始化 models 配置到数据库")
            
            elif config_type == 'pricing':
                if self.pricing_collection.count_documents({}) == 0:
                    # 使用代码中的默认配置初始化
                    default_config = self._get_default_pricing()
                    self.save_pricing(default_config)
                    logger.info("✅ 已从代码默认配置初始化 pricing 配置到数据库")
            
            elif config_type == 'settings':
                if self.settings_collection.count_documents({}) == 0:
                    # 使用代码中的默认配置初始化
                    default_config = self._get_default_settings()
                    self.save_settings(default_config)
                    logger.info("✅ 已从代码默认配置初始化 settings 配置到数据库")
        
        except Exception as e:
            logger.error(f"❌ 确保配置存在失败 ({config_type}): {e}")
            raise RuntimeError(f"确保配置存在失败 ({config_type}): {e}") from e
    
    def load_models(self) -> List[Dict]:
        """
        加载模型配置
        
        Raises:
            RuntimeError: 如果数据库未连接或操作失败
        """
        if not self._connected:
            raise RuntimeError("MongoDB未连接，无法加载模型配置")
        
        # 确保配置存在
        self._ensure_config_exists('models')
        
        try:
            models = list(self.models_collection.find({}, {"_id": 0, "updated_at": 0}))
            if not models:
                # _ensure_config_exists 已经确保配置存在，如果查询结果为空，说明出现异常
                raise RuntimeError("数据库中的模型配置为空，但 _ensure_config_exists 已执行，可能存在数据不一致问题")
            logger.debug(f"✅ 从数据库加载了 {len(models)} 个模型配置")
            return models
        except Exception as e:
            logger.error(f"❌ 从数据库加载模型配置失败: {e}")
            raise RuntimeError(f"从数据库加载模型配置失败: {e}") from e
    
    def save_models(self, models: List[Dict]):
        """
        保存模型配置
        
        Raises:
            RuntimeError: 如果数据库未连接或操作失败
        """
        if not self._connected:
            raise RuntimeError("MongoDB未连接，无法保存模型配置到数据库")
        
        try:
            # 清空现有配置
            self.models_collection.delete_many({})
            
            # 插入新配置
            if models:
                # 为每个模型添加时间戳
                for model in models:
                    model['updated_at'] = datetime.utcnow()
                
                self.models_collection.insert_many(models)
                logger.info(f"✅ 已保存 {len(models)} 个模型配置到数据库")
        except Exception as e:
            logger.error(f"❌ 保存模型配置到数据库失败: {e}")
            raise RuntimeError(f"保存模型配置到数据库失败: {e}") from e
    
    def load_pricing(self) -> List[Dict]:
        """
        加载定价配置
        
        Raises:
            RuntimeError: 如果数据库未连接或操作失败
        """
        if not self._connected:
            raise RuntimeError("MongoDB未连接，无法加载定价配置")
        
        # 确保配置存在
        self._ensure_config_exists('pricing')
        
        try:
            pricing = list(self.pricing_collection.find({}, {"_id": 0, "updated_at": 0}))
            if not pricing:
                # _ensure_config_exists 已经确保配置存在，如果查询结果为空，说明出现异常
                raise RuntimeError("数据库中的定价配置为空，但 _ensure_config_exists 已执行，可能存在数据不一致问题")
            logger.debug(f"✅ 从数据库加载了 {len(pricing)} 个定价配置")
            return pricing
        except Exception as e:
            logger.error(f"❌ 从数据库加载定价配置失败: {e}")
            raise RuntimeError(f"从数据库加载定价配置失败: {e}") from e
    
    def save_pricing(self, pricing: List[Dict]):
        """
        保存定价配置
        
        Raises:
            RuntimeError: 如果数据库未连接或操作失败
        """
        if not self._connected:
            raise RuntimeError("MongoDB未连接，无法保存定价配置到数据库")
        
        try:
            self.pricing_collection.delete_many({})
            
            if pricing:
                for price in pricing:
                    price['updated_at'] = datetime.utcnow()
                
                self.pricing_collection.insert_many(pricing)
                logger.info(f"✅ 已保存 {len(pricing)} 个定价配置到数据库")
        except Exception as e:
            logger.error(f"❌ 保存定价配置到数据库失败: {e}")
            raise RuntimeError(f"保存定价配置到数据库失败: {e}") from e
    
    def load_settings(self) -> Dict:
        """
        加载设置配置
        
        Raises:
            RuntimeError: 如果数据库未连接或操作失败
        """
        if not self._connected:
            raise RuntimeError("MongoDB未连接，无法加载设置配置")
        
        # 确保配置存在
        self._ensure_config_exists('settings')
        
        try:
            # settings 集合只存储一个文档
            setting = self.settings_collection.find_one({}, {"_id": 0, "updated_at": 0})
            if not setting:
                # _ensure_config_exists 已经确保配置存在，如果查询结果为空，说明出现异常
                raise RuntimeError("数据库中的设置配置为空，但 _ensure_config_exists 已执行，可能存在数据不一致问题")
            logger.debug("✅ 从数据库加载了 settings 配置")
            return setting
        except Exception as e:
            logger.error(f"❌ 从数据库加载设置配置失败: {e}")
            raise RuntimeError(f"从数据库加载设置配置失败: {e}") from e
    
    def save_settings(self, settings: Dict):
        """
        保存设置配置
        
        Raises:
            RuntimeError: 如果数据库未连接或操作失败
        """
        if not self._connected:
            raise RuntimeError("MongoDB未连接，无法保存设置配置到数据库")
        
        try:
            # settings 集合只存储一个文档，使用 replace_one 替换
            settings['updated_at'] = datetime.utcnow()
            
            self.settings_collection.replace_one(
                {},  # 空查询匹配所有文档
                settings,
                upsert=True
            )
            logger.info("✅ 已保存 settings 配置到数据库")
        except Exception as e:
            logger.error(f"❌ 保存设置配置到数据库失败: {e}")
            raise RuntimeError(f"保存设置配置到数据库失败: {e}") from e
    
    def load_backtest_config(self) -> Dict:
        """
        加载回测配置
        
        Returns:
            Dict: 回测配置字典，包含以下键：
                - backtest_start_date: str
                - backtest_end_date: str
                - horizon_days: int
                - extend_days_before: int
                - extend_days_after: int
                - weight_mode: str
                - date_mode: str
        
        Raises:
            RuntimeError: 如果数据库未连接或操作失败
        """
        if not self._connected:
            raise RuntimeError("MongoDB未连接，无法加载回测配置")
        
        # 确保配置存在
        self._ensure_config_exists('settings')
        
        try:
            # settings 集合只存储一个文档
            setting = self.settings_collection.find_one({}, {"_id": 0, "updated_at": 0})
            if not setting:
                raise RuntimeError("数据库中的设置配置为空")
            
            # 获取backtest_config字段，如果不存在则返回默认值
            backtest_config = setting.get('backtest_config', {})
            
            # 如果backtest_config为空，返回默认配置
            if not backtest_config:
                from datetime import date, timedelta
                default_config = {
                    "backtest_start_date": (date.today() - timedelta(days=365)).strftime('%Y-%m-%d'),
                    "backtest_end_date": date.today().strftime('%Y-%m-%d'),
                    "horizon_days": 90,
                    "extend_days_before": 30,
                    "extend_days_after": 180,
                    "weight_mode": "equal",
                    "date_mode": "calendar_day"
                }
                logger.info("✅ 回测配置不存在，返回默认配置")
                return default_config
            
            logger.debug("✅ 从数据库加载了回测配置")
            return backtest_config
        except Exception as e:
            logger.error(f"❌ 从数据库加载回测配置失败: {e}")
            raise RuntimeError(f"从数据库加载回测配置失败: {e}") from e
    
    def save_backtest_config(self, backtest_config: Dict):
        """
        保存回测配置
        
        Args:
            backtest_config: 回测配置字典，包含以下键：
                - backtest_start_date: str
                - backtest_end_date: str
                - horizon_days: int
                - extend_days_before: int
                - extend_days_after: int
                - weight_mode: str
                - date_mode: str
        
        Raises:
            RuntimeError: 如果数据库未连接或操作失败
        """
        if not self._connected:
            raise RuntimeError("MongoDB未连接，无法保存回测配置到数据库")
        
        try:
            # 确保settings文档存在
            self._ensure_config_exists('settings')
            
            # 获取当前settings
            current_settings = self.settings_collection.find_one({}, {"_id": 0, "updated_at": 0})
            if not current_settings:
                # 如果不存在，创建新的settings文档
                current_settings = self._get_default_settings()
            
            # 更新backtest_config字段
            current_settings['backtest_config'] = backtest_config
            current_settings['updated_at'] = datetime.utcnow()
            
            # 保存到数据库
            self.settings_collection.replace_one(
                {},  # 空查询匹配所有文档
                current_settings,
                upsert=True
            )
            logger.info("✅ 已保存回测配置到数据库")
        except Exception as e:
            logger.error(f"❌ 保存回测配置到数据库失败: {e}")
            raise RuntimeError(f"保存回测配置到数据库失败: {e}") from e

