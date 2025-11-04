"""
分析表单组件
"""

import streamlit as st
import datetime

# 导入日志模块
from tradingagents.utils.logging_manager import get_logger

from utils.thread_tracker import check_analysis_status
from utils.smart_session_manager import smart_session_manager
from utils.task_control_manager import pause_task, resume_task, stop_task
import time

# 导入用户活动记录器
try:
    from utils.user_activity_logger import user_activity_logger
except ImportError:
    user_activity_logger = None

logger = get_logger('web')


def render_analysis_form():
    """渲染股票分析表单"""

    # st.subheader("📋 分析配置")

    # 添加分析流程说明 - 可展开/收缩的容器
    with st.expander("📊 查看分析流程与步骤", expanded=False):
        st.markdown("""
        ### 🔄 完整分析流程
        
        本系统采用多Agent协同分析架构，为您提供全面的股票投资分析。系统会实时保存每步执行输出，便于追踪和调试。
        
        #### **第一阶段：配置与准备** 🎯 (步骤1-8)
        
        1. **分析启动** 🚀
           - 记录分析开始日志
           - 初始化分析会话ID
        
        2. **成本估算** 💰
           - 根据选择的分析师和研究深度估算分析成本
           - 显示预估的Token使用量和费用
        
        3. **数据预获取和验证** 🔍
           - 验证股票代码格式和有效性
           - 预获取股票基础数据（30天历史数据）
           - 缓存数据以提高后续分析效率
        
        4. **环境验证** 🔧
           - 检查API密钥配置（DASHSCOPE_API_KEY、FINNHUB_API_KEY等）
           - 验证必要的环境变量
        
        5. **构建配置** ⚙️
           - 根据选择的LLM提供商和模型构建配置
           - 设置研究深度、市场类型等参数
        
        6. **格式化股票代码** 📝
           - 根据市场类型格式化股票代码（A股/港股/美股）
           - 确保代码格式符合数据源要求
        
        7. **初始化分析引擎** 🏗️
           - 创建TradingAgentsGraph实例
           - 初始化所有智能体和工具节点
           - 配置模拟模式（如果启用）
        
        8. **步骤输出目录准备** 📁
           - 创建步骤输出保存目录
           - 准备保存每步执行结果
        
        #### **第二阶段：多智能体分析执行** 🔍 (步骤9)
        
        系统使用LangGraph框架执行多智能体协作分析，**每个节点的输出都会被实时保存**：
        
        **📊 分析师团队阶段**（根据您选择的分析师，顺序执行）
        
        - **📈 市场分析师 (Market Analyst)**
          - 技术面分析：K线形态、均线系统、价格趋势
          - 技术指标分析：MACD、RSI、KDJ、布林带等
          - 支撑阻力位分析、成交量分析
          - **输出保存**：`market_report` 字段
        
        - **💰 基本面分析师 (Fundamentals Analyst)**
          - 财务数据分析：营收、利润、现金流、财务比率
          - 公司基本面研究：业务模式、竞争优势
          - 估值水平评估：PE、PB、PS、ROE等估值指标
          - **输出保存**：`fundamentals_report` 字段
        
        - **📰 新闻分析师 (News Analyst)**
          - 新闻事件收集：相关新闻抓取和筛选
          - 事件影响分析：重大事件对股价的影响评估
          - 市场动态追踪：行业动态、政策变化
          - **输出保存**：`news_report` 字段
        
        - **💭 社交媒体分析师 (Social Media Analyst)**（非A股市场）
          - 社交媒体数据采集：Reddit、Twitter等平台
          - 投资者情绪分析：散户情绪、机构观点
          - 热度指标监测：讨论热度、关注度变化
          - **输出保存**：`sentiment_report` 字段
        
        **🎯 研究员辩论阶段**（研究深度≥2时执行）
        
        - **🐂 看涨研究员 (Bull Researcher)**
          - 从乐观角度分析投资机会
          - 输出看涨观点和投资理由
          - **输出保存**：`investment_debate_state.bull_history`
        
        - **🐻 看跌研究员 (Bear Researcher)**
          - 从谨慎角度分析投资风险
          - 输出看跌观点和风险提醒
          - **输出保存**：`investment_debate_state.bear_history`
        
        - **👔 研究经理 (Research Manager)**
          - 综合多头和空头观点
          - 做出综合投资判断
          - **输出保存**：`investment_debate_state.judge_decision`、`investment_plan`
        
        **💼 交易阶段**
        
        - **交易员 (Trader)**
          - 基于研究结果制定交易计划
          - 输出具体的投资建议和执行策略
          - **输出保存**：`trader_investment_plan`
        
        **⚠️ 风险评估阶段**（研究深度≥3时执行）
        
        - **🔥 激进风险分析师 (Risky Analyst)**
          - 从高风险高收益角度分析
          - 输出激进策略建议
          - **输出保存**：`risk_debate_state.risky_history`
        
        - **🛡️ 保守风险分析师 (Safe Analyst)**
          - 从风险控制角度分析
          - 输出保守策略建议
          - **输出保存**：`risk_debate_state.safe_history`
        
        - **⚖️ 中性风险分析师 (Neutral Analyst)**
          - 从平衡角度分析风险
          - 输出平衡策略建议
          - **输出保存**：`risk_debate_state.neutral_history`
        
        - **🎯 风险经理 (Risk Judge)**
          - 综合各方风险评估
          - 做出最终风险决策和风险评级
          - **输出保存**：`risk_debate_state.judge_decision`、`final_trade_decision`
        
        **📡 信号处理阶段**
        
        - 处理最终交易决策信号
        - 提取结构化的投资建议（买入/持有/卖出）
        
        #### **第三阶段：结果处理与保存** 📋 (步骤10-12)
        
        10. **处理分析结果** 📊
            - 提取风险评估数据
            - 记录Token使用情况
            - 格式化分析结果用于显示
        
        11. **记录完成日志** ✅
            - 记录分析完成时间
            - 计算总耗时和总成本
        
        12. **保存分析结果** 💾
            - **本地文件保存**：保存分模块报告到 `results/{stock_symbol}/` 目录
            - **MongoDB保存**：保存分析报告到数据库
            - **步骤输出保存**：每步执行结果已实时保存到 `eval_results/{stock_symbol}/TradingAgentsStrategy_logs/step_outputs/{trade_date}/`
              - 每个步骤单独保存：`step_0001.json`, `step_0002.json`, ...
              - 步骤汇总文件：`steps_summary.json`
              - 所有步骤合并：`all_steps.json`
        
        #### **第四阶段：结果展示** 📊
        
        - **可视化图表**：价格走势、技术指标图表
        - **数据报表**：关键数据整理展示
        - **分析结论**：综合评分与投资建议
        - **详细步骤日志**：可查看每步执行详情
        - **历史记录**：可查看历史分析结果
        
        ---
        
        ### 🔧 高级功能说明
        
        **步骤输出追踪** 📝
        - 系统会自动保存每个节点的执行输出
        - 所有步骤保存在：`eval_results/{股票代码}/TradingAgentsStrategy_logs/step_outputs/{日期}/`
        - 可用于调试、分析优化和结果回溯
        
        **模拟模式支持** 🎭
        - 支持节点级别的模拟模式配置（通过 `.env` 文件）
        - 模拟模式会使用历史步骤输出，节省API成本
        - 配置示例：`MOCK_ANALYSIS_MODE=market,news` 或 `MOCK_ANALYSIS_MODE=true`
        
        **研究深度说明** 📊
        - **1级（快速）**：仅执行分析师团队，无研究员辩论和详细风险评估
        - **2级（基础）**：包含研究员辩论阶段
        - **3级（标准）**：包含完整的研究员辩论和风险评估团队
        - **4-5级（深度）**：更深入的分析和多次迭代讨论
        
        💡 **提示**：研究深度越高，分析越详细，但耗时也越长。建议首次分析使用3级标准分析。
        """)

    # 获取缓存的表单配置（确保不为None）
    cached_config = st.session_state.get('form_config') or {}

    # 调试信息（只在没有分析运行时记录，避免重复）
    if not st.session_state.get('analysis_running', False):
        if cached_config:
            logger.debug(f"📊 [配置恢复] 使用缓存配置: {cached_config}")
        else:
            logger.debug("📊 [配置恢复] 使用默认配置")

    # 创建表单
    with st.form("analysis_form", clear_on_submit=False):

        # 在表单开始时保存当前配置（用于检测变化）
        initial_config = cached_config.copy() if cached_config else {}
        col1, col2 = st.columns(2)
        
        with col1:
            # 市场选择（使用缓存的值）
            market_options = ["美股", "A股", "港股"]
            cached_market = cached_config.get('market_type', 'A股') if cached_config else 'A股'
            try:
                market_index = market_options.index(cached_market)
            except (ValueError, TypeError):
                market_index = 1  # 默认A股

            market_type = st.selectbox(
                "选择市场 🌍",
                options=market_options,
                index=market_index,
                help="选择要分析的股票市场"
            )

            # 根据市场类型显示不同的输入提示
            cached_stock = cached_config.get('stock_symbol', '') if cached_config else ''

            if market_type == "美股":
                stock_symbol = st.text_input(
                    "股票代码 📈",
                    value=cached_stock if (cached_config and cached_config.get('market_type') == '美股') else '',
                    placeholder="输入美股代码，如 AAPL, TSLA, MSFT，然后按回车确认",
                    help="输入要分析的美股代码，输入完成后请按回车键确认",
                    key="us_stock_input",
                    autocomplete="off"  # 修复autocomplete警告
                ).upper().strip()

                logger.debug(f"🔍 [FORM DEBUG] 美股text_input返回值: '{stock_symbol}'")

            elif market_type == "港股":
                stock_symbol = st.text_input(
                    "股票代码 📈",
                    value=cached_stock if (cached_config and cached_config.get('market_type') == '港股') else '',
                    placeholder="输入港股代码，如 0700.HK, 9988.HK, 3690.HK，然后按回车确认",
                    help="输入要分析的港股代码，如 0700.HK(腾讯控股), 9988.HK(阿里巴巴), 3690.HK(美团)，输入完成后请按回车键确认",
                    key="hk_stock_input",
                    autocomplete="off"  # 修复autocomplete警告
                ).upper().strip()

                logger.debug(f"🔍 [FORM DEBUG] 港股text_input返回值: '{stock_symbol}'")

            else:  # A股
                stock_symbol = st.text_input(
                    "股票代码 📈",
                    value=cached_stock if (cached_config and cached_config.get('market_type') == 'A股') else '',
                    placeholder="输入A股代码，如 000001, 600519，然后按回车确认",
                    help="输入要分析的A股代码，如 000001(平安银行), 600519(贵州茅台)，输入完成后请按回车键确认",
                    key="cn_stock_input",
                    autocomplete="off"  # 修复autocomplete警告
                ).strip()

                logger.debug(f"🔍 [FORM DEBUG] A股text_input返回值: '{stock_symbol}'")
            
            # 分析日期
            analysis_date = st.date_input(
                "分析日期 📅",
                value=datetime.date.today(),
                help="选择分析的基准日期"
            )
        
        with col2:
            # 研究深度（使用缓存的值）
            cached_depth = cached_config.get('research_depth', 3) if cached_config else 3
            research_depth = st.select_slider(
                "研究深度 🔍",
                options=[1, 2, 3, 4, 5],
                value=cached_depth,
                format_func=lambda x: {
                    1: "1级 - 快速分析",
                    2: "2级 - 基础分析",
                    3: "3级 - 标准分析",
                    4: "4级 - 深度分析",
                    5: "5级 - 全面分析"
                }[x],
                help="选择分析的深度级别，级别越高分析越详细但耗时更长"
            )
        
        # 分析师团队选择
        st.markdown("### 👥 选择分析师团队")

        col1, col2 = st.columns(2)

        # 获取缓存的分析师选择和市场类型
        cached_analysts = cached_config.get('selected_analysts', ['market', 'fundamentals']) if cached_config else ['market', 'fundamentals']
        cached_market_type = cached_config.get('market_type', 'A股') if cached_config else 'A股'

        # 检测市场类型是否发生变化
        market_type_changed = cached_market_type != market_type

        # 如果市场类型发生变化，需要调整分析师选择
        if market_type_changed:
            if market_type == "A股":
                # 切换到A股：移除社交媒体分析师
                cached_analysts = [analyst for analyst in cached_analysts if analyst != 'social']
                if len(cached_analysts) == 0:
                    cached_analysts = ['market', 'fundamentals']  # 确保至少有默认选择
            else:
                # 切换到非A股：如果只有基础分析师，添加社交媒体分析师
                if 'social' not in cached_analysts and len(cached_analysts) <= 2:
                    cached_analysts.append('social')

        with col1:
            market_analyst = st.checkbox(
                "📈 市场分析师",
                value='market' in cached_analysts,
                help="专注于技术面分析、价格趋势、技术指标"
            )

            # 始终显示社交媒体分析师checkbox，但在A股时禁用
            if market_type == "A股":
                # A股市场：显示但禁用社交媒体分析师
                social_analyst = st.checkbox(
                    "💭 社交媒体分析师",
                    value=False,
                    disabled=True,
                    help="A股市场暂不支持社交媒体分析（国内数据源限制）"
                )
                st.info("💡 A股市场暂不支持社交媒体分析，因为国内数据源限制")
            else:
                # 非A股市场：正常显示社交媒体分析师
                social_analyst = st.checkbox(
                    "💭 社交媒体分析师",
                    value='social' in cached_analysts,
                    help="分析社交媒体情绪、投资者情绪指标"
                )

        with col2:
            news_analyst = st.checkbox(
                "📰 新闻分析师",
                value='news' in cached_analysts,
                help="分析相关新闻事件、市场动态影响"
            )

            fundamentals_analyst = st.checkbox(
                "💰 基本面分析师",
                value='fundamentals' in cached_analysts,
                help="分析财务数据、公司基本面、估值水平"
            )

        # 收集选中的分析师
        selected_analysts = []
        if market_analyst:
            selected_analysts.append(("market", "市场分析师"))
        if social_analyst:
            selected_analysts.append(("social", "社交媒体分析师"))
        if news_analyst:
            selected_analysts.append(("news", "新闻分析师"))
        if fundamentals_analyst:
            selected_analysts.append(("fundamentals", "基本面分析师"))
        
        # 显示选择摘要
        if selected_analysts:
            st.success(f"已选择 {len(selected_analysts)} 个分析师: {', '.join([a[1] for a in selected_analysts])}")
        else:
            st.warning("请至少选择一个分析师")
        
        # 高级选项
        with st.expander("🔧 高级选项"):
            include_sentiment = st.checkbox(
                "包含情绪分析",
                value=True,
                help="是否包含市场情绪和投资者情绪分析"
            )
            
            include_risk_assessment = st.checkbox(
                "包含风险评估",
                value=True,
                help="是否包含详细的风险因素评估"
            )
            
            custom_prompt = st.text_area(
                "自定义分析要求",
                placeholder="输入特定的分析要求或关注点...",
                help="可以输入特定的分析要求，AI会在分析中重点关注"
            )

        # 显示输入状态提示
        if not stock_symbol:
            st.info("💡 请在上方输入股票代码，输入完成后按回车键确认")
        else:
            st.success(f"✅ 已输入股票代码: {stock_symbol}")

        # 添加JavaScript来改善用户体验（使用工具模块）
        from utils.frontend_scripts import inject_stock_input_enhancer
        inject_stock_input_enhancer()

        # 在提交按钮前检测配置变化并保存
        current_config = {
            'stock_symbol': stock_symbol,
            'market_type': market_type,
            'research_depth': research_depth,
            'selected_analysts': [a[0] for a in selected_analysts],
            'include_sentiment': include_sentiment,
            'include_risk_assessment': include_risk_assessment,
            'custom_prompt': custom_prompt
        }

        # 如果配置发生变化，立即保存（即使没有提交）
        if current_config != initial_config:
            st.session_state.form_config = current_config
            try:
                current_analysis_id = st.session_state.get('current_analysis_id', 'form_config_only')
                smart_session_manager.save_analysis_state(
                    analysis_id=current_analysis_id,
                    status=st.session_state.get('analysis_running', False) and 'running' or 'idle',
                    stock_symbol=stock_symbol,
                    market_type=market_type,
                    form_config=current_config
                )
                logger.debug(f"📊 [配置自动保存] 表单配置已更新")
            except Exception as e:
                logger.warning(f"⚠️ [配置自动保存] 保存失败: {e}")

        # 检查当前是否有任务在运行或暂停
        analysis_running = st.session_state.get('analysis_running', False)
        current_analysis_id = st.session_state.get('current_analysis_id')
        
        # 如果有任务在运行或暂停，禁用提交按钮
        if analysis_running and current_analysis_id:
            st.form_submit_button(
                "🚀 开始分析",
                type="primary",
                use_container_width=True,
                disabled=True
            )
            st.info("⚠️ 当前有任务正在运行或暂停中，请先停止或完成当前任务")
            submitted = False
        else:
            # 提交按钮（启用状态）
            submitted = st.form_submit_button(
                "🚀 开始分析",
                type="primary",
                use_container_width=True
            )

    # 在表单外添加任务控制按钮（重新从session_state获取analysis_id）
    form_current_analysis_id = st.session_state.get('current_analysis_id')
    
    # 调试信息
    # if form_current_analysis_id:
    #     st.info(f"🔍 调试：分析ID = {form_current_analysis_id}")
    # else:
    #     st.warning("🔍 调试：没有找到 current_analysis_id")
    
    if form_current_analysis_id:
        # 使用线程检测来获取真实状态
        try:
            actual_status = check_analysis_status(form_current_analysis_id)
            
            logger.debug(f"🎮 [任务控制] 分析ID: {form_current_analysis_id}, 状态: {actual_status}")
            
            # 调试信息
            # st.info(f"🔍 调试：任务状态 = '{actual_status}'")
            
            if actual_status in ['running', 'paused']:
                # st.success(f"✅ 调试：条件满足，应该显示按钮！状态={actual_status}")
                st.markdown("---")
                st.markdown("### 🎮 任务控制")
                
                # 创建按钮列
                btn_col1, btn_col2, btn_col3 = st.columns(3)
                
                with btn_col1:
                    if actual_status == 'running':
                        if st.button("⏸️ 暂停分析", key="pause_btn_form", use_container_width=True):
                            if pause_task(form_current_analysis_id):
                                st.success("✅ 任务已暂停")
                                logger.info(f"⏸️ [用户操作] 暂停任务: {form_current_analysis_id}")
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error("❌ 暂停失败")
                    
                    elif actual_status == 'paused':
                        if st.button("▶️ 继续分析", key="resume_btn_form", use_container_width=True):
                            if resume_task(form_current_analysis_id):
                                st.success("✅ 任务已恢复")
                                logger.info(f"▶️ [用户操作] 恢复任务: {form_current_analysis_id}")
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error("❌ 恢复失败")
                
                with btn_col2:
                    if st.button("⏹️ 停止分析", key="stop_btn_form", use_container_width=True):
                        if stop_task(form_current_analysis_id):
                            st.success("✅ 任务已停止")
                            logger.info(f"⏹️ [用户操作] 停止任务: {form_current_analysis_id}")
                            # 清理分析状态
                            st.session_state.analysis_running = False
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("❌ 停止失败")
                
                with btn_col3:
                    # 预留空间或添加其他控制按钮
                    pass
            else:
                # 调试信息：状态不匹配
                st.warning(f"⚠️ 调试：状态 '{actual_status}' 不在 ['running', 'paused'] 中")
        except Exception as e:
            logger.warning(f"⚠️ [任务控制] 获取任务状态失败: {e}")
            st.error(f"❌ 调试：获取状态失败 - {str(e)}")

    # 只有在提交时才返回数据
    if submitted and stock_symbol:  # 确保有股票代码才提交
        # 添加详细日志
        logger.debug(f"🔍 [FORM DEBUG] ===== 分析表单提交 =====")
        logger.debug(f"🔍 [FORM DEBUG] 用户输入的股票代码: '{stock_symbol}'")
        logger.debug(f"🔍 [FORM DEBUG] 市场类型: '{market_type}'")
        logger.debug(f"🔍 [FORM DEBUG] 分析日期: '{analysis_date}'")
        logger.debug(f"🔍 [FORM DEBUG] 选择的分析师: {[a[0] for a in selected_analysts]}")
        logger.debug(f"🔍 [FORM DEBUG] 研究深度: {research_depth}")

        form_data = {
            'submitted': True,
            'stock_symbol': stock_symbol,
            'market_type': market_type,
            'analysis_date': str(analysis_date),
            'analysts': [a[0] for a in selected_analysts],
            'research_depth': research_depth,
            'include_sentiment': include_sentiment,
            'include_risk_assessment': include_risk_assessment,
            'custom_prompt': custom_prompt
        }

        # 保存表单配置到缓存和持久化存储
        form_config = {
            'stock_symbol': stock_symbol,
            'market_type': market_type,
            'research_depth': research_depth,
            'selected_analysts': [a[0] for a in selected_analysts],
            'include_sentiment': include_sentiment,
            'include_risk_assessment': include_risk_assessment,
            'custom_prompt': custom_prompt
        }
        st.session_state.form_config = form_config

        # 保存到持久化存储
        try:
            # 获取当前分析ID（如果有的话）
            current_analysis_id = st.session_state.get('current_analysis_id', 'form_config_only')
            smart_session_manager.save_analysis_state(
                analysis_id=current_analysis_id,
                status=st.session_state.get('analysis_running', False) and 'running' or 'idle',
                stock_symbol=stock_symbol,
                market_type=market_type,
                form_config=form_config
            )
        except Exception as e:
            logger.warning(f"⚠️ [配置持久化] 保存失败: {e}")

        # 记录用户分析请求活动
        if user_activity_logger:
            try:
                user_activity_logger.log_analysis_request(
                    symbol=stock_symbol,
                    market=market_type,
                    analysis_date=str(analysis_date),
                    research_depth=research_depth,
                    analyst_team=[a[0] for a in selected_analysts],
                    details={
                        'include_sentiment': include_sentiment,
                        'include_risk_assessment': include_risk_assessment,
                        'has_custom_prompt': bool(custom_prompt),
                        'form_source': 'analysis_form'
                    }
                )
                logger.debug(f"📊 [用户活动] 已记录分析请求: {stock_symbol}")
            except Exception as e:
                logger.warning(f"⚠️ [用户活动] 记录失败: {e}")

        logger.info(f"📊 [配置缓存] 表单配置已保存: {form_config}")

        logger.debug(f"🔍 [FORM DEBUG] 返回的表单数据: {form_data}")
        logger.debug(f"🔍 [FORM DEBUG] ===== 表单提交结束 =====")

        return form_data
    elif submitted and not stock_symbol:
        # 用户点击了提交但没有输入股票代码
        logger.error(f"🔍 [FORM DEBUG] 提交失败：股票代码为空")
        st.error("❌ 请输入股票代码后再提交")
        return {'submitted': False}
    else:
        return {'submitted': False}
