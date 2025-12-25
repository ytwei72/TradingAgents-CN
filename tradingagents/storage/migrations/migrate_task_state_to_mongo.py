#!/usr/bin/env python3
"""
Redis任务状态数据迁移工具：将Redis中的任务状态数据迁移到MongoDB

将Redis中残留的task状态数据（props、current_step）迁移到MongoDB的tasks_state_machine集合

使用方法：
    python -m tradingagents.storage.migrations.migrate_task_state_to_mongo

或者直接运行：
    python tradingagents/storage/migrations/migrate_task_state_to_mongo.py
"""

import sys
import os
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from tradingagents.storage.redis.connection import get_redis_client, REDIS_AVAILABLE
from tradingagents.storage.mongodb.tasks_state_machine_helper import tasks_state_machine_helper
from tradingagents.utils.logging_manager import get_logger

logger = get_logger("task_state_migration")


def parse_task_key(key: str) -> Optional[Tuple[str, str]]:
    """
    解析Redis key，提取task_id和sub_key
    
    Args:
        key: Redis key，格式为 "task:{task_id}:{sub_key}"
    
    Returns:
        Tuple[task_id, sub_key] 或 None
    """
    pattern = r"^task:(.+?):(.+)$"
    match = re.match(pattern, key)
    if match:
        task_id = match.group(1)
        sub_key = match.group(2)
        # 只处理 props 和 current_step
        if sub_key in ['props', 'current_step']:
            return (task_id, sub_key)
    return None


def scan_redis_keys(pattern: str = "task:*:props") -> List[str]:
    """
    扫描Redis中所有匹配模式的key
    
    Args:
        pattern: 匹配模式，默认为 "task:*:props"
    
    Returns:
        List[str]: 匹配的key列表
    """
    if not REDIS_AVAILABLE:
        logger.error("Redis不可用，无法扫描key")
        return []
    
    try:
        client = get_redis_client()
        if not client:
            logger.error("无法获取Redis客户端")
            return []
        
        keys = []
        cursor = 0
        
        logger.info(f"正在扫描Redis key（模式: {pattern}）...")
        
        while True:
            cursor, batch_keys = client.scan(
                cursor=cursor,
                match=pattern,
                count=1000
            )
            # 处理bytes类型的key
            if batch_keys:
                keys.extend([k.decode('utf-8') if isinstance(k, bytes) else k for k in batch_keys])
            
            if cursor == 0:
                break
        
        logger.info(f"找到 {len(keys)} 个匹配的key")
        return keys
        
    except Exception as e:
        logger.error(f"扫描Redis key失败: {e}")
        return []


def migrate_single_key(key: str) -> Tuple[bool, Optional[str]]:
    """
    迁移单个Redis key的数据到MongoDB
    
    Args:
        key: Redis key
    
    Returns:
        Tuple[bool, Optional[str]]: (是否成功, 错误信息或None)
        如果返回 (False, None) 表示跳过（不匹配的key）
        如果返回 (False, "error message") 表示失败
        如果返回 (True, None) 表示成功
    """
    if not REDIS_AVAILABLE:
        return (False, "Redis不可用")
    
    try:
        # 解析key
        parsed = parse_task_key(key)
        if not parsed:
            logger.debug(f"跳过不匹配的key: {key}")
            return (False, None)  # None表示跳过
        
        task_id, task_sub_state = parsed
        
        # 获取Redis客户端
        client = get_redis_client()
        if not client:
            return False
        
        # 获取数据
        data_str = client.get(key)
        if not data_str:
            logger.warning(f"key {key} 的数据为空，跳过")
            return (False, None)  # None表示跳过
        
        # 处理bytes类型
        if isinstance(data_str, bytes):
            data_str = data_str.decode('utf-8')
        
        # 解析JSON
        try:
            data = json.loads(data_str)
        except json.JSONDecodeError as e:
            error_msg = f"key {key} 的JSON解析失败: {e}"
            logger.error(error_msg)
            return (False, error_msg)
        
        # 保存到MongoDB
        if not tasks_state_machine_helper.connected:
            error_msg = "MongoDB未连接，无法保存数据"
            logger.error(error_msg)
            return (False, error_msg)
        
        success = tasks_state_machine_helper.update(
            task_id=task_id,
            task_sub_state=task_sub_state,
            data=data
        )
        
        if success:
            logger.debug(f"✅ 迁移成功: task_id={task_id}, task_sub_state={task_sub_state}")
            return (True, None)
        else:
            error_msg = f"MongoDB更新失败: task_id={task_id}, task_sub_state={task_sub_state}"
            logger.warning(f"⚠️ {error_msg}")
            return (False, error_msg)
        
    except Exception as e:
        error_msg = f"迁移key {key} 失败: {e}"
        logger.error(error_msg)
        return (False, error_msg)


def migrate_all_task_states(batch_size: int = 100) -> Dict[str, Any]:
    """
    迁移所有任务状态数据从Redis到MongoDB
    
    Args:
        batch_size: 每批处理的key数量
    
    Returns:
        dict: 迁移统计信息
    """
    if not REDIS_AVAILABLE:
        return {"success": False, "message": "Redis不可用"}
    
    if not tasks_state_machine_helper.connected:
        return {"success": False, "message": "MongoDB未连接"}
    
    try:
        # 扫描所有相关的key
        all_keys = []
        
        # 扫描 props
        logger.info("=" * 60)
        logger.info("开始扫描 props 数据...")
        props_keys = scan_redis_keys("task:*:props")
        all_keys.extend(props_keys)
        
        # 扫描 current_step
        logger.info("=" * 60)
        logger.info("开始扫描 current_step 数据...")
        current_step_keys = scan_redis_keys("task:*:current_step")
        all_keys.extend(current_step_keys)
        
        total = len(all_keys)
        if total == 0:
            logger.info("未找到需要迁移的数据")
            return {
                "success": True,
                "total": 0,
                "migrated": 0,
                "failed": 0,
                "skipped": 0,
                "message": "未找到需要迁移的数据"
            }
        
        logger.info("=" * 60)
        logger.info(f"总共找到 {total} 个key需要迁移")
        logger.info(f"  - props: {len(props_keys)} 个")
        logger.info(f"  - current_step: {len(current_step_keys)} 个")
        logger.info("=" * 60)
        
        # 开始迁移
        migrated = 0
        failed = 0
        skipped = 0
        
        for i, key in enumerate(all_keys):
            try:
                success, error_msg = migrate_single_key(key)
                if success:
                    migrated += 1
                elif error_msg is None:
                    # error_msg为None表示跳过（不匹配的key）
                    skipped += 1
                else:
                    # error_msg不为None表示失败
                    failed += 1
                
                # 每处理一批输出进度
                if (i + 1) % batch_size == 0:
                    logger.info(
                        f"迁移进度: {i + 1}/{total}, "
                        f"已迁移: {migrated}, "
                        f"失败: {failed}, "
                        f"跳过: {skipped}"
                    )
            except Exception as e:
                logger.error(f"处理key {key} 失败: {e}")
                failed += 1
        
        # 最终统计
        logger.info("=" * 60)
        logger.info("迁移完成！")
        logger.info(f"总计: {total}")
        logger.info(f"成功: {migrated}")
        logger.info(f"失败: {failed}")
        logger.info(f"跳过: {skipped}")
        logger.info("=" * 60)
        
        return {
            "success": True,
            "total": total,
            "migrated": migrated,
            "failed": failed,
            "skipped": skipped,
            "props_count": len(props_keys),
            "current_step_count": len(current_step_keys)
        }
        
    except Exception as e:
        logger.error(f"迁移过程发生错误: {e}", exc_info=True)
        return {
            "success": False,
            "message": str(e)
        }


def main():
    """主函数"""
    print("=" * 60)
    print("Redis任务状态数据迁移工具")
    print("将Redis中的task状态数据（props、current_step）迁移到MongoDB")
    print("=" * 60)
    print()
    
    # 检查Redis连接
    if not REDIS_AVAILABLE:
        print("❌ Redis不可用，请检查Redis服务是否启动")
        return
    
    try:
        client = get_redis_client()
        if not client:
            print("❌ 无法获取Redis客户端")
            return
        client.ping()
        print("✅ Redis连接成功")
    except Exception as e:
        print(f"❌ Redis连接失败: {e}")
        return
    
    # 检查MongoDB连接
    if not tasks_state_machine_helper.connected:
        print("❌ MongoDB未连接，请检查MongoDB服务是否启动")
        return
    print("✅ MongoDB连接成功")
    print()
    
    # 执行迁移
    result = migrate_all_task_states(batch_size=100)
    
    # 输出结果
    print()
    if result.get("success"):
        print("✅ 迁移完成！")
        print(f"   总计: {result.get('total', 0)}")
        print(f"   成功: {result.get('migrated', 0)}")
        print(f"   失败: {result.get('failed', 0)}")
        print(f"   props: {result.get('props_count', 0)}")
        print(f"   current_step: {result.get('current_step_count', 0)}")
    else:
        print(f"❌ 迁移失败: {result.get('message', '未知错误')}")


if __name__ == "__main__":
    main()

