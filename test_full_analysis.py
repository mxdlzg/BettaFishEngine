# -*- coding: utf-8 -*-
"""
Full integration test for public opinion analysis workflow.

Tests the complete multi-agent workflow with a real query.
"""

import asyncio
import json
from multi_agents.agent import graph

async def test_analysis(query: str):
    """
    Run a complete analysis workflow.
    
    Args:
        query: The user query to analyze
    """
    print(f"=== Starting Public Opinion Analysis ===")
    print(f"Query: {query}\n")
    
    # Create initial state
    initial_state = {
        "messages": [{"role": "user", "content": query}]
    }
    
    # Run the graph
    print("Starting workflow...")
    final_state = await graph.ainvoke(initial_state)
    
    # Print results
    print("\n=== Workflow Complete ===\n")
    print(f"Task ID: {final_state.get('task_id', 'N/A')}")
    print(f"Query: {final_state.get('query', 'N/A')}")
    print(f"Status: {final_state.get('status', 'N/A')}")
    
    if final_state.get("error"):
        print(f"\nError: {final_state['error']}")
    
    if final_state.get("report_url"):
        print(f"\nReport URL: {final_state['report_url']}")
    
    if final_state.get("report_path"):
        print(f"Report Path: {final_state['report_path']}")
    
    # Show progress summary
    if final_state.get("progress"):
        progress = final_state["progress"]
        print(f"\nProgress: {progress.get('current_step', 'N/A')} - {progress.get('description', 'N/A')}")
        print(f"Percentage: {progress.get('percentage', 0)}%")
    
    # Show data collection summary
    collections = ["query_results", "media_results", "insight_results", "kb_results", "forum_analyses"]
    for coll in collections:
        if coll in final_state and final_state[coll]:
            data = final_state[coll]
            if isinstance(data, dict):
                print(f"\n{coll}: {len(str(data))} chars")
            elif isinstance(data, list):
                print(f"\n{coll}: {len(data)} items")
            else:
                print(f"\n{coll}: {type(data).__name__}")
    
    return final_state


if __name__ == "__main__":
    # Test with Israeli-Palestinian conflict query
    query = "分析巴以冲突的最新舆情态势"
    
    result = asyncio.run(test_analysis(query))
    
    print("\n=== Test Complete ===")
