# -*- coding: utf-8 -*-
"""
Settings module for LangGraph Multi-Agent System.

Centralizes all environment variable management and configuration.
All nodes and tools should read configuration from this module only.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import os

# Load .env file
from dotenv import load_dotenv
load_dotenv()


@dataclass
class Settings:
    """
    Central configuration for the LangGraph public opinion agent.
    
    All environment variables are read once and cached here.
    Nodes should never call os.getenv directly.
    """
    
    # ==================== LLM Configuration ====================
    # OpenAI-compatible model service
    openai_base_url: str = "http://192.168.195.195:18011/v1"
    openai_api_key: str = ""
    
    # Role-specific models (can all use the same model or different ones)
    llm_planner_model: str = ""
    llm_analysis_model: str = ""
    llm_moderator_model: str = ""
    llm_report_model: str = ""
    
    # ==================== MCP Configuration ====================
    alb_mcp_url: str = "http://192.168.195.195:18012/api/mcp"
    alb_mcp_token_fallback: str = ""
    
    # ==================== Search Configuration ====================
    # Primary retriever (free option)
    retriever: str = "duckduckgo"
    
    # Backup search providers (for future use)
    tavily_api_key: Optional[str] = None
    anspire_api_key: Optional[str] = None
    anspire_base_url: str = "https://plugin.anspire.cn/api/ntsearch/search"
    bocha_api_key: Optional[str] = None
    bocha_base_url: str = "https://api.bocha.cn/v1/ai-search"
    
    # ==================== Output Configuration ====================
    report_output_dir: Path = field(default_factory=lambda: Path("./outputs"))
    public_report_base_url: str = "http://192.168.195.195:18019/outputs"
    
    # ==================== Runtime Configuration ====================
    debug: bool = False
    request_timeout_sec: int = 120
    max_retries: int = 2
    
    # ==================== Engine Search Limits ====================
    max_search_results_for_llm: int = 50
    max_reflections: int = 3
    max_paragraphs: int = 6
    search_timeout: int = 240
    max_content_length: int = 500000

    # ==================== Engine Bridge (HTTP only) ====================
    engine_request_timeout_sec: int = 180
    engine_max_retries: int = 2
    query_engine_url: str = "http://127.0.0.1:19000/v1/research/query"
    media_engine_url: str = "http://127.0.0.1:19000/v1/research/media"
    insight_engine_url: str = "http://127.0.0.1:19000/v1/research/insight"
    report_engine_url: str = "http://127.0.0.1:19000/v1/report"
    engine_api_token: str = ""


def load_settings() -> Settings:
    """
    Load settings from environment variables.
    
    Returns:
        Settings: Configured settings instance
    """
    return Settings(
        # LLM Configuration
        openai_base_url=os.getenv("OPENAI_BASE_URL", "http://192.168.195.195:18011/v1"),
        openai_api_key=os.getenv("OPENAI_API_KEY", "gpustack_713b42e0114f7c5a_66a63fc0a2640fa577fc19575a9de515"),
        llm_planner_model=os.getenv("LLM_PLANNER_MODEL", ""),
        llm_analysis_model=os.getenv("LLM_ANALYSIS_MODEL", ""),
        llm_moderator_model=os.getenv("LLM_MODERATOR_MODEL", ""),
        llm_report_model=os.getenv("LLM_REPORT_MODEL", ""),
        
        # MCP Configuration
        alb_mcp_url=os.getenv("ALB_MCP_URL", "http://192.168.195.195:18012/api/mcp"),
        alb_mcp_token_fallback=os.getenv("ALB_MCP_TOKEN_FALLBACK", ""),
        
        # Search Configuration
        retriever=os.getenv("RETRIEVER", "duckduckgo"),
        tavily_api_key=os.getenv("TAVILY_API_KEY"),
        anspire_api_key=os.getenv("ANSPIRE_API_KEY"),
        anspire_base_url=os.getenv("ANSPIRE_BASE_URL", "https://plugin.anspire.cn/api/ntsearch/search"),
        bocha_api_key=os.getenv("BOCHA_WEB_SEARCH_API_KEY"),
        bocha_base_url=os.getenv("BOCHA_BASE_URL", "https://api.bocha.cn/v1/ai-search"),
        
        # Output Configuration
        report_output_dir=Path(os.getenv("REPORT_OUTPUT_DIR", "./outputs")),
        public_report_base_url=os.getenv("PUBLIC_REPORT_BASE_URL", "http://192.168.195.195:18019/outputs"),
        
        # Runtime Configuration
        debug=os.getenv("DEBUG", "0") == "1",
        request_timeout_sec=int(os.getenv("REQUEST_TIMEOUT_SEC", "120")),
        max_retries=int(os.getenv("MAX_RETRIES", "2")),
        
        # Engine Search Limits
        max_search_results_for_llm=int(os.getenv("MAX_SEARCH_RESULTS_FOR_LLM", "50")),
        max_reflections=int(os.getenv("MAX_REFLECTIONS", "3")),
        max_paragraphs=int(os.getenv("MAX_PARAGRAPHS", "6")),
        search_timeout=int(os.getenv("SEARCH_TIMEOUT", "240")),
        max_content_length=int(os.getenv("MAX_CONTENT_LENGTH", "500000")),

        # Engine Bridge (HTTP only)
        engine_request_timeout_sec=int(os.getenv("ENGINE_REQUEST_TIMEOUT_SEC", "180")),
        engine_max_retries=int(os.getenv("ENGINE_MAX_RETRIES", "2")),
        query_engine_url=os.getenv("QUERY_ENGINE_URL", "http://127.0.0.1:19000/v1/research/query"),
        media_engine_url=os.getenv("MEDIA_ENGINE_URL", "http://127.0.0.1:19000/v1/research/media"),
        insight_engine_url=os.getenv("INSIGHT_ENGINE_URL", "http://127.0.0.1:19000/v1/research/insight"),
        report_engine_url=os.getenv("REPORT_ENGINE_URL", "http://127.0.0.1:19000/v1/report"),
        engine_api_token=os.getenv("ENGINE_API_TOKEN", ""),
    )


# Global settings instance (lazy loaded)
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """
    Get the global settings instance, loading it if necessary.
    
    Returns:
        Settings: The global settings instance
    """
    global _settings
    if _settings is None:
        _settings = load_settings()
    return _settings


def reload_settings() -> Settings:
    """
    Force reload settings from environment.
    
    Returns:
        Settings: New settings instance
    """
    global _settings
    _settings = load_settings()
    return _settings
