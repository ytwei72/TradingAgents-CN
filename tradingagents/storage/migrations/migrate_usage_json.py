#!/usr/bin/env python3
"""
将 config/usage.json 迁移到 MongoDB 的 model_usages 集合

该工具会：
1. 读取 config/usage.json 文件
2. 将数据迁移到 MongoDB 的 model_usages 集合
3. 支持增量迁移（跳过已存在的记录）
4. 迁移完成后可以选择是否备份原文件
"""

import os
import json
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

# 导入日志模块
from tradingagents.utils.logging_manager import get_logger
logger = get_logger('tools')

# 导入配置管理器
from tradingagents.storage.mongodb.model_usage_manager import UsageRecord
from tradingagents.storage.mongodb.model_usage_manager import ModelUsageManager


class UsageJsonMigrator:
    """将 usage.json 迁移到 MongoDB"""
    
    def __init__(self, usage_json_path: str = "config/usage.json"):
        """
        初始化迁移器
        
        Args:
            usage_json_path: usage.json 文件路径
        """
        self.usage_json_path = Path(usage_json_path)
        self.usage_manager = None
        
        # 连接 MongoDB
        self._connect()
    
    def _connect(self):
        """连接到 MongoDB"""
        try:
            self.usage_manager = ModelUsageManager()
            if not self.usage_manager.is_connected():
                logger.error("❌ MongoDB 连接失败，无法进行迁移")
                raise ConnectionError("MongoDB 连接失败")
        except Exception as e:
            logger.error(f"❌ 初始化 MongoDB 管理器失败: {e}")
            raise
    
    def load_usage_json(self) -> List[Dict[str, Any]]:
        """
        从 JSON 文件加载使用记录
        
        Returns:
            使用记录列表
        """
        if not self.usage_json_path.exists():
            logger.warning(f"⚠️ 文件不存在: {self.usage_json_path}")
            return []
        
        try:
            with open(self.usage_json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if not isinstance(data, list):
                logger.error(f"❌ JSON 文件格式错误：期望列表，得到 {type(data)}")
                return []
            
            logger.info(f"✅ 从 JSON 文件加载了 {len(data)} 条记录")
            return data
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON 解析错误: {e}")
            return []
        except Exception as e:
            logger.error(f"❌ 读取 JSON 文件失败: {e}")
            return []
    
    def check_existing_records(self, records: List[Dict[str, Any]]) -> Dict[str, bool]:
        """
        检查哪些记录已存在于数据库中
        
        Args:
            records: 使用记录列表
            
        Returns:
            记录ID到是否存在的映射（使用 timestamp + session_id 作为唯一标识）
        """
        if not self.usage_manager.is_connected():
            return {}
        
        existing_map = {}
        
        try:
            # 获取所有已存在的记录（使用 timestamp 和 session_id 作为唯一标识）
            existing_records = self.usage_manager.query_usage_records(limit=100000)
            
            # 构建已存在记录的集合
            existing_set = set()
            for record in existing_records:
                key = f"{record.timestamp}_{record.session_id}"
                existing_set.add(key)
            
            # 检查每条记录是否已存在
            for record in records:
                key = f"{record.get('timestamp')}_{record.get('session_id')}"
                existing_map[key] = key in existing_set
            
            logger.info(f"✅ 检查完成：{sum(existing_map.values())} 条记录已存在，{len(existing_map) - sum(existing_map.values())} 条新记录")
            
        except Exception as e:
            logger.error(f"❌ 检查已存在记录失败: {e}")
        
        return existing_map
    
    def migrate(self, skip_existing: bool = True, backup: bool = True) -> Dict[str, Any]:
        """
        执行迁移
        
        Args:
            skip_existing: 是否跳过已存在的记录
            backup: 是否备份原文件
            
        Returns:
            迁移结果统计
        """
        if not self.usage_manager.is_connected():
            return {
                'success': False,
                'error': 'MongoDB 未连接'
            }
        
        # 加载 JSON 数据
        json_records = self.load_usage_json()
        
        if not json_records:
            return {
                'success': False,
                'error': 'JSON 文件中没有数据'
            }
        
        # 检查已存在的记录
        existing_map = {}
        if skip_existing:
            existing_map = self.check_existing_records(json_records)
        
        # 过滤需要迁移的记录
        records_to_migrate = []
        for record in json_records:
            key = f"{record.get('timestamp')}_{record.get('session_id')}"
            if not skip_existing or not existing_map.get(key, False):
                try:
                    # 转换为 UsageRecord 对象
                    usage_record = UsageRecord(**record)
                    records_to_migrate.append(usage_record)
                except Exception as e:
                    logger.warning(f"⚠️ 跳过无效记录: {e}, 记录: {record}")
                    continue
        
        if not records_to_migrate:
            logger.info("✅ 所有记录已存在于数据库中，无需迁移")
            return {
                'success': True,
                'total': len(json_records),
                'migrated': 0,
                'skipped': len(json_records),
                'message': '所有记录已存在'
            }
        
        # 执行批量插入
        logger.info(f"📤 开始迁移 {len(records_to_migrate)} 条记录到 MongoDB...")
        inserted_count = self.usage_manager.insert_many_usage_records(records_to_migrate)
        
        # 备份原文件
        # if backup and inserted_count > 0:
        #     self._backup_file()
        
        result = {
            'success': True,
            'total': len(json_records),
            'migrated': inserted_count,
            'skipped': len(json_records) - inserted_count,
            'message': f'成功迁移 {inserted_count} 条记录'
        }
        
        logger.info(f"✅ 迁移完成: {result}")
        return result
    
    def _backup_file(self):
        """备份原文件"""
        try:
            backup_path = self.usage_json_path.with_suffix(f'.json.backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}')
            
            import shutil
            shutil.copy2(self.usage_json_path, backup_path)
            
            logger.info(f"✅ 原文件已备份到: {backup_path}")
            
        except Exception as e:
            logger.warning(f"⚠️ 备份文件失败: {e}")
    
    def verify_migration(self) -> Dict[str, Any]:
        """
        验证迁移结果
        
        Returns:
            验证结果统计
        """
        if not self.usage_manager.is_connected():
            return {
                'success': False,
                'error': 'MongoDB 未连接'
            }
        
        # 加载 JSON 数据
        json_records = self.load_usage_json()
        
        if not json_records:
            return {
                'success': False,
                'error': 'JSON 文件中没有数据'
            }
        
        # 从数据库查询所有记录
        db_records = self.usage_manager.query_usage_records(limit=100000)
        
        # 构建数据库记录的集合
        db_set = set()
        for record in db_records:
            key = f"{record.timestamp}_{record.session_id}"
            db_set.add(key)
        
        # 检查 JSON 记录是否都在数据库中
        json_set = set()
        for record in json_records:
            key = f"{record.get('timestamp')}_{record.get('session_id')}"
            json_set.add(key)
        
        missing_in_db = json_set - db_set
        extra_in_db = db_set - json_set
        
        result = {
            'success': len(missing_in_db) == 0,
            'json_count': len(json_records),
            'db_count': len(db_records),
            'missing_in_db': len(missing_in_db),
            'extra_in_db': len(extra_in_db),
            'match_rate': f"{(len(json_set & db_set) / len(json_set) * 100):.2f}%" if json_set else "0%"
        }
        
        if missing_in_db:
            logger.warning(f"⚠️ 有 {len(missing_in_db)} 条 JSON 记录未在数据库中找到")
        if extra_in_db:
            logger.info(f"ℹ️ 数据库中有 {len(extra_in_db)} 条额外记录（可能是新添加的）")
        
        logger.info(f"✅ 验证完成: {result}")
        return result


def main():
    """主函数"""
    import argparse
    # default_usage_file = 'config/usage.json'
    default_usage_file = 'config/usage-1204.json'
    
    parser = argparse.ArgumentParser(description='将 usage.json 迁移到 MongoDB')
    parser.add_argument('--json-path', type=str, default=default_usage_file,
                       help=f'usage.json 文件路径（默认: {default_usage_file}）')
    parser.add_argument('--no-skip-existing', action='store_true',
                       help='不跳过已存在的记录（默认跳过）')
    parser.add_argument('--no-backup', action='store_true',
                       help='不备份原文件（默认备份）')
    parser.add_argument('--verify', action='store_true',
                       help='仅验证迁移结果，不执行迁移')
    
    args = parser.parse_args()
    
    try:
        migrator = UsageJsonMigrator(args.json_path)
        
        if args.verify:
            # 仅验证
            result = migrator.verify_migration()
            if result['success']:
                print(f"✅ 验证通过: 所有记录都已迁移")
            else:
                print(f"❌ 验证失败: {result}")
        else:
            # 执行迁移
            result = migrator.migrate(
                skip_existing=not args.no_skip_existing,
                backup=not args.no_backup
            )
            
            if result['success']:
                print(f"✅ 迁移成功: {result['message']}")
                print(f"   总计: {result['total']} 条")
                print(f"   已迁移: {result['migrated']} 条")
                print(f"   已跳过: {result['skipped']} 条")
            else:
                print(f"❌ 迁移失败: {result.get('error', '未知错误')}")
        
    except Exception as e:
        logger.error(f"❌ 迁移过程出错: {e}", exc_info=True)
        print(f"❌ 迁移失败: {e}")


if __name__ == '__main__':
    main()

