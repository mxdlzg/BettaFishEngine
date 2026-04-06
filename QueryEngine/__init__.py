"""
Deep Search Agent
一个深度搜索AI代理实现

支持两种调用方式：
1. 传统方式: DeepSearchAgent 类
2. LangGraph方式: create_deep_search_graph() 或 run_deep_search()
"""

from .agent import DeepSearchAgent, create_agent
from .utils.config import Settings

# LangGraph版本
try:
    from .graph import (
        DeepSearchState,
        create_deep_search_graph,
        run_deep_search
    )
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    DeepSearchState = None
    create_deep_search_graph = None
    run_deep_search = None

__version__ = "1.1.0"
__author__ = "Deep Search Agent Team"

__all__ = [
    # 传统方式
    "DeepSearchAgent", 
    "create_agent", 
    "Settings",
    # LangGraph方式
    "DeepSearchState",
    "create_deep_search_graph",
    "run_deep_search",
    "LANGGRAPH_AVAILABLE"
]
