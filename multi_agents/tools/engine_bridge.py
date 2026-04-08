# -*- coding: utf-8 -*-
"""
Engine Bridge for LangGraph Multi-Agent System.

Provides a unified HTTP interface to call BettaFish engines
from LangGraph nodes.

This bridge is intentionally stateless and HTTP-only so the
multi_agents package can run independently from engine code.
"""

from typing import Dict, Any, Optional, List
import time
import requests

from multi_agents.settings import get_settings, Settings
from multi_agents.tools.logger import get_logger

logger = get_logger("engine_bridge")


class EngineBridge:
    """
    Bridge layer for calling BettaFish engines via HTTP.

    The bridge keeps no mutable request state and is safe to use from
    concurrent graph executions.
    """
    
    def __init__(self, settings: Optional[Settings] = None):
        """
        Initialize the engine bridge.
        
        Args:
            settings: Settings instance, or None to use global settings
        """
        self.settings = settings or get_settings()

    def _build_headers(self, task_id: str) -> Dict[str, str]:
        """Build per-request headers for engine APIs."""
        headers: Dict[str, str] = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        if task_id:
            headers["X-Task-Id"] = task_id

        if self.settings.engine_api_token:
            headers["Authorization"] = f"Bearer {self.settings.engine_api_token}"

        return headers

    def _post_json(
        self,
        url: str,
        payload: Dict[str, Any],
        task_id: str,
        logs: List[str],
    ) -> Dict[str, Any]:
        """
        Send a JSON POST request with retry.

        This method is stateless and does not keep request/session state,
        which makes it safe under concurrent graph runs.
        """
        max_attempts = max(1, self.settings.engine_max_retries + 1)
        timeout = max(1, self.settings.engine_request_timeout_sec)
        last_error = ""

        for attempt in range(1, max_attempts + 1):
            try:
                logs.append(f"HTTP POST attempt {attempt}/{max_attempts}: {url}")
                resp = requests.post(
                    url,
                    json=payload,
                    headers=self._build_headers(task_id),
                    timeout=timeout,
                )
                if resp.status_code >= 400:
                    body_preview = (resp.text or "")[:1000]
                    raise RuntimeError(f"HTTP {resp.status_code}: {body_preview}")

                data = resp.json()
                if not isinstance(data, dict):
                    raise ValueError("Engine response is not a JSON object")
                return data
            except Exception as e:
                last_error = str(e)
                logs.append(f"Attempt {attempt} failed: {last_error}")
                if attempt < max_attempts:
                    time.sleep(min(2 ** (attempt - 1), 3))

        raise RuntimeError(last_error or "Unknown HTTP error")
    
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
            payload = {
                "query": query,
                "context": context,
            }
            data = self._post_json(self.settings.query_engine_url, payload, task_id, logs)

            duration = time.time() - start_time

            summary = data.get("summary") or data.get("report") or ""
            sources = data.get("sources") or self._extract_sources_from_report(str(summary))
            
            return {
                "summary": summary if isinstance(summary, str) else str(summary),
                "sources": sources if isinstance(sources, list) else [],
                "raw_result": data,
                "stats": {
                    "duration_seconds": duration,
                    "engine": "QueryEngine",
                },
                "logs": logs + (data.get("logs") if isinstance(data.get("logs"), list) else []),
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
            payload = {
                "query": query,
                "context": context,
            }
            data = self._post_json(self.settings.media_engine_url, payload, task_id, logs)

            duration = time.time() - start_time
            summary = data.get("summary") or data.get("report") or ""
            
            return {
                "summary": summary if isinstance(summary, str) else str(summary),
                "platform_distribution": data.get("platform_distribution") if isinstance(data.get("platform_distribution"), dict) else {},
                "media_highlights": data.get("media_highlights") if isinstance(data.get("media_highlights"), list) else [],
                "sources": data.get("sources") if isinstance(data.get("sources"), list) else self._extract_sources_from_report(str(summary)),
                "raw_result": data,
                "stats": {
                    "duration_seconds": duration,
                    "engine": "MediaEngine",
                },
                "logs": logs + (data.get("logs") if isinstance(data.get("logs"), list) else []),
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
            payload = {
                "query": query,
                "context": context,
            }
            data = self._post_json(self.settings.insight_engine_url, payload, task_id, logs)

            duration = time.time() - start_time
            summary = data.get("summary") or data.get("report") or ""
            
            return {
                "summary": summary if isinstance(summary, str) else str(summary),
                "sentiment_summary": data.get("sentiment_summary") if isinstance(data.get("sentiment_summary"), dict) else {},
                "keyword_clusters": data.get("keyword_clusters") if isinstance(data.get("keyword_clusters"), list) else [],
                "topic_clusters": data.get("topic_clusters") if isinstance(data.get("topic_clusters"), list) else [],
                "risk_signals": data.get("risk_signals") if isinstance(data.get("risk_signals"), list) else [],
                "sources": data.get("sources") if isinstance(data.get("sources"), list) else self._extract_sources_from_report(str(summary)),
                "raw_result": data,
                "stats": {
                    "duration_seconds": duration,
                    "engine": "InsightEngine",
                },
                "logs": logs + (data.get("logs") if isinstance(data.get("logs"), list) else []),
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
            payload = {
                "query": query,
                "merged_result": merged_result,
                "context": context,
            }
            data = self._post_json(self.settings.report_engine_url, payload, task_id, logs)
            logs.append("ReportEngine completed")
            
            duration = time.time() - start_time
            
            return {
                "summary_text": data.get("summary_text") or data.get("summary") or "",
                "html_path": data.get("html_path", ""),
                "pdf_path": data.get("pdf_path", ""),
                "docx_path": data.get("docx_path", ""),
                "md_path": data.get("md_path", ""),
                "chart_paths": data.get("chart_paths") if isinstance(data.get("chart_paths"), list) else [],
                "manifest": {
                    "query": query,
                    "task_id": task_id,
                    "duration_seconds": duration,
                    "engine": "ReportEngine",
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
    
    def _normalize_output(self, raw_output: Any) -> Dict[str, Any]:
        """
        Normalize any output format to a standard dict.
        
        Args:
            raw_output: Raw output from engine (dict, str, or None)
        
        Returns:
            Normalized dict with 'content' and 'metadata' keys
        """
        if raw_output is None or raw_output == "":
            return {"content": "", "metadata": {"format": "empty"}}
        
        if isinstance(raw_output, dict):
            content = raw_output.get("report_content") or raw_output.get("content") or str(raw_output)
            return {
                "content": content,
                "metadata": {
                    "format": "dict",
                    "keys": list(raw_output.keys())
                }
            }
        
        if isinstance(raw_output, str):
            return {
                "content": raw_output,
                "metadata": {"format": "text"}
            }
        
        return {
            "content": str(raw_output),
            "metadata": {"format": "unknown"}
        }
    
    def _is_valid_engine(self, engine_name: str) -> bool:
        """
        Check if an engine name is valid.
        
        Args:
            engine_name: Name of the engine
        
        Returns:
            True if valid, False otherwise
        """
        valid_engines = {"query", "media", "insight", "report", "forum"}
        return engine_name.lower() in valid_engines


# Global bridge instance
_bridge: Optional[EngineBridge] = None


def get_engine_bridge() -> EngineBridge:
    """Get the global engine bridge instance."""
    global _bridge
    if _bridge is None:
        _bridge = EngineBridge()
    return _bridge
