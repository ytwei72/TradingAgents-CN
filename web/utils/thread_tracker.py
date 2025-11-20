"""
分析线程跟踪器
用于跟踪和检测分析线程的存活状态，支持任务控制
"""

import threading
import time
from typing import Dict, Optional
from tradingagents.utils.logging_manager import get_logger

logger = get_logger('web')

class ThreadTracker:
    """线程跟踪器 - 支持任务控制"""
    
    def __init__(self):
        self._threads: Dict[str, threading.Thread] = {}
        self._stop_events: Dict[str, threading.Event] = {}  # 停止事件
        self._lock = threading.Lock()
    
    def register_thread(self, analysis_id: str, thread: threading.Thread, stop_event: threading.Event = None):
        """注册分析线程
        
        Args:
            analysis_id: 分析ID
            thread: 线程对象
            stop_event: 停止事件（可选）
        """
        with self._lock:
            self._threads[analysis_id] = thread
            if stop_event:
                self._stop_events[analysis_id] = stop_event
            logger.info(f"📊 [线程跟踪] 注册分析线程: {analysis_id}")
    
    def unregister_thread(self, analysis_id: str):
        """注销分析线程"""
        with self._lock:
            if analysis_id in self._threads:
                del self._threads[analysis_id]
            if analysis_id in self._stop_events:
                del self._stop_events[analysis_id]
            logger.info(f"📊 [线程跟踪] 注销分析线程: {analysis_id}")
    
    def is_thread_alive(self, analysis_id: str) -> bool:
        """检查分析线程是否存活"""
        with self._lock:
            thread = self._threads.get(analysis_id)
            if thread is None:
                return False
            
            is_alive = thread.is_alive()
            if not is_alive:
                # 线程已死亡，自动清理
                del self._threads[analysis_id]
                logger.info(f"📊 [线程跟踪] 线程已死亡，自动清理: {analysis_id}")
            
            return is_alive
    
    def get_alive_threads(self) -> Dict[str, threading.Thread]:
        """获取所有存活的线程"""
        with self._lock:
            alive_threads = {}
            dead_threads = []
            
            for analysis_id, thread in self._threads.items():
                if thread.is_alive():
                    alive_threads[analysis_id] = thread
                else:
                    dead_threads.append(analysis_id)
            
            # 清理死亡线程
            for analysis_id in dead_threads:
                del self._threads[analysis_id]
                logger.info(f"📊 [线程跟踪] 清理死亡线程: {analysis_id}")
            
            return alive_threads
    
    def cleanup_dead_threads(self):
        """清理所有死亡线程"""
        self.get_alive_threads()  # 这会自动清理死亡线程
    
    def get_thread_info(self, analysis_id: str) -> Optional[Dict]:
        """获取线程信息"""
        with self._lock:
            thread = self._threads.get(analysis_id)
            if thread is None:
                return None
            
            return {
                'analysis_id': analysis_id,
                'thread_name': thread.name,
                'thread_id': thread.ident,
                'is_alive': thread.is_alive(),
                'is_daemon': thread.daemon
            }
    
    def get_all_thread_info(self) -> Dict[str, Dict]:
        """获取所有线程信息"""
        with self._lock:
            info = {}
            for analysis_id, thread in self._threads.items():
                info[analysis_id] = {
                    'analysis_id': analysis_id,
                    'thread_name': thread.name,
                    'thread_id': thread.ident,
                    'is_alive': thread.is_alive(),
                    'is_daemon': thread.daemon,
                    'has_stop_event': analysis_id in self._stop_events
                }
            return info
    
    def get_stop_event(self, analysis_id: str) -> Optional[threading.Event]:
        """获取停止事件"""
        with self._lock:
            return self._stop_events.get(analysis_id)
    
    def request_stop(self, analysis_id: str) -> bool:
        """请求停止线程
        
        Returns:
            bool: 是否成功设置停止标志
        """
        with self._lock:
            if analysis_id in self._stop_events:
                self._stop_events[analysis_id].set()
                logger.info(f"⏹️ [线程跟踪] 请求停止线程: {analysis_id}")
                return True
            else:
                logger.warning(f"⚠️ [线程跟踪] 未找到停止事件: {analysis_id}")
                return False

# 全局线程跟踪器实例
thread_tracker = ThreadTracker()

def register_analysis_thread(analysis_id: str, thread: threading.Thread, stop_event: threading.Event = None):
    """注册分析线程"""
    thread_tracker.register_thread(analysis_id, thread, stop_event)

def unregister_analysis_thread(analysis_id: str):
    """注销分析线程"""
    thread_tracker.unregister_thread(analysis_id)

def is_analysis_thread_alive(analysis_id: str) -> bool:
    """检查分析线程是否存活"""
    return thread_tracker.is_thread_alive(analysis_id)

def get_analysis_thread_info(analysis_id: str) -> Optional[Dict]:
    """获取分析线程信息"""
    return thread_tracker.get_thread_info(analysis_id)

def cleanup_dead_analysis_threads():
    """清理所有死亡的分析线程"""
    thread_tracker.cleanup_dead_threads()

def get_all_analysis_threads() -> Dict[str, Dict]:
    """获取所有分析线程信息"""
    return thread_tracker.get_all_thread_info()

def check_analysis_status(analysis_id: str) -> str:
    """
    检查分析状态
    返回: 'running', 'completed', 'failed', 'not_found', 'paused', 'stopped'
    """
    # 首先检查任务控制状态
    try:
        from tradingagents.utils.task_control_manager import get_task_state
        control_state = get_task_state(analysis_id)
        if control_state in ['paused', 'stopped']:
            return control_state
    except Exception:
        pass
    
    # 检查线程是否存活
    if is_analysis_thread_alive(analysis_id):
        return 'running'
    
    # 线程不存在，检查进度数据确定最终状态
    try:
        from .async_progress_tracker import get_progress_by_id
        progress_data = get_progress_by_id(analysis_id)
        
        if progress_data:
            status = progress_data.get('status', 'unknown')
            if status in ['completed', 'failed', 'stopped', 'paused']:
                return status
            else:
                # 状态显示运行中但线程已死亡，说明异常终止
                return 'failed'
        else:
            return 'not_found'
    except Exception as e:
        logger.error(f"📊 [状态检查] 检查进度数据失败: {e}")
        return 'not_found'

def request_stop_thread(analysis_id: str) -> bool:
    """请求停止线程"""
    return thread_tracker.request_stop(analysis_id)

def get_thread_stop_event(analysis_id: str) -> Optional[threading.Event]:
    """获取线程停止事件"""
    return thread_tracker.get_stop_event(analysis_id)
