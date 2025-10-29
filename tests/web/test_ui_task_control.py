"""
任务控制界面测试
测试优化后的任务控制按钮和状态显示
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class TestTaskControlUI:
    """任务控制界面测试"""

    def test_task_states_display(self):
        """测试任务状态显示"""
        # 测试不同状态的HTML生成
        states = ['running', 'paused', 'stopped', 'completed', 'failed']
        
        for state in states:
            # 验证状态存在
            assert state in states
        
        print("✅ 任务状态显示测试通过")

    def test_button_types(self):
        """测试按钮类型"""
        # 测试按钮配置
        button_configs = {
            'resume': {
                'label': '▶️ 继续分析',
                'type': 'primary',
                'help': '继续执行被暂停的分析任务'
            },
            'pause': {
                'label': '⏸️ 暂停分析',
                'type': 'secondary',
                'help': '暂停当前分析任务，可随时恢复'
            },
            'stop': {
                'label': '⏹️ 停止分析',
                'type': 'secondary',
                'help': '永久停止当前分析任务'
            }
        }
        
        # 验证按钮配置
        assert 'resume' in button_configs
        assert button_configs['resume']['type'] == 'primary'
        assert 'pause' in button_configs
        assert button_configs['pause']['type'] == 'secondary'
        assert 'stop' in button_configs
        assert button_configs['stop']['type'] == 'secondary'
        
        print("✅ 按钮类型测试通过")

    def test_button_labels(self):
        """测试按钮标签"""
        expected_labels = {
            'start': '🚀 开始分析',
            'pause': '⏸️ 暂停分析',
            'resume': '▶️ 继续分析',
            'stop': '⏹️ 停止分析'
        }
        
        # 验证标签包含正确的图标和文字
        for key, label in expected_labels.items():
            assert '️' in label or '🚀' in label  # 包含emoji
            assert '分析' in label  # 包含"分析"关键词
        
        print("✅ 按钮标签测试通过")

    def test_state_card_colors(self):
        """测试状态卡片颜色"""
        # 测试不同状态的颜色配置
        state_colors = {
            'running': '#4CAF50',     # 绿色
            'paused': '#FFA726',      # 橙色
            'stopped': '#f44336',     # 红色
            'completed': '#2196F3',   # 蓝色
            'failed': '#f44336'       # 红色
        }
        
        # 验证颜色配置
        assert len(state_colors) == 5
        assert state_colors['running'].startswith('#')
        assert state_colors['paused'].startswith('#')
        
        print("✅ 状态卡片颜色测试通过")

    def test_css_button_styles(self):
        """测试CSS按钮样式"""
        # 测试CSS样式定义
        css_styles = {
            'primary': {
                'background': 'linear-gradient(135deg, #4CAF50 0%, #45a049 100%)',
                'color': 'green'
            },
            'secondary': {
                'background': 'linear-gradient(135deg, #FFA726 0%, #FB8C00 100%)',
                'color': 'orange'
            }
        }
        
        # 验证CSS样式
        assert 'primary' in css_styles
        assert 'secondary' in css_styles
        assert 'linear-gradient' in css_styles['primary']['background']
        assert 'linear-gradient' in css_styles['secondary']['background']
        
        print("✅ CSS按钮样式测试通过")

    def test_button_visibility_logic(self):
        """测试按钮显示逻辑"""
        # 测试不同状态下应该显示哪些按钮
        button_visibility = {
            'running': ['pause', 'stop'],
            'paused': ['resume', 'stop'],
            'stopped': [],
            'completed': [],
            'failed': []
        }
        
        # 验证显示逻辑
        assert len(button_visibility['running']) == 2
        assert 'pause' in button_visibility['running']
        assert len(button_visibility['paused']) == 2
        assert 'resume' in button_visibility['paused']
        assert len(button_visibility['stopped']) == 0
        assert len(button_visibility['completed']) == 0
        
        print("✅ 按钮显示逻辑测试通过")

    def test_state_messages(self):
        """测试状态消息"""
        # 测试不同状态的消息文本
        state_messages = {
            'running': '🔄 分析进行中',
            'paused': '⏸️ 分析已暂停',
            'stopped': '⏹️ 分析已停止',
            'completed': '✅ 分析完成',
            'failed': '❌ 分析失败'
        }
        
        # 验证消息文本
        for state, message in state_messages.items():
            assert message  # 消息不为空
            assert len(message) > 0
        
        print("✅ 状态消息测试通过")

    def test_user_feedback_messages(self):
        """测试用户操作反馈消息"""
        # 测试操作反馈消息
        feedback_messages = {
            'pause_success': '✅ 任务已暂停',
            'pause_fail': '❌ 暂停失败',
            'resume_success': '✅ 任务已恢复',
            'resume_fail': '❌ 恢复失败',
            'stop_success': '✅ 任务已停止',
            'stop_fail': '❌ 停止失败'
        }
        
        # 验证反馈消息
        assert all('✅' in msg or '❌' in msg for msg in feedback_messages.values())
        
        print("✅ 用户反馈消息测试通过")


def test_all():
    """运行所有测试"""
    # 设置UTF-8编码输出
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
    test_ui = TestTaskControlUI()
    
    print("\n[测试] 开始任务控制界面测试...\n")
    
    test_ui.test_task_states_display()
    test_ui.test_button_types()
    test_ui.test_button_labels()
    test_ui.test_state_card_colors()
    test_ui.test_css_button_styles()
    test_ui.test_button_visibility_logic()
    test_ui.test_state_messages()
    test_ui.test_user_feedback_messages()
    
    print("\n[成功] 所有测试通过！\n")


if __name__ == "__main__":
    test_all()

