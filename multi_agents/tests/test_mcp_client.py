# -*- coding: utf-8 -*-
"""Tests for MCP client functionality."""

import pytest
import json
from unittest.mock import Mock, patch, AsyncMock

# Test data
MOCK_KB_LIST_RESPONSE = {
    "jsonrpc": "2.0",
    "id": "test-123",
    "result": {
        "knowledgeBases": [
            {"id": "kb-001", "name": "舆情政策库", "description": "政策文档"},
            {"id": "kb-002", "name": "行业数据库", "description": "行业分析数据"},
        ]
    }
}

MOCK_QUERY_RESPONSE = {
    "jsonrpc": "2.0",
    "id": "test-456",
    "result": {
        "documents": [
            {
                "id": "doc-001",
                "content": "人工智能发展趋势分析报告...",
                "score": 0.95,
                "metadata": {"source": "政策库"}
            }
        ]
    }
}


class TestMCPClient:
    """Test suite for MCP client."""
    
    def test_build_request_payload(self):
        """Test JSON-RPC request payload construction."""
        from multi_agents.tools.mcp_client import MCPClient
        
        client = MCPClient()
        payload = client._build_request("kb.list", {"limit": 10})
        
        assert payload["jsonrpc"] == "2.0"
        assert payload["method"] == "kb.list"
        assert payload["params"]["limit"] == 10
        assert "id" in payload
    
    def test_parse_sse_event(self):
        """Test SSE event parsing."""
        from multi_agents.tools.mcp_client import MCPClient
        
        client = MCPClient()
        
        # Test data event
        event_data = 'data: {"result": "test"}'
        parsed = client._parse_sse_line(event_data)
        assert parsed == {"result": "test"}
        
        # Test event type line (should be ignored)
        event_type = "event: message"
        parsed = client._parse_sse_line(event_type)
        assert parsed is None
        
        # Test empty line
        parsed = client._parse_sse_line("")
        assert parsed is None
    
    def test_auto_select_kb(self):
        """Test automatic knowledge base selection logic."""
        from multi_agents.tools.mcp_client import MCPClient
        
        client = MCPClient()
        
        # Mock available KBs
        available_kbs = [
            {"id": "kb-001", "name": "舆情政策库", "description": "政策相关"},
            {"id": "kb-002", "name": "行业数据库", "description": "行业分析"},
            {"id": "kb-003", "name": "新闻存档", "description": "新闻报道"},
        ]
        
        # Test selection based on query
        query = "人工智能政策"
        selected = client._select_relevant_kbs(query, available_kbs, max_kbs=2)
        
        # Should return list of KB IDs
        assert isinstance(selected, list)
        assert len(selected) <= 2


class TestMCPClientIntegration:
    """Integration tests (require network, skipped in CI)."""
    
    @pytest.mark.skip(reason="Requires live MCP server")
    @pytest.mark.asyncio
    async def test_list_knowledge_bases(self):
        """Test listing knowledge bases from live server."""
        from multi_agents.tools.mcp_client import MCPClient
        
        client = MCPClient()
        kbs = await client.list_knowledge_bases()
        
        assert isinstance(kbs, list)
    
    @pytest.mark.skip(reason="Requires live MCP server")
    @pytest.mark.asyncio
    async def test_query_knowledge_base(self):
        """Test querying knowledge base from live server."""
        from multi_agents.tools.mcp_client import MCPClient
        
        client = MCPClient()
        results = await client.query("人工智能发展", kb_ids=["kb-001"])
        
        assert isinstance(results, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
