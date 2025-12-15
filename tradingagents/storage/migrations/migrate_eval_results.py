#!/usr/bin/env python3
"""
将 eval_results 目录中的历史步骤数据迁移到 MongoDB

该工具会：
1. 遍历 eval_results 目录下所有股票的日期目录
2. 读取每个日期的 all_steps.json 文件
3. 提取最后一个 step 的数据
4. 保存到 MongoDB 的 analysis_steps_status 集合
5. 每只股票的每天只保存一条记录（使用 upsert）
"""

import os
import json
import uuid
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

# 导入日志模块
from tradingagents.utils.logging_manager import get_logger
logger = get_logger('tools')

try:
    from pymongo import MongoClient
    from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
    MONGODB_AVAILABLE = True
except ImportError:
    MONGODB_AVAILABLE = False
    logger.error("❌ pymongo 未安装，无法连接 MongoDB")


class EvalResultsMigrator:
    """将 eval_results 数据迁移到 MongoDB"""
    
    def __init__(self, eval_results_dir: str = "eval_results"):
        """
        初始化迁移器
        
        Args:
            eval_results_dir: eval_results 目录路径
        """
        if not MONGODB_AVAILABLE:
            raise ImportError("pymongo is not installed. Please install it with: pip install pymongo")
        
        self.eval_results_dir = Path(eval_results_dir)
        self.client = None
        self.db = None
        self.collection = None
        self.connected = False
        
        # 连接 MongoDB
        self._connect()
    
    def _connect(self):
        """连接到 MongoDB（只使用统一的连接管理）"""
        try:
            # 只使用统一的连接管理
            from tradingagents.storage.manager import get_mongo_collection
            
            self.collection = get_mongo_collection("analysis_steps_status")
            if not self.collection:
                logger.error("❌ 统一连接管理不可用，无法连接MongoDB")
                self.connected = False
                raise ConnectionError("统一连接管理不可用")
            
            self.connected = True
            logger.info(f"✅ MongoDB连接成功（使用统一连接管理）: analysis_steps_status")
            
        except Exception as e:
            logger.error(f"❌ MongoDB连接失败: {e}")
            self.connected = False
            raise
    
    def find_all_steps_files(self) -> List[Path]:
        """
        查找所有 all_steps.json 文件
        
        Returns:
            所有 all_steps.json 文件的路径列表
        """
        all_steps_files = []
        
        if not self.eval_results_dir.exists():
            logger.error(f"❌ eval_results 目录不存在: {self.eval_results_dir}")
            return all_steps_files
        
        # 遍历所有股票目录
        for ticker_dir in self.eval_results_dir.iterdir():
            if not ticker_dir.is_dir():
                continue
            
            ticker = ticker_dir.name
            step_outputs_dir = ticker_dir / "TradingAgentsStrategy_logs" / "step_outputs"
            
            if not step_outputs_dir.exists():
                logger.debug(f"⚠️ 跳过 {ticker}：step_outputs 目录不存在")
                continue
            
            # 遍历所有日期目录
            for date_dir in step_outputs_dir.iterdir():
                if not date_dir.is_dir():
                    continue
                
                all_steps_file = date_dir / "all_steps.json"
                if all_steps_file.exists():
                    all_steps_files.append(all_steps_file)
        
        logger.info(f"📁 找到 {len(all_steps_files)} 个 all_steps.json 文件")
        return all_steps_files
    
    def extract_last_step(self, all_steps_file: Path) -> Optional[Dict[str, Any]]:
        """
        从 all_steps.json 文件中提取最后一个 step 的数据
        
        Args:
            all_steps_file: all_steps.json 文件路径
            
        Returns:
            最后一个 step 的数据字典，如果文件为空或无效则返回 None
        """
        try:
            with open(all_steps_file, 'r', encoding='utf-8') as f:
                all_steps = json.load(f)
            
            if not all_steps or not isinstance(all_steps, list):
                logger.warning(f"⚠️ {all_steps_file} 文件格式无效：不是列表")
                return None
            
            if len(all_steps) == 0:
                logger.warning(f"⚠️ {all_steps_file} 文件为空")
                return None
            
            # 找到 step_number 最大的 step
            last_step = max(all_steps, key=lambda x: x.get('step_number', 0))
            
            return last_step
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ 解析 JSON 文件失败 {all_steps_file}: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ 读取文件失败 {all_steps_file}: {e}")
            return None
    
    def save_to_mongodb(self, step_data: Dict[str, Any]) -> bool:
        """
        将 step 数据保存到 MongoDB
        
        Args:
            step_data: step 数据字典
            
        Returns:
            保存成功返回 True，否则返回 False
        """
        if not self.connected:
            logger.error("❌ MongoDB 未连接")
            return False
        
        try:
            # 提取关键字段
            ticker = step_data.get('company_of_interest', '')
            trade_date = step_data.get('trade_date', '')
            
            if not ticker or not trade_date:
                logger.warning(f"⚠️ 跳过无效数据：ticker={ticker}, trade_date={trade_date}")
                return False
            
            # 规范化 trade_date 格式（确保是 YYYY-MM-DD 格式）
            try:
                # 尝试解析日期
                if len(trade_date) == 8 and '-' not in trade_date:
                    # 格式：YYYYMMDD
                    trade_date = f"{trade_date[:4]}-{trade_date[4:6]}-{trade_date[6:8]}"
                elif len(trade_date) == 10 and '-' in trade_date:
                    # 格式：YYYY-MM-DD，保持不变
                    pass
                else:
                    logger.warning(f"⚠️ 日期格式异常：{trade_date}")
            except Exception as e:
                logger.warning(f"⚠️ 日期解析失败：{trade_date}, {e}")
            
            # 创建文档，直接使用 step_data 的所有字段
            document = step_data.copy()
            
            # 更新 trade_date（使用规范化后的日期）
            document['trade_date'] = trade_date
            
            # 添加或生成 analysis_id
            if 'analysis_id' not in document or not document.get('analysis_id'):
                document['analysis_id'] = str(uuid.uuid4())
            
            # 不设置 _id，让 MongoDB 自动生成 ObjectId
            
            # 使用 upsert 操作，基于 ticker 和 trade_date 的唯一性
            result = self.collection.update_one(
                {
                    "company_of_interest": ticker,
                    "trade_date": trade_date
                },
                {
                    "$set": document
                },
                upsert=True
            )
            
            if result.upserted_id:
                logger.info(f"✅ 插入新记录: {ticker} - {trade_date} (step {document.get('step_number', 0)}, analysis_id: {document['analysis_id']})")
            else:
                logger.info(f"🔄 更新已存在记录: {ticker} - {trade_date} (step {document.get('step_number', 0)}, analysis_id: {document['analysis_id']})")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 保存到 MongoDB 失败: {e}")
            return False
    
    def migrate(self, dry_run: bool = False) -> Dict[str, Any]:
        """
        执行迁移
        
        Args:
            dry_run: 如果为 True，只扫描文件不实际保存
            
        Returns:
            迁移统计信息
        """
        if not self.connected:
            logger.error("❌ MongoDB 未连接，无法执行迁移")
            return {}
        
        stats = {
            "total_files": 0,
            "successful": 0,
            "failed": 0,
            "skipped": 0,
            "errors": []
        }
        
        logger.info(f"🚀 开始迁移 {'(dry run)' if dry_run else ''}")
        
        # 查找所有 all_steps.json 文件
        all_steps_files = self.find_all_steps_files()
        stats["total_files"] = len(all_steps_files)
        
        if stats["total_files"] == 0:
            logger.warning("⚠️ 未找到任何 all_steps.json 文件")
            return stats
        
        # 处理每个文件
        for all_steps_file in all_steps_files:
            try:
                # 提取最后一个 step
                last_step = self.extract_last_step(all_steps_file)
                
                if last_step is None:
                    stats["skipped"] += 1
                    continue
                
                if dry_run:
                    ticker = last_step.get('company_of_interest', '')
                    trade_date = last_step.get('trade_date', '')
                    step_number = last_step.get('step_number', 0)
                    logger.info(f"📋 [DRY RUN] 将迁移: {ticker} - {trade_date} (step {step_number})")
                    stats["successful"] += 1
                else:
                    # 保存到 MongoDB
                    if self.save_to_mongodb(last_step):
                        stats["successful"] += 1
                    else:
                        stats["failed"] += 1
                        stats["errors"].append(f"{all_steps_file}: 保存失败")
                
            except Exception as e:
                stats["failed"] += 1
                error_msg = f"{all_steps_file}: {str(e)}"
                stats["errors"].append(error_msg)
                logger.error(f"❌ 处理文件失败: {error_msg}")
        
        # 输出统计信息
        logger.info("=" * 60)
        logger.info("📊 迁移统计:")
        logger.info(f"  总文件数: {stats['total_files']}")
        logger.info(f"  成功: {stats['successful']}")
        logger.info(f"  失败: {stats['failed']}")
        logger.info(f"  跳过: {stats['skipped']}")
        if stats['errors']:
            logger.warning(f"  错误详情: {len(stats['errors'])} 个错误")
            for error in stats['errors'][:10]:  # 只显示前10个错误
                logger.warning(f"    - {error}")
        
        return stats


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="将 eval_results 数据迁移到 MongoDB")
    parser.add_argument(
        "--eval-results-dir",
        type=str,
        default="eval_results",
        help="eval_results 目录路径（默认: eval_results）"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只扫描文件，不实际保存到 MongoDB"
    )
    
    args = parser.parse_args()
    
    try:
        migrator = EvalResultsMigrator(eval_results_dir=args.eval_results_dir)
        stats = migrator.migrate(dry_run=args.dry_run)
        
        if args.dry_run:
            logger.info("ℹ️ 这是 dry run 模式，未实际保存数据")
        
        return 0 if stats.get("failed", 0) == 0 else 1
        
    except Exception as e:
        logger.error(f"❌ 迁移失败: {e}")
        return 1


if __name__ == "__main__":
    exit(main())

