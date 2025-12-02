"""
报告服务层
负责报告生成、存储和管理
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

from tradingagents.utils.report_exporter import report_exporter
from tradingagents.utils.mongodb_report_manager import mongodb_report_manager
from tradingagents.utils.logging_manager import get_logger

logger = get_logger('report_service')


class ReportService:
    """报告服务类"""
    
    def __init__(self):
        self.report_exporter = report_exporter
        self.mongodb_manager = mongodb_report_manager
        
        # 获取报告存储目录
        self.reports_base_dir = self._get_reports_base_dir()
        
    def _get_reports_base_dir(self) -> Path:
        """获取报告存储基础目录"""
        # 优先使用环境变量配置
        reports_dir_env = os.getenv("TRADINGAGENTS_RESULTS_DIR")
        if reports_dir_env:
            if not os.path.isabs(reports_dir_env):
                # 相对路径，相对于项目根目录
                project_root = Path(__file__).parent.parent.parent
                reports_dir = project_root / reports_dir_env
            else:
                reports_dir = Path(reports_dir_env)
        else:
            # 默认使用 results 目录
            project_root = Path(__file__).parent.parent.parent
            reports_dir = project_root / "results"
        
        return reports_dir
    
    def generate_report(
        self,
        analysis_results: Dict[str, Any],
        format_type: str = "markdown",
        analysis_id: Optional[str] = None
    ) -> Tuple[str, Optional[str], str]:
        """
        生成报告
        
        Args:
            analysis_results: 分析结果字典
            format_type: 报告格式 (markdown/md/pdf/docx)
            analysis_id: 分析ID（可选）
            
        Returns:
            Tuple[report_id, file_path, message]
        """
        try:
            # 标准化格式类型
            if format_type == "md":
                format_type = "markdown"
            
            # 获取股票代码和分析日期
            stock_symbol = analysis_results.get('stock_symbol', 'UNKNOWN')
            analysis_date = analysis_results.get('analysis_date') or datetime.now().strftime('%Y-%m-%d')
            
            # 生成报告ID
            if analysis_id:
                report_id = f"{analysis_id}_{format_type}"
            else:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                report_id = f"{stock_symbol}_{timestamp}_{format_type}"
            
            # 创建报告存储目录
            stock_dir = self.reports_base_dir / stock_symbol / analysis_date / "reports"
            stock_dir.mkdir(parents=True, exist_ok=True)
            
            # 生成报告内容
            logger.info(f"开始生成 {format_type} 格式报告: {report_id}")
            report_content = self.report_exporter.export_report(analysis_results, format_type)
            
            if report_content is None:
                raise Exception(f"报告生成失败：{format_type} 格式不支持或生成器返回None")
            
            # 确定文件扩展名
            ext_map = {
                "markdown": "md",
                "pdf": "pdf",
                "docx": "docx"
            }
            file_ext = ext_map.get(format_type, "txt")
            
            # 保存报告文件
            file_name = f"report_{analysis_id or datetime.now().strftime('%Y%m%d_%H%M%S')}.{file_ext}"
            file_path = stock_dir / file_name
            
            # 写入文件
            if isinstance(report_content, bytes):
                with open(file_path, 'wb') as f:
                    f.write(report_content)
            else:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(report_content)
            
            logger.info(f"报告已保存到: {file_path}")
            
            # 保存到MongoDB（如果可用）
            if self.mongodb_manager.connected and analysis_id:
                try:
                    # 准备报告内容字典
                    reports_dict = {
                        f"report_{format_type}": str(file_path)
                    }
                    
                    # 保存到MongoDB
                    self.mongodb_manager.save_analysis_report(
                        stock_symbol=stock_symbol,
                        analysis_results=analysis_results,
                        reports=reports_dict,
                        analysis_id=analysis_id
                    )
                    logger.info(f"报告已保存到MongoDB: {analysis_id}")
                except Exception as e:
                    logger.warning(f"保存报告到MongoDB失败: {e}")
            
            return report_id, str(file_path), "报告生成成功"
            
        except Exception as e:
            logger.error(f"生成报告失败: {e}", exc_info=True)
            raise Exception(f"生成报告失败: {str(e)}")
    
    def get_report_path(self, report_id: str) -> Optional[Path]:
        """
        根据report_id获取报告文件路径
        
        Args:
            report_id: 报告ID
            
        Returns:
            报告文件路径，如果不存在返回None
        """
        try:
            # report_id格式: {analysis_id}_{format} 或 {stock_symbol}_{timestamp}_{format}
            # 需要在results目录下搜索
            
            # 简单实现：遍历results目录查找匹配的文件
            for stock_dir in self.reports_base_dir.iterdir():
                if not stock_dir.is_dir():
                    continue
                
                for date_dir in stock_dir.iterdir():
                    if not date_dir.is_dir():
                        continue
                    
                    reports_dir = date_dir / "reports"
                    if not reports_dir.exists():
                        continue
                    
                    # 查找匹配的报告文件
                    for report_file in reports_dir.iterdir():
                        if report_id in report_file.stem:
                            return report_file
            
            # 如果没找到，尝试从MongoDB获取
            if self.mongodb_manager.connected:
                # 提取analysis_id（去掉格式后缀）
                parts = report_id.rsplit('_', 1)
                if len(parts) == 2:
                    analysis_id = parts[0]
                    report_data = self.mongodb_manager.get_report_by_id(analysis_id)
                    if report_data and 'reports' in report_data:
                        # 从reports字段中查找对应格式的报告路径
                        for key, path in report_data['reports'].items():
                            if Path(path).exists():
                                return Path(path)
            
            return None
            
        except Exception as e:
            logger.error(f"获取报告路径失败: {e}")
            return None
    
    def check_report_exists(self, report_id: str) -> bool:
        """检查报告是否存在"""
        return self.get_report_path(report_id) is not None


# 创建全局服务实例
report_service = ReportService()
