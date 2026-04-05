# -*- coding: utf-8 -*-
"""
Progress tracking utilities for the LangGraph multi-agent system.

Provides standardized progress logging and frontend updates.
"""

import time
from typing import Dict, Any, List, Optional
from enum import Enum

from multi_agents.tools.logger import get_logger

logger = get_logger("progress")


class Stage(str, Enum):
    """Standard stage names for progress tracking."""
    CREATED = "created"
    PLANNING = "planning"
    QUERYING = "querying"
    MEDIA_ANALYZING = "media_analyzing"
    INSIGHT_ANALYZING = "insight_analyzing"
    KB_QUERYING = "kb_querying"
    FORUM_ROUND_1 = "forum_round_1"
    FORUM_ROUND_2 = "forum_round_2"
    FORUM_ROUND_3 = "forum_round_3"
    MERGING = "merging"
    REPORT_GENERATING = "report_generating"
    ARTIFACT_PACKAGING = "artifact_packaging"
    COMPLETED = "completed"
    FAILED = "failed"


# User-friendly messages for each stage
STAGE_MESSAGES = {
    Stage.CREATED: "已创建分析任务",
    Stage.PLANNING: "正在制定分析计划",
    Stage.QUERYING: "正在检索公开信息",
    Stage.MEDIA_ANALYZING: "正在分析媒体与评论",
    Stage.INSIGHT_ANALYZING: "正在进行情感与主题洞察",
    Stage.KB_QUERYING: "正在查询知识库",
    Stage.FORUM_ROUND_1: "正在进行第一轮综合分析",
    Stage.FORUM_ROUND_2: "正在进行第二轮综合分析",
    Stage.FORUM_ROUND_3: "正在进行第三轮综合分析",
    Stage.MERGING: "正在整合分析结果",
    Stage.REPORT_GENERATING: "正在生成完整报告",
    Stage.ARTIFACT_PACKAGING: "正在整理附件",
    Stage.COMPLETED: "分析完成",
    Stage.FAILED: "分析失败",
}


def add_progress(
    state: Dict[str, Any],
    stage: str,
    message: Optional[str] = None
) -> Dict[str, Any]:
    """
    Add a progress entry to the state.
    
    Args:
        state: Current state dict
        stage: Stage identifier
        message: Optional custom message (defaults to standard message)
    
    Returns:
        Updated state dict
    """
    # Get message
    if message is None:
        message = STAGE_MESSAGES.get(stage, stage)
    
    # Create progress item
    item = {
        "ts": time.time(),
        "stage": stage,
        "message": message
    }
    
    # Add to state
    progress_log = state.get("progress_log", [])
    progress_log.append(item)
    state["progress_log"] = progress_log
    
    # Log it
    task_id = state.get("task_id", "unknown")
    logger.info(f"[{task_id}] Progress: {stage} - {message}")
    
    return state


def get_progress_text(state: Dict[str, Any]) -> str:
    """
    Get a human-readable progress summary.
    
    Args:
        state: Current state dict
    
    Returns:
        Progress summary text
    """
    progress_log = state.get("progress_log", [])
    if not progress_log:
        return "No progress recorded"
    
    lines = []
    for item in progress_log:
        ts = item.get("ts", 0)
        stage = item.get("stage", "unknown")
        message = item.get("message", "")
        
        # Format timestamp
        from datetime import datetime
        dt = datetime.fromtimestamp(ts)
        time_str = dt.strftime("%H:%M:%S")
        
        lines.append(f"[{time_str}] {message}")
    
    return "\n".join(lines)


def get_current_stage(state: Dict[str, Any]) -> Optional[str]:
    """
    Get the current (most recent) stage.
    
    Args:
        state: Current state dict
    
    Returns:
        Current stage or None
    """
    progress_log = state.get("progress_log", [])
    if progress_log:
        return progress_log[-1].get("stage")
    return None


def mark_failed(state: Dict[str, Any], error_message: str) -> Dict[str, Any]:
    """
    Mark the task as failed.
    
    Args:
        state: Current state dict
        error_message: Error description
    
    Returns:
        Updated state dict
    """
    # Add to errors list
    errors = state.get("errors", [])
    errors.append(error_message)
    state["errors"] = errors
    
    # Add progress entry
    add_progress(state, Stage.FAILED, f"分析失败: {error_message}")
    
    return state


def format_tool_event(
    tool_name: str,
    status: str = "running",
    details: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Format a tool event for frontend display.
    
    Args:
        tool_name: Name of the tool
        status: Tool status (running, completed, failed)
        details: Optional additional details
    
    Returns:
        Tool event dict
    """
    event = {
        "type": "tool_event",
        "tool": tool_name,
        "status": status,
        "timestamp": time.time(),
    }
    if details:
        event["details"] = details
    return event


# Tool name mappings for frontend display
TOOL_DISPLAY_NAMES = {
    "query_engine": "公开信息检索",
    "media_engine": "媒体内容分析",
    "insight_engine": "情感主题洞察",
    "kb_mcp": "知识库查询",
    "forum_round": "多轮综合分析",
    "report_engine": "报告生成",
}


def get_tool_display_name(tool_name: str) -> str:
    """Get user-friendly tool name for display."""
    return TOOL_DISPLAY_NAMES.get(tool_name, tool_name)
