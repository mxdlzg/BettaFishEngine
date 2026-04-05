# -*- coding: utf-8 -*-
"""
Intake node for the LangGraph public opinion workflow.

Parses user input, initializes state, and prepares for analysis.
"""

from typing import Dict, Any, Optional
from langchain_core.messages import HumanMessage

from multi_agents.state import PublicOpinionState, StateUpdate
from multi_agents.tools.ids import generate_task_id
from multi_agents.tools.progress import add_progress, Stage
from multi_agents.tools.logger import get_logger, log_node_start, log_node_end
from multi_agents.tools.llm_client import get_llm_client
from multi_agents.tools.json_utils import extract_json_from_llm_response
from multi_agents.prompts.intake import build_intake_messages

logger = get_logger("intake")


def intake_node(state: PublicOpinionState, config: Optional[Dict] = None) -> StateUpdate:
    """
    Intake node: Parse user input and initialize state.
    
    This node:
    1. Extracts the user's query from messages
    2. Generates a task ID
    3. Extracts metadata (user_id, thread_id, alb_mcp_token)
    4. Initializes progress tracking
    5. Optionally uses LLM to extract structured query info
    
    Args:
        state: Current graph state
        config: Configuration from configurable/metadata
    
    Returns:
        State updates
    """
    config = config or {}
    configurable = config.get("configurable", {})
    
    # Generate task ID
    task_id = generate_task_id("po")
    log_node_start(logger, "intake", task_id)
    
    # Initialize state updates
    updates: StateUpdate = {
        "task_id": task_id,
        "progress_log": [],
        "errors": [],
        "forum_rounds": [],
        "files": {},
    }
    
    # Add progress
    add_progress(updates, Stage.CREATED)
    
    # Extract user query from messages
    query = ""
    messages = state.get("messages", [])
    
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            query = msg.content
            break
        elif isinstance(msg, dict) and msg.get("role") == "user":
            query = msg.get("content", "")
            break
    
    if not query:
        updates["errors"] = ["No query found in messages"]
        log_node_end(logger, "intake", task_id, success=False)
        return updates
    
    updates["query"] = query
    
    # Extract metadata from configurable
    updates["user_id"] = configurable.get("user_id", "")
    updates["thread_id"] = configurable.get("thread_id", "")
    updates["agent_id"] = configurable.get("agent_id", "public-opinion")
    updates["assistant_id"] = configurable.get("assistant_id", "public-opinion")
    updates["source_type"] = configurable.get("source_type", "alb")
    
    # Get MCP token (from metadata or fallback)
    updates["alb_mcp_token"] = configurable.get("alb_mcp_token", "")
    
    # Optionally use LLM to extract structured info
    # (This is done more thoroughly in planner, so we keep it simple here)
    
    logger.info(f"[{task_id}] Intake completed: query='{query[:50]}...'")
    log_node_end(logger, "intake", task_id)
    
    return updates
