# -*- coding: utf-8 -*-
"""
MCP (Model Context Protocol) client for ALB knowledge base access.

Implements SSE-based communication with MCP service for knowledge base queries.
"""

import json
import time
from typing import Dict, Any, Optional, List, Generator
import httpx

from multi_agents.settings import get_settings, Settings
from multi_agents.tools.logger import get_logger
from multi_agents.tools.json_utils import safe_json_loads

logger = get_logger("mcp_client")


class MCPError(Exception):
    """Exception for MCP-related errors."""
    pass


class MCPClient:
    """
    Client for MCP (Model Context Protocol) service.
    
    Communicates with ALB MCP endpoint via SSE for knowledge base access.
    """
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        token: Optional[str] = None,
        timeout_sec: int = 120
    ):
        """
        Initialize the MCP client.
        
        Args:
            base_url: MCP service URL (defaults to settings)
            token: Authentication token (defaults to settings fallback)
            timeout_sec: Request timeout in seconds
        """
        settings = get_settings()
        self.base_url = base_url or settings.alb_mcp_url
        self.token = token or settings.alb_mcp_token_fallback
        self.timeout_sec = timeout_sec
        self._request_id = 0
    
    def _next_request_id(self) -> int:
        """Generate next request ID."""
        self._request_id += 1
        return self._request_id
    
    def _build_headers(self) -> Dict[str, str]:
        """Build request headers with authentication."""
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
        }
    
    def _parse_sse_events(self, response: httpx.Response) -> Generator[Dict[str, Any], None, None]:
        """
        Parse SSE events from response stream.
        
        Args:
            response: HTTP response with SSE stream
        
        Yields:
            Parsed JSON event data
        """
        event_type = None
        data_lines = []
        
        for line in response.iter_lines():
            line = line.strip()
            
            if line.startswith("event:"):
                event_type = line[6:].strip()
            elif line.startswith("data:"):
                data_lines.append(line[5:].strip())
            elif line == "" and data_lines:
                # Empty line signals end of event
                data = "\n".join(data_lines)
                data_lines = []
                
                if data:
                    parsed = safe_json_loads(data)
                    if parsed:
                        yield {"event": event_type, "data": parsed}
                
                event_type = None
    
    def _send_jsonrpc(self, method: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Send a JSON-RPC request to MCP service.
        
        Args:
            method: JSON-RPC method name
            params: Method parameters
        
        Returns:
            Response data
        
        Raises:
            MCPError: On communication or protocol errors
        """
        request_id = self._next_request_id()
        
        payload = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
        }
        if params:
            payload["params"] = params
        
        logger.info(f"MCP request: method={method}, id={request_id}")
        
        try:
            with httpx.Client(timeout=self.timeout_sec) as client:
                response = client.post(
                    self.base_url,
                    headers=self._build_headers(),
                    json=payload,
                )
                response.raise_for_status()
                
                # Collect all SSE events
                result_data = None
                error_data = None
                
                for event in self._parse_sse_events(response):
                    event_data = event.get("data", {})
                    
                    # Check for result
                    if "result" in event_data:
                        result_data = event_data["result"]
                    
                    # Check for error
                    if "error" in event_data:
                        error_data = event_data["error"]
                
                if error_data:
                    raise MCPError(f"MCP error: {error_data}")
                
                if result_data is not None:
                    return result_data
                
                # If no result, return the last event data
                return event_data if 'event_data' in dir() else {}
                
        except httpx.HTTPStatusError as e:
            logger.error(f"MCP HTTP error: {e}")
            raise MCPError(f"HTTP error: {e.response.status_code}")
        except httpx.RequestError as e:
            logger.error(f"MCP request error: {e}")
            raise MCPError(f"Request error: {e}")
        except Exception as e:
            logger.error(f"MCP unexpected error: {e}")
            raise MCPError(f"Unexpected error: {e}")
    
    def initialize(self) -> Dict[str, Any]:
        """
        Initialize MCP connection.
        
        Returns:
            Server capabilities
        """
        return self._send_jsonrpc("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "BettaFish-LangGraph",
                "version": "1.0.0"
            }
        })
    
    def list_tools(self) -> List[Dict[str, Any]]:
        """
        List available MCP tools.
        
        Returns:
            List of tool definitions
        """
        result = self._send_jsonrpc("tools/list")
        return result.get("tools", []) if isinstance(result, dict) else []
    
    def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call an MCP tool.
        
        Args:
            name: Tool name
            arguments: Tool arguments
        
        Returns:
            Tool execution result
        """
        return self._send_jsonrpc("tools/call", {
            "name": name,
            "arguments": arguments
        })
    
    def list_knowledge_bases(self) -> List[Dict[str, Any]]:
        """
        List available knowledge bases.
        
        Attempts to call knowledge base listing tool.
        
        Returns:
            List of knowledge base info dicts
        """
        try:
            # Try common tool names for listing KBs
            for tool_name in ["list_knowledge_bases", "listKnowledgeBases", "kb_list"]:
                try:
                    result = self.call_tool(tool_name, {})
                    if result:
                        return result.get("knowledge_bases", result.get("kbs", []))
                except MCPError:
                    continue
            
            # Fallback: check tools list for KB-related tools
            tools = self.list_tools()
            kb_tools = [t for t in tools if "knowledge" in t.get("name", "").lower() or "kb" in t.get("name", "").lower()]
            logger.info(f"Found KB-related tools: {[t['name'] for t in kb_tools]}")
            
            return []
            
        except Exception as e:
            logger.error(f"Failed to list knowledge bases: {e}")
            return []
    
    def query_knowledge_base(
        self,
        kb_id: str,
        query: str,
        mode: str = "hybrid",
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        Query a knowledge base.
        
        Args:
            kb_id: Knowledge base ID
            query: Query string
            mode: Search mode (hybrid, semantic, keyword)
            top_k: Number of results to return
        
        Returns:
            Query results
        """
        try:
            # Try common tool names for querying
            for tool_name in ["query_knowledge_base", "queryKnowledgeBase", "kb_query", "search_kb"]:
                try:
                    result = self.call_tool(tool_name, {
                        "knowledge_base_id": kb_id,
                        "query": query,
                        "mode": mode,
                        "top_k": top_k
                    })
                    return result
                except MCPError:
                    continue
            
            return {"error": "No knowledge base query tool found"}
            
        except Exception as e:
            logger.error(f"Failed to query knowledge base: {e}")
            return {"error": str(e)}


def get_mcp_client(token: Optional[str] = None) -> MCPClient:
    """
    Get an MCP client instance.
    
    Args:
        token: Optional token override
    
    Returns:
        MCPClient instance
    """
    return MCPClient(token=token)


# ==== Test helper methods ====

def _build_request(method: str, params: Optional[Dict] = None, request_id: int = 1) -> Dict[str, Any]:
    """
    Build a JSON-RPC request payload (for testing).
    
    Args:
        method: JSON-RPC method name
        params: Method parameters
        request_id: Request ID
    
    Returns:
        JSON-RPC request dict
    """
    payload = {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": method,
    }
    if params:
        payload["params"] = params
    return payload


def _parse_sse_line(line: str) -> Optional[Dict[str, Any]]:
    """
    Parse a single SSE line (for testing).
    
    Args:
        line: SSE line
    
    Returns:
        Parsed data or None
    """
    line = line.strip()
    
    if not line:
        return None
    
    if line.startswith("event:"):
        return None  # Event type line, not data
    
    if line.startswith("data:"):
        data_str = line[5:].strip()
        return safe_json_loads(data_str)
    
    return None


def _select_relevant_kbs(
    query: str,
    available_kbs: List[Dict[str, Any]],
    max_kbs: int = 3
) -> List[str]:
    """
    Select relevant knowledge bases based on query (simple heuristic).
    
    Args:
        query: User query
        available_kbs: Available knowledge bases
        max_kbs: Maximum number to select
    
    Returns:
        List of selected KB IDs
    """
    if not available_kbs:
        return []
    
    # Simple keyword matching
    selected = []
    query_lower = query.lower()
    
    for kb in available_kbs:
        kb_name = kb.get("name", "").lower()
        kb_desc = kb.get("description", "").lower()
        
        # Check for keyword overlap
        if any(word in kb_name or word in kb_desc for word in query_lower.split()):
            selected.append(kb.get("id"))
    
    # If no matches, return first few
    if not selected:
        selected = [kb.get("id") for kb in available_kbs[:max_kbs]]
    
    return selected[:max_kbs]


# Add methods to MCPClient for testing compatibility
MCPClient._build_request = lambda self, method, params=None: _build_request(method, params, self._next_request_id())
MCPClient._parse_sse_line = staticmethod(lambda line: _parse_sse_line(line))
MCPClient._select_relevant_kbs = staticmethod(lambda query, kbs, max_kbs=3: _select_relevant_kbs(query, kbs, max_kbs))
