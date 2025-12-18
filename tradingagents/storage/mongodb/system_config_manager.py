#!/usr/bin/env python3
"""
系统配置 MongoDB 管理器
管理 models、pricing、settings 三类系统配置
"""

import json
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
            config_dir: 默认配置文件目录，用于读取默认配置
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
    
    def _create_indexes(self):
        """创建数据库索引"""
        try:
            # models 集合索引：按 provider 和 model_name
            if self.models_collection:
                self.models_collection.create_index([("provider", 1), ("model_name", 1)], unique=True)
            
            # pricing 集合索引：按 provider 和 model_name
            if self.pricing_collection:
                self.pricing_collection.create_index([("provider", 1), ("model_name", 1)], unique=True)
            
            # settings 集合只有一个文档，使用 _id 索引即可
            
        except Exception as e:
            logger.warning(f"⚠️ 创建索引失败: {e}")
    
    def is_connected(self) -> bool:
        """检查是否已连接到MongoDB"""
        return self._connected
    
    def _load_default_from_file(self, config_type: str) -> Any:
        """
        从默认配置文件加载配置
        
        Args:
            config_type: 配置类型，'models', 'pricing', 或 'settings'
        
        Returns:
            配置数据
        """
        file_map = {
            'models': self.config_dir / 'models.json',
            'pricing': self.config_dir / 'pricing.json',
            'settings': self.config_dir / 'settings.json'
        }
        
        config_file = file_map.get(config_type)
        if not config_file or not config_file.exists():
            # 如果文件不存在，返回空数据
            if config_type == 'settings':
                return {}
            return []
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                logger.info(f"📄 从文件加载默认配置: {config_type}")
                return data
        except Exception as e:
            logger.error(f"❌ 加载默认配置文件失败 ({config_type}): {e}")
            if config_type == 'settings':
                return {}
            return []
    
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
        
        return {
            "default_provider": "dashscope",
            "default_model": "qwen-turbo",
            "enable_cost_tracking": True,
            "cost_alert_threshold": 100.0,
            "currency_preference": "CNY",
            "auto_save_usage": True,
            "max_usage_records": 10000,
            "data_dir": default_data_dir,
            "cache_dir": os.path.join(default_data_dir, "cache"),
            "results_dir": os.path.join(os.path.expanduser("~"), "Documents", "TradingAgents", "results"),
            "auto_create_dirs": True,
            "openai_enabled": False,
        }
    
    def _ensure_config_exists(self, config_type: str):
        """
        确保配置存在于数据库中，如果不存在则从默认配置加载
        
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
                    # 从默认配置文件读取（仅用于初始化）
                    default_config = self._load_default_from_file(config_type)
                    if not default_config:
                        default_config = self._get_default_models()
                    self.save_models(default_config)
                    logger.info("✅ 已从默认配置初始化 models 配置到数据库")
            
            elif config_type == 'pricing':
                if self.pricing_collection.count_documents({}) == 0:
                    default_config = self._load_default_from_file(config_type)
                    if not default_config:
                        default_config = self._get_default_pricing()
                    self.save_pricing(default_config)
                    logger.info("✅ 已从默认配置初始化 pricing 配置到数据库")
            
            elif config_type == 'settings':
                if self.settings_collection.count_documents({}) == 0:
                    default_config = self._load_default_from_file(config_type)
                    if not default_config:
                        default_config = self._get_default_settings()
                    self.save_settings(default_config)
                    logger.info("✅ 已从默认配置初始化 settings 配置到数据库")
        
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

