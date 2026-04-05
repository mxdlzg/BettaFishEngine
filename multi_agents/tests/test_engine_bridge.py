# -*- coding: utf-8 -*-
"""Tests for engine bridge functionality."""

import pytest
from unittest.mock import Mock, patch, MagicMock


class TestEngineBridge:
    """Test suite for engine bridge layer."""
    
    def test_normalize_output_dict(self):
        """Test output normalization from dict."""
        from multi_agents.tools.engine_bridge import EngineBridge
        
        bridge = EngineBridge()
        
        # Test with dict output
        raw_output = {
            "report_content": "Analysis results...",
            "status": "success"
        }
        
        normalized = bridge._normalize_output(raw_output)
        
        assert "content" in normalized
        assert "metadata" in normalized
        assert normalized["content"] == "Analysis results..."
    
    def test_normalize_output_string(self):
        """Test output normalization from string."""
        from multi_agents.tools.engine_bridge import EngineBridge
        
        bridge = EngineBridge()
        
        # Test with string output
        raw_output = "Plain text analysis result"
        
        normalized = bridge._normalize_output(raw_output)
        
        assert normalized["content"] == raw_output
        assert normalized["metadata"]["format"] == "text"
    
    def test_normalize_output_empty(self):
        """Test output normalization with empty input."""
        from multi_agents.tools.engine_bridge import EngineBridge
        
        bridge = EngineBridge()
        
        # Test with None
        normalized = bridge._normalize_output(None)
        assert normalized["content"] == ""
        
        # Test with empty string
        normalized = bridge._normalize_output("")
        assert normalized["content"] == ""
    
    def test_engine_name_validation(self):
        """Test that only valid engine names are accepted."""
        from multi_agents.tools.engine_bridge import EngineBridge
        
        bridge = EngineBridge()
        
        valid_engines = ["query", "media", "insight", "report"]
        for engine in valid_engines:
            assert bridge._is_valid_engine(engine) is True
        
        invalid_engines = ["unknown", "fake", ""]
        for engine in invalid_engines:
            assert bridge._is_valid_engine(engine) is False


class TestQueryEngineIntegration:
    """Integration tests for QueryEngine (require full setup)."""
    
    @pytest.mark.skip(reason="Requires full environment setup")
    @pytest.mark.asyncio
    async def test_run_query_engine(self):
        """Test running QueryEngine through bridge."""
        from multi_agents.tools.engine_bridge import EngineBridge
        
        bridge = EngineBridge()
        result = bridge.run_query_engine(
            query="人工智能发展趋势",
            context={"task_id": "test-001"}
        )
        
        assert "summary" in result
        assert len(result.get("summary", "")) > 0


class TestMediaEngineIntegration:
    """Integration tests for MediaEngine."""
    
    @pytest.mark.skip(reason="Requires full environment setup")
    @pytest.mark.asyncio
    async def test_run_media_engine(self):
        """Test running MediaEngine through bridge."""
        from multi_agents.tools.engine_bridge import EngineBridge
        
        bridge = EngineBridge()
        result = bridge.run_media_engine(
            query="人工智能图片分析",
            context={"task_id": "test-002"}
        )
        
        assert "summary" in result


class TestInsightEngineIntegration:
    """Integration tests for InsightEngine."""
    
    @pytest.mark.skip(reason="Requires full environment setup")
    @pytest.mark.asyncio
    async def test_run_insight_engine(self):
        """Test running InsightEngine through bridge."""
        from multi_agents.tools.engine_bridge import EngineBridge
        
        bridge = EngineBridge()
        result = bridge.run_insight_engine(
            query="人工智能情感分析",
            context={"task_id": "test-003"}
        )
        
        assert "summary" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
