# -*- coding: utf-8 -*-
"""
Planner node for the LangGraph public opinion workflow.

Generates an analysis plan based on the user's query.
"""

from typing import Any, Optional
from langchain_core.runnables import RunnableConfig

from multi_agents.state import PublicOpinionState, StateUpdate
from multi_agents.tools.progress import add_progress, Stage
from multi_agents.tools.logger import get_logger, log_node_start, log_node_end
from multi_agents.tools.llm_client import get_llm_client
from multi_agents.prompts.planner import build_planner_messages

logger = get_logger("planner")


def planner_node(state: PublicOpinionState, config: Optional[RunnableConfig] = None) -> StateUpdate:
    """
    Planner node: Generate analysis plan.
    
    This node:
    1. Takes the user's query
    2. Uses LLM to generate a structured analysis plan
    3. Determines which dimensions to focus on
    4. Decides if knowledge base is needed
    
    Args:
        state: Current graph state
        config: Configuration
    
    Returns:
        State updates with plan
    """
    task_id = state.get("task_id", "unknown")
    log_node_start(logger, "planner", task_id)
    
    updates: StateUpdate = {}
    add_progress(updates, Stage.PLANNING)
    
    query = state.get("query", "")
    
    if not query:
        updates["errors"] = state.get("errors", []) + ["No query available for planning"]
        log_node_end(logger, "planner", task_id, success=False)
        return updates
    
    try:
        # Build planner prompt
        extracted_info = {
            "query": query,
            "user_id": state.get("user_id", ""),
            "source_type": state.get("source_type", ""),
        }
        
        messages = build_planner_messages(query, extracted_info)
        
        # Call LLM
        llm_client = get_llm_client()
        plan = llm_client.json_chat(
            messages=messages,
            role="planner",
            default={
                "topic": query,
                "entity": "",
                "region": "中国",
                "time_scope": "最近7天",
                "focus_dimensions": ["事件动态", "情感分析", "风险信号"],
                "report_priority": "comprehensive",
                "needs_kb": True,
                "analysis_goal": "全面了解舆情态势",
            }
        )
        
        updates["plan"] = plan
        logger.info(f"[{task_id}] Plan generated: {plan.get('topic', '')}, dimensions={plan.get('focus_dimensions', [])}")
        
    except Exception as e:
        logger.exception(f"[{task_id}] Planner failed: {e}")
        # Use default plan on failure
        updates["plan"] = {
            "topic": query,
            "entity": "",
            "region": "中国",
            "time_scope": "最近7天",
            "focus_dimensions": ["事件动态", "情感分析", "风险信号"],
            "report_priority": "comprehensive",
            "needs_kb": True,
            "analysis_goal": "全面了解舆情态势",
        }
        updates["errors"] = state.get("errors", []) + [f"Planner error: {str(e)}"]
    
    log_node_end(logger, "planner", task_id)
    return updates
