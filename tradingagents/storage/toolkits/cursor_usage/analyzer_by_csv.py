"""
Cursor Usage Analyzer
用于加载和分析 Cursor 使用情况的 CSV 文件
"""

import re
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from tradingagents.utils.logging_manager import get_logger

logger = get_logger("cursor_usage")


class CursorUsageAnalyzer:
    """Cursor 使用情况分析器"""
    
    def __init__(self, data_dir: Optional[Path] = None):
        """
        初始化分析器
        
        Args:
            data_dir: CSV 文件所在目录，默认为当前模块目录
        """
        if data_dir is None:
            # 默认使用当前模块所在目录
            data_dir = Path(__file__).parent
        
        self.data_dir = Path(data_dir)
        self._csv_files: List[Path] = []
        self._date_list: List[str] = []
        self._data_cache: Dict[str, pd.DataFrame] = {}
        
        # 扫描 CSV 文件
        self._scan_csv_files()
    
    def _scan_csv_files(self):
        """扫描目录中的 CSV 文件并提取日期"""
        pattern = re.compile(r'usage-events-(\d{4}-\d{2}-\d{2})\.csv')
        
        csv_files = []
        dates = []
        
        if not self.data_dir.exists():
            logger.warning(f"数据目录不存在: {self.data_dir}")
            return
        
        for file_path in self.data_dir.glob('usage-events-*.csv'):
            match = pattern.match(file_path.name)
            if match:
                date_str = match.group(1)
                csv_files.append(file_path)
                dates.append(date_str)
        
        # 按日期排序
        sorted_pairs = sorted(zip(dates, csv_files), key=lambda x: x[0])
        self._date_list = [date for date, _ in sorted_pairs]
        self._csv_files = [file for _, file in sorted_pairs]
        
        logger.info(f"扫描到 {len(self._csv_files)} 个 CSV 文件，日期范围: {self._date_list[0] if self._date_list else 'N/A'} 到 {self._date_list[-1] if self._date_list else 'N/A'}")
    
    def get_date_list(self) -> List[str]:
        """获取所有可用的日期列表"""
        return self._date_list.copy()
    
    def get_csv_count(self) -> int:
        """获取 CSV 文件数量"""
        return len(self._csv_files)
    
    def load_csv(self, date: str) -> Optional[pd.DataFrame]:
        """
        加载指定日期的 CSV 文件
        
        Args:
            date: 日期字符串，格式为 YYYY-MM-DD
            
        Returns:
            DataFrame 或 None（如果文件不存在）
        """
        if date in self._data_cache:
            return self._data_cache[date]
        
        # 查找对应的文件
        file_path = None
        for csv_file in self._csv_files:
            if date in csv_file.name:
                file_path = csv_file
                break
        
        if file_path is None or not file_path.exists():
            logger.warning(f"CSV 文件不存在: {date}")
            return None
        
        try:
            df = pd.read_csv(file_path)
            
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
            
            self._data_cache[date] = df
            logger.info(f"成功加载 CSV 文件: {date}, 记录数: {len(df)}")
            return df
            
        except Exception as e:
            logger.error(f"加载 CSV 文件失败 ({date}): {e}")
            return None
    
    def load_date_range(self, start_date: str, end_date: str) -> pd.DataFrame:
        """
        加载日期范围内的所有 CSV 文件并合并
        
        Args:
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            
        Returns:
            合并后的 DataFrame
        """
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        
        dfs = []
        for date_str in self._date_list:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            if start <= date_obj <= end:
                df = self.load_csv(date_str)
                if df is not None:
                    dfs.append(df)
        
        if not dfs:
            logger.warning(f"日期范围内没有找到数据: {start_date} 到 {end_date}")
            return pd.DataFrame()
        
        result = pd.concat(dfs, ignore_index=True)
        logger.info(f"合并日期范围数据: {start_date} 到 {end_date}, 总记录数: {len(result)}")
        return result
    
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
        if start_date and end_date:
            df = self.load_date_range(start_date, end_date)
        else:
            # 加载所有数据
            dfs = []
            for date_str in self._date_list:
                df = self.load_csv(date_str)
                if df is not None:
                    dfs.append(df)
            if not dfs:
                return self._empty_statistics()
            df = pd.concat(dfs, ignore_index=True)
        
        if df.empty:
            return self._empty_statistics()
        
        # 过滤掉 "Aborted, Not Charged" 的记录
        df_filtered = df[df['Kind'] != 'Aborted, Not Charged'].copy()
        
        stats = {
            'total_requests': len(df_filtered),
            'total_cost': float(df_filtered['Cost'].sum()),
            'total_input_tokens': int(df_filtered['Input (w/ Cache Write)'].sum() + 
                                     df_filtered['Input (w/o Cache Write)'].sum()),
            'total_output_tokens': int(df_filtered['Output Tokens'].sum()),
            'total_cache_read': int(df_filtered['Cache Read'].sum()),
            'total_tokens': int(df_filtered['Total Tokens'].sum()),
            'average_cost_per_request': float(df_filtered['Cost'].mean()) if len(df_filtered) > 0 else 0.0,
            'average_tokens_per_request': float(df_filtered['Total Tokens'].mean()) if len(df_filtered) > 0 else 0.0,
        }
        
        return stats
    
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
        if start_date and end_date:
            df = self.load_date_range(start_date, end_date)
        else:
            dfs = []
            for date_str in self._date_list:
                df = self.load_csv(date_str)
                if df is not None:
                    dfs.append(df)
            if not dfs:
                return {}
            df = pd.concat(dfs, ignore_index=True)
        
        if df.empty:
            return {}
        
        # 过滤掉 "Aborted, Not Charged" 的记录
        df_filtered = df[df['Kind'] != 'Aborted, Not Charged'].copy()
        
        # 提取日期（只保留日期部分，去掉时间）
        df_filtered['DateOnly'] = df_filtered['Date'].dt.date
        
        # 按日期分组统计
        daily_stats = {}
        for date_obj, group in df_filtered.groupby('DateOnly'):
            date_str = date_obj.strftime('%Y-%m-%d')
            daily_stats[date_str] = {
                'date': date_str,
                'total_requests': len(group),
                'total_cost': float(group['Cost'].sum()),
                'total_input_tokens': int(group['Input (w/ Cache Write)'].sum() + 
                                         group['Input (w/o Cache Write)'].sum()),
                'total_output_tokens': int(group['Output Tokens'].sum()),
                'total_cache_read': int(group['Cache Read'].sum()),
                'total_tokens': int(group['Total Tokens'].sum()),
                'average_cost_per_request': float(group['Cost'].mean()) if len(group) > 0 else 0.0,
            }
        
        return daily_stats
    
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
        if start_date and end_date:
            df = self.load_date_range(start_date, end_date)
        else:
            dfs = []
            for date_str in self._date_list:
                df = self.load_csv(date_str)
                if df is not None:
                    dfs.append(df)
            if not dfs:
                return {}
            df = pd.concat(dfs, ignore_index=True)
        
        if df.empty:
            return {}
        
        # 过滤掉 "Aborted, Not Charged" 的记录
        df_filtered = df[df['Kind'] != 'Aborted, Not Charged'].copy()
        
        kind_stats = {}
        for kind, group in df_filtered.groupby('Kind'):
            kind_stats[kind] = {
                'kind': kind,
                'total_requests': len(group),
                'total_cost': float(group['Cost'].sum()),
                'total_input_tokens': int(group['Input (w/ Cache Write)'].sum() + 
                                         group['Input (w/o Cache Write)'].sum()),
                'total_output_tokens': int(group['Output Tokens'].sum()),
                'total_cache_read': int(group['Cache Read'].sum()),
                'total_tokens': int(group['Total Tokens'].sum()),
                'average_cost_per_request': float(group['Cost'].mean()) if len(group) > 0 else 0.0,
            }
        
        return kind_stats
    
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
        if start_date and end_date:
            df = self.load_date_range(start_date, end_date)
        else:
            dfs = []
            for date_str in self._date_list:
                df = self.load_csv(date_str)
                if df is not None:
                    dfs.append(df)
            if not dfs:
                return {}
            df = pd.concat(dfs, ignore_index=True)
        
        if df.empty:
            return {}
        
        # 过滤掉 "Aborted, Not Charged" 的记录
        df_filtered = df[df['Kind'] != 'Aborted, Not Charged'].copy()
        
        model_stats = {}
        for model, group in df_filtered.groupby('Model'):
            model_stats[model] = {
                'model': model,
                'total_requests': len(group),
                'total_cost': float(group['Cost'].sum()),
                'total_input_tokens': int(group['Input (w/ Cache Write)'].sum() + 
                                         group['Input (w/o Cache Write)'].sum()),
                'total_output_tokens': int(group['Output Tokens'].sum()),
                'total_cache_read': int(group['Cache Read'].sum()),
                'total_tokens': int(group['Total Tokens'].sum()),
                'average_cost_per_request': float(group['Cost'].mean()) if len(group) > 0 else 0.0,
            }
        
        return model_stats
    
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
        if start_date and end_date:
            df = self.load_date_range(start_date, end_date)
        else:
            dfs = []
            for date_str in self._date_list:
                df = self.load_csv(date_str)
                if df is not None:
                    dfs.append(df)
            if not dfs:
                return {}
            df = pd.concat(dfs, ignore_index=True)
        
        if df.empty:
            return {}
        
        # 过滤掉 "Aborted, Not Charged" 的记录
        df_filtered = df[df['Kind'] != 'Aborted, Not Charged'].copy()
        
        # 提取小时
        df_filtered['Hour'] = df_filtered['Date'].dt.hour
        
        hourly_stats = {}
        for hour, group in df_filtered.groupby('Hour'):
            hourly_stats[int(hour)] = {
                'hour': int(hour),
                'total_requests': len(group),
                'total_cost': float(group['Cost'].sum()),
                'total_tokens': int(group['Total Tokens'].sum()),
            }
        
        return hourly_stats
    
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
        if start_date and end_date:
            df = self.load_date_range(start_date, end_date)
        else:
            dfs = []
            for date_str in self._date_list:
                df = self.load_csv(date_str)
                if df is not None:
                    dfs.append(df)
            if not dfs:
                return {}
            df = pd.concat(dfs, ignore_index=True)
        
        if df.empty:
            return {}
        
        # 过滤掉 "Aborted, Not Charged" 的记录
        df_filtered = df[df['Kind'] != 'Aborted, Not Charged'].copy()
        
        # 按 Kind 和 Model 分组统计
        stats = {
            'free': {
                'total_cost': 0.0,
                'total_requests': 0,
                'auto_cost': 0.0,  # auto 的费用仅作参考
                'auto_requests': 0,
                'models': {}  # 其他模型的费用
            },
            'Included': {
                'total_cost': 0.0,
                'total_requests': 0,
                'auto_cost': 0.0,  # auto 的费用仅作参考
                'auto_requests': 0,
                'models': {}  # 其他模型的费用
            }
        }
        
        for _, row in df_filtered.iterrows():
            kind = row['Kind']
            model = row['Model']
            cost = float(row['Cost'])
            
            if kind not in stats:
                continue
            
            stats[kind]['total_cost'] += cost
            stats[kind]['total_requests'] += 1
            
            if model == 'auto':
                stats[kind]['auto_cost'] += cost
                stats[kind]['auto_requests'] += 1
            else:
                if model not in stats[kind]['models']:
                    stats[kind]['models'][model] = {
                        'model': model,
                        'total_cost': 0.0,
                        'total_requests': 0,
                        'total_tokens': 0,
                    }
                stats[kind]['models'][model]['total_cost'] += cost
                stats[kind]['models'][model]['total_requests'] += 1
                stats[kind]['models'][model]['total_tokens'] += int(row['Total Tokens'])
        
        return stats
    
    def _empty_statistics(self) -> Dict[str, Any]:
        """返回空的统计信息"""
        return {
            'total_requests': 0,
            'total_cost': 0.0,
            'total_input_tokens': 0,
            'total_output_tokens': 0,
            'total_cache_read': 0,
            'total_tokens': 0,
            'average_cost_per_request': 0.0,
            'average_tokens_per_request': 0.0,
        }

