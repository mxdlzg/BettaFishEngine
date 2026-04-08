# -*- coding: utf-8 -*-
"""
Unified Engine Gateway API.

Single-process API service that exposes HTTP endpoints for QueryEngine,
MediaEngine, InsightEngine, and ReportEngine.

Design goals:
- Stateless request handling
- Concurrent-safe execution (no shared mutable request state)
- Single deployment entrypoint for multi_agents integration

This API is designed to be consumed by independently deployed clients.
"""

from __future__ import annotations

import os
import re
import logging
import uuid
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

import uvicorn
from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("engine_gateway")


app = FastAPI(
    title="BettaFish Engine Gateway",
    version="1.1.0",
    description="Standalone gateway for Query/Media/Insight/Report BettaFish engines.",
)


class ResearchRequest(BaseModel):
    query: str = Field(..., description="Research query")
    context: Dict[str, Any] = Field(default_factory=dict, description="Optional context")
    save_report: bool = Field(default=True, description="Whether engine should save report files")
    export_formats: Optional[List[str]] = Field(default=None, description="Optional export formats for QueryEngine")
    engine: Optional[str] = Field(default=None, description="query|media|insight (only for /v1/research)")


class ReportRequest(BaseModel):
    query: str = Field(..., description="Final report query")
    reports: Optional[Union[List[Any], Dict[str, Any]]] = Field(
        default=None,
        description="Optional explicit reports. Accepts list [query, media, insight] or dict.",
    )
    forum_logs: str = Field(default="", description="Optional forum discussion logs")
    custom_template: str = Field(default="", description="Optional custom report template content/path")
    save_report: bool = Field(default=True, description="Whether to persist report artifacts")
    merged_result: Dict[str, Any] = Field(default_factory=dict, description="Merged analysis result")
    context: Dict[str, Any] = Field(default_factory=dict, description="Optional context metadata")


class EngineRuntime:
    """
    Runtime container for embedded engine classes/settings.

    Startup phase loads and validates all engine modules.
    Request phase creates fresh agent instances for concurrency safety.
    """

    def __init__(self):
        self.ready = False
        self.query_agent_class = None
        self.query_settings = None
        self.media_agent_class = None
        self.media_settings = None
        self.insight_agent_class = None
        self.insight_settings = None
        self.report_agent_class = None
        self.report_settings = None

    def initialize(self) -> None:
        project_root = Path(__file__).resolve().parent
        required_files = [
            project_root / "QueryEngine" / "agent.py",
            project_root / "QueryEngine" / "utils" / "config.py",
            project_root / "MediaEngine" / "agent.py",
            project_root / "InsightEngine" / "agent.py",
            project_root / "ReportEngine" / "agent.py",
        ]
        missing = [str(p) for p in required_files if not p.exists()]
        if missing:
            raise RuntimeError(f"Missing embedded engine files: {missing}")

        from QueryEngine.agent import DeepSearchAgent as QueryAgent
        from QueryEngine.utils.config import settings as query_settings
        from MediaEngine.agent import DeepSearchAgent as MediaAgent
        from MediaEngine.utils.config import settings as media_settings
        from InsightEngine.agent import DeepSearchAgent as InsightAgent
        from InsightEngine.utils.config import settings as insight_settings
        from ReportEngine.agent import ReportAgent
        from ReportEngine.utils.config import settings as report_settings

        self.query_agent_class = QueryAgent
        self.query_settings = query_settings
        self.media_agent_class = MediaAgent
        self.media_settings = media_settings
        self.insight_agent_class = InsightAgent
        self.insight_settings = insight_settings
        self.report_agent_class = ReportAgent
        self.report_settings = report_settings
        self.ready = True

    def ensure_ready(self) -> None:
        if not self.ready:
            raise RuntimeError("Engine runtime is not initialized")

    def create_query_agent(self):
        self.ensure_ready()
        return self.query_agent_class(config=self.query_settings)

    def create_media_agent(self):
        self.ensure_ready()
        return self.media_agent_class(config=self.media_settings)

    def create_insight_agent(self):
        self.ensure_ready()
        return self.insight_agent_class(config=self.insight_settings)

    def create_report_agent(self):
        self.ensure_ready()
        return self.report_agent_class(config=self.report_settings)


ENGINE_RUNTIME = EngineRuntime()


def _iso_now() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _build_manifest(engine: str, request_id: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    ctx = context or {}
    return {
        "engine": engine,
        "request_id": request_id,
        "task_id": str(ctx.get("task_id", "")),
        "timestamp": _iso_now(),
    }


def _local_query_engine(query: str, save_report: bool, export_formats: Optional[List[str]]) -> Dict[str, Any]:
    agent = ENGINE_RUNTIME.create_query_agent()
    report = agent.research(query=query, save_report=save_report, export_formats=export_formats)
    summary = report if isinstance(report, str) else str(report)
    return {
        "summary": summary,
        "sources": _extract_sources_from_text(summary),
        "raw_result": {"report": report},
        "logs": ["QueryEngine completed"],
    }


def _local_media_engine(query: str, save_report: bool) -> Dict[str, Any]:
    agent = ENGINE_RUNTIME.create_media_agent()
    report = agent.research(query=query, save_report=save_report)
    summary = report if isinstance(report, str) else str(report)
    return {
        "summary": summary,
        "platform_distribution": {},
        "media_highlights": [],
        "sources": _extract_sources_from_text(summary),
        "raw_result": {"report": report},
        "logs": ["MediaEngine completed"],
    }


def _local_insight_engine(query: str, save_report: bool) -> Dict[str, Any]:
    agent = ENGINE_RUNTIME.create_insight_agent()
    report = agent.research(query=query, save_report=save_report)
    summary = report if isinstance(report, str) else str(report)
    return {
        "summary": summary,
        "sentiment_summary": {},
        "keyword_clusters": [],
        "topic_clusters": [],
        "risk_signals": [],
        "sources": _extract_sources_from_text(summary),
        "raw_result": {"report": report},
        "logs": ["InsightEngine completed"],
    }


def _local_report_engine(body: ReportRequest, reports: List[Any], forum_logs: str) -> Dict[str, Any]:
    agent = ENGINE_RUNTIME.create_report_agent()
    return agent.generate_report(
        query=body.query,
        reports=reports,
        forum_logs=forum_logs,
        custom_template=body.custom_template,
        save_report=body.save_report,
    )


def _extract_sources_from_text(text: str) -> List[Dict[str, str]]:
    if not text:
        return []
    urls = re.findall(r"https?://[^\s\)\]>]+", text)
    dedup: List[str] = []
    for url in urls:
        if url not in dedup:
            dedup.append(url)
    return [{"title": "", "url": url, "platform": "network", "snippet": ""} for url in dedup[:20]]


def _check_auth(authorization: Optional[str]) -> Tuple[bool, str]:
    expected = os.getenv("ENGINE_API_TOKEN", "").strip()
    if not expected:
        return True, ""

    auth_header = authorization or ""
    prefix = "Bearer "
    if not auth_header.startswith(prefix):
        return False, "missing bearer token"

    token = auth_header[len(prefix):].strip()
    if token != expected:
        return False, "invalid token"

    return True, ""


def _require_auth(authorization: Optional[str] = Header(default=None)) -> None:
    ok, reason = _check_auth(authorization)
    if not ok:
        raise HTTPException(status_code=401, detail=f"unauthorized: {reason}")


def _run_query_engine(query: str, save_report: bool, export_formats: Optional[List[str]], context: Dict[str, Any]) -> Dict[str, Any]:
    request_id = str(context.get("request_id") or uuid.uuid4())
    data = _local_query_engine(query, save_report, export_formats)
    summary = data.get("summary") or data.get("report") or ""

    return {
        "summary": summary if isinstance(summary, str) else str(summary),
        "sources": data.get("sources") if isinstance(data.get("sources"), list) else _extract_sources_from_text(str(summary)),
        "raw_result": data,
        "stats": {"engine": "QueryEngine", "timestamp": _iso_now()},
        "manifest": _build_manifest("QueryEngine", request_id, context),
        "logs": data.get("logs") if isinstance(data.get("logs"), list) else ["QueryEngine completed"],
    }


def _run_media_engine(query: str, save_report: bool, context: Dict[str, Any]) -> Dict[str, Any]:
    request_id = str(context.get("request_id") or uuid.uuid4())
    data = _local_media_engine(query, save_report)
    summary = data.get("summary") or data.get("report") or ""

    return {
        "summary": summary if isinstance(summary, str) else str(summary),
        "platform_distribution": data.get("platform_distribution") if isinstance(data.get("platform_distribution"), dict) else {},
        "media_highlights": data.get("media_highlights") if isinstance(data.get("media_highlights"), list) else [],
        "sources": data.get("sources") if isinstance(data.get("sources"), list) else _extract_sources_from_text(str(summary)),
        "raw_result": data,
        "stats": {"engine": "MediaEngine", "timestamp": _iso_now()},
        "manifest": _build_manifest("MediaEngine", request_id, context),
        "logs": data.get("logs") if isinstance(data.get("logs"), list) else ["MediaEngine completed"],
    }


def _run_insight_engine(query: str, save_report: bool, context: Dict[str, Any]) -> Dict[str, Any]:
    request_id = str(context.get("request_id") or uuid.uuid4())
    data = _local_insight_engine(query, save_report)
    summary = data.get("summary") or data.get("report") or ""

    return {
        "summary": summary if isinstance(summary, str) else str(summary),
        "sentiment_summary": data.get("sentiment_summary") if isinstance(data.get("sentiment_summary"), dict) else {},
        "keyword_clusters": data.get("keyword_clusters") if isinstance(data.get("keyword_clusters"), list) else [],
        "topic_clusters": data.get("topic_clusters") if isinstance(data.get("topic_clusters"), list) else [],
        "risk_signals": data.get("risk_signals") if isinstance(data.get("risk_signals"), list) else [],
        "sources": data.get("sources") if isinstance(data.get("sources"), list) else _extract_sources_from_text(str(summary)),
        "raw_result": data,
        "stats": {"engine": "InsightEngine", "timestamp": _iso_now()},
        "manifest": _build_manifest("InsightEngine", request_id, context),
        "logs": data.get("logs") if isinstance(data.get("logs"), list) else ["InsightEngine completed"],
    }


def _normalize_reports_input(reports: Optional[Union[List[Any], Dict[str, Any]]]) -> List[Any]:
    if reports is None:
        return []

    if isinstance(reports, list):
        return reports[:3]

    if isinstance(reports, dict):
        # Accept multiple key naming conventions for easier integration.
        candidates = [
            reports.get("query_engine") or reports.get("query") or reports.get("query_result"),
            reports.get("media_engine") or reports.get("media") or reports.get("media_result"),
            reports.get("insight_engine") or reports.get("insight") or reports.get("insight_result"),
        ]
        normalized: List[Any] = []
        for item in candidates:
            if isinstance(item, dict) and "summary" in item:
                normalized.append(item.get("summary"))
            elif item is not None:
                normalized.append(item)
            else:
                normalized.append("")
        return normalized

    return []


def _build_report_inputs(merged_result: Dict[str, Any], explicit_reports: Optional[Union[List[Any], Dict[str, Any]]]) -> Tuple[List[Any], str]:
    reports: List[Any] = []

    provided = _normalize_reports_input(explicit_reports)
    if provided:
        reports = provided

    if not reports and isinstance(merged_result, dict):
        # Prefer raw engine summaries when provided.
        for key in ("query_result", "media_result", "insight_result"):
            value = merged_result.get(key)
            if isinstance(value, dict) and value.get("summary"):
                reports.append(value.get("summary"))

        if not reports:
            # Fallback to merged summary-like data.
            core = merged_result.get("core_conclusions", [])
            risks = merged_result.get("risk_points", [])
            opps = merged_result.get("opportunities", [])
            reports.extend([str(core), str(risks), str(opps)])

    forum_logs = ""
    if isinstance(merged_result, dict):
        forum_rounds = merged_result.get("forum_rounds")
        if isinstance(forum_rounds, list) and forum_rounds:
            forum_logs = "\n\n".join([str(x) for x in forum_rounds])

    return reports, forum_logs


def _safe_path(path: str) -> str:
    if not path:
        return ""
    return str(Path(path))


def _run_report_engine(body: ReportRequest) -> Dict[str, Any]:
    context = body.context or {}
    request_id = str(context.get("request_id") or uuid.uuid4())
    reports, merged_forum_logs = _build_report_inputs(body.merged_result, body.reports)
    forum_logs = body.forum_logs or merged_forum_logs
    local_result = _local_report_engine(body, reports, forum_logs)
    data = local_result if isinstance(local_result, dict) else {"summary_text": str(local_result)}

    return {
        "summary_text": data.get("summary_text") or data.get("summary") or data.get("html_content", ""),
        "html_path": _safe_path(data.get("html_path", "")),
        "pdf_path": _safe_path(data.get("pdf_path", "")),
        "docx_path": _safe_path(data.get("docx_path", "")),
        "md_path": _safe_path(data.get("md_path", "")),
        "chart_paths": data.get("chart_paths") if isinstance(data.get("chart_paths"), list) else [],
        "manifest": _build_manifest("ReportEngine", request_id, context),
        "logs": data.get("logs") if isinstance(data.get("logs"), list) else ["ReportEngine completed"],
        "raw_result": data,
    }


@app.get("/healthz")
def healthz():
    return {
        "ok": True,
        "service": "engine-gateway",
        "version": app.version,
        "timestamp": _iso_now(),
    }


@app.get("/v1/capabilities")
def capabilities():
    return {
        "service": "engine-gateway",
        "engines": ["query", "media", "insight", "report"],
        "endpoints": {
            "research_dispatch": "/v1/research",
            "research_query": "/v1/research/query",
            "research_media": "/v1/research/media",
            "research_insight": "/v1/research/insight",
            "report": "/v1/report",
            "health": "/healthz",
            "docs": "/docs",
            "redoc": "/redoc",
        },
        "auth": {
            "mode": "optional bearer",
            "env_var": "ENGINE_API_TOKEN",
        },
        "execution": {
            "mode": "embedded-local-only",
            "agent_lifecycle": "new instance per request",
        },
    }


@app.on_event("startup")
def startup_initialize_runtime():
    """Initialize embedded engine runtime at service startup."""
    try:
        ENGINE_RUNTIME.initialize()
        logger.info("Embedded engine runtime initialized")
    except Exception as exc:
        logger.exception(f"Failed to initialize embedded engine runtime: {exc}")
        raise RuntimeError(f"Engine runtime initialization failed: {exc}") from exc


@app.post("/v1/research")
def research_dispatch(body: ResearchRequest, _auth: None = Depends(_require_auth)):
    engine = str(body.engine or "").strip().lower()
    query = body.query.strip()
    context = body.context or {}

    if not engine:
        raise HTTPException(status_code=400, detail="missing field: engine")
    if not query:
        raise HTTPException(status_code=400, detail="missing field: query")

    return _run_research_impl(engine, query, body.save_report, body.export_formats, context)


@app.post("/v1/research/{engine}")
def research_engine(engine: str, body: ResearchRequest, _auth: None = Depends(_require_auth)):
    query = body.query.strip()
    context = body.context or {}
    if not query:
        raise HTTPException(status_code=400, detail="missing field: query")

    return _run_research_impl(engine, query, body.save_report, body.export_formats, context)


def _run_research_impl(
    engine: str,
    query: str,
    save_report: bool,
    export_formats: Optional[List[str]],
    context: Dict[str, Any],
):
    engine_name = str(engine).strip().lower()

    try:
        if engine_name == "query":
            return _run_query_engine(query, save_report, export_formats, context)
        if engine_name == "media":
            return _run_media_engine(query, save_report, context)
        if engine_name == "insight":
            return _run_insight_engine(query, save_report, context)
        raise HTTPException(status_code=400, detail="unsupported engine, use query|media|insight")
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(f"engine '{engine_name}' failed: {exc}")
        raise HTTPException(status_code=500, detail=f"engine '{engine_name}' failed: {exc}")


@app.post("/v1/report")
def report_engine(body: ReportRequest, _auth: None = Depends(_require_auth)):
    query = body.query.strip()

    if not query:
        raise HTTPException(status_code=400, detail="missing field: query")
    if not isinstance(body.merged_result, dict):
        body.merged_result = {}

    try:
        return _run_report_engine(body)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(f"report engine failed: {exc}")
        raise HTTPException(status_code=500, detail=f"report engine failed: {exc}")


if __name__ == "__main__":
    host = os.getenv("ENGINE_GATEWAY_HOST", "0.0.0.0")
    port = int(os.getenv("ENGINE_GATEWAY_PORT", "19000"))
    debug = os.getenv("ENGINE_GATEWAY_DEBUG", "0") == "1"

    logger.info(f"Starting engine gateway on {host}:{port}")
    uvicorn.run("engine_gateway_api:app", host=host, port=port, reload=debug)
