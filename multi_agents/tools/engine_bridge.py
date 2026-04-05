# -*- coding: utf-8 -*-
"""
Engine Bridge for LangGraph Multi-Agent System.

Provides a unified interface to call the original BettaFish engines
(QueryEngine, MediaEngine, InsightEngine, ForumEngine, ReportEngine)
from LangGraph nodes.
"""

import sys
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
import time

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from multi_agents.settings import get_settings, Settings
from multi_agents.tools.logger import get_logger, TaskLogger
from multi_agents.tools.json_utils import safe_json_loads

logger = get_logger("engine_bridge")


class EngineBridge:
    """
    Bridge layer for calling original BettaFish engines.
    
    Wraps each engine's functionality with a standardized interface
    for use by LangGraph nodes.
    """
    
    def __init__(self, settings: Optional[Settings] = None):
        """
        Initialize the engine bridge.
        
        Args:
            settings: Settings instance, or None to use global settings
        """
        self.settings = settings or get_settings()
        self._query_engine = None
        self._media_engine = None
        self._insight_engine = None
        self._report_engine = None
    
    def _import_query_engine(self):
        """Lazy import QueryEngine."""
        if self._query_engine is None:
            try:
                from QueryEngine.agent import DeepSearchAgent
                self._query_engine = DeepSearchAgent
            except ImportError as e:
                logger.error(f"Failed to import QueryEngine: {e}")
                raise
        return self._query_engine
    
    def _import_media_engine(self):
        """Lazy import MediaEngine."""
        if self._media_engine is None:
            try:
                from MediaEngine.agent import DeepSearchAgent
                self._media_engine = DeepSearchAgent
            except ImportError as e:
                logger.error(f"Failed to import MediaEngine: {e}")
                raise
        return self._media_engine
    
    def _import_insight_engine(self):
        """Lazy import InsightEngine."""
        if self._insight_engine is None:
            try:
                from InsightEngine.agent import DeepSearchAgent
                self._insight_engine = DeepSearchAgent
            except ImportError as e:
                logger.error(f"Failed to import InsightEngine: {e}")
                raise
        return self._insight_engine
    
    def _import_report_engine(self):
        """Lazy import ReportEngine."""
        if self._report_engine is None:
            try:
                from ReportEngine.agent import ReportAgent
                self._report_engine = ReportAgent
            except ImportError as e:
                logger.error(f"Failed to import ReportEngine: {e}")
                raise
        return self._report_engine
    
    def run_query_engine(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Run the QueryEngine for public web/news analysis.
        
        Args:
            query: Search query
            context: Additional context (time_range, focus, locale, etc.)
        
        Returns:
            Standardized output dict with summary, sources, raw_result, stats, logs
        """
        context = context or {}
        task_id = context.get("task_id", "unknown")
        logs = []
        start_time = time.time()
        
        logs.append(f"Starting QueryEngine for: {query}")
        
        try:
            # Import and instantiate
            AgentClass = self._import_query_engine()
            
            # Import config for engine
            from config import settings as app_settings
            agent = AgentClass(config=app_settings)
            
            logs.append("QueryEngine initialized")
            
            # Run research
            report = agent.research(query=query, save_report=True)
            
            logs.append("QueryEngine research completed")
            
            # Extract structured result
            duration = time.time() - start_time
            
            return {
                "summary": report if isinstance(report, str) else str(report),
                "sources": self._extract_sources_from_report(report),
                "raw_result": {"report": report},
                "stats": {
                    "duration_seconds": duration,
                    "engine": "QueryEngine",
                },
                "logs": logs,
            }
            
        except Exception as e:
            logs.append(f"QueryEngine error: {str(e)}")
            logger.exception(f"QueryEngine failed: {e}")
            
            return {
                "summary": f"QueryEngine分析失败: {str(e)}",
                "sources": [],
                "raw_result": {"error": str(e)},
                "stats": {"duration_seconds": time.time() - start_time, "error": True},
                "logs": logs,
            }
    
    def run_media_engine(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Run the MediaEngine for media/multimedia analysis.
        
        Args:
            query: Search query
            context: Additional context
        
        Returns:
            Standardized output dict
        """
        context = context or {}
        task_id = context.get("task_id", "unknown")
        logs = []
        start_time = time.time()
        
        logs.append(f"Starting MediaEngine for: {query}")
        
        try:
            AgentClass = self._import_media_engine()
            
            from config import settings as app_settings
            agent = AgentClass(config=app_settings)
            
            logs.append("MediaEngine initialized")
            
            report = agent.research(query=query, save_report=True)
            
            logs.append("MediaEngine research completed")
            
            duration = time.time() - start_time
            
            return {
                "summary": report if isinstance(report, str) else str(report),
                "platform_distribution": {},
                "media_highlights": [],
                "sources": self._extract_sources_from_report(report),
                "raw_result": {"report": report},
                "stats": {
                    "duration_seconds": duration,
                    "engine": "MediaEngine",
                },
                "logs": logs,
            }
            
        except Exception as e:
            logs.append(f"MediaEngine error: {str(e)}")
            logger.exception(f"MediaEngine failed: {e}")
            
            return {
                "summary": f"MediaEngine分析失败: {str(e)}",
                "platform_distribution": {},
                "media_highlights": [],
                "sources": [],
                "raw_result": {"error": str(e)},
                "stats": {"duration_seconds": time.time() - start_time, "error": True},
                "logs": logs,
            }
    
    def run_insight_engine(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Run the InsightEngine for sentiment/topic analysis.
        
        Args:
            query: Search query
            context: Additional context
        
        Returns:
            Standardized output dict
        """
        context = context or {}
        task_id = context.get("task_id", "unknown")
        logs = []
        start_time = time.time()
        
        logs.append(f"Starting InsightEngine for: {query}")
        
        try:
            AgentClass = self._import_insight_engine()
            
            from config import settings as app_settings
            agent = AgentClass(config=app_settings)
            
            logs.append("InsightEngine initialized")
            
            report = agent.research(query=query, save_report=True)
            
            logs.append("InsightEngine research completed")
            
            duration = time.time() - start_time
            
            return {
                "summary": report if isinstance(report, str) else str(report),
                "sentiment_summary": {},
                "keyword_clusters": [],
                "topic_clusters": [],
                "risk_signals": [],
                "sources": self._extract_sources_from_report(report),
                "raw_result": {"report": report},
                "stats": {
                    "duration_seconds": duration,
                    "engine": "InsightEngine",
                },
                "logs": logs,
            }
            
        except Exception as e:
            logs.append(f"InsightEngine error: {str(e)}")
            logger.exception(f"InsightEngine failed: {e}")
            
            return {
                "summary": f"InsightEngine分析失败: {str(e)}",
                "sentiment_summary": {},
                "keyword_clusters": [],
                "topic_clusters": [],
                "risk_signals": [],
                "sources": [],
                "raw_result": {"error": str(e)},
                "stats": {"duration_seconds": time.time() - start_time, "error": True},
                "logs": logs,
            }
    
    def run_forum_round(
        self,
        query: str,
        inputs: Dict[str, Any],
        round_index: int,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Run a single forum discussion round.
        
        Args:
            query: Original query
            inputs: Combined inputs (query_result, media_result, insight_result, kb_result)
            round_index: Round number (0, 1, or 2)
            context: Additional context
        
        Returns:
            Forum round output dict
        """
        context = context or {}
        task_id = context.get("task_id", "unknown")
        
        # For forum rounds, we use the LLM to synthesize results
        # This is handled by the forum_round nodes using LLM prompts
        # Here we just provide a stub for direct bridge calls
        
        return {
            "round_index": round_index,
            "round_summary": f"Forum round {round_index + 1} placeholder",
            "conflicts": [],
            "missing_evidence": [],
            "followup_suggestions": [],
            "intermediate_conclusion": "",
        }
    
    def run_report_engine(
        self,
        query: str,
        merged_result: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Run the ReportEngine to generate final reports.
        
        Args:
            query: Original query
            merged_result: Merged analysis results
            context: Additional context
        
        Returns:
            Report output dict with file paths
        """
        context = context or {}
        task_id = context.get("task_id", "unknown")
        logs = []
        start_time = time.time()
        
        logs.append(f"Starting ReportEngine for: {query}")
        
        try:
            AgentClass = self._import_report_engine()
            
            from config import settings as app_settings
            agent = AgentClass(config=app_settings)
            
            logs.append("ReportEngine initialized")
            
            # The report engine reads from markdown files in the engine directories
            # Trigger report generation
            result = agent.generate_report()
            
            logs.append("ReportEngine completed")
            
            duration = time.time() - start_time
            
            # Find generated files
            from pathlib import Path
            final_reports_dir = PROJECT_ROOT / "final_reports"
            
            html_files = sorted(final_reports_dir.glob("*_report.html"), reverse=True)
            pdf_files = sorted(final_reports_dir.glob("*_report.pdf"), reverse=True)
            
            html_path = str(html_files[0]) if html_files else ""
            pdf_path = str(pdf_files[0]) if pdf_files else ""
            
            return {
                "summary_text": result if isinstance(result, str) else "",
                "html_path": html_path,
                "pdf_path": pdf_path,
                "docx_path": "",
                "md_path": "",
                "chart_paths": [],
                "manifest": {
                    "query": query,
                    "task_id": task_id,
                    "duration_seconds": duration,
                },
            }
            
        except Exception as e:
            logs.append(f"ReportEngine error: {str(e)}")
            logger.exception(f"ReportEngine failed: {e}")
            
            return {
                "summary_text": f"报告生成失败: {str(e)}",
                "html_path": "",
                "pdf_path": "",
                "docx_path": "",
                "md_path": "",
                "chart_paths": [],
                "manifest": {"error": str(e)},
            }
    
    def _extract_sources_from_report(self, report: str) -> List[Dict[str, Any]]:
        """
        Extract source references from a markdown report.
        
        Args:
            report: Markdown report text
        
        Returns:
            List of source dicts
        """
        sources = []
        
        if not report:
            return sources
        
        import re
        
        # Look for URLs
        url_pattern = r'https?://[^\s\)\]>]+'
        urls = re.findall(url_pattern, report)
        
        for url in urls[:20]:  # Limit to 20 sources
            sources.append({
                "title": "",
                "url": url,
                "platform": self._guess_platform(url),
                "snippet": "",
            })
        
        return sources
    
    def _guess_platform(self, url: str) -> str:
        """Guess the platform from a URL."""
        url_lower = url.lower()
        
        platforms = {
            "weibo": "微博",
            "zhihu": "知乎",
            "douyin": "抖音",
            "bilibili": "哔哩哔哩",
            "xiaohongshu": "小红书",
            "github": "GitHub",
            "twitter": "Twitter",
            "baidu": "百度",
            "sina": "新浪",
            "163": "网易",
            "qq": "腾讯",
        }
        
        for key, name in platforms.items():
            if key in url_lower:
                return name
        
        return "网络"


# Global bridge instance
_bridge: Optional[EngineBridge] = None


def get_engine_bridge() -> EngineBridge:
    """Get the global engine bridge instance."""
    global _bridge
    if _bridge is None:
        _bridge = EngineBridge()
    return _bridge
