"""
Cursor Usage Analyzer
用于加载和分析 Cursor 使用情况（从 MongoDB 读取数据）
"""

from typing import List, Dict, Any, Optional
from pathlib import Path

from tradingagents.utils.logging_manager import get_logger

logger = get_logger("cursor_usage")


class CursorUsageAnalyzer:
    """Cursor 使用情况分析器（基于 MongoDB）"""
    
    def __init__(self, account_name: Optional[str] = None):
        """
        初始化分析器
        
        Args:
            account_name: 账户名称，如果指定则只查询该账户的数据
        """
        from tradingagents.storage.mongodb.cursor_usage_manager import CursorUsageManager
        
        self.manager = CursorUsageManager()
        self.account_name = account_name
        
        if not self.manager.is_connected():
            logger.warning("MongoDB 未连接，部分功能可能不可用")
    
    def get_date_list(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[str]:
        """
        获取所有可用的日期列表
        
        Args:
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            
        Returns:
            日期列表
        """
        return self.manager.get_available_dates(
            account_name=self.account_name,
            start_date=start_date,
            end_date=end_date
        )
    
    def get_csv_count(self) -> int:
        """
        获取 CSV 文件数量（兼容性方法，实际返回可用日期数）
        
        Returns:
            可用日期数量
        """
        dates = self.get_date_list()
        return len(dates)
    
    
    def get_total_statistics(self, start_date: Optional[str] = None, 
                            end_date: Optional[str] = None) -> Dict[str, Any]:
        """
        获取总体统计信息
        
        Args:
            start_date: 开始日期 (YYYY-MM-DD)，如果为 None 则使用所有数据
            end_date: 结束日期 (YYYY-MM-DD)，如果为 None 则使用所有数据
            
        Returns:
            统计信息字典
        """
        return self.manager.get_total_statistics(
            account_name=self.account_name,
            start_date=start_date,
            end_date=end_date
        )
    
    def get_daily_statistics(self, start_date: Optional[str] = None,
                            end_date: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        """
        获取按日期分组的统计信息
        
        Args:
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            
        Returns:
            按日期分组的统计信息字典
        """
        return self.manager.get_daily_statistics(
            account_name=self.account_name,
            start_date=start_date,
            end_date=end_date
        )
    
    def get_kind_statistics(self, start_date: Optional[str] = None,
                           end_date: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        """
        按 Kind（免费/包含）分类统计
        
        Args:
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            
        Returns:
            按 Kind 分组的统计信息字典
        """
        return self.manager.get_kind_statistics(
            account_name=self.account_name,
            start_date=start_date,
            end_date=end_date
        )
    
    def get_model_statistics(self, start_date: Optional[str] = None,
                            end_date: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        """
        按模型分类统计
        
        Args:
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            
        Returns:
            按模型分组的统计信息字典
        """
        return self.manager.get_model_statistics(
            account_name=self.account_name,
            start_date=start_date,
            end_date=end_date
        )
    
    def get_hourly_statistics(self, start_date: Optional[str] = None,
                             end_date: Optional[str] = None) -> Dict[int, Dict[str, Any]]:
        """
        按小时统计
        
        Args:
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            
        Returns:
            按小时分组的统计信息字典（键为小时 0-23）
        """
        return self.manager.get_hourly_statistics(
            account_name=self.account_name,
            start_date=start_date,
            end_date=end_date
        )
    
    def get_cost_statistics(self, start_date: Optional[str] = None,
                           end_date: Optional[str] = None) -> Dict[str, Any]:
        """
        获取费用统计（区分free和Included，auto仅作参考，其他模型单独累计）
        
        Args:
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            
        Returns:
            费用统计信息字典
        """
        return self.manager.get_cost_statistics(
            account_name=self.account_name,
            start_date=start_date,
            end_date=end_date
        )

