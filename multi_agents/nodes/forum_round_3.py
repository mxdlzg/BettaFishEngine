# -*- coding: utf-8 -*-
"""
Forum Round 3 node for the LangGraph public opinion workflow.

Final round of multi-source analysis synthesis for consensus.
"""

from typing import Any, Optional
from langchain_core.runnables import RunnableConfig

from multi_agents.state import PublicOpinionState, StateUpdate
from multi_agents.tools.progress import add_progress, Stage
from multi_agents.tools.logger import get_logger, log_node_start, log_node_end
from multi_agents.tools.llm_client import get_llm_client
from multi_agents.prompts.moderator import build_moderator_round_3_messages

logger = get_logger("forum_round_3")


def forum_round_3_node(state: PublicOpinionState, config: Optional[RunnableConfig] = None) -> StateUpdate:
    """
    Forum Round 3 node: Final consensus discussion.
    
    This node:
    1. Takes rounds 1-2 results and all engine results
    2. Conducts final round for consensus building
    3. Forms final conclusions and recommendations
    
    Args:
        state: Current graph state
        config: Configuration
    
    Returns:
        State updates with forum_rounds[2]
    """
    task_id = state.get("task_id", "unknown")
    log_node_start(logger, "forum_round_3", task_id)
    
    updates: StateUpdate = {}
    add_progress(updates, Stage.FORUM_ROUND_3)
    
    query = state.get("query", "")
    query_result = state.get("query_result", {})
    media_result = state.get("media_result", {})
    insight_result = state.get("insight_result", {})
    kb_result = state.get("kb_result", {})
    forum_rounds = state.get("forum_rounds", [])
    
    # Get previous round results
    round_1_result = forum_rounds[0] if len(forum_rounds) > 0 else {}
    round_2_result = forum_rounds[1] if len(forum_rounds) > 1 else {}
    
    try:
        # Build moderator prompt
        messages = build_moderator_round_3_messages(
            query=query,
            round_1_result=round_1_result,
            round_2_result=round_2_result,
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
                "round_summary": "最终分析完成",
                "conflicts": [],
                "missing_evidence": [],
                "followup_suggestions": [],
                "intermediate_conclusion": "",
            }
        )
        
        # Build round result
        round_result = {
            "round_index": 2,
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
        
        logger.info(f"[{task_id}] Forum round 3 completed - consensus reached")
        
    except Exception as e:
        logger.exception(f"[{task_id}] Forum round 3 failed: {e}")
        
        forum_rounds = state.get("forum_rounds", [])
        forum_rounds.append({
            "round_index": 2,
            "round_summary": f"最终分析遇到问题: {str(e)}",
            "conflicts": [],
            "missing_evidence": [],
            "followup_suggestions": [],
            "intermediate_conclusion": "",
        })
        updates["forum_rounds"] = forum_rounds
        updates["errors"] = state.get("errors", []) + [f"Forum round 3 error: {str(e)}"]
    
    log_node_end(logger, "forum_round_3", task_id)
    return updates
