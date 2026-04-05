# -*- coding: utf-8 -*-
"""
Insight Engine node for the LangGraph public opinion workflow.

Calls the InsightEngine for sentiment and topic analysis.
"""

from typing import Any, Optional
from langchain_core.runnables import RunnableConfig

from multi_agents.state import PublicOpinionState, StateUpdate
from multi_agents.tools.progress import add_progress, Stage
from multi_agents.tools.logger import get_logger, log_node_start, log_node_end
from multi_agents.tools.engine_bridge import get_engine_bridge

logger = get_logger("insight_engine_node")


def insight_engine_node(state: PublicOpinionState, config: Optional[RunnableConfig] = None) -> StateUpdate:
    """
    Insight Engine node: Run sentiment and topic analysis.
    
    This node:
    1. Calls the InsightEngine bridge
    2. Performs sentiment analysis and topic clustering
    3. Identifies risk signals
    4. Returns structured results
    
    Args:
        state: Current graph state
        config: Configuration
    
    Returns:
        State updates with insight_result
    """
    task_id = state.get("task_id", "unknown")
    log_node_start(logger, "insight_engine", task_id)
    
    updates: StateUpdate = {}
    add_progress(updates, Stage.INSIGHT_ANALYZING)
    
    query = state.get("query", "")
    plan = state.get("plan", {})
    
    if not query:
        updates["insight_result"] = {
            "summary": "无法执行洞察分析：缺少查询内容",
            "sentiment_summary": {},
            "keyword_clusters": [],
            "topic_clusters": [],
            "risk_signals": [],
            "sources": [],
            "raw_result": {},
            "stats": {"error": True},
            "logs": ["No query provided"],
        }
        log_node_end(logger, "insight_engine", task_id, success=False)
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
        result = bridge.run_insight_engine(query, context)
        
        updates["insight_result"] = result
        logger.info(f"[{task_id}] InsightEngine completed: {len(result.get('risk_signals', []))} risk signals")
        
    except Exception as e:
        logger.exception(f"[{task_id}] InsightEngine failed: {e}")
        updates["insight_result"] = {
            "summary": f"InsightEngine分析失败: {str(e)}",
            "sentiment_summary": {},
            "keyword_clusters": [],
            "topic_clusters": [],
            "risk_signals": [],
            "sources": [],
            "raw_result": {"error": str(e)},
            "stats": {"error": True},
            "logs": [f"Error: {str(e)}"],
        }
        updates["errors"] = state.get("errors", []) + [f"InsightEngine error: {str(e)}"]
    
    log_node_end(logger, "insight_engine", task_id)
    return updates
