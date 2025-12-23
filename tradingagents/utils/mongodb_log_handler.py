#!/usr/bin/env python3
"""
MongoDB日志处理器
将日志直接写入MongoDB数据库，而不是文件
"""

import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional
from queue import Queue, Empty
import threading

# 使用标准库日志，避免循环导入
_bootstrap_logger = logging.getLogger('mongodb_log_handler')


class MongoDBLogHandler(logging.Handler):
    """MongoDB日志处理器"""
    
    def __init__(self, batch_size: int = 100, flush_interval: float = 5.0):
        """
        初始化MongoDB日志处理器
        
        Args:
            batch_size: 批量插入大小（默认100）
            flush_interval: 刷新间隔（秒，默认5秒）
        """
        super().__init__()
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.log_buffer: Queue = Queue()
        self.buffer_lock = threading.Lock()
        self.last_flush_time = datetime.now()
        self._shutdown = False
        
        # 延迟导入，避免循环导入
        self._system_logs_manager = None
        self._get_manager()
        
        # 启动后台线程处理批量插入
        self._worker_thread = threading.Thread(target=self._worker, daemon=True)
        self._worker_thread.start()
    
    def _get_manager(self):
        """获取系统日志管理器（延迟导入）"""
        if self._system_logs_manager is None:
            try:
                from tradingagents.storage.mongodb.system_logs_manager import get_system_logs_manager
                self._system_logs_manager = get_system_logs_manager()
            except Exception as e:
                _bootstrap_logger.warning(f"⚠️ 无法获取系统日志管理器: {e}")
                self._system_logs_manager = None
    
    def emit(self, record: logging.LogRecord):
        """
        处理日志记录
        
        Args:
            record: 日志记录对象
        """
        try:
            # 确保管理器已初始化
            if self._system_logs_manager is None:
                self._get_manager()
            
            # 如果MongoDB不可用，直接返回（不阻塞日志记录）
            if self._system_logs_manager is None or not self._system_logs_manager.connected:
                return
            
            # 将日志记录转换为字典
            log_entry = self._format_record(record)
            
            # 添加到缓冲区（Queue是线程安全的，不需要锁）
            self.log_buffer.put(log_entry, block=False)
            
            # 如果缓冲区达到批量大小，立即刷新
            if self.log_buffer.qsize() >= self.batch_size:
                self._flush_buffer()
            else:
                # 检查是否需要定时刷新
                with self.buffer_lock:
                    now = datetime.now()
                    if (now - self.last_flush_time).total_seconds() >= self.flush_interval:
                        self._flush_buffer()
                        
        except Exception as e:
            # 避免日志处理失败导致程序崩溃
            # 使用标准库日志，避免循环导入
            try:
                _bootstrap_logger.error(f"❌ MongoDB日志处理器错误: {e}", exc_info=True)
            except:
                pass  # 如果日志记录也失败，静默忽略
    
    def _format_record(self, record: logging.LogRecord) -> Dict[str, Any]:
        """
        格式化日志记录为字典
        
        Args:
            record: 日志记录对象
            
        Returns:
            日志条目字典
        """
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # 添加额外字段
        if hasattr(record, 'session_id'):
            log_entry['session_id'] = record.session_id
        if hasattr(record, 'analysis_type'):
            log_entry['analysis_type'] = record.analysis_type
        if hasattr(record, 'stock_symbol'):
            log_entry['stock_symbol'] = record.stock_symbol
        if hasattr(record, 'cost'):
            log_entry['cost'] = record.cost
        if hasattr(record, 'tokens'):
            log_entry['tokens'] = record.tokens
        if hasattr(record, 'provider'):
            log_entry['provider'] = record.provider
        if hasattr(record, 'model'):
            log_entry['model'] = record.model
        if hasattr(record, 'event_type'):
            log_entry['event_type'] = record.event_type
        if hasattr(record, 'duration'):
            log_entry['duration'] = record.duration
        if hasattr(record, 'module_name'):
            log_entry['module_name'] = record.module_name
        if hasattr(record, 'success'):
            log_entry['success'] = record.success
        if hasattr(record, 'error'):
            log_entry['error'] = record.error
        
        # 添加异常信息
        if record.exc_info:
            log_entry['exc_info'] = self.format(record)
        
        return log_entry
    
    def _flush_buffer(self):
        """刷新缓冲区，将日志批量写入MongoDB"""
        if self._system_logs_manager is None:
            self._get_manager()
        
        if self._system_logs_manager is None or not self._system_logs_manager.connected:
            # 如果MongoDB不可用，清空缓冲区避免内存泄漏
            try:
                while True:
                    self.log_buffer.get_nowait()
            except Empty:
                pass
            return
        
        try:
            # 收集缓冲区中的所有日志
            logs_to_insert = []
            with self.buffer_lock:
                while not self.log_buffer.empty():
                    try:
                        log_entry = self.log_buffer.get_nowait()
                        logs_to_insert.append(log_entry)
                    except Empty:
                        break
                
                self.last_flush_time = datetime.now()
            
            # 批量插入
            if logs_to_insert:
                inserted_count = self._system_logs_manager.insert_logs_batch(logs_to_insert)
                if inserted_count < len(logs_to_insert):
                    _bootstrap_logger.warning(
                        f"⚠️ MongoDB日志批量插入部分失败: {inserted_count}/{len(logs_to_insert)}"
                    )
                    
        except Exception as e:
            _bootstrap_logger.error(f"❌ 刷新MongoDB日志缓冲区失败: {e}", exc_info=True)
    
    def _worker(self):
        """后台工作线程，定期刷新缓冲区"""
        while not self._shutdown:
            try:
                # 等待刷新间隔
                import time
                time.sleep(self.flush_interval)
                
                # 检查是否需要刷新
                if not self.log_buffer.empty():
                    self._flush_buffer()
                    
            except Exception as e:
                _bootstrap_logger.error(f"❌ MongoDB日志处理器工作线程错误: {e}", exc_info=True)
    
    def flush(self):
        """立即刷新缓冲区"""
        self._flush_buffer()
        super().flush()
    
    def close(self):
        """关闭处理器，刷新所有待处理的日志"""
        self._shutdown = True
        
        # 等待工作线程结束
        if self._worker_thread.is_alive():
            self._worker_thread.join(timeout=2.0)
        
        # 最后刷新一次
        self._flush_buffer()
        
        super().close()

