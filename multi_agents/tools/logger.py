# -*- coding: utf-8 -*-
"""
Logging utilities for the LangGraph multi-agent system.

Provides consistent logging across all nodes and tools.
"""

import logging
from typing import Optional
from datetime import datetime


# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)


def get_logger(name: str, task_id: Optional[str] = None) -> logging.Logger:
    """
    Get a logger instance with optional task ID prefix.
    
    Args:
        name: Logger name (usually module or node name)
        task_id: Optional task ID to include in logs
    
    Returns:
        Configured logger instance
    """
    logger_name = f"multi_agents.{name}"
    if task_id:
        logger_name = f"{logger_name}[{task_id}]"
    return logging.getLogger(logger_name)


class TaskLogger:
    """
    A logger wrapper that includes task context in all messages.
    """
    
    def __init__(self, name: str, task_id: str):
        """
        Initialize the task logger.
        
        Args:
            name: Logger name
            task_id: Task ID for context
        """
        self.logger = logging.getLogger(f"multi_agents.{name}")
        self.task_id = task_id
    
    def _format_message(self, message: str) -> str:
        """Format message with task ID prefix."""
        return f"[{self.task_id}] {message}"
    
    def debug(self, message: str, *args, **kwargs):
        self.logger.debug(self._format_message(message), *args, **kwargs)
    
    def info(self, message: str, *args, **kwargs):
        self.logger.info(self._format_message(message), *args, **kwargs)
    
    def warning(self, message: str, *args, **kwargs):
        self.logger.warning(self._format_message(message), *args, **kwargs)
    
    def error(self, message: str, *args, **kwargs):
        self.logger.error(self._format_message(message), *args, **kwargs)
    
    def exception(self, message: str, *args, **kwargs):
        self.logger.exception(self._format_message(message), *args, **kwargs)


def log_node_start(logger: logging.Logger, node_name: str, task_id: str):
    """Log the start of a node execution."""
    logger.info(f"[{task_id}] Starting node: {node_name}")


def log_node_end(logger: logging.Logger, node_name: str, task_id: str, success: bool = True):
    """Log the end of a node execution."""
    status = "completed" if success else "failed"
    logger.info(f"[{task_id}] Node {node_name} {status}")


def log_tool_call(logger: logging.Logger, tool_name: str, task_id: str, params: dict = None):
    """Log a tool invocation."""
    param_str = f" with params: {params}" if params else ""
    logger.info(f"[{task_id}] Calling tool: {tool_name}{param_str}")
