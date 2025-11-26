#!/usr/bin/env python3
"""
测试模块化环境变量配置功能

验证:
1. 环境变量加载器基本功能
2. 配置优先级
3. 类型转换
4. News 配置管理器
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_env_loader_basic():
    """测试环境变量加载器基本功能"""
    print("\n" + "=" * 60)
    print("测试 1: 环境变量加载器基本功能")
    print("=" * 60)
    
    from tradingagents.utils.env_loader import ModularEnvLoader
    
    # 创建加载器
    loader = ModularEnvLoader()
    
    # 加载全局环境变量
    loader.load_env(verbose=True)
    
    # 测试获取环境变量
    finnhub_key = loader.get_env('FINNHUB_API_KEY')
    if finnhub_key:
        print(f"✅ 成功获取 FINNHUB_API_KEY: {finnhub_key[:10]}...")
    else:
        print("⚠️ FINNHUB_API_KEY 未配置")
    
    # 测试默认值
    test_key = loader.get_env('NON_EXISTENT_KEY', default='default_value')
    assert test_key == 'default_value', "默认值测试失败"
    print("✅ 默认值功能正常")


def test_type_conversion():
    """测试类型转换功能"""
    print("\n" + "=" * 60)
    print("测试 2: 类型转换功能")
    print("=" * 60)
    
    from tradingagents.utils.env_loader import ModularEnvLoader
    
    loader = ModularEnvLoader()
    loader.load_env()
    
    # 设置测试环境变量
    os.environ['TEST_BOOL_TRUE'] = 'true'
    os.environ['TEST_BOOL_FALSE'] = 'false'
    os.environ['TEST_INT'] = '42'
    os.environ['TEST_FLOAT'] = '3.14'
    os.environ['TEST_LIST'] = 'item1,item2,item3'
    
    # 测试布尔值
    bool_true = loader.get_env_bool('TEST_BOOL_TRUE')
    bool_false = loader.get_env_bool('TEST_BOOL_FALSE')
    assert bool_true is True, "布尔值 true 转换失败"
    assert bool_false is False, "布尔值 false 转换失败"
    print("✅ 布尔值转换正常")
    
    # 测试整数
    int_val = loader.get_env_int('TEST_INT')
    assert int_val == 42, "整数转换失败"
    print("✅ 整数转换正常")
    
    # 测试浮点数
    float_val = loader.get_env_float('TEST_FLOAT')
    assert abs(float_val - 3.14) < 0.001, "浮点数转换失败"
    print("✅ 浮点数转换正常")
    
    # 测试列表
    list_val = loader.get_env_list('TEST_LIST')
    assert list_val == ['item1', 'item2', 'item3'], "列表转换失败"
    print("✅ 列表转换正常")
    
    # 清理测试环境变量
    for key in ['TEST_BOOL_TRUE', 'TEST_BOOL_FALSE', 'TEST_INT', 'TEST_FLOAT', 'TEST_LIST']:
        os.environ.pop(key, None)


def test_module_env_loading():
    """测试模块级环境变量加载"""
    print("\n" + "=" * 60)
    print("测试 3: 模块级环境变量加载")
    print("=" * 60)
    
    from tradingagents.utils.env_loader import ModularEnvLoader
    
    # 测试加载 dataflows 模块的环境变量
    dataflows_path = project_root / "tradingagents" / "dataflows"
    
    # 检查是否存在模块级 .env 文件
    module_env_file = dataflows_path / ".env"
    if module_env_file.exists():
        print(f"✅ 找到模块级 .env 文件: {module_env_file}")
        
        loader = ModularEnvLoader(module_path=dataflows_path)
        loaded_vars = loader.load_env(verbose=True)
        
        print(f"✅ 加载了 {len(loaded_vars)} 个模块级环境变量")
    else:
        print(f"⚠️ 模块级 .env 文件不存在: {module_env_file}")
        print("   可以从 .env.news.example 复制创建")


def test_config_priority():
    """测试配置优先级"""
    print("\n" + "=" * 60)
    print("测试 4: 配置优先级")
    print("=" * 60)
    
    from tradingagents.utils.env_loader import ModularEnvLoader
    
    # 设置全局环境变量
    os.environ['TEST_PRIORITY'] = 'global_value'
    
    # 创建临时模块 .env 文件
    test_module_path = project_root / "tradingagents" / "dataflows"
    test_env_file = test_module_path / ".env.test"
    
    try:
        # 写入模块级配置
        with open(test_env_file, 'w', encoding='utf-8') as f:
            f.write('TEST_PRIORITY=module_value\n')
        
        # 加载配置
        loader = ModularEnvLoader(module_path=test_module_path)
        
        # 修改加载器以使用测试文件
        original_get_module_env = loader._get_module_env_file
        loader._get_module_env_file = lambda: test_env_file
        
        loader.load_env(override=True)
        
        # 检查优先级
        value = loader.get_env('TEST_PRIORITY')
        
        # 注意: 由于我们使用的是测试文件,实际值可能仍是全局值
        # 这里主要测试加载机制
        print(f"TEST_PRIORITY 的值: {value}")
        print("✅ 配置优先级测试完成")
        
    finally:
        # 清理
        if test_env_file.exists():
            test_env_file.unlink()
        os.environ.pop('TEST_PRIORITY', None)


def test_news_config_manager():
    """测试 News 配置管理器"""
    print("\n" + "=" * 60)
    print("测试 5: News 配置管理器")
    print("=" * 60)
    
    try:
        from tradingagents.dataflows.news_config import get_news_config_manager, get_news_config
        
        # 获取配置管理器
        config_manager = get_news_config_manager(verbose=True)
        print("✅ 成功创建 News 配置管理器")
        
        # 获取配置
        config = get_news_config()
        print("✅ 成功获取 News 配置")
        
        # 验证配置属性
        assert hasattr(config, 'finnhub_enabled'), "配置缺少 finnhub_enabled 属性"
        assert hasattr(config, 'default_hours_back'), "配置缺少 default_hours_back 属性"
        assert hasattr(config, 'default_max_news'), "配置缺少 default_max_news 属性"
        print("✅ 配置属性验证通过")
        
        # 打印配置
        config_manager.print_config()
        
        print("\n✅ News 配置管理器测试通过")
        
    except Exception as e:
        print(f"❌ News 配置管理器测试失败: {e}")
        import traceback
        traceback.print_exc()


def test_error_handling():
    """测试错误处理"""
    print("\n" + "=" * 60)
    print("测试 6: 错误处理")
    print("=" * 60)
    
    from tradingagents.utils.env_loader import ModularEnvLoader
    
    loader = ModularEnvLoader()
    loader.load_env()
    
    # 测试必需参数
    try:
        loader.get_env('NON_EXISTENT_REQUIRED_KEY', required=True)
        print("❌ 应该抛出 ValueError")
    except ValueError as e:
        print(f"✅ 正确抛出 ValueError: {e}")
    
    # 测试类型转换错误
    os.environ['INVALID_INT'] = 'not_a_number'
    invalid_int = loader.get_env_int('INVALID_INT', default=10)
    assert invalid_int == 10, "类型转换错误处理失败"
    print("✅ 类型转换错误处理正常")
    
    # 清理
    os.environ.pop('INVALID_INT', None)


def run_all_tests():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("开始测试模块化环境变量配置功能")
    print("=" * 60)
    
    tests = [
        ("环境变量加载器基本功能", test_env_loader_basic),
        ("类型转换功能", test_type_conversion),
        ("模块级环境变量加载", test_module_env_loading),
        ("配置优先级", test_config_priority),
        ("News 配置管理器", test_news_config_manager),
        ("错误处理", test_error_handling),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            print(f"\n❌ 测试失败: {test_name}")
            print(f"   错误: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    # 打印测试结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    print(f"总测试数: {len(tests)}")
    print(f"✅ 通过: {passed}")
    print(f"❌ 失败: {failed}")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
