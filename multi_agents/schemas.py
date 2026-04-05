# -*- coding: utf-8 -*-
"""
Schema definitions using Pydantic for validation.

Provides structured output validation for all bridge functions and node outputs.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime


# ==================== Engine Output Schemas ====================

class SourceItem(BaseModel):
    """A single source reference."""
    title: str = ""
    url: str = ""
    platform: str = ""
    snippet: str = ""
    published_at: Optional[str] = None


class QueryEngineOutputSchema(BaseModel):
    """Validated output from QueryEngine."""
    summary: str = Field(default="", description="Summary of findings")
    sources: List[SourceItem] = Field(default_factory=list, description="Source references")
    raw_result: Dict[str, Any] = Field(default_factory=dict, description="Raw engine output")
    stats: Dict[str, Any] = Field(default_factory=dict, description="Statistics")
    logs: List[str] = Field(default_factory=list, description="Processing logs")


class MediaEngineOutputSchema(BaseModel):
    """Validated output from MediaEngine."""
    summary: str = Field(default="", description="Summary of media analysis")
    platform_distribution: Dict[str, int] = Field(default_factory=dict, description="Content by platform")
    media_highlights: List[Dict[str, Any]] = Field(default_factory=list, description="Key media findings")
    sources: List[SourceItem] = Field(default_factory=list, description="Source references")
    raw_result: Dict[str, Any] = Field(default_factory=dict, description="Raw engine output")
    stats: Dict[str, Any] = Field(default_factory=dict, description="Statistics")
    logs: List[str] = Field(default_factory=list, description="Processing logs")


class InsightEngineOutputSchema(BaseModel):
    """Validated output from InsightEngine."""
    summary: str = Field(default="", description="Summary of insights")
    sentiment_summary: Dict[str, Any] = Field(default_factory=dict, description="Sentiment analysis results")
    keyword_clusters: List[Dict[str, Any]] = Field(default_factory=list, description="Keyword groupings")
    topic_clusters: List[Dict[str, Any]] = Field(default_factory=list, description="Topic groupings")
    risk_signals: List[str] = Field(default_factory=list, description="Identified risk signals")
    sources: List[SourceItem] = Field(default_factory=list, description="Source references")
    raw_result: Dict[str, Any] = Field(default_factory=dict, description="Raw engine output")
    stats: Dict[str, Any] = Field(default_factory=dict, description="Statistics")
    logs: List[str] = Field(default_factory=list, description="Processing logs")


class ForumRoundOutputSchema(BaseModel):
    """Validated output from a forum round."""
    round_index: int = Field(default=0, description="Round number (0, 1, or 2)")
    round_summary: str = Field(default="", description="Summary of this round")
    conflicts: List[str] = Field(default_factory=list, description="Identified conflicts")
    missing_evidence: List[str] = Field(default_factory=list, description="Evidence gaps")
    followup_suggestions: List[str] = Field(default_factory=list, description="Suggested follow-ups")
    intermediate_conclusion: str = Field(default="", description="Intermediate conclusion")


# ==================== Knowledge Base Schemas ====================

class KnowledgeBaseInfo(BaseModel):
    """Information about a knowledge base."""
    id: str
    name: str
    description: str = ""


class KnowledgeBaseAnswer(BaseModel):
    """Answer from a knowledge base query."""
    knowledge_base_id: str
    knowledge_base_name: str
    answer: str
    sources: List[Dict[str, Any]] = Field(default_factory=list)
    citations: List[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class KnowledgeBaseQueryOutputSchema(BaseModel):
    """Validated output from knowledge base queries."""
    selected_knowledge_bases: List[KnowledgeBaseInfo] = Field(default_factory=list)
    answers: List[KnowledgeBaseAnswer] = Field(default_factory=list)
    merged_summary: str = Field(default="")
    sources: List[Dict[str, Any]] = Field(default_factory=list)


# ==================== Merged Analysis Schemas ====================

class MergedAnalysisOutputSchema(BaseModel):
    """Validated output from merge node."""
    core_conclusions: List[str] = Field(default_factory=list, description="Main findings")
    risk_points: List[str] = Field(default_factory=list, description="Identified risks")
    opportunities: List[str] = Field(default_factory=list, description="Potential opportunities")
    key_evidence: List[Dict[str, Any]] = Field(default_factory=list, description="Supporting evidence")
    evidence_map: Dict[str, List[str]] = Field(default_factory=dict, description="Evidence by source")
    stats: Dict[str, Any] = Field(default_factory=dict, description="Analysis statistics")


# ==================== Report Schemas ====================

class ReportOutputSchema(BaseModel):
    """Validated output from report generation."""
    summary_text: str = Field(default="", description="Executive summary")
    html_path: str = Field(default="", description="Path to HTML report")
    pdf_path: str = Field(default="", description="Path to PDF report")
    docx_path: str = Field(default="", description="Path to DOCX report")
    md_path: str = Field(default="", description="Path to Markdown report")
    chart_paths: List[str] = Field(default_factory=list, description="Paths to chart images")
    manifest: Dict[str, Any] = Field(default_factory=dict, description="Report manifest")


class FileArtifactSchema(BaseModel):
    """A file artifact for ALB frontend."""
    filename: str
    url: str
    media_type: str
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


# ==================== Plan Schemas ====================

class PlanOutputSchema(BaseModel):
    """Validated output from planner."""
    topic: str = Field(default="", description="Main topic")
    entity: str = Field(default="", description="Main entity being analyzed")
    region: str = Field(default="", description="Geographic scope")
    time_scope: str = Field(default="", description="Time range for analysis")
    focus_dimensions: List[str] = Field(default_factory=list, description="Analysis dimensions")
    report_priority: str = Field(default="comprehensive", description="Report priority level")
    needs_kb: bool = Field(default=True, description="Whether to query knowledge base")
    analysis_goal: str = Field(default="", description="Goal of the analysis")


# ==================== Manifest Schema ====================

class ManifestSchema(BaseModel):
    """Task manifest for tracking and audit."""
    task_id: str
    query: str
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    selected_knowledge_bases: List[str] = Field(default_factory=list)
    models_used: Dict[str, str] = Field(default_factory=dict)
    files: List[str] = Field(default_factory=list)
    stats: Dict[str, Any] = Field(default_factory=dict)
    duration_seconds: float = Field(default=0.0)
    status: str = Field(default="completed")
