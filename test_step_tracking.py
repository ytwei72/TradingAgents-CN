"""
测试任务状态机的步骤跟踪逻辑
"""
import time
from tradingagents.tasks.task_state_machine import TaskStateMachine, TaskStatus

def test_step_tracking():
    """测试步骤跟踪逻辑"""
    
    # 1. 初始化任务
    print("=" * 60)
    print("测试1: 初始化任务")
    print("=" * 60)
    
    task_id = "test_task_001"
    sm = TaskStateMachine(task_id)
    sm.initialize({
        'stock_symbol': 'AAPL',
        'market_type': '美股'
    })
    
    print(f"当前步骤: {sm.current_step}")
    print(f"历史记录数量: {len(sm.history)}")
    print(f"✅ 预期: 历史为空 - 实际: {len(sm.history) == 0}")
    print()
    
    # 2. 开始步骤1
    print("=" * 60)
    print("测试2: 开始步骤1")
    print("=" * 60)
    
    time.sleep(0.1)  # 模拟耗时
    sm.update_state({
        'status': TaskStatus.RUNNING.value,
        'progress': {
            'current_step': 1,
            'message': '正在收集数据'
        }
    })
    
    print(f"当前步骤索引: {sm.current_step.get('step_index')}")
    print(f"历史记录数量: {len(sm.history)}")
    if sm.history:
        print(f"历史中的步骤索引: {[h.get('step_index') for h in sm.history]}")
        print(f"步骤0的耗时: {sm.history[0].get('elapsed_time', 0):.3f}秒")
    print(f"✅ 预期: 步骤0已结束并添加到历史 - 实际: {len(sm.history) == 1 and sm.history[0].get('step_index') == 0}")
    print()
    
    # 3. 更新步骤1的进度（同一步骤）
    print("=" * 60)
    print("测试3: 更新步骤1的进度")
    print("=" * 60)
    
    time.sleep(0.1)
    sm.update_state({
        'progress': {
            'current_step': 1,
            'message': '数据收集中...50%'
        }
    })
    
    print(f"当前步骤索引: {sm.current_step.get('step_index')}")
    print(f"当前步骤描述: {sm.current_step.get('description')}")
    print(f"历史记录数量: {len(sm.history)}")
    print(f"✅ 预期: 历史不变 - 实际: {len(sm.history) == 1}")
    print()
    
    # 4. 切换到步骤2
    print("=" * 60)
    print("测试4: 切换到步骤2")
    print("=" * 60)
    
    time.sleep(0.1)
    sm.update_state({
        'progress': {
            'current_step': 2,
            'message': '正在分析市场'
        }
    })
    
    print(f"当前步骤索引: {sm.current_step.get('step_index')}")
    print(f"历史记录数量: {len(sm.history)}")
    if len(sm.history) >= 2:
        print(f"历史中的步骤索引: {[h.get('step_index') for h in sm.history]}")
        print(f"步骤1的耗时: {sm.history[1].get('elapsed_time', 0):.3f}秒")
    print(f"✅ 预期: 步骤1已添加到历史 - 实际: {len(sm.history) == 2 and sm.history[1].get('step_index') == 1}")
    print()
    
    # 5. 切换到步骤3
    print("=" * 60)
    print("测试5: 切换到步骤3")
    print("=" * 60)
    
    time.sleep(0.1)
    sm.update_state({
        'progress': {
            'current_step': 3,
            'message': '正在分析基本面'
        }
    })
    
    print(f"当前步骤索引: {sm.current_step.get('step_index')}")
    print(f"历史记录数量: {len(sm.history)}")
    print(f"历史中的步骤索引: {[h.get('step_index') for h in sm.history]}")
    print(f"✅ 预期: 步骤2已添加到历史 - 实际: {len(sm.history) == 3 and sm.history[2].get('step_index') == 2}")
    print()
    
    # 6. 任务完成
    print("=" * 60)
    print("测试6: 任务完成")
    print("=" * 60)
    
    time.sleep(0.1)
    sm.update_state({
        'status': TaskStatus.COMPLETED.value,
        'result': {'success': True}
    })
    
    print(f"当前步骤索引: {sm.current_step.get('step_index')}")
    print(f"当前步骤状态: {sm.current_step.get('status')}")
    print(f"历史记录数量: {len(sm.history)}")
    print(f"历史中的步骤索引: {[h.get('step_index') for h in sm.history]}")
    if len(sm.history) >= 4:
        print(f"步骤3的耗时: {sm.history[3].get('elapsed_time', 0):.3f}秒")
        print(f"步骤3的状态: {sm.history[3].get('status')}")
    print(f"✅ 预期: 步骤3已添加到历史 - 实际: {len(sm.history) == 4 and sm.history[3].get('step_index') == 3}")
    print()
    
    # 7. 验证历史记录完整性
    print("=" * 60)
    print("测试7: 验证历史记录完整性")
    print("=" * 60)
    
    print("\n完整历史记录:")
    for i, step in enumerate(sm.history):
        print(f"\n步骤 {i}:")
        print(f"  索引: {step.get('step_index')}")
        print(f"  描述: {step.get('description')}")
        print(f"  状态: {step.get('status')}")
        print(f"  开始: {step.get('start_time')}")
        print(f"  结束: {step.get('end_time')}")
        print(f"  耗时: {step.get('elapsed_time', 0):.3f}秒")
    
    # 验证
    all_have_index = all(h.get('step_index') is not None for h in sm.history)
    all_have_elapsed = all(h.get('elapsed_time') is not None for h in sm.history)
    all_have_end_time = all(h.get('end_time') is not None for h in sm.history)
    no_duplicates = len(sm.history) == len(set(h.get('step_index') for h in sm.history))
    
    print(f"\n✅ 所有步骤都有索引: {all_have_index}")
    print(f"✅ 所有步骤都有耗时: {all_have_elapsed}")
    print(f"✅ 所有步骤都有结束时间: {all_have_end_time}")
    print(f"✅ 没有重复的步骤: {no_duplicates}")
    print(f"✅ 历史记录数量正确: {len(sm.history) == 4}")
    
    print("\n" + "=" * 60)
    print("测试完成!")
    print("=" * 60)

if __name__ == '__main__':
    test_step_tracking()
