"""
Report service for fetching analysis reports from file system.
"""

from pathlib import Path
from datetime import datetime
from typing import List, Optional
import logging

from app.core.config import settings
from app.schemas.report import Report
from tradingagents.tasks import get_task_manager

logger = logging.getLogger(__name__)

def get_reports(analysis_id: str, stage: Optional[str] = None) -> List[Report]:
    """
    Fetch reports for a given analysis_id, optionally filtered by stage.
    
    :param analysis_id: The analysis task ID
    :param stage: Optional stage to filter reports (e.g., "market_analyst")
    :return: List of Report objects, sorted by created_at
    :raises ValueError: If analysis not found
    """
    # Validate analysis exists
    task_manager = get_task_manager()
    if not task_manager.get_task_status(analysis_id):
        raise ValueError("Analysis task not found")
    
    results_dir = Path(settings.RESULTS_DIR) / analysis_id
    if not results_dir.exists():
        raise ValueError("Results directory not found")
    
    reports: List[Report] = []
    
    # Scan date directories
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
                            
                            reports.append(Report(
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
