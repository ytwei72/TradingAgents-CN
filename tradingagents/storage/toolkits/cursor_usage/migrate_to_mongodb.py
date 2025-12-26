#!/usr/bin/env python3
"""
将 cursor_usage 目录下的 CSV 文件迁移到 MongoDB

该工具会：
1. 遍历 cursor_usage 目录下所有 {account_name}-usage-events-{date}.csv 文件
2. 从文件名中提取 account_name 和 date
3. 读取 CSV 文件内容
4. 为每条记录添加 account_name 字段
5. 保存到 MongoDB 的 cursor_usages 集合
6. 支持去重（基于 account_name + Date + Model + Kind 的组合）

使用方法：
    python -m tradingagents.storage.toolkits.cursor_usage.migrate_to_mongodb

或者直接运行：
    python tradingagents/storage/toolkits/cursor_usage/migrate_to_mongodb.py
"""

import re
import pandas as pd
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

try:
    from pymongo.errors import BulkWriteError
    MONGODB_AVAILABLE = True
except ImportError:
    MONGODB_AVAILABLE = False
    BulkWriteError = None
    print("❌ pymongo 未安装，无法连接 MongoDB")


class CursorUsageMigrator:
    """将 Cursor Usage CSV 文件迁移到 MongoDB"""
    
    def __init__(self, data_dir: Optional[Path] = None, batch_size: int = 1000):
        """
        初始化迁移器
        
        Args:
            data_dir: CSV 文件所在目录，默认为当前模块目录
            batch_size: 批量插入的大小（默认1000）
        """
        if not MONGODB_AVAILABLE:
            raise ImportError("pymongo is not installed. Please install it with: pip install pymongo")
        
        if data_dir is None:
            data_dir = Path(__file__).parent
        
        self.data_dir = Path(data_dir)
        self.batch_size = batch_size
        
        # 使用 CursorUsageManager
        from tradingagents.storage.mongodb.cursor_usage_manager import CursorUsageManager
        self.manager = CursorUsageManager()
        
        if not self.manager.is_connected():
            raise ConnectionError("无法连接到 MongoDB")
        
        print(f"✅ MongoDB连接成功: cursor_usage")
    
    def _parse_filename(self, filename: str) -> Optional[Dict[str, str]]:
        """
        解析文件名，提取 account_name 和 date
        
        Args:
            filename: 文件名，格式为 {account_name}-usage-events-{date}.csv
            
        Returns:
            包含 account_name 和 date 的字典，如果解析失败返回 None
        """
        pattern = re.compile(r'^(.+?)-usage-events-(\d{4}-\d{2}-\d{2})\.csv$')
        match = pattern.match(filename)
        
        if match:
            return {
                'account_name': match.group(1),
                'date': match.group(2)
            }
        return None
    
    def _find_csv_files(self) -> List[Path]:
        """
        查找所有符合格式的 CSV 文件
        
        Returns:
            CSV 文件路径列表
        """
        csv_files = []
        pattern = re.compile(r'^.+?-usage-events-\d{4}-\d{2}-\d{2}\.csv$')
        
        if not self.data_dir.exists():
            print(f"⚠️ 数据目录不存在: {self.data_dir}")
            return csv_files
        
        for file_path in self.data_dir.glob('*-usage-events-*.csv'):
            if pattern.match(file_path.name):
                csv_files.append(file_path)
        
        # 按文件名排序
        csv_files.sort(key=lambda x: x.name)
        
        print(f"📁 找到 {len(csv_files)} 个 CSV 文件")
        return csv_files
    
    def _csv_to_documents(self, csv_file: Path, account_name: str) -> List[Dict[str, Any]]:
        """
        将 CSV 文件转换为 MongoDB 文档列表
        
        Args:
            csv_file: CSV 文件路径
            account_name: 账户名称
            
        Returns:
            MongoDB 文档列表
        """
        documents = []
        
        try:
            df = pd.read_csv(csv_file)
            
            # 转换 Date 列为 datetime
            if 'Date' in df.columns:
                df['Date'] = pd.to_datetime(df['Date'])
            
            # 转换数值列
            numeric_columns = [
                'Input (w/ Cache Write)', 'Input (w/o Cache Write)', 
                'Cache Read', 'Output Tokens', 'Total Tokens', 'Cost'
            ]
            for col in numeric_columns:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
            # 将 DataFrame 转换为字典列表
            for _, row in df.iterrows():
                doc = row.to_dict()
                
                # 添加 account_name 字段
                doc['account_name'] = account_name
                
                # 将 Date 转换为 ISO 格式字符串（MongoDB 存储）
                if 'Date' in doc and pd.notna(doc['Date']):
                    if isinstance(doc['Date'], pd.Timestamp):
                        doc['Date'] = doc['Date'].to_pydatetime()
                
                # 确保数值类型正确
                for col in numeric_columns:
                    if col in doc:
                        doc[col] = float(doc[col]) if pd.notna(doc[col]) else 0.0
                
                documents.append(doc)
            
        except Exception as e:
            print(f"❌ 读取 CSV 文件失败 ({csv_file.name}): {e}")
            raise
        
        return documents
    
    
    def migrate_file(self, csv_file: Path, skip_duplicates: bool = True, dry_run: bool = False) -> Dict[str, Any]:
        """
        迁移单个 CSV 文件
        
        Args:
            csv_file: CSV 文件路径
            skip_duplicates: 是否跳过重复条目
            dry_run: 如果为 True，只扫描不实际保存
            
        Returns:
            迁移统计信息
        """
        stats = {
            "file": str(csv_file),
            "account_name": None,
            "date": None,
            "total_records": 0,
            "saved": 0,
            "skipped": 0,
            "failed": 0,
            "errors": []
        }
        
        try:
            # 解析文件名
            file_info = self._parse_filename(csv_file.name)
            if not file_info:
                stats["errors"].append(f"文件名格式不正确: {csv_file.name}")
                print(f"⚠️ 跳过文件（格式不正确）: {csv_file.name}")
                return stats
            
            stats["account_name"] = file_info['account_name']
            stats["date"] = file_info['date']
            
            print(f"📖 开始处理文件: {csv_file.name} (账户: {file_info['account_name']}, 日期: {file_info['date']})")
            
            # 读取 CSV 文件
            documents = self._csv_to_documents(csv_file, file_info['account_name'])
            stats["total_records"] = len(documents)
            
            if dry_run:
                stats["saved"] = len(documents)
                print(f"  [DRY RUN] 将插入 {len(documents)} 条记录")
            else:
                # 批量插入
                batch = []
                for i, doc in enumerate(documents):
                    batch.append(doc)
                    
                    # 当达到批量大小时，执行批量插入
                    if len(batch) >= self.batch_size:
                        saved_count = self.manager.insert_many(batch, skip_duplicates=skip_duplicates)
                        stats["saved"] += saved_count
                        stats["skipped"] += len(batch) - saved_count
                        batch = []
                        
                        if (i + 1) % (self.batch_size * 10) == 0:
                            print(f"  已处理 {i + 1}/{len(documents)} 条记录，已保存 {stats['saved']} 条")
                
                # 处理剩余的记录
                if batch:
                    saved_count = self.manager.insert_many(batch, skip_duplicates=skip_duplicates)
                    stats["saved"] += saved_count
                    stats["skipped"] += len(batch) - saved_count
                
                print(f"✅ 文件处理完成: 总计 {stats['total_records']} 条，已保存 {stats['saved']} 条，跳过 {stats['skipped']} 条")
            
        except Exception as e:
            stats["failed"] = stats["total_records"]
            stats["errors"].append(str(e))
            print(f"❌ 处理文件失败 ({csv_file.name}): {e}")
        
        return stats
    
    def migrate_all(self, skip_duplicates: bool = True, dry_run: bool = False) -> Dict[str, Any]:
        """
        迁移所有 CSV 文件
        
        Args:
            skip_duplicates: 是否跳过重复条目
            dry_run: 如果为 True，只扫描不实际保存
            
        Returns:
            总体迁移统计信息
        """
        if not self.manager.is_connected():
            print("❌ MongoDB 未连接")
            return {}
        
        csv_files = self._find_csv_files()
        
        if not csv_files:
            print("⚠️ 没有找到符合格式的 CSV 文件")
            return {}
        
        overall_stats = {
            "total_files": len(csv_files),
            "processed_files": 0,
            "total_records": 0,
            "total_saved": 0,
            "total_skipped": 0,
            "total_failed": 0,
            "file_stats": []
        }
        
        print(f"\n🚀 开始迁移 {len(csv_files)} 个文件...")
        if dry_run:
            print("⚠️  DRY RUN 模式：只扫描，不实际保存\n")
        
        for i, csv_file in enumerate(csv_files, 1):
            print(f"\n[{i}/{len(csv_files)}] ", end="")
            file_stats = self.migrate_file(csv_file, skip_duplicates=skip_duplicates, dry_run=dry_run)
            
            overall_stats["processed_files"] += 1
            overall_stats["total_records"] += file_stats["total_records"]
            overall_stats["total_saved"] += file_stats["saved"]
            overall_stats["total_skipped"] += file_stats["skipped"]
            overall_stats["total_failed"] += file_stats["failed"]
            overall_stats["file_stats"].append(file_stats)
        
        print(f"\n{'='*60}")
        print(f"📊 迁移完成统计:")
        print(f"  总文件数: {overall_stats['total_files']}")
        print(f"  已处理: {overall_stats['processed_files']}")
        print(f"  总记录数: {overall_stats['total_records']}")
        print(f"  已保存: {overall_stats['total_saved']}")
        print(f"  已跳过: {overall_stats['total_skipped']}")
        print(f"  失败: {overall_stats['total_failed']}")
        print(f"{'='*60}\n")
        
        return overall_stats


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='将 Cursor Usage CSV 文件迁移到 MongoDB')
    parser.add_argument('--data-dir', type=str, help='CSV 文件所在目录（默认：当前模块目录）')
    parser.add_argument('--batch-size', type=int, default=1000, help='批量插入大小（默认：1000）')
    parser.add_argument('--no-skip-duplicates', action='store_true', help='不跳过重复记录')
    parser.add_argument('--dry-run', action='store_true', help='只扫描不实际保存')
    
    args = parser.parse_args()
    
    try:
        data_dir = Path(args.data_dir) if args.data_dir else None
        migrator = CursorUsageMigrator(data_dir=data_dir, batch_size=args.batch_size)
        
        migrator.migrate_all(
            skip_duplicates=not args.no_skip_duplicates,
            dry_run=args.dry_run
        )
        
    except KeyboardInterrupt:
        print("\n\n⚠️ 用户中断操作")
    except Exception as e:
        print(f"\n❌ 迁移失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

