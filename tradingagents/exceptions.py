"""
任务控制相关异常
"""


class TaskControlException(Exception):
    """任务控制基础异常"""
    pass


class TaskControlStoppedException(TaskControlException):
    """任务被停止异常"""
    pass


class TaskControlPausedException(TaskControlException):
    """任务被暂停异常（如果需要区分）"""
    pass
