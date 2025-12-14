# TradingAgents/graph/trading_graph.py

import os
from pathlib import Path
import json
from datetime import date, datetime
from typing import Dict, Any, Tuple, List, Optional
import time
import random

from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from tradingagents.llm_adapters import ChatDashScope, ChatDashScopeOpenAI, ChatGoogleOpenAI

from langgraph.prebuilt import ToolNode

from tradingagents.agents import *
from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.agents.utils.memory import FinancialSituationMemory

# 导入统一日志系统
from tradingagents.utils.logging_init import get_logger

# 导入日志模块
from tradingagents.utils.logging_manager import get_logger
logger = get_logger('agents')
from tradingagents.agents.utils.agent_states import (
    AgentState,
    InvestDebateState,
    RiskDebateState,
)
from tradingagents.dataflows.interface import set_config

from .conditional_logic import ConditionalLogic
from .setup import GraphSetup
from .propagation import Propagator
from .reflection import Reflector
from .signal_processing import SignalProcessor


class TradingAgentsGraph:
    """Main class that orchestrates the trading agents framework."""

    def __init__(
        self,
        selected_analysts=["market", "social", "news", "fundamentals"],
        debug=False,
        config: Dict[str, Any] = None,
    ):
        """Initialize the trading agents graph and components.

        Args:
            selected_analysts: List of analyst types to include
            debug: Whether to run in debug mode
            config: Configuration dictionary. If None, uses default config
        """
        self.debug = debug
        self.config = config or DEFAULT_CONFIG

        # Update the interface's config
        set_config(self.config)

        # Create necessary directories
        os.makedirs(
            os.path.join(self.config["project_dir"], "dataflows/data_cache"),
            exist_ok=True,
        )

        # Initialize LLMs
        if self.config["llm_provider"].lower() == "openai":
            self.deep_thinking_llm = ChatOpenAI(model=self.config["deep_think_llm"], base_url=self.config["backend_url"])
            self.quick_thinking_llm = ChatOpenAI(model=self.config["quick_think_llm"], base_url=self.config["backend_url"])
        elif self.config["llm_provider"] == "siliconflow":
            # SiliconFlow支持：使用OpenAI兼容API
            siliconflow_api_key = os.getenv('SILICONFLOW_API_KEY')
            if not siliconflow_api_key:
                raise ValueError("使用SiliconFlow需要设置SILICONFLOW_API_KEY环境变量")

            logger.info(f"🌐 [SiliconFlow] 使用API密钥: {siliconflow_api_key[:20]}...")

            self.deep_thinking_llm = ChatOpenAI(
                model=self.config["deep_think_llm"],
                base_url=self.config["backend_url"],
                api_key=siliconflow_api_key,
                temperature=0.1,
                max_tokens=2000
            )
            self.quick_thinking_llm = ChatOpenAI(
                model=self.config["quick_think_llm"],
                base_url=self.config["backend_url"],
                api_key=siliconflow_api_key,
                temperature=0.1,
                max_tokens=2000
            )
        elif self.config["llm_provider"] == "openrouter":
            # OpenRouter支持：优先使用OPENROUTER_API_KEY，否则使用OPENAI_API_KEY
            openrouter_api_key = os.getenv('OPENROUTER_API_KEY') or os.getenv('OPENAI_API_KEY')
            if not openrouter_api_key:
                raise ValueError("使用OpenRouter需要设置OPENROUTER_API_KEY或OPENAI_API_KEY环境变量")

            logger.info(f"🌐 [OpenRouter] 使用API密钥: {openrouter_api_key[:20]}...")

            self.deep_thinking_llm = ChatOpenAI(
                model=self.config["deep_think_llm"],
                base_url=self.config["backend_url"],
                api_key=openrouter_api_key
            )
            self.quick_thinking_llm = ChatOpenAI(
                model=self.config["quick_think_llm"],
                base_url=self.config["backend_url"],
                api_key=openrouter_api_key
            )
        elif self.config["llm_provider"] == "ollama":
            self.deep_thinking_llm = ChatOpenAI(model=self.config["deep_think_llm"], base_url=self.config["backend_url"])
            self.quick_thinking_llm = ChatOpenAI(model=self.config["quick_think_llm"], base_url=self.config["backend_url"])
        elif self.config["llm_provider"].lower() == "anthropic":
            self.deep_thinking_llm = ChatAnthropic(model=self.config["deep_think_llm"], base_url=self.config["backend_url"])
            self.quick_thinking_llm = ChatAnthropic(model=self.config["quick_think_llm"], base_url=self.config["backend_url"])
        elif self.config["llm_provider"].lower() == "google":
            # 使用 Google OpenAI 兼容适配器，解决工具调用格式不匹配问题
            logger.info(f"🔧 使用Google AI OpenAI 兼容适配器 (解决工具调用问题)")
            google_api_key = os.getenv('GOOGLE_API_KEY')
            if not google_api_key:
                raise ValueError("使用Google AI需要设置GOOGLE_API_KEY环境变量")
            
            self.deep_thinking_llm = ChatGoogleOpenAI(
                model=self.config["deep_think_llm"],
                google_api_key=google_api_key,
                temperature=0.1,
                max_tokens=2000
            )
            self.quick_thinking_llm = ChatGoogleOpenAI(
                model=self.config["quick_think_llm"],
                google_api_key=google_api_key,
                temperature=0.1,
                max_tokens=2000,
                transport="rest"
            )
            
            logger.info(f"✅ [Google AI] 已启用优化的工具调用和内容格式处理")
        elif (self.config["llm_provider"].lower() == "dashscope" or
              self.config["llm_provider"].lower() == "alibaba" or
              "dashscope" in self.config["llm_provider"].lower() or
              "阿里百炼" in self.config["llm_provider"]):
            # 使用 OpenAI 兼容适配器，支持原生 Function Calling
            logger.info(f"🔧 使用阿里百炼 OpenAI 兼容适配器 (支持原生工具调用)")
            self.deep_thinking_llm = ChatDashScopeOpenAI(
                model=self.config["deep_think_llm"],
                temperature=0.1,
                max_tokens=2000
            )
            self.quick_thinking_llm = ChatDashScopeOpenAI(
                model=self.config["quick_think_llm"],
                temperature=0.1,
                max_tokens=2000
            )
        elif (self.config["llm_provider"].lower() == "deepseek" or
              "deepseek" in self.config["llm_provider"].lower()):
            # DeepSeek V3配置 - 使用支持token统计的适配器
            from tradingagents.llm_adapters.deepseek_adapter import ChatDeepSeek


            deepseek_api_key = os.getenv('DEEPSEEK_API_KEY')
            if not deepseek_api_key:
                raise ValueError("使用DeepSeek需要设置DEEPSEEK_API_KEY环境变量")

            deepseek_base_url = os.getenv('DEEPSEEK_BASE_URL', 'https://api.deepseek.com')

            # 使用支持token统计的DeepSeek适配器
            self.deep_thinking_llm = ChatDeepSeek(
                model=self.config["deep_think_llm"],
                api_key=deepseek_api_key,
                base_url=deepseek_base_url,
                temperature=0.1,
                max_tokens=2000
            )
            self.quick_thinking_llm = ChatDeepSeek(
                model=self.config["quick_think_llm"],
                api_key=deepseek_api_key,
                base_url=deepseek_base_url,
                temperature=0.1,
                max_tokens=2000
                )

            logger.info(f"✅ [DeepSeek] 已启用token统计功能")
        elif self.config["llm_provider"].lower() == "custom_openai":
            # 自定义OpenAI端点配置
            from tradingagents.llm_adapters.openai_compatible_base import create_openai_compatible_llm
            
            custom_api_key = os.getenv('CUSTOM_OPENAI_API_KEY')
            if not custom_api_key:
                raise ValueError("使用自定义OpenAI端点需要设置CUSTOM_OPENAI_API_KEY环境变量")
            
            custom_base_url = self.config.get("custom_openai_base_url", "https://api.openai.com/v1")
            
            logger.info(f"🔧 [自定义OpenAI] 使用端点: {custom_base_url}")
            
            # 使用OpenAI兼容适配器创建LLM实例
            self.deep_thinking_llm = create_openai_compatible_llm(
                provider="custom_openai",
                model=self.config["deep_think_llm"],
                base_url=custom_base_url,
                temperature=0.1,
                max_tokens=2000
            )
            self.quick_thinking_llm = create_openai_compatible_llm(
                provider="custom_openai",
                model=self.config["quick_think_llm"],
                base_url=custom_base_url,
                temperature=0.1,
                max_tokens=2000
            )
            
            logger.info(f"✅ [自定义OpenAI] 已配置自定义端点: {custom_base_url}")
        elif self.config["llm_provider"].lower() == "qianfan":
            # 百度千帆（文心一言）配置 - 统一由适配器内部读取与校验 QIANFAN_API_KEY
            from tradingagents.llm_adapters.openai_compatible_base import create_openai_compatible_llm
            
            # 使用OpenAI兼容适配器创建LLM实例（基类会使用千帆默认base_url并负责密钥校验）
            self.deep_thinking_llm = create_openai_compatible_llm(
                provider="qianfan",
                model=self.config["deep_think_llm"],
                temperature=0.1,
                max_tokens=2000
            )
            self.quick_thinking_llm = create_openai_compatible_llm(
                provider="qianfan",
                model=self.config["quick_think_llm"],
                temperature=0.1,
                max_tokens=2000
            )
            logger.info("✅ [千帆] 文心一言适配器已配置成功")
        else:
            raise ValueError(f"Unsupported LLM provider: {self.config['llm_provider']}")
        
        self.toolkit = Toolkit(config=self.config)

        # Initialize memories (如果启用)
        memory_enabled = self.config.get("memory_enabled", True)
        if memory_enabled:
            # 使用单例ChromaDB管理器，避免并发创建冲突
            self.bull_memory = FinancialSituationMemory("bull_memory", self.config)
            self.bear_memory = FinancialSituationMemory("bear_memory", self.config)
            self.trader_memory = FinancialSituationMemory("trader_memory", self.config)
            self.invest_judge_memory = FinancialSituationMemory("invest_judge_memory", self.config)
            self.risk_manager_memory = FinancialSituationMemory("risk_manager_memory", self.config)
        else:
            # 创建空的内存对象
            self.bull_memory = None
            self.bear_memory = None
            self.trader_memory = None
            self.invest_judge_memory = None
            self.risk_manager_memory = None

        # Create tool nodes
        self.tool_nodes = self._create_tool_nodes()

        # Initialize components
        # 从config读取辩论和风险讨论的轮数配置
        max_debate_rounds = self.config.get("max_debate_rounds", 1)
        max_risk_discuss_rounds = self.config.get("max_risk_discuss_rounds", 1)
        self.conditional_logic = ConditionalLogic(
            max_debate_rounds=max_debate_rounds,
            max_risk_discuss_rounds=max_risk_discuss_rounds
        )
        self.graph_setup = GraphSetup(
            self.quick_thinking_llm,
            self.deep_thinking_llm,
            self.toolkit,
            self.tool_nodes,
            self.bull_memory,
            self.bear_memory,
            self.trader_memory,
            self.invest_judge_memory,
            self.risk_manager_memory,
            self.conditional_logic,
            self.config,
            getattr(self, 'react_llm', None),
        )

        self.propagator = Propagator()
        self.reflector = Reflector(self.quick_thinking_llm)
        self.signal_processor = SignalProcessor(self.quick_thinking_llm)

        # State tracking
        self.curr_state = None
        self.ticker = None
        self.log_states_dict = {}  # date to full state dict
        
        # Step-by-step output tracking (内存保存)
        self.step_traces = []  # List of all chunks during execution
        self.enable_step_tracking = self.config.get("enable_step_tracking", True)  # 默认启用
        
        # 模拟模式配置
        self.mock_mode_config = self._load_mock_mode_config()
        # 从环境变量读取sleep时间配置，如果没有则使用默认值
        self.mock_sleep_min = float(os.getenv('MOCK_SLEEP_MIN', '2'))  # 默认2秒
        self.mock_sleep_max = float(os.getenv('MOCK_SLEEP_MAX', '10'))  # 默认10秒
        
        # MongoDB步骤状态管理器（用于存储和读取步骤状态）
        from tradingagents.utils.mongodb_steps_status_manager import mongodb_steps_status_manager
        self.steps_status_manager = mongodb_steps_status_manager

        # Set up the graph
        self.graph = self.graph_setup.setup_graph(selected_analysts)
        
        # 设置graph实例到模拟模式辅助工具中
        from .mock_mode_helper import set_graph_instance
        set_graph_instance(self)

    def _create_tool_nodes(self) -> Dict[str, ToolNode]:
        """Create tool nodes for different data sources."""
        return {
            "market": ToolNode(
                [
                    # 统一工具
                    self.toolkit.get_stock_market_data_unified,
                    # online tools
                    self.toolkit.get_YFin_data_online,
                    self.toolkit.get_stockstats_indicators_report_online,
                    # offline tools
                    self.toolkit.get_YFin_data,
                    self.toolkit.get_stockstats_indicators_report,
                ]
            ),
            "social": ToolNode(
                [
                    # online tools
                    self.toolkit.get_stock_news_openai,
                    # offline tools
                    self.toolkit.get_reddit_stock_info,
                ]
            ),
            "news": ToolNode(
                [
                    # online tools
                    self.toolkit.get_global_news_openai,
                    self.toolkit.get_google_news,
                    # offline tools
                    self.toolkit.get_finnhub_news,
                    self.toolkit.get_reddit_news,
                ]
            ),
            "fundamentals": ToolNode(
                [
                    # 统一工具
                    self.toolkit.get_stock_fundamentals_unified,
                    # offline tools
                    self.toolkit.get_finnhub_company_insider_sentiment,
                    self.toolkit.get_finnhub_company_insider_transactions,
                    self.toolkit.get_simfin_balance_sheet,
                    self.toolkit.get_simfin_cashflow,
                    self.toolkit.get_simfin_income_stmt,
                ]
            ),
        }

    def propagate(self, company_name, trade_date, analysis_id=None, session_id=None):
        """Run the trading agents graph for a company on a specific date."""
        
        # 添加详细的接收日志
        logger.debug(f"🔍 [GRAPH DEBUG] ===== TradingAgentsGraph.propagate 接收参数 =====")
        logger.debug(f"🔍 [GRAPH DEBUG] 接收到的company_name: '{company_name}' (类型: {type(company_name)})")
        logger.debug(f"🔍 [GRAPH DEBUG] 接收到的trade_date: '{trade_date}' (类型: {type(trade_date)})")
        logger.debug(f"🔍 [GRAPH DEBUG] 接收到的analysis_id: '{analysis_id}' (类型: {type(analysis_id)})")
        logger.debug(f"🔍 [GRAPH DEBUG] 接收到的session_id: '{session_id}' (类型: {type(session_id)})")

        self.ticker = company_name
        logger.debug(f"🔍 [GRAPH DEBUG] 设置self.ticker: '{self.ticker}'")

        # Initialize state
        logger.debug(f"🔍 [GRAPH DEBUG] 创建初始状态，传递参数: company_name='{company_name}', trade_date='{trade_date}', analysis_id='{analysis_id}', session_id='{session_id}'")
        init_agent_state = self.propagator.create_initial_state(
            company_name, trade_date, analysis_id=analysis_id, session_id=session_id
        )
        logger.debug(f"🔍 [GRAPH DEBUG] 初始状态中的company_of_interest: '{init_agent_state.get('company_of_interest', 'NOT_FOUND')}'")
        logger.debug(f"🔍 [GRAPH DEBUG] 初始状态中的trade_date: '{init_agent_state.get('trade_date', 'NOT_FOUND')}'")
        logger.debug(f"🔍 [GRAPH DEBUG] 初始状态中的analysis_id: '{init_agent_state.get('analysis_id', 'NOT_FOUND')}'")
        logger.debug(f"🔍 [GRAPH DEBUG] 初始状态中的session_id: '{init_agent_state.get('session_id', 'NOT_FOUND')}'")
        args = self.propagator.get_graph_args()

        # 清空之前的步骤追踪
        self.step_traces = []

        # 创建步骤输出保存目录
        step_output_dir = self._prepare_step_output_directory(trade_date)

        # 使用stream模式收集所有步骤（无论debug模式与否）
        trace = []
        step_count = 0
        
        logger.info(f"📊 [步骤追踪] 开始收集每步输出，保存目录: {step_output_dir}")
        
        for chunk in self.graph.stream(init_agent_state, **args):
            step_count += 1
            
            # 检查任务控制信号（暂停/停止）
            if analysis_id:
                from tradingagents.tasks import get_task_manager
                from tradingagents.exceptions import TaskControlStoppedException
                task_manager = get_task_manager()
                
                # 检查停止信号
                if task_manager.should_stop(analysis_id):
                    logger.info(f"⏹️ [任务控制] 收到停止信号，中断分析: {analysis_id}")
                    raise TaskControlStoppedException(f"任务已被停止: {analysis_id}")
                
                # 检查暂停信号并等待
                if task_manager.should_pause(analysis_id):
                    logger.info(f"⏸️ [任务控制] 收到暂停信号，等待恢复: {analysis_id}")
                    task_manager.wait_if_paused(analysis_id)
                    
                    # 恢复后再次检查是否被停止
                    if task_manager.should_stop(analysis_id):
                        logger.info(f"⏹️ [任务控制] 暂停期间收到停止信号: {analysis_id}")
                        raise TaskControlStoppedException(f"任务已被停止: {analysis_id}")
                    logger.info(f"▶️ [任务控制] 任务恢复执行: {analysis_id}")
            
            # 序列化chunk以便保存
            serialized_chunk = self._serialize_chunk(chunk, step_count)
            
            # 保存到内存
            trace.append(chunk)
            self.step_traces.append(serialized_chunk)
            
            # 保存每个chunk到文件
            if self.enable_step_tracking:
                self._save_chunk_to_file(serialized_chunk, step_count, step_output_dir)
            
            # Debug模式下打印
            if self.debug and len(chunk.get("messages", [])) > 0:
                chunk["messages"][-1].pretty_print()
            
            logger.debug(f"📝 [步骤追踪] 已保存步骤 {step_count}")

        # 获取最终状态
        final_state = trace[-1] if trace else self.graph.invoke(init_agent_state, **args)
        
        # 保存所有步骤的汇总文件
        if self.enable_step_tracking:
            self._save_steps_summary(trace, step_output_dir)
        
        logger.info(f"✅ [步骤追踪] 完成，共收集 {step_count} 个步骤")

        # Store current state for reflection
        self.curr_state = final_state

        # Log state
        self._log_state(trade_date, final_state)

        # Return decision and processed signal
        return final_state, self.process_signal(final_state["final_trade_decision"], company_name, analysis_id=analysis_id)

    def _load_mock_mode_config(self) -> Dict[str, bool]:
        """加载模拟模式配置，支持节点级别的配置
        
        支持的配置格式：
        - MOCK_ANALYSIS_MODE=true: 所有节点启用模拟模式
        - MOCK_ANALYSIS_MODE=false: 所有节点禁用模拟模式
        - MOCK_ANALYSIS_MODE=market,news: 只对market和news节点启用模拟模式
        - MOCK_ANALYSIS_MODE=market_analyst,bull_researcher: 支持节点名称
        """
        mock_config = os.getenv('MOCK_ANALYSIS_MODE', 'false').strip().lower()
        
        # 如果配置为false，所有节点都不启用
        if mock_config == 'false' or mock_config == '':
            return {}
        
        # 如果配置为true，所有节点都启用
        if mock_config == 'true':
            return {'all': True}
        
        # 解析节点列表
        node_list = [node.strip() for node in mock_config.split(',')]
        config = {}
        
        # 节点名称映射（支持多种命名方式）
        node_mapping = {
            'market': 'market_analyst',
            'market_analyst': 'market_analyst',
            'fundamentals': 'fundamentals_analyst',
            'fundamentals_analyst': 'fundamentals_analyst',
            'news': 'news_analyst',
            'news_analyst': 'news_analyst',
            'social': 'social_media_analyst',
            'social_media_analyst': 'social_media_analyst',
            'bull': 'bull_researcher',
            'bull_researcher': 'bull_researcher',
            'bear': 'bear_researcher',
            'bear_researcher': 'bear_researcher',
            'research_manager': 'research_manager',
            'trader': 'trader',
            'risky': 'risky_analyst',
            'risky_analyst': 'risky_analyst',
            'safe': 'safe_analyst',
            'safe_analyst': 'safe_analyst',
            'neutral': 'neutral_analyst',
            'neutral_analyst': 'neutral_analyst',
            'risk_manager': 'risk_manager',
            'risk_judge': 'risk_manager',
        }
        
        for node in node_list:
            normalized_node = node_mapping.get(node, node)
            config[normalized_node] = True
        
        logger.info(f"🎭 [模拟模式配置] 已加载: {config}")
        return config
    
    def _should_use_mock_mode(self, node_name: str) -> bool:
        """检查某个节点是否应该使用模拟模式
        
        Args:
            node_name: 节点名称，如 'market_analyst', 'bull_researcher' 等
            
        Returns:
            如果应该使用模拟模式返回True，否则返回False
        """
        if not self.mock_mode_config:
            return False
        
        # 如果配置了'all'，所有节点都启用
        if self.mock_mode_config.get('all', False):
            return True
        
        # 检查节点是否在配置列表中
        return self.mock_mode_config.get(node_name, False)
    
    def _load_historical_step_output(self, node_name: str, ticker: str, trade_date: str, current_state: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """从MongoDB的analysis_steps_status集合中加载指定节点的历史输出
        
        Args:
            node_name: 节点名称
            ticker: 股票代码
            trade_date: 交易日期
            current_state: 当前状态字典，用于获取count值
            
        Returns:
            如果找到历史输出则返回状态字典，否则返回None
        """
        # 优先从MongoDB读取
        if self.steps_status_manager.is_connected():
            try:
                doc = self.steps_status_manager.load_step_status(ticker, trade_date)
                
                if doc:
                    # 查找匹配的节点输出
                    # 由于MongoDB中存储的是单个步骤数据，直接使用该文档
                    # 检查是否匹配当前节点
                    if self._match_node_output(node_name, "", doc):
                        logger.info(f"🎭 [模拟模式] 从MongoDB找到历史输出: {node_name} (股票: {ticker}, 日期: {trade_date})")
                        return self._convert_historical_to_state(doc, node_name, current_state)
                    else:
                        logger.debug(f"🔍 [模拟模式] MongoDB中找到记录但节点不匹配: {node_name}")
                else:
                    logger.debug(f"🔍 [模拟模式] MongoDB中未找到记录: {ticker} - {trade_date}")
                    
            except Exception as e:
                logger.warning(f"⚠️ [模拟模式] 从MongoDB读取失败: {e}，尝试从文件系统读取")
        
        # 如果MongoDB读取失败，回退到文件系统
        # 查找历史步骤文件
        step_output_dir = Path(f"eval_results/{ticker}/TradingAgentsStrategy_logs/step_outputs")
        
        # 尝试多个可能的日期格式
        possible_dates = [
            trade_date,
            trade_date.replace('-', ''),
            str(datetime.strptime(trade_date, '%Y-%m-%d').strftime('%Y%m%d')) if '-' in trade_date else None
        ]
        
        for date_str in possible_dates:
            if not date_str:
                continue
            
            date_dir = step_output_dir / date_str
            
            # 检查all_steps.json文件
            all_steps_file = date_dir / "all_steps.json"
            if all_steps_file.exists():
                try:
                    with open(all_steps_file, 'r', encoding='utf-8') as f:
                        all_steps = json.load(f)
                    
                    # 查找匹配的节点输出（找到最匹配的步骤）
                    best_match = None
                    best_match_score = 0
                    
                    for step in all_steps:
                        # 检查消息内容中是否包含节点标识
                        messages = step.get('messages', [])
                        match_score = 0
                        
                        for msg in messages:
                            content = str(msg.get('content', ''))
                            # 根据节点名称和内容特征匹配，计算匹配分数
                            if self._match_node_output(node_name, content, step):
                                # 计算匹配分数（关键词匹配数量）
                                match_score = self._calculate_match_score(node_name, content, step)
                                if match_score > best_match_score:
                                    best_match = step
                                    best_match_score = match_score
                    
                    if best_match:
                        logger.info(f"🎭 [模拟模式] 从文件系统找到历史输出: {node_name} (步骤 {best_match.get('step_number', '?')}, 匹配分数: {best_match_score})")
                        return self._convert_historical_to_state(best_match, node_name, current_state)
                except Exception as e:
                    logger.debug(f"🔍 [模拟模式] 读取历史文件失败: {e}")
                    continue
        
        logger.warning(f"⚠️ [模拟模式] 未找到节点 {node_name} 的历史输出")
        return None
    
    def _match_node_output(self, node_name: str, content: str, step: Dict[str, Any]) -> bool:
        """检查步骤是否匹配指定的节点
        
        Args:
            node_name: 节点名称
            content: 消息内容
            step: 步骤数据
            
        Returns:
            如果匹配返回True
        """
        # 特殊处理：risk_manager节点，优先检查其特定输出字段
        if node_name == 'risk_manager':
            # risk_manager的主要输出字段是risk_debate_state.judge_decision和final_trade_decision
            risk_debate_state = step.get('risk_debate_state', {})
            if isinstance(risk_debate_state, dict):
                judge_decision = risk_debate_state.get('judge_decision', '')
                if judge_decision and len(str(judge_decision).strip()) > 0:
                    return True
            
            # 检查final_trade_decision字段（risk_manager的输出）
            final_decision = step.get('final_trade_decision', '')
            if final_decision and len(str(final_decision).strip()) > 0:
                # 进一步确认：final_trade_decision通常包含风险评级信息
                final_decision_str = str(final_decision).lower()
                if any(keyword in final_decision_str for keyword in ['风险', 'risk', '风险评级', '风险等级']):
                    return True
        
        # 节点名称到关键词的映射
        node_keywords = {
            'market_analyst': ['市场', '技术', '价格', 'market', '技术分析', '技术指标'],
            'fundamentals_analyst': ['基本面', '财务', 'fundamental', '财务指标', '财务报表'],
            'news_analyst': ['新闻', 'news', '事件', '新闻事件'],
            'social_media_analyst': ['社交', '情绪', 'sentiment', '社交媒体'],
            'bull_researcher': ['看涨', 'bull', '多头', '乐观'],
            'bear_researcher': ['看跌', 'bear', '空头', '悲观'],
            'research_manager': ['研究经理', '综合', '综合判断'],
            'trader': ['交易', 'trader', '交易计划', '投资建议'],
            'risky_analyst': ['激进', 'risky', '高风险'],
            'safe_analyst': ['保守', 'safe', '低风险'],
            'neutral_analyst': ['中性', 'neutral', '平衡'],
            'risk_manager': ['风险经理', '风险决策', '风险评级', '风险等级', 'risk_manager', 'risk judge'],
        }
        
        keywords = node_keywords.get(node_name, [])
        if not keywords:
            return False
        
        # 检查内容或字段是否包含关键词
        content_lower = content.lower()
        for keyword in keywords:
            if keyword.lower() in content_lower:
                return True
        
        # 检查步骤中的报告字段
        report_fields = ['market_report', 'fundamentals_report', 'news_report', 
                        'sentiment_report', 'investment_plan', 'final_trade_decision']
        for field in report_fields:
            field_content = step.get(field, '')
            if field_content:
                for keyword in keywords:
                    if keyword.lower() in str(field_content).lower():
                        return True
        
        return False
    
    def _calculate_match_score(self, node_name: str, content: str, step: Dict[str, Any]) -> int:
        """计算匹配分数
        
        Args:
            node_name: 节点名称
            content: 消息内容
            step: 步骤数据
            
        Returns:
            匹配分数（越高越好）
        """
        score = 0
        
        # 特殊处理：risk_manager节点，优先检查其特定输出字段（给予高分）
        if node_name == 'risk_manager':
            risk_debate_state = step.get('risk_debate_state', {})
            if isinstance(risk_debate_state, dict):
                judge_decision = risk_debate_state.get('judge_decision', '')
                if judge_decision and len(str(judge_decision).strip()) > 0:
                    score += 10  # 高风险特征，优先匹配
            
            # final_trade_decision是risk_manager的主要输出
            final_decision = step.get('final_trade_decision', '')
            if final_decision and len(str(final_decision).strip()) > 0:
                final_decision_str = str(final_decision).lower()
                if any(keyword in final_decision_str for keyword in ['风险', 'risk', '风险评级', '风险等级']):
                    score += 10  # 高风险特征，优先匹配
        
        node_keywords = {
            'market_analyst': ['市场', '技术', '价格', 'market', '技术分析', '技术指标'],
            'fundamentals_analyst': ['基本面', '财务', 'fundamental', '财务指标', '财务报表'],
            'news_analyst': ['新闻', 'news', '事件', '新闻事件'],
            'social_media_analyst': ['社交', '情绪', 'sentiment', '社交媒体'],
            'bull_researcher': ['看涨', 'bull', '多头', '乐观'],
            'bear_researcher': ['看跌', 'bear', '空头', '悲观'],
            'research_manager': ['研究经理', '综合', '综合判断'],
            'trader': ['交易', 'trader', '交易计划', '投资建议'],
            'risky_analyst': ['激进', 'risky', '高风险'],
            'safe_analyst': ['保守', 'safe', '低风险'],
            'neutral_analyst': ['中性', 'neutral', '平衡'],
            'risk_manager': ['风险经理', '风险决策', '风险评级', '风险等级', 'risk_manager', 'risk judge'],
        }
        
        keywords = node_keywords.get(node_name, [])
        content_lower = content.lower()
        
        # 计算关键词匹配数量
        for keyword in keywords:
            if keyword.lower() in content_lower:
                score += 1
        
        # 检查报告字段
        report_fields = ['market_report', 'fundamentals_report', 'news_report', 
                        'sentiment_report', 'investment_plan', 'final_trade_decision']
        for field in report_fields:
            field_content = step.get(field, '')
            if field_content:
                for keyword in keywords:
                    if keyword.lower() in str(field_content).lower():
                        score += 1
        
        return score
    
    def _convert_historical_to_state(self, historical_step: Dict[str, Any], node_name: str, current_state: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """将历史步骤数据转换为状态字典
        
        Args:
            historical_step: 历史步骤数据
            node_name: 节点名称
            current_state: 当前状态字典，用于获取count值
            
        Returns:
            状态字典
        """
        # 创建基础状态
        state = {
            'company_of_interest': historical_step.get('company_of_interest', ''),
            'trade_date': historical_step.get('trade_date', ''),
            'messages': []
        }
        
        # 转换消息
        for msg in historical_step.get('messages', []):
            if isinstance(msg, dict):
                msg_type = msg.get('type', '')
                content = msg.get('content', '')
                if msg_type == 'tuple':
                    state['messages'].append((msg.get('role', 'human'), content))
                else:
                    # 创建简单的消息对象
                    from langchain_core.messages import AIMessage
                    state['messages'].append(AIMessage(content=content))
        
        # 复制报告字段
        report_fields = ['market_report', 'fundamentals_report', 'news_report', 
                        'sentiment_report', 'investment_plan', 'trader_investment_plan',
                        'final_trade_decision']
        for field in report_fields:
            if field in historical_step:
                state[field] = historical_step[field]
        
        # 复制辩论状态
        # 使用当前state的count值（如果存在），否则设为0
        if 'investment_debate_state' in historical_step:
            investment_state = historical_step['investment_debate_state'].copy() if isinstance(historical_step['investment_debate_state'], dict) else historical_step['investment_debate_state']
            if isinstance(investment_state, dict):
                # 如果当前state中有count值，使用当前state的count值；否则设为0
                if current_state and 'investment_debate_state' in current_state and isinstance(current_state['investment_debate_state'], dict):
                    current_count = current_state['investment_debate_state'].get('count')
                    if current_count is not None:
                        investment_state['count'] = current_count
                    else:
                        investment_state['count'] = 0
                else:
                    investment_state['count'] = 0
            state['investment_debate_state'] = investment_state
        
        if 'risk_debate_state' in historical_step:
            risk_state = historical_step['risk_debate_state'].copy() if isinstance(historical_step['risk_debate_state'], dict) else historical_step['risk_debate_state']
            if isinstance(risk_state, dict):
                # 如果当前state中有count值，使用当前state的count值；否则设为0
                if current_state and 'risk_debate_state' in current_state and isinstance(current_state['risk_debate_state'], dict):
                    current_count = current_state['risk_debate_state'].get('count')
                    if current_count is not None:
                        risk_state['count'] = current_count
                    else:
                        risk_state['count'] = 0
                else:
                    risk_state['count'] = 0
            state['risk_debate_state'] = risk_state
        
        return state
    
    def _prepare_step_output_directory(self, trade_date: str) -> Path:
        """准备步骤输出保存目录"""
        directory = Path(f"eval_results/{self.ticker}/TradingAgentsStrategy_logs/step_outputs/{trade_date}")
        directory.mkdir(parents=True, exist_ok=True)
        return directory
    
    def _serialize_chunk(self, chunk: Dict[str, Any], step_number: int) -> Dict[str, Any]:
        """序列化chunk，将LangChain消息对象转换为可序列化的格式"""
        serialized = {
            "step_number": step_number,
            "timestamp": datetime.now().isoformat(),
            "company_of_interest": chunk.get("company_of_interest", ""),
            "trade_date": chunk.get("trade_date", ""),
        }
        
        # 序列化消息列表
        messages = []
        for msg in chunk.get("messages", []):
            if hasattr(msg, "content"):
                # LangChain消息对象
                msg_dict = {
                    "type": type(msg).__name__,
                    "content": str(msg.content) if msg.content else "",
                }
                # 添加工具调用信息
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    msg_dict["tool_calls"] = []
                    for tool_call in msg.tool_calls:
                        if isinstance(tool_call, dict):
                            msg_dict["tool_calls"].append(tool_call)
                        else:
                            msg_dict["tool_calls"].append({
                                "name": getattr(tool_call, "name", ""),
                                "args": getattr(tool_call, "args", {}),
                                "id": getattr(tool_call, "id", "")
                            })
            elif isinstance(msg, tuple):
                # 元组格式的消息 (role, content)
                msg_dict = {
                    "type": "tuple",
                    "role": msg[0],
                    "content": str(msg[1]) if len(msg) > 1 else ""
                }
            else:
                # 其他格式
                msg_dict = {
                    "type": type(msg).__name__,
                    "content": str(msg)
                }
            messages.append(msg_dict)
        
        serialized["messages"] = messages
        
        # 保存所有报告字段
        report_fields = [
            "market_report", "fundamentals_report", "sentiment_report", 
            "news_report", "investment_plan", "trader_investment_plan",
            "final_trade_decision"
        ]
        for field in report_fields:
            if field in chunk:
                serialized[field] = chunk[field]
        
        # 保存辩论状态
        if "investment_debate_state" in chunk:
            debate_state = chunk["investment_debate_state"]
            serialized["investment_debate_state"] = {
                "bull_history": debate_state.get("bull_history", ""),
                "bear_history": debate_state.get("bear_history", ""),
                "history": debate_state.get("history", ""),
                "current_response": debate_state.get("current_response", ""),
                "judge_decision": debate_state.get("judge_decision", ""),
                "count": debate_state.get("count", 0)
            }
        
        if "risk_debate_state" in chunk:
            risk_state = chunk["risk_debate_state"]
            serialized["risk_debate_state"] = {
                "risky_history": risk_state.get("risky_history", ""),
                "safe_history": risk_state.get("safe_history", ""),
                "neutral_history": risk_state.get("neutral_history", ""),
                "history": risk_state.get("history", ""),
                "judge_decision": risk_state.get("judge_decision", ""),
                "count": risk_state.get("count", 0)
            }
        
        return serialized
    
    def _save_chunk_to_file(self, serialized_chunk: Dict[str, Any], step_number: int, output_dir: Path):
        """保存单个chunk到MongoDB和/或文件"""
        # 优先保存到MongoDB
        if self.steps_status_manager.is_connected():
            try:
                success = self.steps_status_manager.save_step_status(serialized_chunk)
                if success:
                    ticker = serialized_chunk.get('company_of_interest', '')
                    trade_date = serialized_chunk.get('trade_date', '')
                    logger.debug(f"💾 [步骤保存] 已保存步骤 {step_number} 到MongoDB: {ticker} - {trade_date}")
                else:
                    logger.warning(f"⚠️ [步骤保存] 保存到MongoDB失败，将尝试保存到文件系统")
            except Exception as e:
                logger.warning(f"⚠️ [步骤保存] 保存到MongoDB失败: {e}，将尝试保存到文件系统")
        
        # 同时保存到文件系统（作为备份）
        filename = output_dir / f"step_{step_number:04d}.json"
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(serialized_chunk, f, ensure_ascii=False, indent=2)
            logger.debug(f"💾 [步骤保存] 已保存步骤 {step_number} 到 {filename}")
        except Exception as e:
            logger.error(f"❌ [步骤保存] 保存步骤 {step_number} 到文件失败: {e}")
    
    def _save_steps_summary(self, trace: List[Dict[str, Any]], output_dir: Path):
        """保存所有步骤的汇总文件"""
        summary = {
            "total_steps": len(trace),
            "company_of_interest": self.ticker,
            "trade_date": trace[0].get("trade_date", "") if trace else "",
            "generated_at": datetime.now().isoformat(),
            "steps_summary": []
        }
        
        for i, chunk in enumerate(trace, 1):
            step_info = {
                "step_number": i,
                "has_messages": len(chunk.get("messages", [])) > 0,
                "message_count": len(chunk.get("messages", [])),
                "updated_fields": []
            }
            
            # 检测哪些字段被更新了
            for field in ["market_report", "fundamentals_report", "sentiment_report", 
                         "news_report", "investment_plan", "trader_investment_plan",
                         "final_trade_decision"]:
                if field in chunk and chunk[field]:
                    step_info["updated_fields"].append(field)
            
            # 检测是否有工具调用
            tool_calls = []
            for msg in chunk.get("messages", []):
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    for tool_call in msg.tool_calls:
                        if isinstance(tool_call, dict):
                            tool_calls.append(tool_call.get("name", "unknown"))
                        else:
                            tool_calls.append(getattr(tool_call, "name", "unknown"))
            
            if tool_calls:
                step_info["tool_calls"] = tool_calls
            
            summary["steps_summary"].append(step_info)
        
        # 保存汇总文件
        summary_file = output_dir / "steps_summary.json"
        try:
            with open(summary_file, 'w', encoding='utf-8') as f:
                json.dump(summary, f, ensure_ascii=False, indent=2)
            logger.info(f"📊 [步骤汇总] 已保存汇总文件: {summary_file}")
        except Exception as e:
            logger.error(f"❌ [步骤汇总] 保存汇总文件失败: {e}")
        
        # 同时保存所有序列化的chunk到一个文件（便于查看）
        all_steps_file = output_dir / "all_steps.json"
        try:
            with open(all_steps_file, 'w', encoding='utf-8') as f:
                json.dump(self.step_traces, f, ensure_ascii=False, indent=2)
            logger.info(f"📊 [步骤汇总] 已保存所有步骤到: {all_steps_file}")
        except Exception as e:
            logger.error(f"❌ [步骤汇总] 保存所有步骤失败: {e}")

    def _log_state(self, trade_date, final_state):
        """Log the final state to a JSON file."""
        self.log_states_dict[str(trade_date)] = {
            "company_of_interest": final_state["company_of_interest"],
            "trade_date": final_state["trade_date"],
            "market_report": final_state["market_report"],
            "sentiment_report": final_state["sentiment_report"],
            "news_report": final_state["news_report"],
            "fundamentals_report": final_state["fundamentals_report"],
            "investment_debate_state": {
                "bull_history": final_state["investment_debate_state"]["bull_history"],
                "bear_history": final_state["investment_debate_state"]["bear_history"],
                "history": final_state["investment_debate_state"]["history"],
                "current_response": final_state["investment_debate_state"][
                    "current_response"
                ],
                "judge_decision": final_state["investment_debate_state"][
                    "judge_decision"
                ],
            },
            "trader_investment_decision": final_state["trader_investment_plan"],
            "risk_debate_state": {
                "risky_history": final_state["risk_debate_state"]["risky_history"],
                "safe_history": final_state["risk_debate_state"]["safe_history"],
                "neutral_history": final_state["risk_debate_state"]["neutral_history"],
                "history": final_state["risk_debate_state"]["history"],
                "judge_decision": final_state["risk_debate_state"]["judge_decision"],
            },
            "investment_plan": final_state["investment_plan"],
            "final_trade_decision": final_state["final_trade_decision"],
        }

        # Save to file
        directory = Path(f"eval_results/{self.ticker}/TradingAgentsStrategy_logs/")
        directory.mkdir(parents=True, exist_ok=True)

        with open(
            f"eval_results/{self.ticker}/TradingAgentsStrategy_logs/full_states_log.json",
            "w",
        ) as f:
            json.dump(self.log_states_dict, f, indent=4)

    def reflect_and_remember(self, returns_losses):
        """Reflect on decisions and update memory based on returns."""
        self.reflector.reflect_bull_researcher(
            self.curr_state, returns_losses, self.bull_memory
        )
        self.reflector.reflect_bear_researcher(
            self.curr_state, returns_losses, self.bear_memory
        )
        self.reflector.reflect_trader(
            self.curr_state, returns_losses, self.trader_memory
        )
        self.reflector.reflect_invest_judge(
            self.curr_state, returns_losses, self.invest_judge_memory
        )
        self.reflector.reflect_risk_manager(
            self.curr_state, returns_losses, self.risk_manager_memory
        )

    def process_signal(self, full_signal, stock_symbol=None, analysis_id=None):
        """Process a signal to extract the core decision."""
        return self.signal_processor.process_signal(full_signal, stock_symbol, analysis_id=analysis_id)
