#!/usr/bin/env python3
"""
任务状态机数据迁移工具：补充company_name字段

为现有数据库中的props类文档补充company_name字段（根据stock_symbol查询）

使用方法：
    python -m tradingagents.storage.migrations.supplement_company_name

或者直接运行：
    python tradingagents/storage/migrations/supplement_company_name.py
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from tradingagents.storage.mongodb.tasks_state_machine_helper import tasks_state_machine_helper
from tradingagents.storage.mongodb.stock_dict_manager import stock_dict_manager
from tradingagents.utils.logging_manager import get_logger

logger = get_logger("supplement_company_name")


def supplement_company_name_for_task(task_id: str, props_data: dict) -> bool:
    """
    为单个任务的props数据补充company_name
    
    Args:
        task_id: 任务ID
        props_data: props数据字典
        
    Returns:
        bool: 是否补充成功
    """
    try:
        params = props_data.get('params', {})
        
        # 检查是否已有company_name
        if params.get('company_name'):
            logger.debug(f"任务 {task_id} 已有company_name: {params.get('company_name')}")
            return True
        
        # 获取stock_symbol
        stock_symbol = params.get('stock_symbol')
        if not stock_symbol:
            logger.debug(f"任务 {task_id} 没有stock_symbol，跳过")
            return True  # 没有stock_symbol，视为成功（无需补充）
        
        # 查询公司名称
        if not stock_dict_manager or not stock_dict_manager.connected:
            logger.warning(f"stock_dict_manager未连接，无法获取公司名称")
            return False
        
        company_name = stock_dict_manager.get_company_name(stock_symbol)
        if not company_name:
            logger.warning(f"任务 {task_id} 的股票代码 {stock_symbol} 未找到公司名称")
            return True  # 未找到公司名称，视为成功（可能不是A股）
        
        # 更新params中的company_name
        params['company_name'] = company_name
        
        # 更新props_data
        props_data['params'] = params
        
        # 保存到数据库
        success = tasks_state_machine_helper.update(
            task_id=task_id,
            task_sub_state='props',
            data=props_data
        )
        
        if success:
            logger.info(f"✅ 任务 {task_id} 已补充company_name: {stock_symbol} -> {company_name}")
            return True
        else:
            logger.error(f"❌ 任务 {task_id} 更新失败")
            return False
            
    except Exception as e:
        logger.error(f"❌ 补充任务 {task_id} 的company_name失败: {e}", exc_info=True)
        return False


def supplement_all_tasks(batch_size: int = 100, dry_run: bool = False) -> dict:
    """
    批量为所有任务的props数据补充company_name
    
    Args:
        batch_size: 每批处理的任务数量
        dry_run: 是否为 dry run 模式（只检查不更新）
        
    Returns:
        dict: 迁移统计信息
    """
    if not tasks_state_machine_helper.connected:
        return {"success": False, "message": "tasks_state_machine_helper未连接"}
    
    if not stock_dict_manager.connected:
        return {"success": False, "message": "stock_dict_manager未连接"}
    
    try:
        # 查询所有props子状态的记录
        query = {'task_sub_state': 'props'}
        cursor = tasks_state_machine_helper.collection.find(query)
        
        total = 0
        updated = 0
        skipped = 0
        failed = 0
        no_stock_symbol = 0
        no_company_name_found = 0
        
        logger.info(f"开始{'（dry run模式）' if dry_run else ''}批量补充company_name...")
        
        for doc in cursor:
            total += 1
            task_id = doc.get('task_id', '')
            props_data = doc.get('data', {})
            
            try:
                params = props_data.get('params', {})
                
                # 检查是否已有company_name
                if params.get('company_name'):
                    skipped += 1
                    if total % batch_size == 0:
                        logger.debug(f"进度: {total}, 已更新: {updated}, 跳过: {skipped}, 失败: {failed}")
                    continue
                
                # 获取stock_symbol
                stock_symbol = params.get('stock_symbol')
                if not stock_symbol:
                    no_stock_symbol += 1
                    skipped += 1
                    if total % batch_size == 0:
                        logger.debug(f"进度: {total}, 已更新: {updated}, 跳过: {skipped}, 失败: {failed}")
                    continue
                
                # 查询公司名称
                company_name = stock_dict_manager.get_company_name(stock_symbol)
                if not company_name:
                    no_company_name_found += 1
                    skipped += 1
                    if total % batch_size == 0:
                        logger.debug(f"进度: {total}, 已更新: {updated}, 跳过: {skipped}, 失败: {failed}")
                    continue
                
                # 如果是dry run模式，只记录不更新
                if dry_run:
                    logger.info(f"[DRY RUN] 任务 {task_id}: {stock_symbol} -> {company_name}")
                    updated += 1
                else:
                    # 更新params中的company_name
                    params['company_name'] = company_name
                    props_data['params'] = params
                    
                    # 保存到数据库
                    success = tasks_state_machine_helper.update(
                        task_id=task_id,
                        task_sub_state='props',
                        data=props_data
                    )
                    
                    if success:
                        updated += 1
                    else:
                        failed += 1
                
                # 每处理一批输出进度
                if total % batch_size == 0:
                    logger.info(f"进度: {total}, 已更新: {updated}, 跳过: {skipped}, 失败: {failed}")
                    
            except Exception as e:
                logger.error(f"处理任务 {task_id} 失败: {e}")
                failed += 1
        
        result = {
            "success": True,
            "total": total,
            "updated": updated,
            "skipped": skipped,
            "failed": failed,
            "no_stock_symbol": no_stock_symbol,
            "no_company_name_found": no_company_name_found,
            "dry_run": dry_run
        }
        
        logger.info(f"批量补充完成: 总计 {total}, 已更新 {updated}, 跳过 {skipped}, 失败 {failed}")
        logger.info(f"  其中：无stock_symbol {no_stock_symbol}, 未找到公司名称 {no_company_name_found}")
        return result
        
    except Exception as e:
        logger.error(f"批量补充失败: {e}", exc_info=True)
        return {"success": False, "message": str(e)}


def main():
    """主迁移流程"""
    logger.info("=" * 60)
    logger.info("开始补充任务状态机数据中的company_name字段")
    logger.info("=" * 60)
    
    # 检查连接
    if not tasks_state_machine_helper.connected:
        logger.error("❌ tasks_state_machine_helper未连接，请检查MongoDB配置")
        return False
    
    if not stock_dict_manager.connected:
        logger.error("❌ stock_dict_manager未连接，请检查MongoDB配置")
        return False
    
    logger.info("✅ 连接检查通过")
    
    # 执行迁移
    result = supplement_all_tasks(batch_size=100, dry_run=False)
    
    if result.get("success"):
        logger.info("\n" + "=" * 60)
        logger.info("迁移总结")
        logger.info("=" * 60)
        logger.info(f"总计: {result.get('total')} 个任务")
        logger.info(f"已更新: {result.get('updated')} 个任务")
        logger.info(f"跳过: {result.get('skipped')} 个任务（已有company_name或无stock_symbol）")
        logger.info(f"失败: {result.get('failed')} 个任务")
        logger.info(f"  其中：无stock_symbol {result.get('no_stock_symbol')}, 未找到公司名称 {result.get('no_company_name_found')}")
        logger.info("=" * 60)
        
        if result.get("failed") == 0:
            logger.info("✅ 所有数据迁移成功！")
            return True
        else:
            logger.warning(f"⚠️ 有 {result.get('failed')} 个任务迁移失败，请检查日志")
            return False
    else:
        logger.error(f"❌ 迁移失败: {result.get('message')}")
        return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="补充任务状态机数据中的company_name字段")
    parser.add_argument(
        "--task-id",
        type=str,
        help="补充指定任务的数据（如果不指定，则补充所有任务）"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="dry run模式，只检查不更新"
    )
    
    args = parser.parse_args()
    
    if args.task_id:
        # 补充单个任务
        if not tasks_state_machine_helper.connected:
            logger.error("❌ tasks_state_machine_helper未连接")
            sys.exit(1)
        
        if not stock_dict_manager.connected:
            logger.error("❌ stock_dict_manager未连接")
            sys.exit(1)
        
        props_data = tasks_state_machine_helper.find_one(args.task_id, 'props')
        if not props_data:
            logger.error(f"❌ 未找到任务 {args.task_id} 的props数据")
            sys.exit(1)
        
        success = supplement_company_name_for_task(args.task_id, props_data)
        sys.exit(0 if success else 1)
    else:
        # 补充所有任务
        success = main()
        sys.exit(0 if success else 1)

