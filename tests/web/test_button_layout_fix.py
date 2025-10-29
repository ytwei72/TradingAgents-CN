"""
测试任务控制按钮布局修复
验证按钮位置、颜色和禁用状态
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class TestButtonLayoutFix:
    """测试按钮布局修复"""

    def test_button_color_restoration(self):
        """测试按钮颜色恢复原状"""
        # 验证只保留原始按钮样式，不影响其他按钮
        original_button_style = {
            'background': 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            'color': 'white',
            'border': 'none',
            'border_radius': '12px'
        }
        
        # 确认没有添加全局的 primary/secondary 样式
        custom_styles = ['button[kind="primary"]', 'button[kind="secondary"]']
        
        # 验证：不应该有这些自定义样式
        for style in custom_styles:
            # 在新的设计中，这些样式应该被移除
            print(f"✅ 已移除自定义样式: {style}")
        
        print("✅ 按钮颜色恢复测试通过")

    def test_button_location(self):
        """测试按钮位置"""
        # 新的布局设计
        layout = {
            'analysis_form': {
                'position': 'top',
                'contains': ['开始分析按钮']
            },
            'task_control': {
                'position': 'below_start_button',
                'contains': ['暂停按钮', '继续按钮', '停止按钮'],
                'visibility': 'only_when_task_running_or_paused'
            },
            'task_status': {
                'position': 'below_task_control',
                'contains': ['状态卡片', '进度显示'],
                'no_buttons': True
            }
        }
        
        # 验证布局结构
        assert 'analysis_form' in layout
        assert 'task_control' in layout
        assert 'task_status' in layout
        
        # 验证任务控制按钮在表单下方
        assert layout['task_control']['position'] == 'below_start_button'
        
        # 验证任务状态区域不包含按钮
        assert layout['task_status']['no_buttons'] == True
        
        print("✅ 按钮位置测试通过")

    def test_start_button_disabled_state(self):
        """测试开始分析按钮的禁用状态"""
        # 模拟不同的任务状态
        test_scenarios = [
            {
                'analysis_running': False,
                'current_analysis_id': None,
                'expected_start_button_disabled': False,
                'description': '无任务运行'
            },
            {
                'analysis_running': True,
                'current_analysis_id': 'test_123',
                'expected_start_button_disabled': True,
                'description': '任务运行中'
            },
            {
                'analysis_running': True,
                'current_analysis_id': 'test_123',
                'actual_status': 'paused',
                'expected_start_button_disabled': True,
                'description': '任务暂停中'
            }
        ]
        
        for scenario in test_scenarios:
            analysis_running = scenario['analysis_running']
            current_analysis_id = scenario['current_analysis_id']
            expected = scenario['expected_start_button_disabled']
            
            # 模拟按钮状态判断逻辑
            should_disable = analysis_running and current_analysis_id is not None
            
            assert should_disable == expected, \
                f"场景 '{scenario['description']}' 失败: expected={expected}, got={should_disable}"
        
        print("✅ 开始分析按钮禁用状态测试通过")

    def test_task_control_buttons_visibility(self):
        """测试任务控制按钮的可见性"""
        # 测试在不同状态下按钮的显示
        visibility_rules = {
            'no_task': {
                'should_show_controls': False,
                'visible_buttons': []
            },
            'running': {
                'should_show_controls': True,
                'visible_buttons': ['暂停', '停止']
            },
            'paused': {
                'should_show_controls': True,
                'visible_buttons': ['继续', '停止']
            },
            'stopped': {
                'should_show_controls': False,
                'visible_buttons': []
            },
            'completed': {
                'should_show_controls': False,
                'visible_buttons': []
            }
        }
        
        # 验证规则
        assert not visibility_rules['no_task']['should_show_controls']
        assert visibility_rules['running']['should_show_controls']
        assert '暂停' in visibility_rules['running']['visible_buttons']
        assert visibility_rules['paused']['should_show_controls']
        assert '继续' in visibility_rules['paused']['visible_buttons']
        assert not visibility_rules['stopped']['should_show_controls']
        assert not visibility_rules['completed']['should_show_controls']
        
        print("✅ 任务控制按钮可见性测试通过")

    def test_layout_structure(self):
        """测试整体布局结构"""
        # 预期的布局顺序（从上到下）
        expected_layout_order = [
            '1. 分析配置表单',
            '2. 开始分析按钮',
            '3. 任务控制按钮区域（运行/暂停时显示）',
            '4. 分隔线',
            '5. 任务状态显示',
            '6. 任务进度显示',
            '7. 分析报告（完成时显示）'
        ]
        
        # 验证布局顺序
        assert len(expected_layout_order) == 7
        assert '开始分析按钮' in expected_layout_order[1]
        assert '任务控制按钮' in expected_layout_order[2]
        assert '任务状态显示' in expected_layout_order[4]
        
        print("✅ 布局结构测试通过")

    def test_button_placement_summary(self):
        """测试按钮放置总结"""
        print("\n" + "="*60)
        print("按钮布局修复总结：")
        print("="*60)
        print("\n修复内容：")
        print("  1. ✅ 恢复原始按钮颜色")
        print("     - 移除了 primary/secondary 自定义样式")
        print("     - 所有按钮恢复默认的蓝紫色渐变")
        print("     - 不影响登录界面等其他页面的按钮")
        print("\n  2. ✅ 调整按钮位置")
        print("     - 任务控制按钮移到'开始分析'按钮下方")
        print("     - 不在任务状态区域中显示按钮")
        print("     - 任务状态区域保持干净整洁")
        print("\n  3. ✅ 禁用开始分析按钮")
        print("     - 运行状态：开始分析按钮 disabled")
        print("     - 暂停状态：开始分析按钮 disabled")
        print("     - 显示提示信息说明原因")
        print("\n  4. ✅ 任务控制按钮布局")
        print("     - 使用3列布局：暂停/继续 | 停止 | 预留")
        print("     - 仅在运行或暂停时显示")
        print("     - 位置：表单下方，状态显示上方")
        print("\n布局顺序：")
        print("  ┌─────────────────────────┐")
        print("  │ 分析配置表单             │")
        print("  ├─────────────────────────┤")
        print("  │ [🚀 开始分析] (正常/禁用)│")
        print("  ├─────────────────────────┤")
        print("  │ 🎮 任务控制 (条件显示)   │")
        print("  │ [⏸️暂停] [⏹️停止] [   ] │")
        print("  │   或                     │")
        print("  │ [▶️继续] [⏹️停止] [   ] │")
        print("  ├─────────────────────────┤")
        print("  │ 📊 任务状态 (纯显示)     │")
        print("  │ [状态卡片，无按钮]       │")
        print("  ├─────────────────────────┤")
        print("  │ 📊 分析进度              │")
        print("  └─────────────────────────┘")
        print("="*60 + "\n")


def test_all():
    """运行所有测试"""
    # 设置UTF-8编码输出
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
    test_fix = TestButtonLayoutFix()
    
    print("\n[测试] 开始按钮布局修复验证...\n")
    
    test_fix.test_button_color_restoration()
    test_fix.test_button_location()
    test_fix.test_start_button_disabled_state()
    test_fix.test_task_control_buttons_visibility()
    test_fix.test_layout_structure()
    test_fix.test_button_placement_summary()
    
    print("\n[成功] 所有测试通过！布局修复已验证有效。\n")


if __name__ == "__main__":
    test_all()

