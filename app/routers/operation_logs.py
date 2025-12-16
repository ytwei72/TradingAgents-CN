"""
操作日志API路由
用于读取和查询结构化日志文件
"""

import json
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel

router = APIRouter()

# 日志文件路径
# __file__ 是 app/routers/operation_logs.py
# parent 是 app/routers
# parent.parent 是 app
# parent.parent.parent 是项目根目录
LOGS_DIR = Path(__file__).parent.parent.parent / "logs"
STRUCTURED_LOG_FILE = LOGS_DIR / "tradingagents_structured.log"


def parse_timestamp(timestamp_str: str) -> Optional[datetime]:
    """解析时间戳字符串"""
    try:
        # 尝试解析ISO格式: 2025-12-09T09:44:05.591394
        return datetime.fromisoformat(timestamp_str)
    except (ValueError, AttributeError):
        try:
            # 尝试解析带时区的格式
            timestamp_str = timestamp_str.replace('Z', '+00:00')
            return datetime.fromisoformat(timestamp_str)
        except:
            return None


def clean_ansi_codes(text: str) -> str:
    """移除ANSI颜色码"""
    if not text:
        return text
    # 移除ANSI转义序列
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)


def get_log_files() -> List[Path]:
    """获取所有日志文件，按修改时间倒序排列（最新的在前）"""
    if not LOGS_DIR.exists():
        return []
    
    log_files = []
    
    # 主日志文件
    if STRUCTURED_LOG_FILE.exists():
        log_files.append(STRUCTURED_LOG_FILE)
    
    # 备份日志文件 (tradingagents_structured.log.1, tradingagents_structured.log.2, ...)
    backup_files = sorted(
        LOGS_DIR.glob("tradingagents_structured.log.*"),
        key=lambda x: int(x.suffix.lstrip('.')) if x.suffix.lstrip('.').isdigit() else 0,
        reverse=True
    )
    log_files.extend(backup_files)
    
    return log_files


def read_logs_from_file(file_path: Path) -> List[Dict[str, Any]]:
    """从日志文件读取所有日志条目"""
    logs = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    log_entry = json.loads(line)
                    # 清理level字段中的ANSI码
                    if 'level' in log_entry:
                        log_entry['level'] = clean_ansi_codes(log_entry['level'])
                    if 'message' in log_entry:
                        log_entry['message'] = clean_ansi_codes(log_entry['message'])
                    # 解析时间戳为datetime对象以便后续筛选
                    if 'timestamp' in log_entry:
                        log_entry['parsed_timestamp'] = parse_timestamp(log_entry['timestamp'])
                    logs.append(log_entry)
                except json.JSONDecodeError as e:
                    # 跳过无法解析的行
                    continue
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取日志文件失败: {str(e)}")
    
    return logs


class LogsResponse(BaseModel):
    success: bool
    data: List[Dict[str, Any]]
    total: int
    filtered_total: int
    message: str


@router.get("/query", response_model=LogsResponse)
async def get_operation_logs(
    start_date: Optional[str] = Query(None, description="开始日期 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="结束日期 (YYYY-MM-DD)"),
    days: Optional[int] = Query(None, description="近N天"),
    keyword: Optional[str] = Query(None, description="关键字搜索"),
    level: Optional[str] = Query(None, description="日志级别过滤 (INFO, WARNING, ERROR)"),
    logger: Optional[str] = Query(None, description="Logger名称过滤"),
    limit: Optional[int] = Query(1000, description="返回结果数量限制", ge=1, le=10000)
):
    """
    获取操作日志
    
    支持：
    - 日期区间筛选（start_date和end_date）
    - 近N天筛选（days参数）
    - 关键字搜索（在message字段中搜索）
    - 日志级别过滤
    - Logger名称过滤
    """
    try:
        # 获取所有日志文件
        log_files = get_log_files()
        if not log_files:
            return LogsResponse(
                success=True,
                data=[],
                total=0,
                filtered_total=0,
                message="未找到日志文件"
            )
        
        # 读取所有日志
        all_logs = []
        for log_file in log_files:
            logs = read_logs_from_file(log_file)
            all_logs.extend(logs)
        
        # 按时间戳排序（最新的在前）
        all_logs.sort(key=lambda x: x.get('parsed_timestamp') or datetime.min, reverse=True)
        
        total_count = len(all_logs)
        
        # 日期筛选
        if days:
            # 近N天
            end_dt = datetime.now().replace(hour=23, minute=59, second=59)
            start_dt = (end_dt - timedelta(days=days)).replace(hour=0, minute=0, second=0)
            filtered_logs = [
                log for log in all_logs
                if log.get('parsed_timestamp') and start_dt <= log['parsed_timestamp'] <= end_dt
            ]
        elif start_date or end_date:
            # 日期区间
            if start_date:
                start_dt = datetime.strptime(start_date, '%Y-%m-%d').replace(hour=0, minute=0, second=0)
            else:
                start_dt = datetime.min
            
            if end_date:
                end_dt = datetime.strptime(end_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
            else:
                end_dt = datetime.now()
            
            filtered_logs = [
                log for log in all_logs
                if log.get('parsed_timestamp') and start_dt <= log['parsed_timestamp'] <= end_dt
            ]
        else:
            filtered_logs = all_logs
        
        # 关键字搜索（在message字段中）
        if keyword:
            keyword_lower = keyword.lower()
            filtered_logs = [
                log for log in filtered_logs
                if keyword_lower in log.get('message', '').lower()
                or keyword_lower in log.get('module', '').lower()
                or keyword_lower in log.get('function', '').lower()
                or keyword_lower in log.get('logger', '').lower()
            ]
        
        # 日志级别过滤
        if level:
            level_upper = level.upper()
            filtered_logs = [
                log for log in filtered_logs
                if level_upper in log.get('level', '').upper()
            ]
        
        # Logger名称过滤
        if logger:
            logger_lower = logger.lower()
            filtered_logs = [
                log for log in filtered_logs
                if logger_lower in log.get('logger', '').lower()
            ]
        
        # 应用数量限制
        filtered_logs = filtered_logs[:limit]
        
        # 移除parsed_timestamp字段（不需要返回给前端）
        for log in filtered_logs:
            log.pop('parsed_timestamp', None)
        
        return LogsResponse(
            success=True,
            data=filtered_logs,
            total=total_count,
            filtered_total=len(filtered_logs),
            message="获取日志成功"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取日志失败: {str(e)}")


@router.get("/stats")
async def get_logs_stats():
    """获取日志统计信息"""
    try:
        log_files = get_log_files()
        if not log_files:
            return {
                "success": True,
                "data": {
                    "total_files": 0,
                    "files": []
                }
            }
        
        files_info = []
        for log_file in log_files:
            try:
                stat = log_file.stat()
                files_info.append({
                    "filename": log_file.name,
                    "size": stat.st_size,
                    "modified_time": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "exists": True
                })
            except Exception as e:
                files_info.append({
                    "filename": log_file.name,
                    "exists": False,
                    "error": str(e)
                })
        
        return {
            "success": True,
            "data": {
                "total_files": len(log_files),
                "files": files_info
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取日志统计失败: {str(e)}")

