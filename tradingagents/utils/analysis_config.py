"""
分析配置构建器
负责根据参数构建分析配置，复用已有的配置管理类
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional
from tradingagents.default_config import DEFAULT_CONFIG

# 导入日志模块
from tradingagents.utils.logging_manager import get_logger
logger = get_logger('web')


class AnalysisConfigBuilder:
    """分析配置构建器"""
    
    def __init__(self, project_root: Optional[Path] = None):
        """初始化配置构建器"""
        self.project_root = project_root or Path(__file__).parent.parent.parent
    
    def build_config(
        self,
        llm_provider: str,
        llm_model: str,
        research_depth: int,
        market_type: str = "美股"
    ) -> Dict[str, Any]:
        """
        构建分析配置
        
        Args:
            llm_provider: LLM提供商
            llm_model: 模型名称
            research_depth: 研究深度（1-5）
            market_type: 市场类型
            
        Returns:
            配置字典
        """
        # 从默认配置开始
        config = DEFAULT_CONFIG.copy()
        
        # 设置基础LLM配置
        config["llm_provider"] = llm_provider
        config["deep_think_llm"] = llm_model
        config["quick_think_llm"] = llm_model
        
        # 根据研究深度设置辩论轮次
        config.update(self._get_debate_config(research_depth))
        
        # 设置通用配置
        config["memory_enabled"] = True
        config["online_tools"] = True
        
        # 根据LLM提供商设置模型和backend_url
        config.update(self._get_provider_config(llm_provider, llm_model, research_depth))
        
        # 设置路径配置
        config.update(self._get_path_config())
        
        # 确保目录存在
        self._ensure_directories(config)
        
        logger.info(f"📋 [配置构建] 研究深度: {research_depth}, 提供商: {llm_provider}")
        logger.info(f"📋 [配置构建] 快速模型: {config['quick_think_llm']}, 深度模型: {config['deep_think_llm']}")
        
        return config
    
    def _get_debate_config(self, research_depth: int) -> Dict[str, Any]:
        """根据研究深度获取辩论配置"""
        depth_configs = {
            1: {"max_debate_rounds": 1, "max_risk_discuss_rounds": 1},
            2: {"max_debate_rounds": 1, "max_risk_discuss_rounds": 1},
            3: {"max_debate_rounds": 1, "max_risk_discuss_rounds": 2},
            4: {"max_debate_rounds": 2, "max_risk_discuss_rounds": 2},
            5: {"max_debate_rounds": 3, "max_risk_discuss_rounds": 3},
        }
        return depth_configs.get(research_depth, depth_configs[3])
    
    def _get_provider_config(
        self,
        llm_provider: str,
        llm_model: str,
        research_depth: int
    ) -> Dict[str, Any]:
        """根据LLM提供商获取配置"""
        provider_configs = {
            "dashscope": lambda: self._get_dashscope_config(research_depth),
            "deepseek": lambda: self._get_deepseek_config(),
            "qianfan": lambda: self._get_qianfan_config(research_depth),
            "google": lambda: self._get_google_config(research_depth),
            "openai": lambda: self._get_openai_config(llm_model),
            "openrouter": lambda: self._get_openrouter_config(llm_model),
            "siliconflow": lambda: self._get_siliconflow_config(llm_model),
            "custom_openai": lambda: self._get_custom_openai_config(llm_model),
        }
        
        config_func = provider_configs.get(llm_provider.lower())
        if config_func:
            return config_func()
        
        # 默认配置
        return {
            "backend_url": "https://api.openai.com/v1",
            "quick_think_llm": llm_model,
            "deep_think_llm": llm_model,
        }
    
    def _get_dashscope_config(self, research_depth: int) -> Dict[str, Any]:
        """获取DashScope配置"""
        model_map = {
            1: ("qwen-turbo", "qwen-plus"),
            2: ("qwen-plus", "qwen-plus"),
            3: ("qwen-plus", "qwen3-max"),
            4: ("qwen-plus", "qwen3-max"),
            5: ("qwen3-max", "qwen3-max"),
        }
        quick_model, deep_model = model_map.get(research_depth, ("qwen-plus", "qwen3-max"))
        
        return {
            "backend_url": "https://dashscope.aliyuncs.com/api/v1",
            "quick_think_llm": quick_model,
            "deep_think_llm": deep_model,
        }
    
    def _get_deepseek_config(self) -> Dict[str, Any]:
        """获取DeepSeek配置"""
        return {
            "backend_url": "https://api.deepseek.com",
            "quick_think_llm": "deepseek-chat",
            "deep_think_llm": "deepseek-chat",
        }
    
    def _get_qianfan_config(self, research_depth: int) -> Dict[str, Any]:
        """获取千帆（文心一言）配置"""
        if research_depth <= 2:
            model = "ernie-3.5-8k"
        elif research_depth <= 4:
            model = "ernie-4.0-turbo-8k"
        else:
            model = "ernie-4.0-turbo-8k"
        
        logger.info(f"🤖 [千帆] 快速模型: {model}, 深度模型: {model}")
        return {
            "backend_url": "https://aip.baidubce.com",
            "quick_think_llm": model,
            "deep_think_llm": model,
        }
    
    def _get_google_config(self, research_depth: int) -> Dict[str, Any]:
        """获取Google AI配置"""
        model_map = {
            1: ("gemini-2.5-flash-lite-preview-06-17", "gemini-2.0-flash"),
            2: ("gemini-2.0-flash", "gemini-1.5-pro"),
            3: ("gemini-1.5-pro", "gemini-2.5-flash"),
            4: ("gemini-2.5-flash", "gemini-2.5-pro"),
            5: ("gemini-2.5-pro", "gemini-2.5-pro"),
        }
        quick_model, deep_model = model_map.get(research_depth, ("gemini-1.5-pro", "gemini-2.5-flash"))
        
        logger.info(f"🤖 [Google AI] 快速模型: {quick_model}, 深度模型: {deep_model}")
        return {
            "backend_url": "https://api.openai.com/v1",
            "quick_think_llm": quick_model,
            "deep_think_llm": deep_model,
        }
    
    def _get_openai_config(self, llm_model: str) -> Dict[str, Any]:
        """获取OpenAI配置"""
        logger.info(f"🤖 [OpenAI] 使用模型: {llm_model}")
        return {
            "backend_url": "https://api.openai.com/v1",
            "quick_think_llm": llm_model,
            "deep_think_llm": llm_model,
        }
    
    def _get_openrouter_config(self, llm_model: str) -> Dict[str, Any]:
        """获取OpenRouter配置"""
        logger.info(f"🌐 [OpenRouter] 使用模型: {llm_model}")
        return {
            "backend_url": "https://openrouter.ai/api/v1",
            "quick_think_llm": llm_model,
            "deep_think_llm": llm_model,
        }
    
    def _get_siliconflow_config(self, llm_model: str) -> Dict[str, Any]:
        """获取SiliconFlow配置"""
        logger.info(f"🌐 [SiliconFlow] 使用模型: {llm_model}")
        return {
            "backend_url": "https://api.siliconflow.cn/v1",
            "quick_think_llm": llm_model,
            "deep_think_llm": llm_model,
        }
    
    def _get_custom_openai_config(self, llm_model: str) -> Dict[str, Any]:
        """获取自定义OpenAI配置"""
        # 尝试从streamlit session state获取，如果没有则使用默认值
        try:
            import streamlit as st
            custom_base_url = st.session_state.get("custom_openai_base_url", "https://api.openai.com/v1")
        except:
            custom_base_url = os.getenv("CUSTOM_OPENAI_BASE_URL", "https://api.openai.com/v1")
        
        logger.info(f"🔧 [自定义OpenAI] 使用模型: {llm_model}, API端点: {custom_base_url}")
        return {
            "backend_url": custom_base_url,
            "custom_openai_base_url": custom_base_url,
            "quick_think_llm": llm_model,
            "deep_think_llm": llm_model,
        }
    
    def _get_path_config(self) -> Dict[str, Any]:
        """获取路径配置"""
        config = {}
        
        # 数据目录
        if not os.getenv("TRADINGAGENTS_DATA_DIR"):
            config["data_dir"] = str(self.project_root / "data")
        else:
            env_data_dir = os.getenv("TRADINGAGENTS_DATA_DIR")
            if os.path.isabs(env_data_dir):
                config["data_dir"] = env_data_dir
            else:
                config["data_dir"] = str(self.project_root / env_data_dir)
        
        # 结果目录
        if not os.getenv("TRADINGAGENTS_RESULTS_DIR"):
            config["results_dir"] = str(self.project_root / "results")
        else:
            env_results_dir = os.getenv("TRADINGAGENTS_RESULTS_DIR")
            if os.path.isabs(env_results_dir):
                config["results_dir"] = env_results_dir
            else:
                config["results_dir"] = str(self.project_root / env_results_dir)
        
        # 缓存目录
        if not os.getenv("TRADINGAGENTS_CACHE_DIR"):
            config["data_cache_dir"] = str(self.project_root / "tradingagents" / "dataflows" / "data_cache")
        else:
            env_cache_dir = os.getenv("TRADINGAGENTS_CACHE_DIR")
            if os.path.isabs(env_cache_dir):
                config["data_cache_dir"] = env_cache_dir
            else:
                config["data_cache_dir"] = str(self.project_root / env_cache_dir)
        
        return config
    
    def _ensure_directories(self, config: Dict[str, Any]) -> None:
        """确保必要的目录存在"""
        directories = [
            config.get("data_dir"),
            config.get("results_dir"),
            config.get("data_cache_dir"),
        ]
        
        for directory in directories:
            if directory:
                os.makedirs(directory, exist_ok=True)
        
        logger.info(f"📁 [目录配置] 数据目录: {config.get('data_dir')}")
        logger.info(f"📁 [目录配置] 结果目录: {config.get('results_dir')}")
        logger.info(f"📁 [目录配置] 缓存目录: {config.get('data_cache_dir')}")

