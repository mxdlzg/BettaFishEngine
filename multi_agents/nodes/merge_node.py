# -*- coding: utf-8 -*-
"""
Merge node for the LangGraph public opinion workflow.

Merges all analysis results into unified conclusions.
"""

from typing import Any, Optional, Dict, List
from langchain_core.runnables import RunnableConfig

from multi_agents.state import PublicOpinionState, StateUpdate
from multi_agents.tools.progress import add_progress, Stage
from multi_agents.tools.logger import get_logger, log_node_start, log_node_end
from multi_agents.tools.llm_client import get_llm_client
from multi_agents.prompts.merge import build_merge_messages

logger = get_logger("merge_node")


def merge_node(state: PublicOpinionState, config: Optional[RunnableConfig] = None) -> StateUpdate:
    """
    Merge node: Combine all results into unified analysis.
    
    This node:
    1. Takes all engine results and forum discussions
    2. Uses LLM to synthesize into unified conclusions
    3. Extracts key evidence and risk/opportunity points
    
    Args:
        state: Current graph state
        config: Configuration
    
    Returns:
        State updates with merged_result
    """
    task_id = state.get("task_id", "unknown")
    log_node_start(logger, "merge", task_id)
    
    updates: StateUpdate = {}
    add_progress(updates, Stage.MERGING)
    
    query = state.get("query", "")
    plan = state.get("plan", {})
    query_result = state.get("query_result", {})
    media_result = state.get("media_result", {})
    insight_result = state.get("insight_result", {})
    kb_result = state.get("kb_result", {})
    forum_rounds = state.get("forum_rounds", [])
    
    try:
        # Build merge prompt
        messages = build_merge_messages(
            query=query,
            plan=plan,
            query_result=query_result,
            media_result=media_result,
            insight_result=insight_result,
            kb_result=kb_result,
            forum_rounds=forum_rounds,
        )
        
        # Call LLM
        llm_client = get_llm_client()
        result = llm_client.json_chat(
            messages=messages,
            role="analysis",
            max_tokens=6000,
            default={
                "core_conclusions": ["分析结果整合中"],
                "risk_points": [],
                "opportunities": [],
                "key_evidence": [],
                "evidence_map": {},
                "stats": {},
            }
        )
        
        # Build merged result
        merged_result = {
            "core_conclusions": result.get("core_conclusions", []),
            "risk_points": result.get("risk_points", []),
            "opportunities": result.get("opportunities", []),
            "key_evidence": result.get("key_evidence", []),
            "evidence_map": result.get("evidence_map", {}),
            "stats": _calculate_stats(query_result, media_result, insight_result, kb_result),
        }
        
        updates["merged_result"] = merged_result
        
        logger.info(
            f"[{task_id}] Merge completed: "
            f"{len(merged_result['core_conclusions'])} conclusions, "
            f"{len(merged_result['risk_points'])} risks, "
            f"{len(merged_result['opportunities'])} opportunities"
        )
        
    except Exception as e:
        logger.exception(f"[{task_id}] Merge failed: {e}")
        
        # Create basic merged result from available data
        updates["merged_result"] = _fallback_merge(
            query_result, media_result, insight_result, kb_result, forum_rounds
        )
        updates["errors"] = state.get("errors", []) + [f"Merge error: {str(e)}"]
    
    log_node_end(logger, "merge", task_id)
    return updates


def _calculate_stats(
    query_result: Dict,
    media_result: Dict,
    insight_result: Dict,
    kb_result: Dict
) -> Dict[str, Any]:
    """Calculate summary statistics."""
    return {
        "query_sources": len(query_result.get("sources", [])),
        "media_sources": len(media_result.get("sources", [])),
        "insight_sources": len(insight_result.get("sources", [])),
        "kb_answers": len(kb_result.get("answers", [])),
        "total_sources": (
            len(query_result.get("sources", [])) +
            len(media_result.get("sources", [])) +
            len(insight_result.get("sources", []))
        ),
    }


def _fallback_merge(
    query_result: Dict,
    media_result: Dict,
    insight_result: Dict,
    kb_result: Dict,
    forum_rounds: list
) -> Dict[str, Any]:
    """Create a basic merged result without LLM."""
    conclusions = []
    
    # Extract summaries as conclusions
    if query_result.get("summary"):
        conclusions.append(f"公开信息分析: {query_result['summary'][:200]}")
    if media_result.get("summary"):
        conclusions.append(f"媒体分析: {media_result['summary'][:200]}")
    if insight_result.get("summary"):
        conclusions.append(f"洞察分析: {insight_result['summary'][:200]}")
    
    # Extract risks from insight
    risks = insight_result.get("risk_signals", [])
    
    # Get final forum conclusion
    if forum_rounds:
        final_round = forum_rounds[-1]
        if final_round.get("intermediate_conclusion"):
            conclusions.append(final_round["intermediate_conclusion"])
    
    return {
        "core_conclusions": conclusions if conclusions else ["分析结果待整合"],
        "risk_points": risks,
        "opportunities": [],
        "key_evidence": [],
        "evidence_map": {},
        "stats": _calculate_stats(query_result, media_result, insight_result, kb_result),
    }
