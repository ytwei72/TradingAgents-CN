#!/usr/bin/env python3
"""
将 logs 目录下的 tradingagents_structured.log* 文件迁移到 MongoDB

该工具会：
1. 遍历 logs 目录下所有 tradingagents_structured.log* 文件（默认包括轮转文件，可使用 --no-rotated 排除）
2. 读取每行的 JSON 格式日志
3. 清理 ANSI 颜色代码
4. 保存到 MongoDB 的 trading_agents_logs 集合
5. 支持去重（基于 timestamp + logger + message 的组合）

使用方法：
    python -m tradingagents.storage.migrations.migrate_logs

    不包含轮转文件，只处理主日志文件
    python -m tradingagents.storage.migrations.migrate_logs --no-rotated

或者直接运行：
    python tradingagents/storage/migrations/migrate_logs.py
"""

import os
import json
import re
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

# 注意：这里不能使用 tradingagents.utils.logging_manager 的 logger
# 原因：迁移工具会将日志写入 MongoDB，而使用 logging_manager 的 logger 会触发
# MongoDBLogHandler，导致迁移工具自己的日志也被写入 MongoDB，形成死循环：
# 迁移工具记录日志 -> MongoDBLogHandler 写入 MongoDB -> 迁移工具读取并迁移 -> 再次记录日志 -> ...
# 因此使用 print 直接输出到控制台，避免死循环
# from tradingagents.utils.logging_manager import get_logger
# logger = get_logger('tools')

try:
    from pymongo import MongoClient
    from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError, BulkWriteError
    MONGODB_AVAILABLE = True
except ImportError:
    MONGODB_AVAILABLE = False
    BulkWriteError = None
    print("❌ pymongo 未安装，无法连接 MongoDB")


class LogsMigrator:
    """将日志文件迁移到 MongoDB"""
    
    def __init__(self, logs_dir: str = "logs", batch_size: int = 1000, include_rotated: bool = True):
        """
        初始化迁移器
        
        Args:
            logs_dir: logs 目录路径
            batch_size: 批量插入的大小（默认1000）
            include_rotated: 是否包含轮转文件（.log.1, .log.2 等），默认 True
        """
        if not MONGODB_AVAILABLE:
            raise ImportError("pymongo is not installed. Please install it with: pip install pymongo")
        
        self.logs_dir = Path(logs_dir)
        self.batch_size = batch_size
        self.include_rotated = include_rotated
        self.client = None
        self.db = None
        self.collection = None
        self.connected = False
        
        # 连接 MongoDB
        self._connect()
    
    def _connect(self):
        """连接到 MongoDB（使用统一的连接管理）"""
        try:
            # 使用统一的连接管理
            from tradingagents.storage.manager import get_mongo_collection
            
            self.collection = get_mongo_collection("trading_agents_logs")
            if self.collection is None:
                print("❌ 统一连接管理不可用，无法连接MongoDB")
                self.connected = False
                raise ConnectionError("统一连接管理不可用")
            
            # 创建索引以提高查询性能
            self._create_indexes()
            
            self.connected = True
            print(f"✅ MongoDB连接成功（使用统一连接管理）: trading_agents_logs")
            
        except Exception as e:
            print(f"❌ MongoDB连接失败: {e}")
            self.connected = False
            raise
    
    def _create_indexes(self):
        """创建索引以提高查询性能"""
        try:
            # 创建复合索引用于去重查询（如果不存在则创建）
            self.collection.create_index([("timestamp", 1), ("logger", 1), ("message", 1)], background=True)
            # 创建时间索引用于时间范围查询
            self.collection.create_index([("timestamp", 1)], background=True)
            # 创建 logger 索引用于按日志器查询
            self.collection.create_index([("logger", 1)], background=True)
            print("✅ 索引创建成功")
        except Exception as e:
            print(f"⚠️ 创建索引失败（可能已存在）: {e}")
    
    def find_log_files(self) -> List[Path]:
        """
        查找所有 tradingagents_structured.log* 文件
        
        Returns:
            所有匹配的日志文件路径列表
        """
        log_files = []
        
        if not self.logs_dir.exists():
            print(f"❌ logs 目录不存在: {self.logs_dir}")
            return log_files
        
        # 查找所有匹配的文件
        # tradingagents_structured.log, tradingagents_structured.log.1, tradingagents_structured.log.2, etc.
        pattern = "tradingagents_structured.log*"
        
        for log_file in self.logs_dir.glob(pattern):
            if log_file.is_file():
                # 如果不包含轮转文件，则跳过轮转文件
                if not self.include_rotated:
                    # 检查是否是轮转文件（包含 .log.数字 格式）
                    if re.search(r'\.log\.\d+$', log_file.name):
                        continue
                log_files.append(log_file)
        
        # 按文件名排序（主文件在前，轮转文件按数字顺序）
        log_files.sort(key=lambda x: self._get_log_file_order(x))
        
        print(f"📁 找到 {len(log_files)} 个日志文件{'（不包含轮转文件）' if not self.include_rotated else ''}")
        for log_file in log_files:
            print(f"   - {log_file.name}")
        
        return log_files
    
    def _get_log_file_order(self, log_file: Path) -> tuple:
        """
        获取日志文件的排序顺序
        
        Args:
            log_file: 日志文件路径
            
        Returns:
            排序元组：(主文件=0, 轮转编号)
        """
        name = log_file.name
        if name == "tradingagents_structured.log":
            return (0, 0)
        
        # 提取轮转编号
        match = re.search(r'\.(\d+)$', name)
        if match:
            return (1, int(match.group(1)))
        
        return (2, 0)
    
    def clean_ansi_codes(self, text: str) -> str:
        """
        清理 ANSI 颜色代码
        
        Args:
            text: 包含 ANSI 代码的文本
            
        Returns:
            清理后的文本
        """
        # ANSI 转义序列的正则表达式
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        return ansi_escape.sub('', text)
    
    def parse_log_line(self, line: str) -> Optional[Dict[str, Any]]:
        """
        解析日志行（JSON格式）
        
        Args:
            line: 日志行内容
            
        Returns:
            解析后的日志字典，如果解析失败则返回 None
        """
        line = line.strip()
        if not line:
            return None
        
        try:
            log_entry = json.loads(line)
            
            # 清理 ANSI 颜色代码（主要在 level 字段中）
            if 'level' in log_entry and isinstance(log_entry['level'], str):
                log_entry['level'] = self.clean_ansi_codes(log_entry['level'])
            
            # 确保 timestamp 字段存在且格式正确
            if 'timestamp' in log_entry:
                try:
                    # 尝试解析 ISO 格式的时间戳
                    if isinstance(log_entry['timestamp'], str):
                        dt = datetime.fromisoformat(log_entry['timestamp'].replace('Z', '+00:00'))
                        log_entry['timestamp'] = dt
                except Exception as e:
                    # 静默忽略时间戳解析失败，不输出到控制台（避免输出过多）
                    pass
            
            # 添加迁移元数据
            log_entry['migrated_at'] = datetime.now()
            
            return log_entry
            
        except json.JSONDecodeError as e:
            # 静默忽略 JSON 解析失败，不输出到控制台（避免输出过多）
            return None
        except Exception as e:
            # 静默忽略解析失败，不输出到控制台（避免输出过多）
            return None
    
    def filter_duplicates(self, log_entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        批量过滤重复的日志条目
        
        Args:
            log_entries: 日志条目列表
            
        Returns:
            过滤后的日志条目列表（不包含重复项）
        """
        if not self.connected or not log_entries:
            return log_entries
        
        try:
            # 构建批量查询条件（使用 $or 查询）
            queries = []
            for entry in log_entries:
                queries.append({
                    "timestamp": entry.get('timestamp'),
                    "logger": entry.get('logger'),
                    "message": entry.get('message')
                })
            
            if not queries:
                return log_entries
            
            # 批量查询已存在的记录
            existing_records = set()
            # 使用 $or 查询，但 MongoDB 对 $or 查询有限制，所以分批查询
            batch_query_size = 100  # 每次查询100条
            for i in range(0, len(queries), batch_query_size):
                batch_queries = queries[i:i + batch_query_size]
                if batch_queries:
                    or_query = {"$or": batch_queries}
                    existing = self.collection.find(
                        or_query,
                        {"timestamp": 1, "logger": 1, "message": 1}
                    )
                    for record in existing:
                        # 创建唯一标识
                        key = (
                            record.get('timestamp'),
                            record.get('logger'),
                            record.get('message')
                        )
                        existing_records.add(key)
            
            # 过滤掉已存在的记录
            filtered_entries = []
            for entry in log_entries:
                key = (
                    entry.get('timestamp'),
                    entry.get('logger'),
                    entry.get('message')
                )
                if key not in existing_records:
                    filtered_entries.append(entry)
            
            return filtered_entries
            
        except Exception as e:
            print(f"⚠️ 批量去重失败，将插入所有记录: {e}")
            return log_entries
    
    def save_batch_to_mongodb(self, log_entries: List[Dict[str, Any]], skip_duplicates: bool = True) -> int:
        """
        批量保存日志条目到 MongoDB
        
        Args:
            log_entries: 日志条目列表
            skip_duplicates: 是否跳过重复条目
            
        Returns:
            成功插入的记录数
        """
        if not self.connected:
            print("❌ MongoDB 未连接")
            return 0
        
        if not log_entries:
            return 0
        
        try:
            # 如果需要去重，先过滤重复项
            if skip_duplicates:
                original_count = len(log_entries)
                log_entries = self.filter_duplicates(log_entries)
                if len(log_entries) < original_count:
                    print(f"  去重: {original_count} -> {len(log_entries)} 条")
            
            if not log_entries:
                return 0
            
            # 批量插入（ordered=False 表示即使部分失败也继续插入）
            result = self.collection.insert_many(log_entries, ordered=False)
            
            return len(result.inserted_ids)
            
        except Exception as e:
            # 处理部分成功的情况（ordered=False 时，即使有错误也会继续插入）
            # BulkWriteError 包含部分成功的结果
            if BulkWriteError and isinstance(e, BulkWriteError):
                # 计算成功插入的数量
                write_errors = e.details.get('writeErrors', [])
                successful_count = len(log_entries) - len(write_errors)
                if successful_count > 0:
                    print(f"⚠️ 批量插入部分失败: {successful_count} 条成功，{len(write_errors)} 条失败")
                else:
                    print(f"❌ 批量插入全部失败: {e}")
                return successful_count
            
            # 其他错误
            print(f"❌ 批量保存到 MongoDB 失败: {e}")
            return 0
    
    def migrate_file(self, log_file: Path, skip_duplicates: bool = True, dry_run: bool = False) -> Dict[str, Any]:
        """
        迁移单个日志文件（使用批量插入）
        
        Args:
            log_file: 日志文件路径
            skip_duplicates: 是否跳过重复条目
            dry_run: 如果为 True，只扫描不实际保存
            
        Returns:
            迁移统计信息
        """
        stats = {
            "file": str(log_file),
            "total_lines": 0,
            "parsed": 0,
            "saved": 0,
            "skipped": 0,
            "failed": 0,
            "errors": []
        }
        
        try:
            print(f"📖 开始处理文件: {log_file.name} (批量大小: {self.batch_size})")
            
            batch = []  # 批量插入缓冲区
            
            with open(log_file, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    stats["total_lines"] += 1
                    
                    # 解析日志行
                    log_entry = self.parse_log_line(line)
                    
                    if log_entry is None:
                        stats["skipped"] += 1
                        continue
                    
                    stats["parsed"] += 1
                    
                    if dry_run:
                        stats["saved"] += 1
                        if line_num % 1000 == 0:
                            print(f"  [DRY RUN] 已处理 {line_num} 行")
                    else:
                        # 添加到批量缓冲区
                        batch.append(log_entry)
                        
                        # 当达到批量大小时，执行批量插入
                        if len(batch) >= self.batch_size:
                            saved_count = self.save_batch_to_mongodb(batch, skip_duplicates=skip_duplicates)
                            stats["saved"] += saved_count
                            
                            # 计算跳过的数量（如果启用去重）
                            if skip_duplicates:
                                skipped_in_batch = len(batch) - saved_count
                                stats["skipped"] += skipped_in_batch
                            
                            batch = []  # 清空缓冲区
                            
                            if line_num % (self.batch_size * 10) == 0:
                                print(f"  已处理 {line_num} 行，已保存 {stats['saved']} 条，跳过 {stats['skipped']} 条")
                
                # 处理剩余的记录
                if not dry_run and batch:
                    saved_count = self.save_batch_to_mongodb(batch, skip_duplicates=skip_duplicates)
                    stats["saved"] += saved_count
                    
                    if skip_duplicates:
                        skipped_in_batch = len(batch) - saved_count
                        stats["skipped"] += skipped_in_batch
            
            print(f"✅ 文件处理完成: {log_file.name}")
            print(f"   总行数: {stats['total_lines']}, 解析成功: {stats['parsed']}, "
                  f"保存: {stats['saved']}, 跳过: {stats['skipped']}, 失败: {stats['failed']}")
            
        except Exception as e:
            stats["failed"] += 1
            error_msg = f"处理文件失败: {str(e)}"
            stats["errors"].append(error_msg)
            print(f"❌ {error_msg}")
        
        return stats
    
    def migrate(self, skip_duplicates: bool = True, dry_run: bool = False) -> Dict[str, Any]:
        """
        执行迁移
        
        Args:
            skip_duplicates: 是否跳过重复条目
            dry_run: 如果为 True，只扫描文件不实际保存
            
        Returns:
            迁移统计信息
        """
        if not self.connected:
            print("❌ MongoDB 未连接，无法执行迁移")
            return {}
        
        stats = {
            "total_files": 0,
            "total_lines": 0,
            "total_parsed": 0,
            "total_saved": 0,
            "total_skipped": 0,
            "total_failed": 0,
            "files": [],
            "errors": []
        }
        
        print(f"🚀 开始迁移 {'(dry run)' if dry_run else ''}")
        
        # 查找所有日志文件
        log_files = self.find_log_files()
        stats["total_files"] = len(log_files)
        
        if stats["total_files"] == 0:
            print("⚠️ 未找到任何日志文件")
            return stats
        
        # 处理每个文件
        for log_file in log_files:
            try:
                file_stats = self.migrate_file(log_file, skip_duplicates=skip_duplicates, dry_run=dry_run)
                stats["files"].append(file_stats)
                
                # 累计统计
                stats["total_lines"] += file_stats["total_lines"]
                stats["total_parsed"] += file_stats["parsed"]
                stats["total_saved"] += file_stats["saved"]
                stats["total_skipped"] += file_stats["skipped"]
                stats["total_failed"] += file_stats["failed"]
                
                if file_stats["errors"]:
                    stats["errors"].extend(file_stats["errors"])
                
            except Exception as e:
                stats["total_failed"] += 1
                error_msg = f"{log_file}: {str(e)}"
                stats["errors"].append(error_msg)
                print(f"❌ 处理文件失败: {error_msg}")
        
        # 输出统计信息
        print("=" * 60)
        print("📊 迁移统计:")
        print(f"  总文件数: {stats['total_files']}")
        print(f"  总行数: {stats['total_lines']}")
        print(f"  解析成功: {stats['total_parsed']}")
        print(f"  保存成功: {stats['total_saved']}")
        print(f"  跳过: {stats['total_skipped']}")
        print(f"  失败: {stats['total_failed']}")
        
        if stats['errors']:
            print(f"  错误详情: {len(stats['errors'])} 个错误")
            for error in stats['errors'][:10]:  # 只显示前10个错误
                print(f"    - {error}")
        
        return stats


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="将日志文件迁移到 MongoDB")
    parser.add_argument(
        "--logs-dir",
        type=str,
        default="logs",
        help="logs 目录路径（默认: logs）"
    )
    parser.add_argument(
        "--no-skip-duplicates",
        action="store_true",
        help="不跳过重复条目（默认会跳过重复）"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只扫描文件，不实际保存到 MongoDB"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=1000,
        help="批量插入的大小（默认: 1000）"
    )
    parser.add_argument(
        "--no-rotated",
        action="store_true",
        help="不包含轮转文件（.log.1, .log.2 等），只处理主日志文件"
    )
    
    args = parser.parse_args()
    
    try:
        migrator = LogsMigrator(
            logs_dir=args.logs_dir,
            batch_size=args.batch_size,
            include_rotated=not args.no_rotated
        )
        stats = migrator.migrate(
            skip_duplicates=not args.no_skip_duplicates,
            dry_run=args.dry_run
        )
        
        if args.dry_run:
            print("ℹ️ 这是 dry run 模式，未实际保存数据")
        
        return 0 if stats.get("total_failed", 0) == 0 else 1
        
    except Exception as e:
        print(f"❌ 迁移失败: {e}")
        return 1


if __name__ == "__main__":
    exit(main())

"""
# 使用默认批量大小（1000），包含所有日志文件（包括轮转文件）
python -m tradingagents.storage.migrations.migrate_logs

# 自定义批量大小（例如5000）
python -m tradingagents.storage.migrations.migrate_logs --batch-size 5000

# 不包含轮转文件，只处理主日志文件
python -m tradingagents.storage.migrations.migrate_logs --no-rotated

# 其他参数保持不变
python -m tradingagents.storage.migrations.migrate_logs --logs-dir logs --dry-run
"""
