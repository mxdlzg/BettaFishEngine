# -*- coding: utf-8 -*-
"""
Artifacts node for the LangGraph public opinion workflow.

Packages output files and prepares state.files for ALB frontend.
"""

from typing import Any, Optional
from langchain_core.runnables import RunnableConfig
from pathlib import Path
from datetime import datetime

from multi_agents.state import PublicOpinionState, StateUpdate
from multi_agents.tools.progress import add_progress, Stage
from multi_agents.tools.logger import get_logger, log_node_start, log_node_end
from multi_agents.tools.artifacts import (
    ensure_task_dir,
    write_text_file,
    write_json_file,
    build_state_files,
    generate_answer_md,
    generate_manifest,
)
from multi_agents.settings import get_settings

logger = get_logger("artifacts_node")


def artifacts_node(state: PublicOpinionState, config: Optional[RunnableConfig] = None) -> StateUpdate:
    """
    Artifacts node: Package output files.
    
    This node:
    1. Creates answer.md summary
    2. Creates manifest.json
    3. Copies/links report files
    4. Builds state.files for ALB frontend
    
    Args:
        state: Current graph state
        config: Configuration
    
    Returns:
        State updates with artifacts and files
    """
    task_id = state.get("task_id", "unknown")
    log_node_start(logger, "artifacts", task_id)
    
    updates: StateUpdate = {}
    add_progress(updates, Stage.ARTIFACT_PACKAGING)
    
    settings = get_settings()
    
    try:
        # Ensure task directory
        task_dir = ensure_task_dir(settings.report_output_dir, task_id)
        
        # Get data for artifacts
        query = state.get("query", "")
        merged_result = state.get("merged_result", {})
        report_result = state.get("report_result", {})
        auto_selected_kbs = state.get("auto_selected_knowledge_bases", [])
        
        # Calculate duration
        progress_log = state.get("progress_log", [])
        start_ts = progress_log[0]["ts"] if progress_log else datetime.now().timestamp()
        duration = datetime.now().timestamp() - start_ts
        
        # 1. Generate answer.md
        answer_content = generate_answer_md(merged_result, task_id)
        answer_path = task_dir / "answer.md"
        write_text_file(answer_path, answer_content)
        
        # 2. Generate manifest.json
        file_list = []
        if report_result.get("html_path"):
            file_list.append(report_result["html_path"])
        if report_result.get("pdf_path"):
            file_list.append(report_result["pdf_path"])
        if report_result.get("md_path"):
            file_list.append(report_result["md_path"])
        file_list.append(str(answer_path))
        
        manifest = generate_manifest(
            task_id=task_id,
            query=query,
            selected_kbs=[kb.get("id", "") for kb in auto_selected_kbs],
            files=file_list,
            stats=merged_result.get("stats", {}),
            duration_seconds=duration,
        )
        manifest_path = task_dir / "manifest.json"
        write_json_file(manifest_path, manifest)
        
        # 3. Copy report files if they're outside task_dir
        html_path = report_result.get("html_path", "")
        pdf_path = report_result.get("pdf_path", "")
        
        if html_path and Path(html_path).exists():
            # Copy to task dir if not already there
            if str(task_dir) not in html_path:
                import shutil
                dest = task_dir / "report.html"
                shutil.copy2(html_path, dest)
                html_path = str(dest)
        
        if pdf_path and Path(pdf_path).exists():
            if str(task_dir) not in pdf_path:
                import shutil
                dest = task_dir / "report.pdf"
                shutil.copy2(pdf_path, dest)
                pdf_path = str(dest)
        
        # 4. Build state.files
        files = build_state_files(task_dir, task_id)
        
        # 5. Build artifacts result
        artifacts = {
            "task_id": task_id,
            "answer_md_path": str(answer_path),
            "html_path": html_path,
            "pdf_path": pdf_path,
            "docx_path": "",
            "manifest_path": str(manifest_path),
            "chart_paths": report_result.get("chart_paths", []),
        }
        
        updates["artifacts"] = artifacts
        updates["files"] = files
        
        logger.info(f"[{task_id}] Artifacts packaged: {len(files)} files")
        
    except Exception as e:
        logger.exception(f"[{task_id}] Artifacts packaging failed: {e}")
        
        updates["artifacts"] = {
            "task_id": task_id,
            "answer_md_path": "",
            "html_path": "",
            "pdf_path": "",
            "docx_path": "",
            "manifest_path": "",
            "chart_paths": [],
        }
        updates["files"] = {}
        updates["errors"] = state.get("errors", []) + [f"Artifacts error: {str(e)}"]
    
    log_node_end(logger, "artifacts", task_id)
    return updates
