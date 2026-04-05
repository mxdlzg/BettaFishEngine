# -*- coding: utf-8 -*-
"""
LangGraph Agent for BettaFish Public Opinion Analysis.

This module defines the main StateGraph that orchestrates the public opinion
analysis workflow, integrating all engines and MCP knowledge base access.
"""

from langgraph.graph import StateGraph, START, END

from multi_agents.state import PublicOpinionState

# Import all nodes
from multi_agents.nodes.intake import intake_node
from multi_agents.nodes.planner import planner_node
from multi_agents.nodes.query_engine_node import query_engine_node
from multi_agents.nodes.media_engine_node import media_engine_node
from multi_agents.nodes.insight_engine_node import insight_engine_node
from multi_agents.nodes.kb_mcp_node import kb_mcp_node
from multi_agents.nodes.forum_round_1 import forum_round_1_node
from multi_agents.nodes.forum_round_2 import forum_round_2_node
from multi_agents.nodes.forum_round_3 import forum_round_3_node
from multi_agents.nodes.merge_node import merge_node
from multi_agents.nodes.report_node import report_node
from multi_agents.nodes.artifacts_node import artifacts_node
from multi_agents.nodes.finalize_node import finalize_node


def create_graph() -> StateGraph:
    """
    Create and configure the public opinion analysis StateGraph.
    
    The graph follows this flow:
    1. intake - Parse user input, initialize state
    2. planner - Generate analysis plan
    3. query_engine - Public web/news analysis
    4. media_engine - Media/multimedia analysis
    5. insight_engine - Sentiment/topic analysis
    6. kb_mcp - Knowledge base queries via MCP
    7. forum_round_1 - First synthesis discussion
    8. forum_round_2 - Second synthesis discussion
    9. forum_round_3 - Final consensus discussion
    10. merge - Combine all results
    11. report - Generate reports
    12. artifacts - Package output files
    13. finalize - Create final answer
    
    Returns:
        Compiled StateGraph
    """
    # Create the graph builder
    builder = StateGraph(PublicOpinionState)
    
    # Add all nodes
    builder.add_node("intake", intake_node)
    builder.add_node("planner", planner_node)
    builder.add_node("query_engine", query_engine_node)
    builder.add_node("media_engine", media_engine_node)
    builder.add_node("insight_engine", insight_engine_node)
    builder.add_node("kb_mcp", kb_mcp_node)
    builder.add_node("forum_round_1", forum_round_1_node)
    builder.add_node("forum_round_2", forum_round_2_node)
    builder.add_node("forum_round_3", forum_round_3_node)
    builder.add_node("merge", merge_node)
    builder.add_node("report", report_node)
    builder.add_node("artifacts", artifacts_node)
    builder.add_node("finalize", finalize_node)
    
    # Define edges (sequential flow)
    builder.add_edge(START, "intake")
    builder.add_edge("intake", "planner")
    builder.add_edge("planner", "query_engine")
    builder.add_edge("query_engine", "media_engine")
    builder.add_edge("media_engine", "insight_engine")
    builder.add_edge("insight_engine", "kb_mcp")
    builder.add_edge("kb_mcp", "forum_round_1")
    builder.add_edge("forum_round_1", "forum_round_2")
    builder.add_edge("forum_round_2", "forum_round_3")
    builder.add_edge("forum_round_3", "merge")
    builder.add_edge("merge", "report")
    builder.add_edge("report", "artifacts")
    builder.add_edge("artifacts", "finalize")
    builder.add_edge("finalize", END)
    
    return builder


# Compile the graph for LangGraph Platform
graph = create_graph().compile()


# For direct testing
if __name__ == "__main__":
    import json
    
    # Test with a simple query
    test_input = {
        "messages": [
            {"role": "user", "content": "分析最近关于人工智能的舆情趋势"}
        ]
    }
    
    print("Testing public opinion graph...")
    print(f"Input: {json.dumps(test_input, ensure_ascii=False, indent=2)}")
    
    # Run the graph
    result = graph.invoke(test_input)
    
    print("\nResult:")
    print(f"Task ID: {result.get('task_id')}")
    print(f"Final Answer:\n{result.get('final_answer', '')[:500]}...")
    print(f"Files: {list(result.get('files', {}).keys())}")
    print(f"Errors: {result.get('errors', [])}")
