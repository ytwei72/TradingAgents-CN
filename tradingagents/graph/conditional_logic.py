# TradingAgents/graph/conditional_logic.py

from tradingagents.agents.utils.agent_states import AgentState

# 导入统一日志系统
from tradingagents.utils.logging_init import get_logger
logger = get_logger("default")


class ConditionalLogic:
    """Handles conditional logic for determining graph flow."""

    def __init__(self, max_debate_rounds=1, max_risk_discuss_rounds=1):
        """Initialize with configuration parameters."""
        self.max_debate_rounds = max_debate_rounds
        self.max_risk_discuss_rounds = max_risk_discuss_rounds

    def should_continue_market(self, state: AgentState):
        """Determine if market analysis should continue."""
        messages = state["messages"]
        last_message = messages[-1]

        # 只有AIMessage才有tool_calls属性
        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            return "tools_market"
        return "Msg Clear Market"

    def should_continue_social(self, state: AgentState):
        """Determine if social media analysis should continue."""
        messages = state["messages"]
        last_message = messages[-1]

        # 只有AIMessage才有tool_calls属性
        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            return "tools_social"
        return "Msg Clear Social"

    def should_continue_news(self, state: AgentState):
        """Determine if news analysis should continue."""
        messages = state["messages"]
        last_message = messages[-1]

        # 只有AIMessage才有tool_calls属性
        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            return "tools_news"
        return "Msg Clear News"

    def should_continue_fundamentals(self, state: AgentState):
        """Determine if fundamentals analysis should continue."""
        messages = state["messages"]
        last_message = messages[-1]

        # 只有AIMessage才有tool_calls属性
        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            return "tools_fundamentals"
        return "Msg Clear Fundamentals"

    def should_continue_debate(self, state: AgentState) -> str:
        """Determine if debate should continue."""
        debate_state = state["investment_debate_state"]
        count = debate_state.get("count", 0)
        current_response = debate_state.get("current_response", "")
        
        # 计算最大允许的count值（2个节点各执行max_debate_rounds次）
        max_count = 2 * self.max_debate_rounds
        
        # 如果达到最大轮数，结束辩论
        if count >= max_count:
            logger.info(f"📊 [辩论] 达到最大轮数 ({count} >= {max_count})，结束辩论，跳转到 Research Manager")
            return "Research Manager"
        
        # 如果当前响应以"Bull"开头，轮到看跌研究员
        if current_response.startswith("Bull"):
            logger.info(f"📊 [辩论] 当前响应以'Bull'开头 (count={count}/{max_count})，轮到看跌研究员")
            return "Bear Researcher"
        
        # 否则轮到看涨研究员（初始状态或当前响应以"Bear"开头）
        logger.info(f"📊 [辩论] 轮到看涨研究员 (count={count}/{max_count}, current_response={current_response[:50] if current_response else '空'}...)")
        return "Bull Researcher"

    def should_continue_risk_analysis(self, state: AgentState) -> str:
        """Determine if risk analysis should continue."""
        risk_state = state["risk_debate_state"]
        count = risk_state.get("count", 0)
        latest_speaker = risk_state.get("latest_speaker", "")
        
        # 计算最大允许的count值（3个节点各执行max_risk_discuss_rounds次）
        max_count = 3 * self.max_risk_discuss_rounds
        
        # 如果达到最大轮数，结束风险分析
        if count >= max_count:
            logger.info(f"⚠️ [风险分析] 达到最大轮数 ({count} >= {max_count})，结束风险分析，跳转到 Risk Judge")
            return "Risk Judge"
        
        # 如果最后发言者是激进分析师，轮到保守分析师
        if latest_speaker.startswith("Risky"):
            logger.info(f"⚠️ [风险分析] 最后发言者是激进分析师 (count={count}/{max_count})，轮到保守分析师")
            return "Safe Analyst"
        
        # 如果最后发言者是保守分析师，轮到中性分析师
        if latest_speaker.startswith("Safe"):
            logger.info(f"⚠️ [风险分析] 最后发言者是保守分析师 (count={count}/{max_count})，轮到中性分析师")
            return "Neutral Analyst"
        
        # 否则轮到激进分析师（初始状态或最后发言者是中性分析师）
        logger.info(f"⚠️ [风险分析] 轮到激进分析师 (count={count}/{max_count}, latest_speaker={latest_speaker or '空'})")
        return "Risky Analyst"
