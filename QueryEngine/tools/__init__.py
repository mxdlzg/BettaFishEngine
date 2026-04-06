"""
工具调用模块
提供外部工具接口，如网络搜索等
"""

from .duckduckgo_search import (
    DuckDuckGoNewsAgency, 
    SearchResult, 
    DuckDuckGoResponse, 
    ImageResult
)

__all__ = [
    "DuckDuckGoNewsAgency", 
    "SearchResult", 
    "DuckDuckGoResponse", 
    "ImageResult"
]
