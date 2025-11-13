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
        
        # 检查是否已经有完整的报告（避免死循环）
        fundamentals_report = state.get('fundamentals_report', '')
        if fundamentals_report and len(fundamentals_report) > 100:
            # 检查报告是否包含错误信息（如果是错误，允许重试一次）
            error_indicators = ['失败', '错误', '异常', '不可用', '无法获取', '调用失败']
            is_error_report = any(indicator in fundamentals_report for indicator in error_indicators)
            
            if not is_error_report:
                logger.info(f"📊 [条件判断] 基本面分析已有完整报告（{len(fundamentals_report)}字符），结束分析")
                return "Msg Clear Fundamentals"
        
        # 检查消息历史中的工具调用次数，避免无限循环
        tool_call_count = 0
        tool_message_count = 0
        for msg in messages:
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                tool_call_count += len(msg.tool_calls)
            # 检查工具返回的消息
            if hasattr(msg, '__class__') and 'ToolMessage' in msg.__class__.__name__:
                tool_message_count += 1
        
        # 如果工具调用次数过多（>=3次），强制结束
        if tool_call_count >= 3:
            logger.warning(f"📊 [条件判断] 工具调用次数过多（{tool_call_count}次），强制结束基本面分析以避免死循环")
            return "Msg Clear Fundamentals"
        
        # 如果已经有工具返回的消息，检查是否有错误
        if tool_message_count > 0:
            # 检查最后几条消息中是否有工具返回的错误
            recent_messages = messages[-min(5, len(messages)):]
            for msg in recent_messages:
                if hasattr(msg, '__class__') and 'ToolMessage' in msg.__class__.__name__:
                    if hasattr(msg, 'content') and msg.content:
                        content = str(msg.content)
                        error_indicators = ['失败', '错误', '异常', '不可用', '无法获取', '调用失败', '数据为空', '获取失败', '❌']
                        if any(indicator in content for indicator in error_indicators):
                            # 如果工具返回错误且已经调用过工具，强制结束
                            if tool_call_count >= 1:
                                logger.warning(f"📊 [条件判断] 检测到工具返回错误且已调用过工具，强制结束基本面分析")
                                return "Msg Clear Fundamentals"
        
        last_message = messages[-1] if messages else None
        if not last_message:
            return "Msg Clear Fundamentals"

        # 只有AIMessage才有tool_calls属性
        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            return "tools_fundamentals"
        return "Msg Clear Fundamentals"

    def should_continue_debate(self, state: AgentState) -> str:
        """Determine if debate should continue."""
        debate_state = state["investment_debate_state"]
        count = debate_state.get("count", 0)
        
        # 计算最大允许的count值（2个节点各执行max_debate_rounds次）
        max_count = 2 * self.max_debate_rounds
        
        # 如果达到最大轮数，结束辩论
        if count >= max_count:
            logger.info(f"📊 [辩论] 达到最大轮数 ({count} >= {max_count})，结束辩论，跳转到 Research Manager")
            return "Research Manager"
        
        # 使用count计数来决定下一个发言者
        # count为偶数（包括0）时，轮到看涨研究员；count为奇数时，轮到看跌研究员
        if count % 2 == 0:
            logger.info(f"📊 [辩论] count={count} (偶数)，轮到看涨研究员")
            return "Bull Researcher"
        else:
            logger.info(f"📊 [辩论] count={count} (奇数)，轮到看跌研究员")
            return "Bear Researcher"

    def should_continue_risk_analysis(self, state: AgentState) -> str:
        """Determine if risk analysis should continue."""
        risk_state = state["risk_debate_state"]
        count = risk_state.get("count", 0)
        
        # 计算最大允许的count值（3个节点各执行max_risk_discuss_rounds次）
        max_count = 3 * self.max_risk_discuss_rounds
        
        # 如果达到最大轮数，结束风险分析
        if count >= max_count:
            logger.info(f"⚠️ [风险分析] 达到最大轮数 ({count} >= {max_count})，结束风险分析，跳转到 Risk Judge")
            return "Risk Judge"
        
        # 使用count计数来决定下一个发言者
        # count % 3 == 0: 激进分析师
        # count % 3 == 1: 保守分析师
        # count % 3 == 2: 中性分析师
        if count % 3 == 0:
            logger.info(f"⚠️ [风险分析] count={count} (mod 3 == 0)，轮到激进分析师")
            return "Risky Analyst"
        elif count % 3 == 1:
            logger.info(f"⚠️ [风险分析] count={count} (mod 3 == 1)，轮到保守分析师")
            return "Safe Analyst"
        else:  # count % 3 == 2
            logger.info(f"⚠️ [风险分析] count={count} (mod 3 == 2)，轮到中性分析师")
            return "Neutral Analyst"
