# -*- coding: utf-8 -*-
"""Tests for state flow and graph execution."""

import pytest
from typing import Dict, Any


class TestPublicOpinionState:
    """Test suite for state management."""
    
    def test_initial_state_structure(self):
        """Test that initial state has all required fields."""
        from multi_agents.state import PublicOpinionState
        
        # Create minimal initial state
        state: PublicOpinionState = {
            "messages": [{"role": "user", "content": "测试查询"}],
            "task_id": "",
            "query": "",
            "analysis_plan": {},
            "selected_kbs": [],
            "query_engine_result": {},
            "media_engine_result": {},
            "insight_engine_result": {},
            "kb_results": [],
            "forum_rounds": [],
            "merged_result": {},
            "report_md": "",
            "report_html": "",
            "files": {},
            "progress_log": [],
            "errors": [],
            "final_answer": "",
        }
        
        # Verify all fields exist
        assert "messages" in state
        assert "task_id" in state
        assert "files" in state
        assert "progress_log" in state
    
    def test_state_immutability(self):
        """Test that state updates create new state objects."""
        initial = {
            "messages": [],
            "task_id": "test-001",
            "errors": [],
        }
        
        # Simulate a state update (as nodes do)
        update = {"task_id": "test-002"}
        new_state = {**initial, **update}
        
        # Original should be unchanged
        assert initial["task_id"] == "test-001"
        assert new_state["task_id"] == "test-002"


class TestNodeStateFlow:
    """Test state flow between nodes."""
    
    def test_intake_node_output(self):
        """Test intake node produces expected state updates."""
        from multi_agents.nodes.intake import intake_node
        
        input_state = {
            "messages": [{"role": "user", "content": "分析人工智能舆情"}],
            "task_id": "",
            "query": "",
            "analysis_plan": {},
            "selected_kbs": [],
            "query_engine_result": {},
            "media_engine_result": {},
            "insight_engine_result": {},
            "kb_results": [],
            "forum_rounds": [],
            "merged_result": {},
            "report_md": "",
            "report_html": "",
            "files": {},
            "progress_log": [],
            "errors": [],
            "final_answer": "",
        }
        
        result = intake_node(input_state)
        
        # Should have task_id and query
        assert "task_id" in result
        assert "query" in result
        assert len(result["task_id"]) > 0
        assert result["query"] == "分析人工智能舆情"
    
    def test_progress_log_accumulation(self):
        """Test that progress_log accumulates across nodes."""
        from multi_agents.tools.progress import add_progress, Stage
        
        state = {"progress_log": [], "task_id": "test-001"}
        
        # Add multiple progress entries
        state = add_progress(state, Stage.CREATED)
        state = add_progress(state, Stage.PLANNING)
        state = add_progress(state, Stage.QUERYING)
        
        assert len(state["progress_log"]) == 3
        assert state["progress_log"][0]["stage"] == Stage.CREATED
        assert state["progress_log"][2]["stage"] == Stage.QUERYING
    
    def test_error_accumulation(self):
        """Test that errors accumulate without overwriting."""
        state = {"errors": []}
        
        # Add errors
        state["errors"] = state["errors"] + ["Error 1"]
        state["errors"] = state["errors"] + ["Error 2"]
        
        assert len(state["errors"]) == 2
        assert "Error 1" in state["errors"]
        assert "Error 2" in state["errors"]


class TestGraphExecution:
    """Test full graph execution."""
    
    @pytest.mark.skip(reason="Requires full environment setup")
    def test_full_graph_execution(self):
        """Test complete graph execution end-to-end."""
        from multi_agents.agent import graph
        
        input_state = {
            "messages": [{"role": "user", "content": "分析人工智能发展趋势"}]
        }
        
        result = graph.invoke(input_state)
        
        assert "task_id" in result
        assert "final_answer" in result
        assert len(result["final_answer"]) > 0
    
    @pytest.mark.skip(reason="Requires full environment setup")
    def test_graph_with_minimal_query(self):
        """Test graph handles minimal queries."""
        from multi_agents.agent import graph
        
        input_state = {
            "messages": [{"role": "user", "content": "AI"}]
        }
        
        result = graph.invoke(input_state)
        
        # Should still produce output even with minimal query
        assert "final_answer" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
