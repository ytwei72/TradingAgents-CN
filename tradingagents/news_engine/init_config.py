#!/usr/bin/env python3
"""
News 模块配置初始化脚本

从项目根目录 .env 文件读取 API 密钥,更新 news 模块 .env 文件
保留 .env.example 的所有内容和注释,只替换 API 密钥的值
"""

import os
import sys
import re
from pathlib import Path
from datetime import datetime

# 项目根目录
project_root = Path(__file__).parent.parent.parent
news_module_dir = Path(__file__).parent

# 全局 .env 文件路径
global_env_file = project_root / ".env"
# 模块 .env 文件路径
module_env_file = news_module_dir / ".env"
# 模块 .env.example 文件路径
example_env_file = news_module_dir / ".env.example"


def read_env_value(env_file: Path, key: str) -> str:
    """从 .env 文件读取指定键的值"""
    if not env_file.exists():
        return ""
    
    try:
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith(key + "="):
                    value = line.split("=", 1)[1]
                    # 移除引号
                    value = value.strip('"').strip("'")
                    return value
    except Exception as e:
        print(f"读取 {env_file} 失败: {e}")
    
    return ""


def update_env_line(line: str, api_keys: dict) -> str:
    """
    更新配置行中的 API 密钥
    
    Args:
        line: 配置文件的一行
        api_keys: API 密钥字典
        
    Returns:
        更新后的行
    """
    # 需要更新的键值对
    keys_to_update = {
        "NEWSAPI_KEY": api_keys.get("NEWSAPI_KEY", ""),
        "ALPHA_VANTAGE_API_KEY": api_keys.get("ALPHA_VANTAGE_API_KEY", ""),
        "FINNHUB_API_KEY": api_keys.get("FINNHUB_API_KEY", ""),
        "TUSHARE_TOKEN": api_keys.get("TUSHARE_TOKEN", ""),
        "EODHD_API_TOKEN": api_keys.get("EODHD_API_TOKEN", ""),
    }
    
    # 检查是否是需要更新的键
    for key, value in keys_to_update.items():
        # 匹配注释掉的或未注释的配置行
        # 格式: # KEY=value 或 KEY=value
        pattern = rf'^#?\s*{key}=.*$'
        
        if re.match(pattern, line.strip()):
            if value:
                # 如果有值，更新为实际值（注释掉的行会从全局继承）
                return f"# {key}={value}\n"
            else:
                # 如果没有值，保持示例格式
                return f"# {key}=your_{key.lower()}_here\n"
    
    # 不需要更新的值，保持原样
    return line


def create_news_env():
    """创建 news 模块的 .env 文件"""
    print("=" * 60)
    print("News 模块配置初始化")
    print("=" * 60)
    
    # 检查 .env.example 文件
    if not example_env_file.exists():
        print(f"\n错误: .env.example 文件不存在: {example_env_file}")
        return False
    
    print(f"\n找到 .env.example 文件: {example_env_file}")
    
    # 检查全局 .env 文件
    if not global_env_file.exists():
        print(f"\n⚠️  警告: 全局 .env 文件不存在: {global_env_file}")
        print(f"   将使用 .env.example 的默认配置生效")
    else:
        print(f"\n找到全局 .env 文件: {global_env_file}")
    
    # 读取全局配置中的 API 密钥
    print(f"\n📖 读取全局配置中的 API 密钥...")
    
    api_keys = {
        "NEWSAPI_KEY": read_env_value(global_env_file, "NEWSAPI_KEY"),
        "ALPHA_VANTAGE_API_KEY": read_env_value(global_env_file, "ALPHA_VANTAGE_API_KEY"),
        "FINNHUB_API_KEY": read_env_value(global_env_file, "FINNHUB_API_KEY"),
        "TUSHARE_TOKEN": read_env_value(global_env_file, "TUSHARE_TOKEN"),
        "EODHD_API_TOKEN": read_env_value(global_env_file, "EODHD_API_TOKEN"),
    }
    
    # 显示读取的 API 密钥
    print(f"\n📋 API 密钥状态:")
    for key, value in api_keys.items():
        if value:
            display_value = value[:10] + "..." if len(value) > 10 else value
            print(f"  ✅ {key}: {display_value}")
        else:
            print(f"  ⚠️  {key}: 未配置")
    
    # 读取 .env.example 文件内容
    print(f"\n📝 读取 .env.example 文件...")
    
    try:
        with open(example_env_file, 'r', encoding='utf-8') as f:
            example_lines = f.readlines()
        
        print(f"读取到 {len(example_lines)} 行配置")
        
    except Exception as e:
        print(f"\n读取 .env.example 文件失败: {e}")
        return False
    
    # 更新 API 密钥
    print(f"\n🔧 更新 API 密钥...")
    
    updated_lines = []
    updated_count = 0
    
    for line in example_lines:
        updated_line = update_env_line(line, api_keys)
        updated_lines.append(updated_line)
        
        # 检查是否更新了
        if updated_line != line and not line.startswith("#"):
            updated_count += 1
    
    print(f"更新了 {updated_count} 个配置项")
    
    # 写入模块 .env 文件
    print(f"\n💾 写入模块 .env 文件...")
    
    try:
        with open(module_env_file, 'w', encoding='utf-8') as f:
            f.writelines(updated_lines)
        
        print(f"成功创建模块 .env 文件: {module_env_file}")
        
        # 显示配置摘要
        print(f"\n📊 配置摘要:")
        print(f"  📄 保留 .env.example 的所有内容和注释")
        print(f"  🔑 从全局 .env 读取 {sum(1 for v in api_keys.values() if v)} 个 API 密钥")
        print(f"  ✏️  更新了 {updated_count} 个配置项")
        
        print(f"\n🔧 API 密钥配置:")
        configured_keys = [k for k, v in api_keys.items() if v]
        if configured_keys:
            for key in configured_keys:
                print(f"  ✅ {key}")
        else:
            print(f"  ⚠️  未配置任何 API 密钥")
        
        print(f"\n💡 提示:")
        print(f"  1. API 密钥已从全局 .env 继承(注释形式)")
        print(f"  2. 模块会自动使用全局 .env 中的 API 密钥")
        print(f"  3. 如需覆盖全局配置,请取消注释并修改相应配置项")
        print(f"  4. 所有其他配置保持 .env.example 的默认配置")
        print(f"  5. 运行测试验证配置: python tradingagents/news/test_news.py")
        
        return True
        
    except Exception as e:
        print(f"\n写入模块 .env 文件失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print()
    
    # 检查是否已存在模块 .env 文件
    if module_env_file.exists():
        print(f"⚠️  模块 .env 文件已存在: {module_env_file}")
        response = input("是否覆盖? (y/N): ").strip().lower()
        
        if response not in ['y', 'yes']:
            print("已取消操作")
            return
    
    # 创建配置文件
    success = create_news_env()
    
    if success:
        print(f"\n" + "=" * 60)
        print("配置初始化完成")
        print("=" * 60)
    else:
        print(f"\n" + "=" * 60)
        print("配置初始化失败")
        print("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()
