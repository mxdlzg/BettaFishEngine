# -*- coding: utf-8 -*-
"""
ID generation utilities for the LangGraph multi-agent system.

Provides consistent ID generation for tasks, traces, and other identifiers.
"""

import uuid
from datetime import datetime


def generate_task_id(prefix: str = "po") -> str:
    """
    Generate a unique task ID.
    
    Args:
        prefix: Prefix for the task ID (default: "po" for public opinion)
    
    Returns:
        A unique task ID in format: {prefix}_{timestamp}_{short_uuid}
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    short_uuid = uuid.uuid4().hex[:8]
    return f"{prefix}_{timestamp}_{short_uuid}"


def generate_trace_id() -> str:
    """
    Generate a unique trace ID for logging and debugging.
    
    Returns:
        A UUID string
    """
    return str(uuid.uuid4())


def generate_short_id() -> str:
    """
    Generate a short unique ID.
    
    Returns:
        An 8-character hex string
    """
    return uuid.uuid4().hex[:8]


def task_dir_name(task_id: str) -> str:
    """
    Generate a directory name for a task.
    
    Args:
        task_id: The task ID
    
    Returns:
        Directory name in format: task_{task_id}
    """
    return f"task_{task_id}"
