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

import asyncio
import os
import re
import inspect
import logging
import ctypes
import uuid
import copy
import json
import time
import threading
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union, Set
from queue import Queue, Empty

import uvicorn
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import inspect


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
    discussion_intensity: str = Field(default="normal", description="low|normal|high")
    max_reflections: Optional[int] = Field(default=None, description="Override engine reflection rounds")
    max_paragraphs: Optional[int] = Field(default=None, description="Override max report paragraphs")
    max_paragraph_workers: Optional[int] = Field(default=None, description="Override paragraph concurrency workers")
    max_search_results: Optional[int] = Field(default=None, description="Override max search results")
    search_timeout: Optional[int] = Field(default=None, description="Override search timeout in seconds")
    enable_local_db_search: Optional[bool] = Field(default=None, description="Enable local DB search for this request")
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
    max_chapter_workers: Optional[int] = Field(default=None, description="Override report chapter concurrency workers")
    chapter_json_max_attempts: Optional[int] = Field(default=None, description="Override per-chapter JSON retry attempts")
    content_sparse_min_attempts: Optional[int] = Field(default=None, description="Override per-chapter sparse-content retry attempts")
    enable_json_response_format: Optional[bool] = Field(default=None, description="Request JSON object response_format from compatible LLM APIs")
    enable_cross_engine_json_rescue: Optional[bool] = Field(default=None, description="Enable cross-engine LLM rescue for malformed chapter JSON")
    enable_llm_structural_repair: Optional[bool] = Field(default=None, description="Enable LLM repair when local chapter normalization fails validation")
    chapter_repair_timeout: Optional[float] = Field(default=None, description="Timeout seconds for chapter JSON repair LLM calls")
    gateway_max_attempts: Optional[int] = Field(default=None, description="Override whole report gateway retry attempts")


class ForumRequest(BaseModel):
    forum_logs: Union[str, List[str]] = Field(..., description="Forum logs as text or line list")
    max_lines: Optional[int] = Field(default=60, description="Max forum log lines to include")
    max_chars: Optional[int] = Field(default=16000, description="Max total chars for forum logs")
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
        self.forum_host_class = None
        self.forum_host_params: Dict[str, Any] = {}

    def initialize(self) -> None:
        project_root = Path(__file__).resolve().parent
        required_files = [
            project_root / "QueryEngine" / "agent.py",
            project_root / "QueryEngine" / "utils" / "config.py",
            project_root / "MediaEngine" / "agent.py",
            project_root / "InsightEngine" / "agent.py",
            project_root / "ReportEngine" / "agent.py",
            project_root / "ForumEngine" / "llm_host.py",
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
        from ForumEngine.llm_host import ForumHost
        from config import settings as root_settings

        self.query_agent_class = QueryAgent
        self.query_settings = query_settings
        self.media_agent_class = MediaAgent
        self.media_settings = media_settings
        self.insight_agent_class = InsightAgent
        self.insight_settings = insight_settings
        self.report_agent_class = ReportAgent
        self.report_settings = report_settings
        self.forum_host_class = ForumHost
        self.forum_host_params = {
            "api_key": root_settings.FORUM_HOST_API_KEY,
            "base_url": root_settings.FORUM_HOST_BASE_URL,
            "model_name": root_settings.FORUM_HOST_MODEL_NAME,
        }
        self.ready = True

    def ensure_ready(self) -> None:
        if not self.ready:
            raise RuntimeError("Engine runtime is not initialized")

    def _clone_settings(self, settings_obj: Any) -> Any:
        if hasattr(settings_obj, "model_copy"):
            return settings_obj.model_copy(deep=True)
        return copy.deepcopy(settings_obj)

    def _apply_overrides(self, cfg: Any, overrides: Dict[str, Any]) -> None:
        for key, value in overrides.items():
            if value is None:
                continue
            if hasattr(cfg, key):
                setattr(cfg, key, value)

    def create_query_agent(self, overrides: Optional[Dict[str, Any]] = None):
        self.ensure_ready()
        cfg = self._clone_settings(self.query_settings)
        self._apply_overrides(cfg, overrides or {})
        return self.query_agent_class(config=cfg)

    def create_media_agent(self, overrides: Optional[Dict[str, Any]] = None):
        self.ensure_ready()
        cfg = self._clone_settings(self.media_settings)
        self._apply_overrides(cfg, overrides or {})
        return self.media_agent_class(config=cfg)

    def create_insight_agent(self, overrides: Optional[Dict[str, Any]] = None):
        self.ensure_ready()
        cfg = self._clone_settings(self.insight_settings)
        self._apply_overrides(cfg, overrides or {})
        return self.insight_agent_class(config=cfg)

    def create_report_agent(self, overrides: Optional[Dict[str, Any]] = None):
        self.ensure_ready()
        cfg = self._clone_settings(self.report_settings)
        self._apply_overrides(cfg, overrides or {})
        return self.report_agent_class(config=cfg)

    def create_forum_host(self):
        self.ensure_ready()
        return self.forum_host_class(**self.forum_host_params)


ENGINE_RUNTIME = EngineRuntime()


def _project_root() -> Path:
    return Path(__file__).resolve().parent


def _report_download_roots() -> List[Path]:
    root = _project_root()
    return [
        (root / "outputs").resolve(),
        (root / "final_reports").resolve(),
        (root / "logs").resolve(),
    ]


INSIGHT_REQUIRED_TABLES = [
    "bilibili_video",
    "bilibili_video_comment",
    "douyin_aweme",
    "douyin_aweme_comment",
    "kuaishou_video",
    "kuaishou_video_comment",
    "weibo_note",
    "weibo_note_comment",
    "xhs_note",
    "xhs_note_comment",
    "zhihu_content",
    "zhihu_comment",
    "tieba_note",
    "tieba_comment",
    "daily_news",
]


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _ensure_request_id(context: Optional[Dict[str, Any]] = None) -> str:
    ctx = context if isinstance(context, dict) else {}
    request_id = str(ctx.get("request_id") or "").strip()
    if not request_id:
        request_id = str(uuid.uuid4())
        ctx["request_id"] = request_id
    return request_id


async def _get_insight_missing_tables(required_tables: List[str]) -> List[str]:
    from InsightEngine.utils.db import get_async_engine

    engine = get_async_engine()
    async with engine.connect() as conn:
        existing_tables = await conn.run_sync(lambda sync_conn: inspect(sync_conn).get_table_names())
    existing_set = {str(t).lower() for t in existing_tables}
    return [table for table in required_tables if table.lower() not in existing_set]


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


def _sse_event(event: str, data: Dict[str, Any]) -> str:
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n"


def _force_stop_thread(thread: threading.Thread) -> bool:
    """Best-effort thread cancellation for long-running sync engine code after client disconnect."""
    if not thread.is_alive() or thread.ident is None:
        return False
    try:
        result = ctypes.pythonapi.PyThreadState_SetAsyncExc(
            ctypes.c_long(thread.ident), ctypes.py_object(SystemExit)
        )
        if result == 1:
            return True
        if result > 1:
            ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(thread.ident), None)
    except Exception:
        return False
    return False


class _StreamThreadTracker:
    """Track threads spawned by a stream worker so child worker logs stay attached to the SSE request."""

    _lock = threading.RLock()
    _patched = False
    _original_start = None
    _roots: Dict[int, Set[int]] = {}

    @classmethod
    def start_root(cls, root_thread_id: int) -> None:
        cls._install()
        with cls._lock:
            cls._roots[int(root_thread_id)] = {int(root_thread_id)}

    @classmethod
    def finish_root(cls, root_thread_id: int) -> None:
        with cls._lock:
            cls._roots.pop(int(root_thread_id), None)

    @classmethod
    def is_related(cls, root_thread_id: int, thread_id: int) -> bool:
        with cls._lock:
            return int(thread_id) in cls._roots.get(int(root_thread_id), set())

    @classmethod
    def _root_ids_for_parent(cls, parent_thread_id: int) -> List[int]:
        with cls._lock:
            parent_thread_id = int(parent_thread_id)
            return [
                root_id
                for root_id, thread_ids in cls._roots.items()
                if parent_thread_id in thread_ids
            ]

    @classmethod
    def _register_child_for_roots(cls, root_ids: List[int], child_thread_id: int) -> None:
        if not root_ids:
            return
        with cls._lock:
            child_thread_id = int(child_thread_id)
            for root_id in root_ids:
                thread_ids = cls._roots.get(int(root_id))
                if thread_ids is not None:
                    thread_ids.add(child_thread_id)

    @classmethod
    def _unregister_child_for_roots(cls, root_ids: List[int], child_thread_id: int) -> None:
        if not root_ids:
            return
        with cls._lock:
            child_thread_id = int(child_thread_id)
            for root_id in root_ids:
                thread_ids = cls._roots.get(int(root_id))
                if thread_ids is not None and child_thread_id != int(root_id):
                    thread_ids.discard(child_thread_id)

    @classmethod
    def _install(cls) -> None:
        with cls._lock:
            if cls._patched:
                return
            original_start = threading.Thread.start
            cls._original_start = original_start

            def tracked_start(thread_self, *args, **kwargs):
                parent_thread_id = threading.get_ident()
                root_ids = cls._root_ids_for_parent(parent_thread_id)
                if root_ids and not getattr(thread_self, "_engine_gateway_thread_tracked", False):
                    original_run = thread_self.run

                    def tracked_run(*run_args, **run_kwargs):
                        child_thread_id = threading.get_ident()
                        cls._register_child_for_roots(root_ids, child_thread_id)
                        try:
                            return original_run(*run_args, **run_kwargs)
                        finally:
                            cls._unregister_child_for_roots(root_ids, child_thread_id)

                    thread_self.run = tracked_run
                    thread_self._engine_gateway_thread_tracked = True
                return original_start(thread_self, *args, **kwargs)

            threading.Thread.start = tracked_start
            cls._patched = True


class _QueueLogHandler(logging.Handler):
    """Forward Python logging records to the stream queue as log events."""

    def __init__(self, queue: Queue, target_thread_id: int, request_id: str):
        super().__init__()
        self.queue = queue
        self.target_thread_id = target_thread_id
        self.request_id = request_id

    @staticmethod
    def _is_stream_related_thread(thread_id: int, target_thread_id: int, thread_name: str = "") -> bool:
        """Include the stream worker thread, its descendants, and known paragraph pool thread names."""
        if int(thread_id) == int(target_thread_id):
            return True
        if _StreamThreadTracker.is_related(int(target_thread_id), int(thread_id)):
            return True
        normalized_name = str(thread_name or "").lower()
        return normalized_name.startswith(f"paragraph-worker-{int(target_thread_id)}")

    def emit(self, record: logging.LogRecord) -> None:
        record_thread_id = int(getattr(record, "thread", -1) or -1)
        record_thread_name = str(getattr(record, "threadName", "") or "")
        if not self._is_stream_related_thread(record_thread_id, self.target_thread_id, record_thread_name):
            return
        try:
            self.queue.put(
                (
                    "log",
                    {
                        "timestamp": _iso_now(),
                        "source": "logging",
                        "logger": record.name,
                        "level": record.levelname,
                        "message": record.getMessage(),
                        "request_id": self.request_id,
                    },
                )
            )
        except Exception:
            pass


class _QueueStreamWriter:
    """Capture print/stdout/stderr and forward complete lines to the stream queue."""

    def __init__(self, queue: Queue, source: str):
        self.queue = queue
        self.source = source
        self._buffer = ""

    def write(self, text: str) -> int:
        if not text:
            return 0
        self._buffer += text
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            line = line.rstrip("\r")
            if line.strip():
                self.queue.put(
                    (
                        "log",
                        {
                            "timestamp": _iso_now(),
                            "source": self.source,
                            "level": "INFO",
                            "message": line,
                        },
                    )
                )
        return len(text)

    def flush(self) -> None:
        line = self._buffer.strip()
        if line:
            self.queue.put(
                (
                    "log",
                    {
                        "timestamp": _iso_now(),
                        "source": self.source,
                        "level": "INFO",
                        "message": line,
                    },
                )
            )
        self._buffer = ""


def _stream_with_heartbeat(run_fn, stream_meta: Dict[str, Any], request: Optional[Request] = None) -> StreamingResponse:
    queue: Queue = Queue()
    heartbeat_interval = 10.0
    disconnect_poll_interval = float(os.getenv("ENGINE_STREAM_DISCONNECT_POLL_INTERVAL", "5.0"))
    if disconnect_poll_interval < 0.2:
        disconnect_poll_interval = 0.2
    request_id = str(stream_meta.get("request_id") or uuid.uuid4())

    def worker() -> None:
        worker_thread_id = threading.get_ident()
        _StreamThreadTracker.start_root(worker_thread_id)
        root_logger = logging.getLogger()
        queue_handler = _QueueLogHandler(queue, target_thread_id=worker_thread_id, request_id=request_id)
        loguru_logger = None
        loguru_sink_id = None

        def _emit_loguru(message) -> None:
            try:
                record = message.record
                record_thread = record.get("thread")
                record_thread_id = getattr(record_thread, "id", None)
                record_thread_name = getattr(record_thread, "name", "")
                if not _QueueLogHandler._is_stream_related_thread(
                    int(record_thread_id or -1),
                    worker_thread_id,
                    str(record_thread_name or ""),
                ):
                    return
                queue.put(
                    (
                        "log",
                        {
                            "timestamp": _iso_now(),
                            "source": "loguru",
                            "logger": record.get("name", ""),
                            "level": getattr(record.get("level"), "name", "INFO"),
                            "message": record.get("message", ""),
                            "request_id": request_id,
                        },
                    )
                )
            except Exception:
                pass

        root_logger.addHandler(queue_handler)

        def _stream_handler(event_type: str, payload: Dict[str, Any]) -> None:
            """Forward engine stage/progress events to SSE queue."""
            try:
                event_name = str(event_type or "log")
                queue.put(
                    (
                        "event",
                        {
                            "event": event_name,
                            "payload": payload if isinstance(payload, dict) else {"message": str(payload)},
                        },
                    )
                )
            except Exception:
                pass

        try:
            # Query/Media/Insight engines mainly log via loguru. Attach a temporary sink per request.
            from loguru import logger as _loguru_logger  # type: ignore

            loguru_logger = _loguru_logger
            loguru_sink_id = loguru_logger.add(
                _emit_loguru,
                level="DEBUG",
                enqueue=False,
                filter=lambda r: _QueueLogHandler._is_stream_related_thread(
                    int(getattr(r.get("thread"), "id", -1) or -1),
                    worker_thread_id,
                    str(getattr(r.get("thread"), "name", "") or ""),
                ),
            )
        except Exception:
            loguru_logger = None
            loguru_sink_id = None

        try:
            queue.put(
                (
                    "log",
                    {
                        "timestamp": _iso_now(),
                        "source": "gateway",
                        "level": "INFO",
                        "message": "stream worker started",
                        "meta": stream_meta,
                        "request_id": request_id,
                    },
                )
            )
            # Do not globally redirect stdout/stderr here. It is process-global and causes
            # cross-request log mixing under concurrent stream requests.
            supports_stream_handler = False
            try:
                supports_stream_handler = "stream_handler" in inspect.signature(run_fn).parameters
            except Exception:
                supports_stream_handler = False

            if supports_stream_handler:
                result = run_fn(stream_handler=_stream_handler)
            else:
                result = run_fn()
            queue.put(
                (
                    "log",
                    {
                        "timestamp": _iso_now(),
                        "source": "gateway",
                        "level": "INFO",
                        "message": "engine execution completed",
                        "request_id": request_id,
                    },
                )
            )
            queue.put(("result", result))
        except HTTPException as exc:
            queue.put(
                (
                    "log",
                    {
                        "timestamp": _iso_now(),
                        "source": "gateway",
                        "level": "ERROR",
                        "message": f"HTTPException: {exc.detail}",
                        "request_id": request_id,
                    },
                )
            )
            queue.put(("error", {"status_code": exc.status_code, "detail": exc.detail}))
        except SystemExit:
            queue.put(
                (
                    "log",
                    {
                        "timestamp": _iso_now(),
                        "source": "gateway",
                        "level": "WARNING",
                        "message": "engine execution cancelled after client disconnect",
                        "request_id": request_id,
                    },
                )
            )
        except Exception as exc:
            queue.put(
                (
                    "log",
                    {
                        "timestamp": _iso_now(),
                        "source": "gateway",
                        "level": "ERROR",
                        "message": f"Unhandled exception: {exc}",
                        "request_id": request_id,
                    },
                )
            )
            queue.put(("error", {"status_code": 500, "detail": str(exc)}))
        finally:
            _StreamThreadTracker.finish_root(worker_thread_id)
            root_logger.removeHandler(queue_handler)
            if loguru_logger is not None and loguru_sink_id is not None:
                try:
                    loguru_logger.remove(loguru_sink_id)
                except Exception:
                    pass

    worker_thread = threading.Thread(target=worker, daemon=True)
    worker_thread.start()

    async def event_generator():
        started_at = time.time()
        last_heartbeat_at = started_at
        yield _sse_event("started", {"timestamp": _iso_now(), **stream_meta})
        while True:
            if request is not None and await request.is_disconnected():
                cancelled = _force_stop_thread(worker_thread)
                logger.warning(
                    "client disconnected for stream request, cancellation attempted=%s meta=%s",
                    cancelled,
                    stream_meta,
                )
                break

            try:
                item_type, payload = queue.get(timeout=disconnect_poll_interval)
            except Empty:
                now = time.time()
                if now - last_heartbeat_at >= heartbeat_interval:
                    yield _sse_event("heartbeat", {"elapsed_seconds": round(now - started_at, 1)})
                    yield _sse_event(
                        "log",
                        {
                            "timestamp": _iso_now(),
                            "source": "gateway",
                            "level": "DEBUG",
                            "message": "engine still running",
                            "elapsed_seconds": round(now - started_at, 1),
                            "request_id": request_id,
                        },
                    )
                    last_heartbeat_at = now
                continue

            if item_type == "log":
                yield _sse_event("log", payload if isinstance(payload, dict) else {"message": str(payload)})
                continue

            if item_type == "event":
                event_name = "log"
                event_payload: Dict[str, Any] = {"message": ""}
                if isinstance(payload, dict):
                    event_name = str(payload.get("event") or "log")
                    raw_payload = payload.get("payload")
                    if isinstance(raw_payload, dict):
                        event_payload = raw_payload
                    elif raw_payload is not None:
                        event_payload = {"message": str(raw_payload)}
                else:
                    event_payload = {"message": str(payload)}
                yield _sse_event(event_name, event_payload)
                continue

            if item_type == "result":
                result_payload = payload if isinstance(payload, dict) else {"result": payload}
                if isinstance(result_payload, dict):
                    raw_result = result_payload.get("raw_result")
                    if isinstance(raw_result, dict) and ("summary" in raw_result) and ("summary" in result_payload):
                        result_payload = dict(result_payload)
                        result_payload.pop("summary", None)
                done_payload = {
                    "ok": True,
                    "elapsed_seconds": round(time.time() - started_at, 1),
                    "result": result_payload,
                }
                yield _sse_event(
                    "done",
                    done_payload,
                )
                break

            yield _sse_event("error", payload if isinstance(payload, dict) else {"detail": str(payload)})
            yield _sse_event(
                "done",
                {
                    "ok": False,
                    "elapsed_seconds": round(time.time() - started_at, 1),
                    "error": payload if isinstance(payload, dict) else {"detail": str(payload)},
                },
            )
            break

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _clamp_optional_int(value: Optional[int], minimum: int, maximum: int) -> Optional[int]:
    if value is None:
        return None
    return max(minimum, min(maximum, int(value)))


def _build_runtime_overrides(body: ResearchRequest) -> Dict[str, Any]:
    search_results_cap = _clamp_optional_int(body.max_search_results, 1, 100)
    overrides: Dict[str, Any] = {
        "MAX_REFLECTIONS": _clamp_optional_int(body.max_reflections, 0, 8),
        "MAX_PARAGRAPHS": _clamp_optional_int(body.max_paragraphs, 1, 12),
        "MAX_PARAGRAPH_WORKERS": _clamp_optional_int(body.max_paragraph_workers, 1, 12),
        "MAX_SEARCH_RESULTS": search_results_cap,
        "MAX_SEARCH_RESULTS_FOR_LLM": search_results_cap,
        "DEFAULT_SEARCH_TOPIC_GLOBALLY_LIMIT_PER_TABLE": search_results_cap,
        "DEFAULT_SEARCH_TOPIC_BY_DATE_LIMIT_PER_TABLE": search_results_cap,
        "DEFAULT_GET_COMMENTS_FOR_TOPIC_LIMIT": _clamp_optional_int(body.max_search_results, 1, 500),
        "DEFAULT_SEARCH_TOPIC_ON_PLATFORM_LIMIT": _clamp_optional_int(body.max_search_results, 1, 500),
        "SEARCH_TIMEOUT": _clamp_optional_int(body.search_timeout, 10, 600),
    }

    if body.enable_local_db_search is not None:
        overrides["ENABLE_LOCAL_DB_SEARCH"] = bool(body.enable_local_db_search)

    intensity = (body.discussion_intensity or "normal").strip().lower()
    presets: Dict[str, Dict[str, int]] = {
        "low": {
            "MAX_REFLECTIONS": 1,
            "MAX_PARAGRAPHS": 3,
            "MAX_SEARCH_RESULTS": 8,
            "SEARCH_TIMEOUT": 90,
        },
        "high": {
            "MAX_REFLECTIONS": 4,
            "MAX_PARAGRAPHS": 8,
            "MAX_SEARCH_RESULTS": 30,
            "SEARCH_TIMEOUT": 300,
        },
    }

    if intensity in presets:
        for k, v in presets[intensity].items():
            if overrides.get(k) is None:
                overrides[k] = v

    return {k: v for k, v in overrides.items() if v is not None}


def _build_report_runtime_overrides(body: ReportRequest) -> Dict[str, Any]:
    overrides: Dict[str, Any] = {
        "CHAPTER_MAX_WORKERS": _clamp_optional_int(body.max_chapter_workers, 1, 16),
        "CHAPTER_JSON_MAX_ATTEMPTS": _clamp_optional_int(body.chapter_json_max_attempts, 1, 5),
        "CONTENT_SPARSE_MIN_ATTEMPTS": _clamp_optional_int(body.content_sparse_min_attempts, 1, 5),
    }
    if body.enable_json_response_format is not None:
        overrides["ENABLE_JSON_RESPONSE_FORMAT"] = bool(body.enable_json_response_format)
    if body.enable_cross_engine_json_rescue is not None:
        overrides["ENABLE_CROSS_ENGINE_JSON_RESCUE"] = bool(body.enable_cross_engine_json_rescue)
    if body.enable_llm_structural_repair is not None:
        overrides["ENABLE_LLM_STRUCTURAL_REPAIR"] = bool(body.enable_llm_structural_repair)
    if body.chapter_repair_timeout is not None:
        overrides["CHAPTER_REPAIR_TIMEOUT"] = max(10.0, min(300.0, float(body.chapter_repair_timeout)))
    return {k: v for k, v in overrides.items() if v is not None}


def _local_query_engine(query: str, save_report: bool, export_formats: Optional[List[str]], overrides: Dict[str, int]) -> Dict[str, Any]:
    agent = ENGINE_RUNTIME.create_query_agent(overrides=overrides)
    report = agent.research(query=query, save_report=save_report, export_formats=export_formats)
    summary = report if isinstance(report, str) else str(report)
    return {
        "summary": summary,
        "sources": _extract_sources_from_text(summary),
        "raw_result": {"report": report},
        "logs": ["QueryEngine completed"],
    }


def _local_media_engine(query: str, save_report: bool, overrides: Dict[str, int]) -> Dict[str, Any]:
    agent = ENGINE_RUNTIME.create_media_agent(overrides=overrides)
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


def _local_insight_engine(query: str, save_report: bool, overrides: Dict[str, int]) -> Dict[str, Any]:
    agent = ENGINE_RUNTIME.create_insight_agent(overrides=overrides)
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


def _local_report_engine(
    body: ReportRequest,
    reports: List[Any],
    forum_logs: str,
    stream_handler=None,
) -> Dict[str, Any]:
    agent = ENGINE_RUNTIME.create_report_agent(overrides=_build_report_runtime_overrides(body))
    return agent.generate_report(
        query=body.query,
        reports=reports,
        forum_logs=forum_logs,
        custom_template=body.custom_template,
        save_report=body.save_report,
        stream_handler=stream_handler,
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


def _run_query_engine(query: str, save_report: bool, export_formats: Optional[List[str]], context: Dict[str, Any], overrides: Dict[str, int]) -> Dict[str, Any]:
    request_id = str(context.get("request_id") or uuid.uuid4())
    data = _local_query_engine(query, save_report, export_formats, overrides)
    summary = data.get("summary") or data.get("report") or ""

    return {
        "summary": summary if isinstance(summary, str) else str(summary),
        "sources": data.get("sources") if isinstance(data.get("sources"), list) else _extract_sources_from_text(str(summary)),
        "raw_result": data.get("raw_result") if isinstance(data.get("raw_result"), dict) else data,
        "stats": {"engine": "QueryEngine", "timestamp": _iso_now()},
        "manifest": _build_manifest("QueryEngine", request_id, context),
        "logs": data.get("logs") if isinstance(data.get("logs"), list) else ["QueryEngine completed"],
    }


def _run_media_engine(query: str, save_report: bool, context: Dict[str, Any], overrides: Dict[str, int]) -> Dict[str, Any]:
    request_id = str(context.get("request_id") or uuid.uuid4())
    data = _local_media_engine(query, save_report, overrides)
    summary = data.get("summary") or data.get("report") or ""

    return {
        "summary": summary if isinstance(summary, str) else str(summary),
        "platform_distribution": data.get("platform_distribution") if isinstance(data.get("platform_distribution"), dict) else {},
        "media_highlights": data.get("media_highlights") if isinstance(data.get("media_highlights"), list) else [],
        "sources": data.get("sources") if isinstance(data.get("sources"), list) else _extract_sources_from_text(str(summary)),
        "raw_result": data.get("raw_result") if isinstance(data.get("raw_result"), dict) else data,
        "stats": {"engine": "MediaEngine", "timestamp": _iso_now()},
        "manifest": _build_manifest("MediaEngine", request_id, context),
        "logs": data.get("logs") if isinstance(data.get("logs"), list) else ["MediaEngine completed"],
    }


def _run_insight_engine(query: str, save_report: bool, context: Dict[str, Any], overrides: Dict[str, int]) -> Dict[str, Any]:
    request_id = str(context.get("request_id") or uuid.uuid4())
    data = _local_insight_engine(query, save_report, overrides)
    summary = data.get("summary") or data.get("report") or ""

    return {
        "summary": summary if isinstance(summary, str) else str(summary),
        "sentiment_summary": data.get("sentiment_summary") if isinstance(data.get("sentiment_summary"), dict) else {},
        "keyword_clusters": data.get("keyword_clusters") if isinstance(data.get("keyword_clusters"), list) else [],
        "topic_clusters": data.get("topic_clusters") if isinstance(data.get("topic_clusters"), list) else [],
        "risk_signals": data.get("risk_signals") if isinstance(data.get("risk_signals"), list) else [],
        "sources": data.get("sources") if isinstance(data.get("sources"), list) else _extract_sources_from_text(str(summary)),
        "raw_result": data.get("raw_result") if isinstance(data.get("raw_result"), dict) else data,
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


def _report_item_text(value: Any) -> str:
    """Normalize a report item to text for emptiness checks and diagnostics."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    try:
        return str(value).strip()
    except Exception:
        return ""


def _validate_report_inputs_or_raise(
    reports: List[Any],
    body: "ReportRequest",
) -> None:
    """Fail fast when report inputs are empty, with actionable diagnostics in logs."""
    normalized = ["", "", ""]
    for idx in range(3):
        if idx < len(reports):
            normalized[idx] = _report_item_text(reports[idx])

    engine_keys = ["query_engine", "media_engine", "insight_engine"]
    missing_engines: List[str] = []
    for idx, key in enumerate(engine_keys):
        text = normalized[idx]
        if text in ("", "[]", "{}", "None", "null"):
            missing_engines.append(key)

    if not missing_engines:
        return

    explicit_type = type(body.reports).__name__ if body.reports is not None else "None"
    explicit_keys: List[str] = []
    if isinstance(body.reports, dict):
        explicit_keys = sorted([str(k) for k in body.reports.keys()])
    merged_keys = sorted([str(k) for k in (body.merged_result or {}).keys()])
    logger.error(
        "Report input validation failed: missing engines={}, explicit_reports_type={}, explicit_report_keys={}, merged_result_keys={}, report_lengths={}",
        missing_engines,
        explicit_type,
        explicit_keys,
        merged_keys,
        [len(x) for x in normalized],
    )

    raise HTTPException(
        status_code=400,
        detail={
            "message": "report inputs are empty for one or more engines",
            "missing_engines": missing_engines,
            "required_order": ["query_engine", "media_engine", "insight_engine"],
            "hint": "Provide non-empty reports (list or dict) or ensure merged_result includes usable engine summaries.",
        },
    )


def _dump_report_request_for_log(body: "ReportRequest") -> str:
    """Serialize report request body for diagnostics."""
    try:
        if hasattr(body, "model_dump"):
            payload = body.model_dump()
        else:
            payload = body.dict()  # type: ignore[attr-defined]
    except Exception:
        payload = {
            "query": getattr(body, "query", ""),
            "reports": getattr(body, "reports", None),
            "forum_logs": getattr(body, "forum_logs", ""),
            "custom_template": getattr(body, "custom_template", ""),
            "save_report": getattr(body, "save_report", True),
            "merged_result": getattr(body, "merged_result", {}),
            "context": getattr(body, "context", {}),
        }

    try:
        return json.dumps(payload, ensure_ascii=False, default=str)
    except Exception:
        return str(payload)


def _safe_path(path: str) -> str:
    if not path:
        return ""
    return str(Path(path))


def _is_non_retriable_report_error(exc: Exception) -> bool:
    """Treat most 4xx upstream HTTP errors as permanent and fail fast."""
    response = getattr(exc, "response", None)
    status_code = int(getattr(response, "status_code", 0) or 0)
    if 400 <= status_code < 500 and status_code != 429:
        return True
    message = str(exc or "").lower()
    if "404 client error" in message or "400 client error" in message or "401 client error" in message or "403 client error" in message:
        return True
    return False


def _resolve_download_file(path_text: str) -> Path:
    """Resolve user-provided file path under allowlisted report output directories."""
    if not path_text or not str(path_text).strip():
        raise HTTPException(status_code=400, detail="missing query param: path")

    candidate = Path(path_text.strip())
    if not candidate.is_absolute():
        candidate = (_project_root() / candidate).resolve()
    else:
        candidate = candidate.resolve()

    allowed = _report_download_roots()
    is_allowed = any(str(candidate).lower().startswith(str(base).lower() + os.sep) or candidate == base for base in allowed)
    if not is_allowed:
        raise HTTPException(status_code=403, detail="path is outside allowed report directories")

    if not candidate.exists() or not candidate.is_file():
        raise HTTPException(status_code=404, detail="file not found")

    return candidate


def _run_report_engine(body: ReportRequest, stream_handler=None) -> Dict[str, Any]:
    logger.info("Raw /v1/report request payload: {}", _dump_report_request_for_log(body))
    context = body.context or {}
    request_id = str(context.get("request_id") or uuid.uuid4())
    reports, merged_forum_logs = _build_report_inputs(body.merged_result, body.reports)
    _validate_report_inputs_or_raise(reports, body)
    forum_logs = body.forum_logs or merged_forum_logs

    def emit(event_type: str, payload: Dict[str, Any]) -> None:
        if stream_handler is None:
            return
        try:
            stream_handler(event_type, payload)
        except Exception:
            pass

    whole_run_attempts = body.gateway_max_attempts
    if whole_run_attempts is None:
        try:
            whole_run_attempts = int(os.getenv("REPORT_ENGINE_GATEWAY_MAX_ATTEMPTS", "1"))
        except ValueError:
            whole_run_attempts = 1
    whole_run_attempts = max(1, min(3, int(whole_run_attempts)))

    local_result = None
    for attempt in range(1, whole_run_attempts + 1):
        try:
            emit(
                "stage",
                {
                    "stage": "agent_running",
                    "attempt": attempt,
                    "message": f"正在调用ReportAgent生成报告（第{attempt}次尝试）",
                },
            )
            local_result = _local_report_engine(
                body,
                reports,
                forum_logs,
                stream_handler=stream_handler,
            )
            break
        except Exception as exc:
            is_chapter_json_parse = exc.__class__.__name__ == "ChapterJsonParseError"
            if is_chapter_json_parse:
                hint_message = "尝试将Report Engine的API更换为算力更强、上下文更长的LLM"
                emit(
                    "warning",
                    {
                        "stage": "agent_running",
                        "attempt": attempt,
                        "reason": "chapter_json_parse",
                        "error": str(exc),
                        "message": hint_message,
                    },
                )
                raise HTTPException(status_code=502, detail=hint_message) from exc

            if _is_non_retriable_report_error(exc):
                fast_fail_message = f"ReportAgent执行失败（不可重试）: {str(exc)}"
                emit(
                    "warning",
                    {
                        "stage": "agent_running",
                        "attempt": attempt,
                        "reason": "non_retriable",
                        "message": fast_fail_message,
                    },
                )
                raise HTTPException(status_code=502, detail=fast_fail_message) from exc

            emit(
                "warning",
                {
                    "stage": "agent_running",
                    "attempt": attempt,
                    "message": f"ReportAgent执行失败: {str(exc)}",
                },
            )
            if attempt == whole_run_attempts:
                raise
            backoff = min(5 * attempt, 15)
            emit(
                "stage",
                {
                    "stage": "retry_wait",
                    "attempt": attempt,
                    "wait_seconds": backoff,
                    "message": f"{backoff} 秒后重试生成任务",
                },
            )
            time.sleep(backoff)

    if local_result is None:
        raise HTTPException(status_code=500, detail="report generation failed without result")

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


def _normalize_forum_logs(raw_logs: Union[str, List[str]], max_lines: Optional[int], max_chars: Optional[int]) -> List[str]:
    if isinstance(raw_logs, list):
        lines = [str(x) for x in raw_logs if str(x).strip()]
    elif isinstance(raw_logs, str):
        lines = [line for line in raw_logs.splitlines() if line.strip()]
    else:
        lines = []

    if max_lines is not None:
        max_lines = _clamp_optional_int(max_lines, 1, 500)
        lines = lines[-max_lines:]

    if max_chars is not None:
        max_chars = _clamp_optional_int(max_chars, 200, 200000)
        merged = "\n".join(lines)
        if len(merged) > max_chars:
            merged = merged[-max_chars:]
            lines = [line for line in merged.splitlines() if line.strip()]

    return lines


def _run_forum_engine(body: ForumRequest) -> Dict[str, Any]:
    context = body.context or {}
    request_id = str(context.get("request_id") or uuid.uuid4())
    forum_logs = _normalize_forum_logs(body.forum_logs, body.max_lines, body.max_chars)

    if not forum_logs:
        raise HTTPException(status_code=400, detail="forum_logs is empty")

    host = ENGINE_RUNTIME.create_forum_host()
    speech = host.generate_host_speech(forum_logs)
    if not speech:
        raise HTTPException(status_code=502, detail="ForumEngine failed to generate host speech")

    return {
        "host_speech": speech,
        "manifest": _build_manifest("ForumEngine", request_id, context),
        "logs": ["ForumEngine completed"],
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
        "engines": ["query", "media", "insight", "forum", "report"],
        "endpoints": {
            "research_dispatch": "/v1/research",
            "research_query": "/v1/research/query",
            "research_media": "/v1/research/media",
            "research_insight": "/v1/research/insight",
            "research_stream_dispatch": "/v1/research/stream",
            "research_stream_engine": "/v1/research/{engine}/stream",
            "forum_host_speech": "/v1/forum/host-speech",
            "forum_host_speech_stream": "/v1/forum/host-speech/stream",
            "report": "/v1/report",
            "report_stream": "/v1/report/stream",
            "report_download": "/v1/report/download?path=<relative_or_absolute_file_path>",
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
async def startup_initialize_runtime():
    """Initialize embedded engine runtime at service startup."""
    try:
        ENGINE_RUNTIME.initialize()
        logger.info("Embedded engine runtime initialized")

        check_enabled = _env_bool("ENGINE_INSIGHT_DB_CHECK_ON_STARTUP", True)
        fail_fast = _env_bool("ENGINE_INSIGHT_DB_FAIL_FAST", False)

        if check_enabled:
            missing_tables = await _get_insight_missing_tables(INSIGHT_REQUIRED_TABLES)
            if missing_tables:
                logger.warning(
                    "InsightEngine dependency check: missing %d tables: %s",
                    len(missing_tables),
                    ", ".join(missing_tables),
                )
                if fail_fast:
                    raise RuntimeError(
                        "InsightEngine dependency check failed (missing tables): "
                        + ", ".join(missing_tables)
                    )
            else:
                logger.info(
                    "InsightEngine dependency check passed (%d/%d tables found)",
                    len(INSIGHT_REQUIRED_TABLES),
                    len(INSIGHT_REQUIRED_TABLES),
                )
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

    return _run_research_impl(engine, query, body.save_report, body.export_formats, context, body)


@app.post("/v1/research/stream")
def research_dispatch_stream(body: ResearchRequest, request: Request, _auth: None = Depends(_require_auth)):
    engine = str(body.engine or "").strip().lower()
    query = body.query.strip()
    context = body.context or {}
    request_id = _ensure_request_id(context)

    if not engine:
        raise HTTPException(status_code=400, detail="missing field: engine")
    if not query:
        raise HTTPException(status_code=400, detail="missing field: query")

    return _stream_with_heartbeat(
        lambda: _run_research_impl(engine, query, body.save_report, body.export_formats, context, body),
        {
            "engine": engine,
            "query": query,
            "mode": "research_stream",
            "request_id": request_id,
        },
        request,
    )


@app.post("/v1/research/{engine}")
def research_engine(engine: str, body: ResearchRequest, _auth: None = Depends(_require_auth)):
    query = body.query.strip()
    context = body.context or {}
    if not query:
        raise HTTPException(status_code=400, detail="missing field: query")

    return _run_research_impl(engine, query, body.save_report, body.export_formats, context, body)


@app.post("/v1/research/{engine}/stream")
def research_engine_stream(engine: str, body: ResearchRequest, request: Request, _auth: None = Depends(_require_auth)):
    query = body.query.strip()
    context = body.context or {}
    request_id = _ensure_request_id(context)
    if not query:
        raise HTTPException(status_code=400, detail="missing field: query")

    return _stream_with_heartbeat(
        lambda: _run_research_impl(engine, query, body.save_report, body.export_formats, context, body),
        {
            "engine": str(engine).strip().lower(),
            "query": query,
            "mode": "research_stream",
            "request_id": request_id,
        },
        request,
    )


def _run_research_impl(
    engine: str,
    query: str,
    save_report: bool,
    export_formats: Optional[List[str]],
    context: Dict[str, Any],
    body: ResearchRequest,
):
    engine_name = str(engine).strip().lower()
    overrides = _build_runtime_overrides(body)

    try:
        if engine_name == "query":
            return _run_query_engine(query, save_report, export_formats, context, overrides)
        if engine_name == "media":
            return _run_media_engine(query, save_report, context, overrides)
        if engine_name == "insight":
            return _run_insight_engine(query, save_report, context, overrides)
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


@app.post("/v1/report/stream")
def report_engine_stream(body: ReportRequest, request: Request, _auth: None = Depends(_require_auth)):
    query = body.query.strip()
    context = body.context or {}
    request_id = _ensure_request_id(context)
    if not query:
        raise HTTPException(status_code=400, detail="missing field: query")
    if not isinstance(body.merged_result, dict):
        body.merged_result = {}

    return _stream_with_heartbeat(
        lambda stream_handler=None: _run_report_engine(body, stream_handler=stream_handler),
        {
            "engine": "report",
            "query": query,
            "mode": "report_stream",
            "request_id": request_id,
        },
        request,
    )


@app.get("/v1/report/download")
def report_download(path: str, filename: Optional[str] = None, _auth: None = Depends(_require_auth)):
    file_path = _resolve_download_file(path)
    download_name = filename.strip() if isinstance(filename, str) and filename.strip() else file_path.name
    return FileResponse(path=str(file_path), filename=download_name, media_type="application/octet-stream")


@app.post("/v1/forum/host-speech")
def forum_engine(body: ForumRequest, _auth: None = Depends(_require_auth)):
    try:
        return _run_forum_engine(body)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(f"forum engine failed: {exc}")
        raise HTTPException(status_code=500, detail=f"forum engine failed: {exc}")


@app.post("/v1/forum/host-speech/stream")
def forum_engine_stream(body: ForumRequest, request: Request, _auth: None = Depends(_require_auth)):
    context = body.context or {}
    request_id = _ensure_request_id(context)
    return _stream_with_heartbeat(
        lambda: _run_forum_engine(body),
        {
            "engine": "forum",
            "mode": "forum_stream",
            "request_id": request_id,
        },
        request,
    )


if __name__ == "__main__":
    host = os.getenv("ENGINE_GATEWAY_HOST", "0.0.0.0")
    port = int(os.getenv("ENGINE_GATEWAY_PORT", "19000"))
    debug = os.getenv("ENGINE_GATEWAY_DEBUG", "0") == "1"

    logger.info(f"Starting engine gateway on {host}:{port}")
    uvicorn.run("engine_gateway_api:app", host=host, port=port, reload=debug)
