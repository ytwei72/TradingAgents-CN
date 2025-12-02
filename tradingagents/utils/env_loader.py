#!/usr/bin/env python3
"""
模块化环境变量加载工具
支持全局和模块级别的 .env 文件加载
"""

import os
from pathlib import Path
from typing import Optional, Dict, List
from dotenv import load_dotenv

from tradingagents.utils.logging_manager import get_logger
logger = get_logger('agents')


class ModularEnvLoader:
    """
    模块化环境变量加载器
    
    功能:
    1. 支持全局 .env 文件(项目根目录)
    2. 支持模块级 .env 文件(模块目录下)
    3. 配置优先级: 模块级 > 全局级 > 系统环境变量
    4. 支持环境变量缓存,避免重复加载
    """
    
    # 类级别的加载记录,避免重复加载
    _loaded_files: Dict[str, bool] = {}
    _env_cache: Dict[str, str] = {}
    
    def __init__(self, module_name: Optional[str] = None, module_path: Optional[Path] = None, load_global: bool = True):
        """
        初始化环境变量加载器
        
        Args:
            module_name: 模块名称,用于查找模块级 .env 文件
            module_path: 模块路径,如果提供则直接使用该路径查找 .env
            load_global: 是否加载全局 .env 文件
        """
        self.module_name = module_name
        self.module_path = module_path
        self.load_global = load_global
        self.project_root = self._get_project_root()
        
    @staticmethod
    def _get_project_root() -> Path:
        """获取项目根目录"""
        # 从当前文件位置推断项目根目录
        current_file = Path(__file__)  # tradingagents/utils/env_loader.py
        project_root = current_file.parent.parent.parent  # 向上三级到项目根目录
        return project_root
    
    def load_env(self, override: bool = True, verbose: bool = False) -> Dict[str, str]:
        """
        加载环境变量
        
        加载顺序:
        1. 先加载全局 .env (项目根目录)
        2. 再加载模块级 .env (如果存在)
        3. 模块级配置会覆盖全局配置
        
        Args:
            override: 是否覆盖已存在的环境变量
            verbose: 是否输出详细日志
            
        Returns:
            加载的环境变量字典
        """
        loaded_vars = {}
        
        # 1. 加载全局 .env
        if self.load_global:
            global_env_file = self.project_root / ".env"
            if global_env_file.exists():
                if verbose:
                    logger.info(f"📂 加载全局环境变量: {global_env_file}")
                
                # 只在未加载过时才加载
                if str(global_env_file) not in self._loaded_files:
                    load_dotenv(global_env_file, override=override)
                    self._loaded_files[str(global_env_file)] = True
                    if verbose:
                        logger.info(f"✅ 全局环境变量加载完成")
            else:
                if verbose:
                    logger.warning(f"⚠️ 全局 .env 文件不存在: {global_env_file}")
        
        # 2. 加载模块级 .env
        module_env_file = self._get_module_env_file()
        if module_env_file and module_env_file.exists():
            if verbose:
                logger.info(f"📂 加载模块级环境变量: {module_env_file}")
            
            # 只在未加载过时才加载
            if str(module_env_file) not in self._loaded_files:
                # 读取模块级环境变量
                module_vars = self._load_env_file(module_env_file)
                
                # 应用到环境变量(会覆盖全局配置)
                for key, value in module_vars.items():
                    if override or key not in os.environ:
                        os.environ[key] = value
                        loaded_vars[key] = value
                
                self._loaded_files[str(module_env_file)] = True
                
                if verbose:
                    logger.info(f"✅ 模块级环境变量加载完成,共 {len(module_vars)} 个配置项")
                    logger.debug(f"   加载的配置项: {list(module_vars.keys())}")
        
        return loaded_vars
    
    def _get_module_env_file(self) -> Optional[Path]:
        """获取模块级 .env 文件路径"""
        if self.module_path:
            # 如果提供了模块路径,直接使用
            return self.module_path / ".env"
        
        if self.module_name:
            # 根据模块名称查找模块目录
            # 支持的查找路径:
            # 1. tradingagents/{module_name}/.env
            # 2. tradingagents/dataflows/{module_name}/.env
            # 3. tradingagents/agents/{module_name}/.env
            
            search_paths = [
                self.project_root / "tradingagents" / self.module_name,
                self.project_root / "tradingagents" / "dataflows" / self.module_name,
                self.project_root / "tradingagents" / "agents" / self.module_name,
            ]
            
            for path in search_paths:
                env_file = path / ".env"
                if env_file.exists():
                    return env_file
        
        return None
    
    @staticmethod
    def _load_env_file(env_file: Path) -> Dict[str, str]:
        """
        读取 .env 文件内容
        
        Args:
            env_file: .env 文件路径
            
        Returns:
            环境变量字典
        """
        env_vars = {}
        
        try:
            with open(env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    
                    # 跳过空行和注释
                    if not line or line.startswith('#'):
                        continue
                    
                    # 解析 KEY=VALUE 格式
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        
                        # 移除引号
                        if value.startswith('"') and value.endswith('"'):
                            value = value[1:-1]
                        elif value.startswith("'") and value.endswith("'"):
                            value = value[1:-1]
                        
                        env_vars[key] = value
        
        except Exception as e:
            logger.error(f"❌ 读取 .env 文件失败: {env_file}, 错误: {e}")
        
        return env_vars
    
    def get_env(self, key: str, default: Optional[str] = None, required: bool = False) -> Optional[str]:
        """
        获取环境变量值
        
        Args:
            key: 环境变量名
            default: 默认值
            required: 是否必需(如果必需但未找到,会抛出异常)
            
        Returns:
            环境变量值
            
        Raises:
            ValueError: 当 required=True 且环境变量不存在时
        """
        value = os.getenv(key, default)
        
        if required and value is None:
            raise ValueError(f"必需的环境变量未设置: {key}")
        
        return value
    
    def get_env_bool(self, key: str, default: bool = False) -> bool:
        """
        获取布尔类型的环境变量
        
        支持的值:
        - True: true, True, TRUE, 1, yes, Yes, YES, on, On, ON
        - False: false, False, FALSE, 0, no, No, NO, off, Off, OFF
        
        Args:
            key: 环境变量名
            default: 默认值
            
        Returns:
            布尔值
        """
        value = os.getenv(key)
        
        if value is None:
            return default
        
        return value.lower() in ['true', '1', 'yes', 'on']
    
    def get_env_int(self, key: str, default: int = 0) -> int:
        """
        获取整数类型的环境变量
        
        Args:
            key: 环境变量名
            default: 默认值
            
        Returns:
            整数值
        """
        value = os.getenv(key)
        
        if value is None:
            return default
        
        try:
            return int(value)
        except ValueError:
            logger.warning(f"⚠️ 环境变量 {key}={value} 无法转换为整数,使用默认值 {default}")
            return default
    
    def get_env_float(self, key: str, default: float = 0.0) -> float:
        """
        获取浮点数类型的环境变量
        
        Args:
            key: 环境变量名
            default: 默认值
            
        Returns:
            浮点数值
        """
        value = os.getenv(key)
        
        if value is None:
            return default
        
        try:
            return float(value)
        except ValueError:
            logger.warning(f"⚠️ 环境变量 {key}={value} 无法转换为浮点数,使用默认值 {default}")
            return default
    
    def get_env_list(self, key: str, separator: str = ',', default: Optional[List[str]] = None) -> List[str]:
        """
        获取列表类型的环境变量
        
        Args:
            key: 环境变量名
            separator: 分隔符
            default: 默认值
            
        Returns:
            字符串列表
        """
        value = os.getenv(key)
        
        if value is None:
            return default or []
        
        return [item.strip() for item in value.split(separator) if item.strip()]
    
    @classmethod
    def reset_cache(cls):
        """重置加载缓存(主要用于测试)"""
        cls._loaded_files.clear()
        cls._env_cache.clear()


# 便捷函数

def load_module_env(module_name: str, override: bool = True, verbose: bool = False) -> Dict[str, str]:
    """
    加载指定模块的环境变量
    
    Args:
        module_name: 模块名称
        override: 是否覆盖已存在的环境变量
        verbose: 是否输出详细日志
        
    Returns:
        加载的环境变量字典
    """
    loader = ModularEnvLoader(module_name=module_name)
    return loader.load_env(override=override, verbose=verbose)


def load_module_env_from_path(module_path: Path, override: bool = True, verbose: bool = False) -> Dict[str, str]:
    """
    从指定路径加载模块环境变量
    
    Args:
        module_path: 模块路径
        override: 是否覆盖已存在的环境变量
        verbose: 是否输出详细日志
        
    Returns:
        加载的环境变量字典
    """
    loader = ModularEnvLoader(module_path=module_path)
    return loader.load_env(override=override, verbose=verbose)


def get_module_env_loader(module_name: Optional[str] = None, module_path: Optional[Path] = None) -> ModularEnvLoader:
    """
    获取模块环境变量加载器实例
    
    Args:
        module_name: 模块名称
        module_path: 模块路径
        
    Returns:
        ModularEnvLoader 实例
    """
    return ModularEnvLoader(module_name=module_name, module_path=module_path)
