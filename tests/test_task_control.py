"""
任务控制功能测试脚本
测试暂停、恢复和停止功能
"""

import sys
import os
import time
import threading
from pathlib import Path

# 设置UTF-8编码
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_task_control_manager():
    """测试任务控制管理器"""
    print("=" * 60)
    print("测试任务控制管理器")
    print("=" * 60)
    
    from web.utils.task_control_manager import (
        TaskControlManager, register_task, pause_task, 
        resume_task, stop_task, should_stop, should_pause, 
        wait_if_paused, get_task_state
    )
    
    # 1. 测试任务注册
    print("\n1. 测试任务注册...")
    analysis_id = "test_analysis_001"
    register_task(analysis_id)
    assert get_task_state(analysis_id) == 'running', "任务初始状态应该是running"
    print("✅ 任务注册成功")
    
    # 2. 测试暂停功能
    print("\n2. 测试暂停功能...")
    assert pause_task(analysis_id), "暂停任务应该成功"
    assert get_task_state(analysis_id) == 'paused', "任务状态应该是paused"
    assert should_pause(analysis_id), "should_pause应该返回True"
    print("✅ 暂停功能正常")
    
    # 3. 测试恢复功能
    print("\n3. 测试恢复功能...")
    assert resume_task(analysis_id), "恢复任务应该成功"
    assert get_task_state(analysis_id) == 'running', "任务状态应该是running"
    assert not should_pause(analysis_id), "should_pause应该返回False"
    print("✅ 恢复功能正常")
    
    # 4. 测试停止功能
    print("\n4. 测试停止功能...")
    assert stop_task(analysis_id), "停止任务应该成功"
    assert get_task_state(analysis_id) == 'stopped', "任务状态应该是stopped"
    assert should_stop(analysis_id), "should_stop应该返回True"
    print("✅ 停止功能正常")
    
    # 5. 测试停止后无法暂停/恢复
    print("\n5. 测试停止后的状态...")
    assert not pause_task(analysis_id), "停止后不应该能暂停"
    assert not resume_task(analysis_id), "停止后不应该能恢复"
    print("✅ 停止后状态控制正常")
    
    print("\n" + "=" * 60)
    print("✅ 任务控制管理器测试通过！")
    print("=" * 60)


def test_async_progress_tracker():
    """测试异步进度跟踪器的任务控制集成"""
    print("\n" + "=" * 60)
    print("测试异步进度跟踪器的任务控制集成")
    print("=" * 60)
    
    from web.utils.async_progress_tracker import AsyncProgressTracker
    
    # 创建跟踪器
    print("\n1. 创建进度跟踪器...")
    analysis_id = "test_analysis_002"
    tracker = AsyncProgressTracker(
        analysis_id=analysis_id,
        analysts=['market', 'fundamentals'],
        research_depth=2,
        llm_provider='dashscope'
    )
    print("✅ 跟踪器创建成功")
    
    # 测试暂停标记
    print("\n2. 测试暂停标记...")
    tracker.mark_paused()
    progress = tracker.get_progress()
    assert progress['control_state'] == 'paused', "控制状态应该是paused"
    print("✅ 暂停标记正常")
    
    # 测试恢复标记
    print("\n3. 测试恢复标记...")
    tracker.mark_resumed()
    progress = tracker.get_progress()
    assert progress['control_state'] == 'running', "控制状态应该是running"
    print("✅ 恢复标记正常")
    
    # 测试停止标记
    print("\n4. 测试停止标记...")
    tracker.mark_stopped("测试停止")
    progress = tracker.get_progress()
    assert progress['status'] == 'stopped', "状态应该是stopped"
    assert progress['control_state'] == 'stopped', "控制状态应该是stopped"
    print("✅ 停止标记正常")
    
    # 测试有效时间计算
    print("\n5. 测试有效时间计算...")
    analysis_id = "test_analysis_003"
    tracker2 = AsyncProgressTracker(
        analysis_id=analysis_id,
        analysts=['market'],
        research_depth=1,
        llm_provider='dashscope'
    )
    
    # 运行1秒
    time.sleep(1)
    elapsed_1 = tracker2.get_effective_elapsed_time()
    
    # 暂停
    tracker2.mark_paused()
    time.sleep(1)  # 暂停1秒
    
    # 恢复
    tracker2.mark_resumed()
    time.sleep(1)  # 再运行1秒
    elapsed_2 = tracker2.get_effective_elapsed_time()
    
    # 有效时间应该约为2秒（排除暂停的1秒）
    assert 1.8 < elapsed_2 < 2.5, f"有效时间应该约为2秒，实际: {elapsed_2:.2f}秒"
    print(f"✅ 有效时间计算正常: {elapsed_2:.2f}秒（预期约2秒）")
    
    print("\n" + "=" * 60)
    print("✅ 异步进度跟踪器测试通过！")
    print("=" * 60)


def test_simulated_task_with_control():
    """模拟一个可控制的任务"""
    print("\n" + "=" * 60)
    print("测试模拟任务的暂停/恢复/停止")
    print("=" * 60)
    
    from web.utils.task_control_manager import (
        register_task, pause_task, resume_task, 
        stop_task, should_stop, wait_if_paused
    )
    
    analysis_id = "test_analysis_004"
    register_task(analysis_id)
    
    completed_steps = []
    task_stopped = False
    
    def simulated_task():
        """模拟一个长时间运行的任务"""
        nonlocal task_stopped
        
        for i in range(10):
            # 检查暂停
            wait_if_paused(analysis_id)
            
            # 检查停止
            if should_stop(analysis_id):
                print(f"  任务在步骤 {i} 收到停止信号")
                task_stopped = True
                break
            
            # 执行工作
            print(f"  执行步骤 {i}...")
            completed_steps.append(i)
            time.sleep(0.3)
        
        if not task_stopped:
            print("  任务完成所有步骤")
    
    # 启动任务线程
    print("\n1. 启动模拟任务...")
    task_thread = threading.Thread(target=simulated_task, daemon=True)
    task_thread.start()
    
    # 让任务运行几步
    time.sleep(1)
    print(f"\n2. 运行了 {len(completed_steps)} 个步骤")
    
    # 暂停任务
    print("\n3. 暂停任务...")
    pause_task(analysis_id)
    step_count_before_pause = len(completed_steps)
    time.sleep(1)
    step_count_during_pause = len(completed_steps)
    assert step_count_before_pause == step_count_during_pause, "暂停期间不应该执行新步骤"
    print(f"✅ 暂停成功，步骤数保持在 {step_count_during_pause}")
    
    # 恢复任务
    print("\n4. 恢复任务...")
    resume_task(analysis_id)
    time.sleep(1)
    step_count_after_resume = len(completed_steps)
    assert step_count_after_resume > step_count_during_pause, "恢复后应该继续执行"
    print(f"✅ 恢复成功，已执行 {step_count_after_resume} 个步骤")
    
    # 停止任务
    print("\n5. 停止任务...")
    stop_task(analysis_id)
    time.sleep(1)
    
    # 等待线程结束
    task_thread.join(timeout=2)
    
    assert task_stopped, "任务应该被停止"
    assert len(completed_steps) < 10, "任务应该在完成前被停止"
    print(f"✅ 停止成功，完成了 {len(completed_steps)}/10 个步骤")
    
    print("\n" + "=" * 60)
    print("✅ 模拟任务控制测试通过！")
    print("=" * 60)


def test_checkpoint_saving():
    """测试检查点保存和加载"""
    print("\n" + "=" * 60)
    print("测试检查点保存和加载")
    print("=" * 60)
    
    from web.utils.task_control_manager import (
        register_task, save_checkpoint, load_checkpoint
    )
    
    analysis_id = "test_analysis_005"
    register_task(analysis_id)
    
    # 1. 保存检查点
    print("\n1. 保存检查点...")
    checkpoint_data = {
        'current_step': 5,
        'total_steps': 10,
        'state_data': {'key': 'value'},
        'timestamp': time.time()
    }
    save_checkpoint(analysis_id, checkpoint_data)
    print("✅ 检查点保存成功")
    
    # 2. 加载检查点
    print("\n2. 加载检查点...")
    loaded_data = load_checkpoint(analysis_id)
    assert loaded_data is not None, "应该能加载检查点"
    assert loaded_data['current_step'] == 5, "检查点数据应该匹配"
    assert loaded_data['state_data']['key'] == 'value', "嵌套数据应该匹配"
    print("✅ 检查点加载成功")
    
    print("\n" + "=" * 60)
    print("✅ 检查点功能测试通过！")
    print("=" * 60)


def main():
    """运行所有测试"""
    print("\n" + "=" * 80)
    print(" " * 20 + "任务控制功能完整测试")
    print("=" * 80)
    
    try:
        # 测试1: 任务控制管理器
        test_task_control_manager()
        
        # 测试2: 异步进度跟踪器
        test_async_progress_tracker()
        
        # 测试3: 模拟任务控制
        test_simulated_task_with_control()
        
        # 测试4: 检查点功能
        test_checkpoint_saving()
        
        print("\n" + "=" * 80)
        print(" " * 25 + "🎉 所有测试通过！ 🎉")
        print("=" * 80)
        print("\n功能清单:")
        print("  ✅ 任务注册和状态管理")
        print("  ✅ 任务暂停功能")
        print("  ✅ 任务恢复功能")
        print("  ✅ 任务停止功能")
        print("  ✅ 暂停时长统计")
        print("  ✅ 有效时间计算")
        print("  ✅ 检查点保存和加载")
        print("  ✅ 线程控制集成")
        print("\n" + "=" * 80 + "\n")
        
        return True
        
    except Exception as e:
        print("\n" + "=" * 80)
        print(" " * 25 + "❌ 测试失败 ❌")
        print("=" * 80)
        print(f"\n错误信息: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

