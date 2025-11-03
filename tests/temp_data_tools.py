#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量重命名分析结果文件
去除文件名最前面的"analysis_"前缀

例如：
- analysis_analysis_3f879bc4_20251031_105244.json -> analysis_3f879bc4_20251031_105244.json
"""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Dict, Any

try:
    from web.utils.mongodb_report_manager import mongodb_report_manager
except Exception:
    mongodb_report_manager = None


def remove_analysis_prefix_from_files(results_dir: str = None) -> Tuple[int, int, List[str]]:
    """
    对指定目录下的所有JSON文件，去除文件名最前面的"analysis_"前缀
    
    Args:
        results_dir: 分析结果目录路径，默认为 web/data/analysis_results
    
    Returns:
        Tuple[int, int, List[str]]: (成功重命名数量, 失败数量, 重命名的文件列表)
    """
    
    # 确定目录路径
    if results_dir is None:
        # 获取项目根目录
        current_file = Path(__file__)
        project_root = current_file.parent.parent
        results_dir = project_root / "web" / "data" / "analysis_results"
    else:
        results_dir = Path(results_dir)
    
    # 检查目录是否存在
    if not results_dir.exists():
        print(f"❌ 目录不存在: {results_dir}")
        return 0, 0, []
    
    if not results_dir.is_dir():
        print(f"❌ 不是目录: {results_dir}")
        return 0, 0, []
    
    print(f"📂 扫描目录: {results_dir}")
    
    # 查找所有JSON文件
    json_files = list(results_dir.glob("*.json"))
    
    if not json_files:
        print(f"⚠️ 目录中没有找到JSON文件")
        return 0, 0, []
    
    print(f"📊 找到 {len(json_files)} 个JSON文件")
    
    success_count = 0
    failure_count = 0
    renamed_files = []
    
    # 处理每个文件
    for json_file in json_files:
        original_name = json_file.name
        
        # 检查文件名是否以"analysis_"开头
        if not original_name.startswith("analysis_"):
            print(f"⏭️  跳过（不以analysis_开头）: {original_name}")
            continue
        
        # 去除第一个"analysis_"前缀
        new_name = original_name[len("analysis_"):]
        
        # 检查新文件名是否有效
        if not new_name:
            print(f"⚠️  跳过（去除前缀后文件名为空）: {original_name}")
            failure_count += 1
            continue
        
        # 检查新文件名是否已经存在
        new_file_path = json_file.parent / new_name
        if new_file_path.exists():
            print(f"⚠️  跳过（目标文件已存在）: {original_name} -> {new_name}")
            failure_count += 1
            continue
        
        try:
            # 重命名文件
            json_file.rename(new_file_path)
            print(f"✅ 重命名成功: {original_name} -> {new_name}")
            success_count += 1
            renamed_files.append(f"{original_name} -> {new_name}")
        except Exception as e:
            print(f"❌ 重命名失败: {original_name} -> {new_name}, 错误: {e}")
            failure_count += 1
    
    # 输出统计信息
    print(f"\n📊 重命名统计:")
    print(f"  ✅ 成功: {success_count} 个文件")
    print(f"  ❌ 失败: {failure_count} 个文件")
    print(f"  📁 总计: {len(json_files)} 个文件")
    
    return success_count, failure_count, renamed_files


def preview_rename_operations(results_dir: str = None) -> List[Tuple[str, str]]:
    """
    预览重命名操作，不实际执行重命名
    
    Args:
        results_dir: 分析结果目录路径，默认为 web/data/analysis_results
    
    Returns:
        List[Tuple[str, str]]: [(原文件名, 新文件名), ...] 列表
    """
    
    # 确定目录路径
    if results_dir is None:
        current_file = Path(__file__)
        project_root = current_file.parent.parent
        results_dir = project_root / "web" / "data" / "analysis_results"
    else:
        results_dir = Path(results_dir)
    
    if not results_dir.exists():
        print(f"❌ 目录不存在: {results_dir}")
        return []
    
    # 查找所有JSON文件
    json_files = list(results_dir.glob("*.json"))
    
    rename_operations = []
    
    for json_file in json_files:
        original_name = json_file.name
        
        if not original_name.startswith("analysis_"):
            continue
        
        new_name = original_name[len("analysis_"):]
        
        if not new_name:
            continue
        
        new_file_path = json_file.parent / new_name
        if new_file_path.exists():
            continue
        
        rename_operations.append((original_name, new_name))
    
    return rename_operations


def rename_result_files():
    """主函数"""
    print("=" * 60)
    print("批量重命名分析结果文件")
    print("去除文件名最前面的'analysis_'前缀")
    print("=" * 60)
    print()
    
    # 先预览重命名操作
    print("🔍 预览重命名操作...")
    preview_ops = preview_rename_operations()
    
    if not preview_ops:
        print("✅ 没有需要重命名的文件")
        return
    
    print(f"\n📋 将重命名 {len(preview_ops)} 个文件:")
    for i, (old_name, new_name) in enumerate(preview_ops[:10], 1):  # 只显示前10个
        print(f"  {i}. {old_name} -> {new_name}")
    
    if len(preview_ops) > 10:
        print(f"  ... 还有 {len(preview_ops) - 10} 个文件")
    
    # 询问确认
    print()
    response = input("⚠️  是否执行重命名操作？(y/N): ").strip().lower()
    
    if response != 'y':
        print("❌ 操作已取消")
        return
    
    # 执行重命名
    print()
    print("🔄 开始执行重命名...")
    success_count, failure_count, renamed_files = remove_analysis_prefix_from_files()
    
    print()
    if success_count > 0:
        print(f"✅ 重命名完成！成功处理 {success_count} 个文件")
    if failure_count > 0:
        print(f"⚠️  有 {failure_count} 个文件处理失败")
    
    if renamed_files:
        print(f"\n📝 重命名详情（前10个）:")
        for i, rename_info in enumerate(renamed_files[:10], 1):
            print(f"  {i}. {rename_info}")


def _parse_datetime(value: Any) -> datetime:
    """将多种时间格式转换为 datetime，用于 created_at/updated_at/timestamp。"""
    if isinstance(value, datetime):
        return value
    if isinstance(value, (int, float)):
        try:
            # 当作unix时间戳
            return datetime.fromtimestamp(float(value))
        except Exception:
            pass
    if isinstance(value, str):
        # 尝试多种常见格式
        for fmt in (
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%fZ",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%d",
        ):
            try:
                return datetime.strptime(value, fmt)
            except Exception:
                continue
        # 回退: 尝试 fromisoformat
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except Exception:
            pass
    # 最后兜底返回当前时间
    return datetime.now()


def import_analysis_results_to_mongo(results_dir: str = None) -> Tuple[int, int, int]:
    """
    读取 web/data/analysis_results 目录下的 JSON 文件，提取字段并保存到 Mongo 的 analysis_reports 集合。

    约定：
    - analysis_id 使用文件名（不含 .json）
    - Mongo 文档结构参考 data/analysis_results/111.txt
    - 各字段尽量从 JSON 原样映射，缺失时使用合理默认值

    Returns:
        (processed_count, success_count, failure_count)
    """

    # 检查 Mongo 管理器
    if mongodb_report_manager is None or not getattr(mongodb_report_manager, "connected", False):
        print("❌ MongoDB 未连接或管理器不可用，无法导入")
        return 0, 0, 0

    # 目录解析
    if results_dir is None:
        current_file = Path(__file__)
        project_root = current_file.parent.parent
        results_dir = project_root / "web" / "data" / "analysis_results"
    else:
        results_dir = Path(results_dir)

    if not results_dir.exists() or not results_dir.is_dir():
        print(f"❌ 目录无效: {results_dir}")
        return 0, 0, 0

    json_files = list(results_dir.glob("*.json"))
    if not json_files:
        print("⚠️ 未找到任何 JSON 文件")
        return 0, 0, 0

    processed = 0
    success = 0
    failure = 0

    for json_path in sorted(json_files):
        processed += 1
        analysis_id = json_path.stem  # 文件名不含后缀

        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data: Dict[str, Any] = json.load(f)

            # 尽量按源数据映射
            stock_symbol = (
                data.get("stock_symbol")
                or data.get("symbol")
                or data.get("stock")
                or ""
            )

            analysis_date = (
                data.get("analysis_date")
                or data.get("date")
            )
            if not analysis_date:
                # 从 timestamp 推断或使用今天日期
                ts_val = data.get("timestamp")
                ts_dt = _parse_datetime(ts_val) if ts_val is not None else datetime.now()
                analysis_date = ts_dt.strftime("%Y-%m-%d")

            analysts = data.get("analysts", [])
            research_depth = data.get("research_depth", data.get("depth", 1))
            status = data.get("status", "completed")
            source = data.get("source", "mongodb")
            summary = data.get("summary", "")

            # 决策与报告改为从 full_data 中取
            full_data = data.get("full_data", {}) or {}
            formatted_decision = (
                (full_data.get("decision") if isinstance(full_data, dict) else None)
                or {}
            )
            # reports 从 full_data.state 取，并按 111.txt 的字段白名单过滤
            state = (full_data.get("state") if isinstance(full_data, dict) else None) or {}
            allowed_report_fields = [
                "market_report",
                "news_report",
                "fundamentals_report",
                "investment_plan",
                "trader_investment_plan",
                "final_trade_decision",
                "investment_debate_state",
                "risk_debate_state",
                "markdown",
                "generated_at",
            ]

            reports = {}
            for key in allowed_report_fields:
                if key in state:
                    val = state.get(key)
                    # 统一为字符串或基础类型；复杂结构转为字符串存储
                    if isinstance(val, (dict, list)):
                        try:
                            val = json.dumps(val, ensure_ascii=False)
                        except Exception:
                            val = str(val)
                    reports[key] = val

            # 时间字段
            created_at = _parse_datetime(data.get("created_at")) if data.get("created_at") else datetime.now()
            updated_at = _parse_datetime(data.get("updated_at")) if data.get("updated_at") else created_at
            ts_field = data.get("timestamp")
            timestamp_dt = _parse_datetime(ts_field) if ts_field is not None else created_at

            # 组装与 数据库中数据结构 对齐的文档
            report_doc: Dict[str, Any] = {
                "analysis_id": analysis_id,
                "analysis_date": analysis_date,
                "analysts": analysts,
                "created_at": created_at,
                "formatted_decision": formatted_decision,
                "reports": reports,
                "research_depth": int(research_depth) if isinstance(research_depth, (int, float, str)) else 1,
                "source": source,
                "status": status,
                "stock_symbol": stock_symbol,
                "summary": summary,
                "timestamp": timestamp_dt,
                "updated_at": updated_at,
            }

            ok = mongodb_report_manager.save_report(report_doc)
            if ok:
                success += 1
                print(f"✅ 已导入: {analysis_id}")
            else:
                failure += 1
                print(f"❌ 导入失败: {analysis_id}")

        except Exception as e:
            failure += 1
            print(f"❌ 处理文件失败: {json_path.name}, 错误: {e}")

    print(f"\n📊 导入完成: 共处理 {processed} 个文件, 成功 {success}, 失败 {failure}")
    return processed, success, failure


if __name__ == "__main__":
    # rename_result_files()
    import_analysis_results_to_mongo()

