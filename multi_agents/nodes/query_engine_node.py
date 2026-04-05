# -*- coding: utf-8 -*-
"""
Query Engine node for the LangGraph public opinion workflow.

Calls the QueryEngine for public web/news analysis.
"""

from typing import Dict, Any, Optional

from multi_agents.state import PublicOpinionState, StateUpdate
from multi_agents.tools.progress import add_progress, Stage
from multi_agents.tools.logger import get_logger, log_node_start, log_node_end
from multi_agents.tools.engine_bridge import get_engine_bridge

logger = get_logger("query_engine_node")


def query_engine_node(state: PublicOpinionState, config: Optional[Dict] = None) -> StateUpdate:
    """
    Query Engine node: Run public information analysis.
    
    This node:
    1. Calls the QueryEngine bridge
    2. Performs web/news search and analysis
    3. Returns structured results
    
    Args:
        state: Current graph state
        config: Configuration
    
    Returns:
        State updates with query_result
    """
    task_id = state.get("task_id", "unknown")
    log_node_start(logger, "query_engine", task_id)
    
    updates: StateUpdate = {}
    add_progress(updates, Stage.QUERYING)
    
    query = state.get("query", "")
    plan = state.get("plan", {})
    
    if not query:
        updates["query_result"] = {
            "summary": "无法执行查询：缺少查询内容",
            "sources": [],
            "raw_result": {},
            "stats": {"error": True},
            "logs": ["No query provided"],
        }
        log_node_end(logger, "query_engine", task_id, success=False)
        return updates
    
    try:
        # Build context from plan
        context = {
            "task_id": task_id,
            "time_range": plan.get("time_scope", "最近7天"),
            "focus": plan.get("focus_dimensions", []),
            "locale": plan.get("region", "中国"),
        }
        
        # Call engine bridge
        bridge = get_engine_bridge()
        result = bridge.run_query_engine(query, context)
        
        updates["query_result"] = result
        logger.info(f"[{task_id}] QueryEngine completed: {len(result.get('sources', []))} sources")
        
    except Exception as e:
        logger.exception(f"[{task_id}] QueryEngine failed: {e}")
        updates["query_result"] = {
            "summary": f"QueryEngine分析失败: {str(e)}",
            "sources": [],
            "raw_result": {"error": str(e)},
            "stats": {"error": True},
            "logs": [f"Error: {str(e)}"],
        }
        updates["errors"] = state.get("errors", []) + [f"QueryEngine error: {str(e)}"]
    
    log_node_end(logger, "query_engine", task_id)
    return updates
