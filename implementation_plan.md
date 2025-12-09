# Implementation Plan - Fix Analysis Steps and History

## Goal Description
Fix issues related to step indexing, duration calculation, risk debate rounds, and step descriptions in the analysis task history. Also update the frontend to display step descriptions.

## User Review Required
> [!IMPORTANT]
> This plan modifies core message publishing and state machine logic.

## Proposed Changes

### Backend

#### [MODIFY] [message_decorators.py](file:///e:/Develop/AI-Agents/TradingAgents/tradingagents/messaging/decorators/message_decorators.py)
- **Issue 1 (Step Index)**: Check `_publish_step_message`. Ensure `tool_calling` does not increment `step_index` or create a new step entry that looks like a main step if it's just an event within a step.
- **Issue 2 (Duration)**: Verify duration calculation in `_publish_step_message`.
- **Issue 4 (Description)**: Modify `_publish_step_message` or `TaskStateMachine` to use a static functional description for the step instead of the dynamic log message.

#### [MODIFY] [task_state_machine.py](file:///e:/Develop/AI-Agents/TradingAgents/tradingagents/tasks/task_state_machine.py)
- Ensure `update_step` logic correctly handles events without advancing the step index unnecessarily.
- Ensure `description` field is preserved or set correctly.

#### [MODIFY] [trading_graph.py](file:///e:/Develop/AI-Agents/TradingAgents/tradingagents/graph/trading_graph.py) or [conditional_logic.py](file:///e:/Develop/AI-Agents/TradingAgents/tradingagents/graph/conditional_logic.py)
- **Issue 3 (Risk Debate)**: Check the logic for risk debate rounds. Ensure the plan matches the execution.

### Frontend

#### [MODIFY] [StockAnalyzeView.vue](file:///e:/Develop/AI-Agents/TradingAgents/frontend/src/views/StockAnalyzeView.vue)
- **Issue 5 (Display Description)**: Update the step list to display the `description` field from the API response.

## Verification Plan

### Automated Tests
- Run `test_step_tracking.py` (if available or create one) to simulate a task and verify the history output.

### Manual Verification
- Run a stock analysis task.
- Check `history` API response for:
    - Continuous `step_index`.
    - Correct `duration`.
    - Correct number of risk debate rounds.
    - Static `description`.
- Check Frontend UI for step descriptions.
