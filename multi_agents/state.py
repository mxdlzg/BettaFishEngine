# -*- coding: utf-8 -*-
"""
State definitions for LangGraph Multi-Agent System.

Defines the complete state schema that flows through all nodes.
All nodes should only read/write fields defined here.
"""

from typing import TypedDict, List, Dict, Any, Optional
from typing_extensions import Annotated
from langgraph.graph.message import add_messages


class EvidenceItem(TypedDict, total=False):
    """A single piece of evidence from any source."""
    id: str
    title: str
    summary: str
    source: str
    url: str
    platform: str
    confidence: float
    metadata: Dict[str, Any]


class KnowledgeBaseResult(TypedDict, total=False):
    """Result from MCP knowledge base queries."""
    selected_knowledge_bases: List[Dict[str, Any]]
    answers: List[Dict[str, Any]]
    merged_summary: str
    sources: List[Dict[str, Any]]


class ReportArtifacts(TypedDict, total=False):
    """Generated report file artifacts."""
    task_id: str
    answer_md_path: str
    html_path: str
    pdf_path: str
    docx_path: str
    manifest_path: str
    chart_paths: List[str]


class ProgressItem(TypedDict, total=False):
    """A single progress log entry."""
    ts: float
    stage: str
    message: str


class FileEntry(TypedDict, total=False):
    """A file entry for ALB frontend."""
    filename: str
    url: str
    media_type: str
    created_at: str


class ForumRound(TypedDict, total=False):
    """Result of a single forum discussion round."""
    round_index: int
    round_summary: str
    conflicts: List[str]
    missing_evidence: List[str]
    followup_suggestions: List[str]
    intermediate_conclusion: str


class PlanOutput(TypedDict, total=False):
    """Output from the planner node."""
    topic: str
    entity: str
    region: str
    time_scope: str
    focus_dimensions: List[str]
    report_priority: str
    needs_kb: bool
    analysis_goal: str


class QueryEngineOutput(TypedDict, total=False):
    """Output from QueryEngine bridge."""
    summary: str
    sources: List[Dict[str, Any]]
    raw_result: Dict[str, Any]
    stats: Dict[str, Any]
    logs: List[str]


class MediaEngineOutput(TypedDict, total=False):
    """Output from MediaEngine bridge."""
    summary: str
    platform_distribution: Dict[str, Any]
    media_highlights: List[Dict[str, Any]]
    sources: List[Dict[str, Any]]
    raw_result: Dict[str, Any]
    stats: Dict[str, Any]
    logs: List[str]


class InsightEngineOutput(TypedDict, total=False):
    """Output from InsightEngine bridge."""
    summary: str
    sentiment_summary: Dict[str, Any]
    keyword_clusters: List[Dict[str, Any]]
    topic_clusters: List[Dict[str, Any]]
    risk_signals: List[str]
    sources: List[Dict[str, Any]]
    raw_result: Dict[str, Any]
    stats: Dict[str, Any]
    logs: List[str]


class MergedResult(TypedDict, total=False):
    """Merged analysis result from all sources."""
    core_conclusions: List[str]
    risk_points: List[str]
    opportunities: List[str]
    key_evidence: List[Dict[str, Any]]
    evidence_map: Dict[str, List[str]]
    stats: Dict[str, Any]


class ReportResult(TypedDict, total=False):
    """Result from report generation."""
    summary_text: str
    html_path: str
    pdf_path: str
    docx_path: str
    md_path: str
    chart_paths: List[str]
    manifest: Dict[str, Any]


class PublicOpinionState(TypedDict, total=False):
    """
    The main state object that flows through the entire graph.
    
    All nodes read from and write to this state.
    Fields are optional (total=False) to allow incremental building.
    """
    
    # ==================== Input & Identity ====================
    messages: Annotated[list, add_messages]  # LangGraph message history
    query: str  # The user's original question/topic
    task_id: str  # Unique identifier for this analysis task
    user_id: str  # User identifier from ALB
    thread_id: str  # Thread identifier from ALB
    agent_id: str  # This agent's identifier
    source_type: str  # Source type (e.g., "alb", "direct")
    assistant_id: str  # Assistant ID for LangGraph
    
    # ==================== Authentication ====================
    alb_mcp_token: str  # Token for MCP knowledge base access
    
    # ==================== Planning ====================
    plan: PlanOutput  # Analysis plan from planner
    
    # ==================== Engine Results ====================
    query_result: QueryEngineOutput  # Public web/news analysis
    media_result: MediaEngineOutput  # Media/multimedia analysis
    insight_result: InsightEngineOutput  # Sentiment/topic analysis
    kb_result: KnowledgeBaseResult  # Knowledge base query results
    auto_selected_knowledge_bases: List[Dict[str, Any]]  # Auto-selected KBs
    
    # ==================== Forum Discussion ====================
    forum_rounds: List[ForumRound]  # Three rounds of forum discussion
    
    # ==================== Merged Analysis ====================
    merged_result: MergedResult  # Unified analysis from all sources
    
    # ==================== Report Generation ====================
    report_result: ReportResult  # Generated report details
    artifacts: ReportArtifacts  # File artifacts
    
    # ==================== Output ====================
    files: Dict[str, FileEntry]  # Files for ALB frontend
    progress_log: List[ProgressItem]  # Progress tracking
    final_answer: str  # Final markdown answer for user
    
    # ==================== Error Handling ====================
    errors: List[str]  # List of errors encountered


# Type alias for state update functions
StateUpdate = Dict[str, Any]
