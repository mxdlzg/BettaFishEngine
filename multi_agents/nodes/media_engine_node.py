# -*- coding: utf-8 -*-
"""
Media Engine node for the LangGraph public opinion workflow.

Calls the MediaEngine for media/multimedia analysis.
"""

from typing import Dict, Any, Optional

from multi_agents.state import PublicOpinionState, StateUpdate
from multi_agents.tools.progress import add_progress, Stage
from multi_agents.tools.logger import get_logger, log_node_start, log_node_end
from multi_agents.tools.engine_bridge import get_engine_bridge

logger = get_logger("media_engine_node")


def media_engine_node(state: PublicOpinionState, config: Optional[Dict] = None) -> StateUpdate:
    """
    Media Engine node: Run media content analysis.
    
    This node:
    1. Calls the MediaEngine bridge
    2. Performs multimedia/media search and analysis
    3. Returns structured results with platform distribution
    
    Args:
        state: Current graph state
        config: Configuration
    
    Returns:
        State updates with media_result
    """
    task_id = state.get("task_id", "unknown")
    log_node_start(logger, "media_engine", task_id)
    
    updates: StateUpdate = {}
    add_progress(updates, Stage.MEDIA_ANALYZING)
    
    query = state.get("query", "")
    plan = state.get("plan", {})
    
    if not query:
        updates["media_result"] = {
            "summary": "无法执行媒体分析：缺少查询内容",
            "platform_distribution": {},
            "media_highlights": [],
            "sources": [],
            "raw_result": {},
            "stats": {"error": True},
            "logs": ["No query provided"],
        }
        log_node_end(logger, "media_engine", task_id, success=False)
        return updates
    
    try:
        # Build context from plan
        context = {
            "task_id": task_id,
            "time_range": plan.get("time_scope", "最近7天"),
            "focus": plan.get("focus_dimensions", []),
        }
        
        # Call engine bridge
        bridge = get_engine_bridge()
        result = bridge.run_media_engine(query, context)
        
        updates["media_result"] = result
        logger.info(f"[{task_id}] MediaEngine completed: {len(result.get('sources', []))} sources")
        
    except Exception as e:
        logger.exception(f"[{task_id}] MediaEngine failed: {e}")
        updates["media_result"] = {
            "summary": f"MediaEngine分析失败: {str(e)}",
            "platform_distribution": {},
            "media_highlights": [],
            "sources": [],
            "raw_result": {"error": str(e)},
            "stats": {"error": True},
            "logs": [f"Error: {str(e)}"],
        }
        updates["errors"] = state.get("errors", []) + [f"MediaEngine error: {str(e)}"]
    
    log_node_end(logger, "media_engine", task_id)
    return updates
