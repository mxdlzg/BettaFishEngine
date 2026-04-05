# -*- coding: utf-8 -*-
"""
Knowledge Base MCP node for the LangGraph public opinion workflow.

Queries ALB knowledge bases via MCP protocol.
"""

from typing import Any, Optional, List, Dict
from langchain_core.runnables import RunnableConfig

from multi_agents.state import PublicOpinionState, StateUpdate
from multi_agents.tools.progress import add_progress, Stage
from multi_agents.tools.logger import get_logger, log_node_start, log_node_end
from multi_agents.tools.mcp_client import get_mcp_client, MCPError
from multi_agents.tools.llm_client import get_llm_client
from multi_agents.settings import get_settings
from multi_agents.prompts.kb_selector import build_kb_selector_messages

logger = get_logger("kb_mcp_node")


def kb_mcp_node(state: PublicOpinionState, config: Optional[RunnableConfig] = None) -> StateUpdate:
    """
    Knowledge Base MCP node: Query knowledge bases.
    
    This node:
    1. Gets MCP token (from state or fallback)
    2. Lists available knowledge bases
    3. Uses LLM to select relevant KBs
    4. Queries selected knowledge bases
    5. Merges and standardizes results
    
    Args:
        state: Current graph state
        config: Configuration
    
    Returns:
        State updates with kb_result and auto_selected_knowledge_bases
    """
    task_id = state.get("task_id", "unknown")
    log_node_start(logger, "kb_mcp", task_id)
    
    updates: StateUpdate = {}
    add_progress(updates, Stage.KB_QUERYING)
    
    query = state.get("query", "")
    plan = state.get("plan", {})
    
    # Check if KB is needed
    if not plan.get("needs_kb", True):
        logger.info(f"[{task_id}] KB query skipped: needs_kb=False")
        updates["kb_result"] = {
            "selected_knowledge_bases": [],
            "answers": [],
            "merged_summary": "知识库查询已跳过",
            "sources": [],
        }
        updates["auto_selected_knowledge_bases"] = []
        log_node_end(logger, "kb_mcp", task_id)
        return updates
    
    # Get MCP token
    token = state.get("alb_mcp_token", "")
    if not token:
        settings = get_settings()
        token = settings.alb_mcp_token_fallback
    
    if not token:
        logger.warning(f"[{task_id}] No MCP token available, skipping KB query")
        updates["kb_result"] = {
            "selected_knowledge_bases": [],
            "answers": [],
            "merged_summary": "未配置MCP令牌，无法查询知识库",
            "sources": [],
        }
        updates["auto_selected_knowledge_bases"] = []
        log_node_end(logger, "kb_mcp", task_id)
        return updates
    
    try:
        # Get MCP client
        mcp_client = get_mcp_client(token)
        
        # List available knowledge bases
        knowledge_bases = mcp_client.list_knowledge_bases()
        logger.info(f"[{task_id}] Found {len(knowledge_bases)} knowledge bases")
        
        if not knowledge_bases:
            updates["kb_result"] = {
                "selected_knowledge_bases": [],
                "answers": [],
                "merged_summary": "未找到可用的知识库",
                "sources": [],
            }
            updates["auto_selected_knowledge_bases"] = []
            log_node_end(logger, "kb_mcp", task_id)
            return updates
        
        # Use LLM to select relevant KBs
        selected_kbs = _select_knowledge_bases(query, plan, knowledge_bases)
        logger.info(f"[{task_id}] Selected {len(selected_kbs)} knowledge bases")
        
        updates["auto_selected_knowledge_bases"] = selected_kbs
        
        # Query selected knowledge bases
        answers = []
        all_sources = []
        
        for kb in selected_kbs:
            kb_id = kb.get("id", "")
            kb_name = kb.get("name", "")
            
            try:
                result = mcp_client.query_knowledge_base(
                    kb_id=kb_id,
                    query=query,
                    mode="hybrid",
                    top_k=5
                )
                
                answer = {
                    "knowledge_base_id": kb_id,
                    "knowledge_base_name": kb_name,
                    "answer": result.get("answer", ""),
                    "sources": result.get("sources", []),
                    "citations": result.get("citations", []),
                    "confidence": result.get("confidence", 0.0),
                }
                answers.append(answer)
                all_sources.extend(result.get("sources", []))
                
            except MCPError as e:
                logger.warning(f"[{task_id}] Failed to query KB {kb_id}: {e}")
        
        # Merge summaries
        merged_summary = _merge_kb_answers(answers)
        
        updates["kb_result"] = {
            "selected_knowledge_bases": selected_kbs,
            "answers": answers,
            "merged_summary": merged_summary,
            "sources": all_sources,
        }
        
        logger.info(f"[{task_id}] KB query completed: {len(answers)} answers")
        
    except Exception as e:
        logger.exception(f"[{task_id}] KB MCP node failed: {e}")
        updates["kb_result"] = {
            "selected_knowledge_bases": [],
            "answers": [],
            "merged_summary": f"知识库查询失败: {str(e)}",
            "sources": [],
        }
        updates["auto_selected_knowledge_bases"] = []
        updates["errors"] = state.get("errors", []) + [f"KB MCP error: {str(e)}"]
    
    log_node_end(logger, "kb_mcp", task_id)
    return updates


def _select_knowledge_bases(
    query: str,
    plan: Dict[str, Any],
    knowledge_bases: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Use LLM to select relevant knowledge bases.
    
    Args:
        query: User's query
        plan: Analysis plan
        knowledge_bases: Available knowledge bases
    
    Returns:
        List of selected knowledge base info dicts
    """
    if not knowledge_bases:
        return []
    
    # If only one KB, use it directly
    if len(knowledge_bases) == 1:
        return knowledge_bases
    
    try:
        llm_client = get_llm_client()
        messages = build_kb_selector_messages(query, plan, knowledge_bases)
        
        result = llm_client.json_chat(
            messages=messages,
            role="planner",
            default={"selected": []}
        )
        
        selected_ids = [item.get("id") for item in result.get("selected", [])]
        
        # Filter to selected KBs
        return [kb for kb in knowledge_bases if kb.get("id") in selected_ids]
        
    except Exception as e:
        logger.warning(f"KB selection failed, using all: {e}")
        # On failure, return up to 3 KBs
        return knowledge_bases[:3]


def _merge_kb_answers(answers: List[Dict[str, Any]]) -> str:
    """
    Merge multiple KB answers into a summary.
    
    Args:
        answers: List of KB answer dicts
    
    Returns:
        Merged summary string
    """
    if not answers:
        return "未获取到知识库回答"
    
    summaries = []
    for ans in answers:
        kb_name = ans.get("knowledge_base_name", "未知知识库")
        answer_text = ans.get("answer", "")
        if answer_text:
            summaries.append(f"**{kb_name}**:\n{answer_text[:500]}")
    
    return "\n\n".join(summaries) if summaries else "知识库未返回有效内容"
