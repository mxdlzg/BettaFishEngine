# -*- coding: utf-8 -*-
"""
Forum Round 1 node for the LangGraph public opinion workflow.

First round of multi-source analysis synthesis.
"""

from typing import Any, Optional
from langchain_core.runnables import RunnableConfig

from multi_agents.state import PublicOpinionState, StateUpdate
from multi_agents.tools.progress import add_progress, Stage
from multi_agents.tools.logger import get_logger, log_node_start, log_node_end
from multi_agents.tools.llm_client import get_llm_client
from multi_agents.prompts.moderator import build_moderator_round_1_messages

logger = get_logger("forum_round_1")


def forum_round_1_node(state: PublicOpinionState, config: Optional[RunnableConfig] = None) -> StateUpdate:
    """
    Forum Round 1 node: First synthesis discussion.
    
    This node:
    1. Takes all engine results
    2. Conducts first round of comprehensive review
    3. Identifies conflicts, gaps, and initial conclusions
    
    Args:
        state: Current graph state
        config: Configuration
    
    Returns:
        State updates with forum_rounds[0]
    """
    task_id = state.get("task_id", "unknown")
    log_node_start(logger, "forum_round_1", task_id)
    
    updates: StateUpdate = {}
    add_progress(updates, Stage.FORUM_ROUND_1)
    
    query = state.get("query", "")
    query_result = state.get("query_result", {})
    media_result = state.get("media_result", {})
    insight_result = state.get("insight_result", {})
    kb_result = state.get("kb_result", {})
    
    try:
        # Build moderator prompt
        messages = build_moderator_round_1_messages(
            query=query,
            query_result=query_result,
            media_result=media_result,
            insight_result=insight_result,
            kb_result=kb_result,
        )
        
        # Call LLM
        llm_client = get_llm_client()
        result = llm_client.json_chat(
            messages=messages,
            role="moderator",
            default={
                "round_summary": "第一轮分析完成",
                "conflicts": [],
                "missing_evidence": [],
                "followup_suggestions": [],
                "intermediate_conclusion": "",
            }
        )
        
        # Build round result
        round_result = {
            "round_index": 0,
            "round_summary": result.get("round_summary", ""),
            "conflicts": result.get("conflicts", []),
            "missing_evidence": result.get("missing_evidence", []),
            "followup_suggestions": result.get("followup_suggestions", []),
            "intermediate_conclusion": result.get("intermediate_conclusion", ""),
        }
        
        # Add to forum_rounds
        forum_rounds = state.get("forum_rounds", [])
        forum_rounds.append(round_result)
        updates["forum_rounds"] = forum_rounds
        
        logger.info(f"[{task_id}] Forum round 1 completed: {len(round_result.get('conflicts', []))} conflicts found")
        
    except Exception as e:
        logger.exception(f"[{task_id}] Forum round 1 failed: {e}")
        
        # Add placeholder result
        forum_rounds = state.get("forum_rounds", [])
        forum_rounds.append({
            "round_index": 0,
            "round_summary": f"第一轮分析遇到问题: {str(e)}",
            "conflicts": [],
            "missing_evidence": [],
            "followup_suggestions": [],
            "intermediate_conclusion": "",
        })
        updates["forum_rounds"] = forum_rounds
        updates["errors"] = state.get("errors", []) + [f"Forum round 1 error: {str(e)}"]
    
    log_node_end(logger, "forum_round_1", task_id)
    return updates
