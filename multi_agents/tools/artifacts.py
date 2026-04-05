# -*- coding: utf-8 -*-
"""
Artifact management utilities for the LangGraph multi-agent system.

Handles output directories, file generation, and ALB-compatible file entries.
"""

import os
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

from multi_agents.settings import get_settings
from multi_agents.tools.logger import get_logger
from multi_agents.tools.ids import task_dir_name

logger = get_logger("artifacts")


# MIME type mappings
MEDIA_TYPES = {
    ".md": "text/markdown",
    ".html": "text/html",
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".json": "application/json",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}


def ensure_task_dir(base_dir: Optional[Path] = None, task_id: str = "") -> Path:
    """
    Ensure the task output directory exists.
    
    Args:
        base_dir: Base output directory (defaults to settings)
        task_id: Task identifier
    
    Returns:
        Path to the task directory
    """
    settings = get_settings()
    base = base_dir or settings.report_output_dir
    
    task_dir = Path(base) / task_dir_name(task_id)
    task_dir.mkdir(parents=True, exist_ok=True)
    
    # Also create assets subdirectory
    (task_dir / "assets").mkdir(exist_ok=True)
    
    return task_dir


def write_text_file(path: Path, content: str, encoding: str = "utf-8") -> None:
    """
    Write text content to a file.
    
    Args:
        path: File path
        content: Text content
        encoding: Text encoding
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding=encoding)
    logger.info(f"Written text file: {path}")


def write_json_file(path: Path, data: Dict[str, Any], indent: int = 2) -> None:
    """
    Write JSON data to a file.
    
    Args:
        path: File path
        data: Data to serialize
        indent: JSON indentation
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=indent)
    logger.info(f"Written JSON file: {path}")


def build_file_entry(
    abs_path: Path,
    public_base_url: str,
    task_id: str,
    media_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    Build an ALB-compatible file entry.
    
    Args:
        abs_path: Absolute path to the file
        public_base_url: Base URL for public access
        task_id: Task identifier
        media_type: MIME type (auto-detected if not provided)
    
    Returns:
        File entry dict for state.files
    """
    filename = abs_path.name
    suffix = abs_path.suffix.lower()
    
    # Auto-detect media type
    if media_type is None:
        media_type = MEDIA_TYPES.get(suffix, "application/octet-stream")
    
    # Build URL
    relative_path = f"{task_dir_name(task_id)}/{filename}"
    url = f"{public_base_url.rstrip('/')}/{relative_path}"
    
    return {
        "filename": filename,
        "url": url,
        "media_type": media_type,
        "created_at": datetime.now().isoformat(),
    }


def build_state_files(task_dir: Path, task_id: str) -> Dict[str, Dict[str, Any]]:
    """
    Build state.files from all files in the task directory.
    
    Args:
        task_dir: Task directory path
        task_id: Task identifier
    
    Returns:
        Dict mapping file paths to file entries
    """
    settings = get_settings()
    files = {}
    
    # Collect all files
    for file_path in task_dir.rglob("*"):
        if file_path.is_file():
            entry = build_file_entry(
                file_path,
                settings.public_report_base_url,
                task_id
            )
            # Use relative path as key
            rel_path = str(file_path.relative_to(task_dir.parent))
            files[rel_path] = entry
    
    return files


def generate_answer_md(merged_result: Dict[str, Any], task_id: str) -> str:
    """
    Generate the answer.md summary file content.
    
    Args:
        merged_result: Merged analysis result
        task_id: Task identifier
    
    Returns:
        Markdown content
    """
    lines = [
        "# 舆情分析摘要",
        "",
        f"**任务ID**: {task_id}",
        f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## 核心结论",
        "",
    ]
    
    # Add core conclusions
    conclusions = merged_result.get("core_conclusions", [])
    for i, conclusion in enumerate(conclusions, 1):
        lines.append(f"{i}. {conclusion}")
    
    lines.extend(["", "## 风险点", ""])
    
    # Add risk points
    risks = merged_result.get("risk_points", [])
    for risk in risks:
        lines.append(f"- ⚠️ {risk}")
    
    lines.extend(["", "## 机会点", ""])
    
    # Add opportunities
    opportunities = merged_result.get("opportunities", [])
    for opp in opportunities:
        lines.append(f"- ✅ {opp}")
    
    lines.extend(["", "## 关键证据", ""])
    
    # Add key evidence
    evidence = merged_result.get("key_evidence", [])
    for item in evidence[:5]:  # Limit to top 5
        title = item.get("title", "")
        source = item.get("source", "")
        lines.append(f"- {title} ({source})")
    
    return "\n".join(lines)


def generate_manifest(
    task_id: str,
    query: str,
    selected_kbs: List[str],
    files: List[str],
    stats: Dict[str, Any],
    duration_seconds: float = 0.0
) -> Dict[str, Any]:
    """
    Generate the manifest.json content.
    
    Args:
        task_id: Task identifier
        query: Original query
        selected_kbs: Selected knowledge base IDs
        files: List of generated file paths
        stats: Execution statistics
        duration_seconds: Total execution time
    
    Returns:
        Manifest dict
    """
    settings = get_settings()
    
    return {
        "task_id": task_id,
        "query": query,
        "timestamp": datetime.now().isoformat(),
        "selected_knowledge_bases": selected_kbs,
        "models_used": {
            "planner": settings.llm_planner_model,
            "analysis": settings.llm_analysis_model,
            "moderator": settings.llm_moderator_model,
            "report": settings.llm_report_model,
        },
        "files": files,
        "stats": stats,
        "duration_seconds": duration_seconds,
        "status": "completed",
    }


def cleanup_old_tasks(base_dir: Optional[Path] = None, max_age_days: int = 7) -> int:
    """
    Clean up old task directories.
    
    Args:
        base_dir: Base output directory
        max_age_days: Maximum age in days
    
    Returns:
        Number of directories removed
    """
    import shutil
    from datetime import timedelta
    
    settings = get_settings()
    base = base_dir or settings.report_output_dir
    
    if not base.exists():
        return 0
    
    cutoff = datetime.now() - timedelta(days=max_age_days)
    removed = 0
    
    for task_dir in base.iterdir():
        if task_dir.is_dir() and task_dir.name.startswith("task_"):
            # Check modification time
            mtime = datetime.fromtimestamp(task_dir.stat().st_mtime)
            if mtime < cutoff:
                try:
                    shutil.rmtree(task_dir)
                    removed += 1
                    logger.info(f"Removed old task directory: {task_dir}")
                except Exception as e:
                    logger.error(f"Failed to remove {task_dir}: {e}")
    
    return removed


# ==== Test helper functions ====

def add_file_to_state(
    state: Dict[str, Any],
    name: str,
    path: str,
    media_type: str
) -> Dict[str, Any]:
    """
    Add a file entry to state.files.
    
    Args:
        state: Current state
        name: File name
        path: File path
        media_type: MIME type
    
    Returns:
        Updated state
    """
    files = dict(state.get("files", {}))
    files[name] = {
        "name": name,
        "path": path,
        "mediaType": media_type,
        "created_at": datetime.now().isoformat(),
    }
    return {**state, "files": files}


def build_public_url(
    filename: str,
    task_id: str = "",
    base_url: str = ""
) -> str:
    """
    Build a public URL for a file.
    
    Args:
        filename: File name
        task_id: Task ID (optional)
        base_url: Base URL (defaults to settings)
    
    Returns:
        Public URL
    """
    if not base_url:
        settings = get_settings()
        base_url = settings.public_report_base_url
    
    base_url = base_url.rstrip("/")
    
    if task_id:
        return f"{base_url}/{task_dir_name(task_id)}/{filename}"
    return f"{base_url}/{filename}"
    
    return removed
