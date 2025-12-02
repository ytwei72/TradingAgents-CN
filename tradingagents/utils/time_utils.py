#!/usr/bin/env python3
"""
Time Utilities

时间工具类，提供统一的时间格式转换功能
"""

from datetime import datetime
from typing import Union, Optional
from enum import Enum


class TimeGranularity(Enum):
    """时间颗粒度枚举"""
    DAY = "day"      # 天级别：%Y-%m-%d
    SECOND = "second"  # 秒级别：%Y-%m-%d %H:%M:%S


class TaTimes:
    """TradingAgents 时间工具类"""
    
    # 默认格式映射
    DEFAULT_FORMATS = {
        TimeGranularity.DAY: '%Y-%m-%d',
        TimeGranularity.SECOND: '%Y-%m-%d %H:%M:%S'
    }
    
    # 常用的时间格式列表，用于自动解析
    COMMON_FORMATS = [
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%d',
        '%Y/%m/%d %H:%M:%S',
        '%Y/%m/%d',
        '%Y%m%d',
        '%Y%m%d%H%M%S',
        '%Y-%m-%dT%H:%M:%S',
        '%Y-%m-%dT%H:%M:%S.%f',
    ]
    
    @staticmethod
    def convert_format(
        time_input: Union[datetime, str],
        granularity: TimeGranularity = TimeGranularity.DAY,
        format_str: Optional[str] = None
    ) -> str:
        """
        转换时间格式
        
        Args:
            time_input: 时间输入，支持 datetime 对象或字符串
            granularity: 时间颗粒度，默认为天级别
            format_str: 输出格式字符串，如果为 None 则根据颗粒度自动选择
            
        Returns:
            格式化后的时间字符串
            
        Raises:
            ValueError: 当输入的时间字符串无法解析时
            TypeError: 当输入类型不支持时
            
        Examples:
            >>> TaTimes.convert_format(datetime.now(), TimeGranularity.DAY)
            '2025-12-02'
            
            >>> TaTimes.convert_format('2025-12-02 11:30:00', TimeGranularity.DAY)
            '2025-12-02'
            
            >>> TaTimes.convert_format('2025-12-02', TimeGranularity.SECOND)
            '2025-12-02 00:00:00'
            
            >>> TaTimes.convert_format('2025-12-02 11:30:00', format_str='%Y%m%d')
            '20251202'
        """
        # 确定输出格式
        output_format = format_str or TaTimes.DEFAULT_FORMATS[granularity]
        
        # 如果输入已经是 datetime 对象，直接格式化
        if isinstance(time_input, datetime):
            return time_input.strftime(output_format)
        
        # 如果输入是字符串，先解析为 datetime
        if isinstance(time_input, str):
            dt = TaTimes._parse_datetime(time_input)
            return dt.strftime(output_format)
        
        # 不支持的类型
        raise TypeError(
            f"不支持的时间输入类型: {type(time_input).__name__}。"
            f"仅支持 datetime 或 str 类型"
        )
    
    @staticmethod
    def _parse_datetime(time_str: str) -> datetime:
        """
        解析时间字符串为 datetime 对象
        
        Args:
            time_str: 时间字符串
            
        Returns:
            datetime 对象
            
        Raises:
            ValueError: 当无法解析时间字符串时
        """
        # 尝试使用常用格式解析
        for fmt in TaTimes.COMMON_FORMATS:
            try:
                return datetime.strptime(time_str, fmt)
            except ValueError:
                continue
        
        # 尝试 ISO 格式解析
        try:
            return datetime.fromisoformat(time_str)
        except ValueError:
            pass
        
        # 所有格式都失败
        raise ValueError(
            f"无法解析时间字符串: '{time_str}'。"
            f"支持的格式包括: {', '.join(TaTimes.COMMON_FORMATS)}"
        )
    
    @staticmethod
    def to_day_format(time_input: Union[datetime, str]) -> str:
        """
        转换为天级别格式 (%Y-%m-%d)
        
        Args:
            time_input: 时间输入
            
        Returns:
            天级别格式的时间字符串
        """
        return TaTimes.convert_format(time_input, TimeGranularity.DAY)
    
    @staticmethod
    def to_second_format(time_input: Union[datetime, str]) -> str:
        """
        转换为秒级别格式 (%Y-%m-%d %H:%M:%S)
        
        Args:
            time_input: 时间输入
            
        Returns:
            秒级别格式的时间字符串
        """
        return TaTimes.convert_format(time_input, TimeGranularity.SECOND)
