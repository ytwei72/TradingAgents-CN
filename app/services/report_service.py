"""
Report service for fetching analysis reports from file system.
"""

from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict, Any
import logging
import subprocess
import time

from app.schemas.report import AnalysisReport, REPORT_DISPLAY_NAMES
from tradingagents.tasks import get_task_manager
from tradingagents.storage.mongodb.report_manager import mongodb_report_manager

logger = logging.getLogger(__name__)


def get_reports_from_fs(analysis_id: str, stage: Optional[str] = None, report_date: Optional[str] = None) -> List[AnalysisReport]:
    """
    Fetch reports for a given analysis_id, optionally filtered by stage and report_date.

    :param analysis_id: The analysis task ID
    :param stage: Optional stage to filter reports (e.g., "market_analyst")
    :param report_date: Optional report date to filter (format: "YYYY-MM-DD")
    :return: List of Report objects, sorted by created_at
    :raises ValueError: If analysis not found
    """
    # Validate analysis exists
    task_manager = get_task_manager()
    task_status = task_manager.get_task_status(analysis_id)
    if not task_status:
        raise ValueError("Analysis task not found")

    # Get config from task status
    config = task_status.get('config', {})
    stock_symbol = task_status.get('stock_symbol') or analysis_id
    results_dir = Path(config.get('results_dir', 'results')) / stock_symbol
    if not results_dir.exists():
        raise ValueError("Results directory not found")

    reports: List[AnalysisReport] = []

    # Scan date directories
    if report_date:
        try:
            target_date = datetime.strptime(report_date, '%Y-%m-%d').strftime('%Y-%m-%d')
            date_dir = results_dir / target_date
            if date_dir.is_dir():
                reports_path = date_dir / "reports"
                if reports_path.exists() and reports_path.is_dir():
                    for md_file in reports_path.glob("*.md"):
                        try:
                            with open(md_file, 'r', encoding='utf-8') as f:
                                content = f.read()

                            # Extract title from first # line
                            lines = [line.strip() for line in content.split('\n')]
                            title = ""
                            for line in lines:
                                if line.startswith('# '):
                                    title = line[2:].strip()
                                    break
                            if not title:
                                title = md_file.stem.replace('_', ' ').title()

                            # Map filename to stage
                            filename_lower = md_file.stem.lower()
                            if 'final_trade_decision' in filename_lower:
                                stage_name = "final_decision"
                            elif 'market_analyst' in filename_lower:
                                stage_name = "market_analyst"
                            elif 'news_analyst' in filename_lower:
                                stage_name = "news_analyst"
                            else:
                                stage_name = md_file.stem.replace('_', ' ').title()

                            if stage is None or stage_name.lower() == stage.lower():
                                created_at = datetime.fromtimestamp(md_file.stat().st_mtime)

                                reports.append(AnalysisReport(
                                    report_id=md_file.stem,
                                    title=title,
                                    stage=stage_name,
                                    content=content,
                                    created_at=created_at,
                                    file_path=str(md_file)
                                ))
                        except Exception as e:
                            logger.error(f"Error reading report file {md_file}: {e}")
                            continue
        except ValueError:
            raise ValueError(f"Invalid report_date format: {report_date}. Expected 'YYYY-MM-DD'")
    else:
        for date_dir in results_dir.iterdir():
            if date_dir.is_dir():
                reports_path = date_dir / "reports"
                if reports_path.exists() and reports_path.is_dir():
                    for md_file in reports_path.glob("*.md"):
                        try:
                            with open(md_file, 'r', encoding='utf-8') as f:
                                content = f.read()

                            # Extract title from first # line
                            lines = [line.strip() for line in content.split('\n')]
                            title = ""
                            for line in lines:
                                if line.startswith('# '):
                                    title = line[2:].strip()
                                    break
                            if not title:
                                title = md_file.stem.replace('_', ' ').title()

                            # Map filename to stage
                            filename_lower = md_file.stem.lower()
                            if 'final_trade_decision' in filename_lower:
                                stage_name = "final_decision"
                            elif 'market_analyst' in filename_lower:
                                stage_name = "market_analyst"
                            elif 'news_analyst' in filename_lower:
                                stage_name = "news_analyst"
                            else:
                                stage_name = md_file.stem.replace('_', ' ').title()

                            if stage is None or stage_name.lower() == stage.lower():
                                created_at = datetime.fromtimestamp(md_file.stat().st_mtime)

                                reports.append(AnalysisReport(
                                    report_id=md_file.stem,
                                    title=title,
                                    stage=stage_name,
                                    content=content,
                                    created_at=created_at,
                                    file_path=str(md_file)
                                ))
                        except Exception as e:
                            logger.error(f"Error reading report file {md_file}: {e}")
                            continue

    return sorted(reports, key=lambda r: r.created_at)


def get_reports_from_db(analysis_id: str, stage: Optional[str] = None) -> List[AnalysisReport]:
    """
    Fetch reports from database for a given analysis_id, optionally filtered by stage.

    :param analysis_id: The analysis task ID
    :param stage: Optional stage to filter reports (e.g., "market_analyst")
    :return: List of Report objects, sorted by created_at
    :raises ValueError: If analysis not found or no reports
    """
    # Validate analysis exists
    task_manager = get_task_manager()
    task_status = task_manager.get_task_status(analysis_id)
    if not task_status:
        raise ValueError("Analysis task not found")

    # Get report document from MongoDB
    report_doc = mongodb_report_manager.get_report_by_id(analysis_id)
    if not report_doc:
        raise ValueError("No report found in database for analysis_id")

    reports_data = report_doc.get("reports", {})
    reports: List[AnalysisReport] = []

    for stage_name, content in reports_data.items():
        if stage is None or stage_name.lower() == stage.lower():
            stage_display_name = REPORT_DISPLAY_NAMES.get(stage_name, None)
            if not stage_display_name:
                continue

            # Extract title from first # line
            lines = [line.strip() for line in content.split('\n')]
            title = ""
            for line in lines:
                if line.startswith('# '):
                    title = line[2:].strip()
                    break
            if not title:
                title = stage_name.replace('_', ' ').title()

            # Use document timestamp for created_at
            timestamp = report_doc.get("timestamp")
            if isinstance(timestamp, datetime):
                created_at = timestamp
            else:
                created_at = datetime.fromtimestamp(float(timestamp)) if timestamp else datetime.now()
            
            reports.append(
                AnalysisReport(
                    title=title,
                    stage=stage_name,
                    stage_display_name=stage_display_name,
                    content=content,
                    created_at=created_at,
                    # file_path not set, defaults to None
                )
            )

    if not reports:
        raise ValueError("No reports found matching the criteria")

    # Sort by created_at (though all should be same, but to match FS)
    return sorted(reports, key=lambda r: r.created_at)


class ReportService:
    def __init__(self):
        self.results_dir = None  # Will be set per operation

    def generate_report(self, analysis_results: Dict[str, Any], format_type: str, analysis_id: str) -> tuple[str, Path, str]:
        if format_type not in ['markdown', 'pdf', 'docx']:
            raise ValueError(f"Unsupported format: {format_type}")

        # Get results_dir from config
        config = analysis_results.get('config', {})
        results_dir = config.get('results_dir', 'results')
        self.results_dir = Path(results_dir)

        # Get date for directory
        analysis_date_str = analysis_results.get('analysis_date')
        if analysis_date_str:
            try:
                date_obj = datetime.strptime(analysis_date_str, '%Y-%m-%d').date()
            except ValueError:
                date_obj = datetime.now().date()
        else:
            date_obj = datetime.now().date()

        reports_dir = self.results_dir / analysis_id / date_obj.strftime('%Y-%m-%d') / 'reports'
        reports_dir.mkdir(parents=True, exist_ok=True)

        base_name = f"{analysis_id}_{int(time.time())}"
        md_filename = f"{base_name}.md"
        md_path = reports_dir / md_filename

        # Generate markdown
        md_content = self._generate_markdown_content(analysis_results)
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(md_content)

        if format_type == 'markdown':
            file_path = md_path
            report_id = md_filename
            message = "Markdown report generated successfully"
        else:
            if format_type == 'pdf':
                output_path = reports_dir / f"{base_name}.pdf"
                try:
                    subprocess.run(['pandoc', str(md_path), '-o', str(output_path)], check=True, capture_output=True)
                except subprocess.CalledProcessError:
                    raise ValueError("Failed to generate PDF. Ensure pandoc is installed.")
            elif format_type == 'docx':
                output_path = reports_dir / f"{base_name}.docx"
                try:
                    subprocess.run(['pandoc', '-f', 'markdown', str(md_path), '-o', str(output_path)], check=True, capture_output=True)
                except subprocess.CalledProcessError:
                    raise ValueError("Failed to generate DOCX. Ensure pandoc is installed.")

            file_path = output_path
            report_id = output_path.name
            message = f"{format_type.upper()} report generated successfully"

        return report_id, file_path, message

    def _generate_markdown_content(self, analysis_results: Dict[str, Any]) -> str:
        stock_symbol = analysis_results.get('stock_symbol', 'Unknown Stock')
        content = f"# 投资分析报告 - {stock_symbol}\n\n"
        content += f"**分析ID**: {analysis_results.get('analysis_id', 'N/A')}\n"
        content += f"**分析日期**: {analysis_results.get('analysis_date', 'N/A')}\n\n"

        if summary := analysis_results.get('summary'):
            content += "## 执行摘要\n\n"
            content += f"{summary}\n\n"

        if analysts := analysis_results.get('analysts'):
            content += "## 分析团队\n\n"
            content += "参与分析师: " + ", ".join(analysts) + "\n\n"

        # Research depth
        research_depth = analysis_results.get('research_depth', 1)
        content += f"## 研究深度\n\n深度级别: {research_depth}/5\n\n"

        # Reports sections
        reports = analysis_results.get('reports', {})
        for stage, report_data in reports.items():
            content += f"## {stage.replace('_', ' ').title()} 分析\n\n"
            if isinstance(report_data, dict) and 'content' in report_data:
                content += f"{report_data['content']}\n\n"
            else:
                content += f"{report_data}\n\n"

        # Decision
        decision = analysis_results.get('decision', {})
        if decision:
            content += "## 投资决策\n\n"
            if 'recommendation' in decision:
                content += f"**推荐**: {decision['recommendation']}\n\n"
            if 'confidence' in decision:
                content += f"**置信度**: {decision['confidence']}%\n\n"
            if 'rationale' in decision:
                content += f"**理由**: {decision['rationale']}\n\n"
            content += "---\n\n"

        content += f"*报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*"

        return content

    def get_report_path(self, report_filename: str, analysis_id: str = None) -> Optional[Path]:
        """
        Find the full path to a report file by its filename.

        :param report_filename: The filename of the report (with extension)
        :param analysis_id: Analysis ID to get config
        :return: Path to the file if found, else None
        """
        if not analysis_id:
            return None

        task_manager = get_task_manager()
        task_status = task_manager.get_task_status(analysis_id)
        if not task_status:
            logger.error(f"Task status not found for {analysis_id}")
            return None

        config = task_status.get('config', {})
        results_dir = config.get('results_dir', 'results')
        self.results_dir = Path(results_dir)

        try:
            for analysis_dir in self.results_dir.iterdir():
                if analysis_dir.is_dir():
                    for date_dir in analysis_dir.iterdir():
                        if date_dir.is_dir():
                            reports_path = date_dir / "reports"
                            if reports_path.exists() and reports_path.is_dir():
                                candidate_path = reports_path / report_filename
                                if candidate_path.exists():
                                    return candidate_path
        except Exception as e:
            logger.error(f"Error searching for report {report_filename}: {e}")

        return None


report_service = ReportService()
