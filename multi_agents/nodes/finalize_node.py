# -*- coding: utf-8 -*-
"""
Finalize node for the LangGraph public opinion workflow.

Generates the final answer for user display.
"""

from typing import Dict, Any, Optional

from multi_agents.state import PublicOpinionState, StateUpdate
from multi_agents.tools.progress import add_progress, Stage, get_progress_text
from multi_agents.tools.logger import get_logger, log_node_start, log_node_end

logger = get_logger("finalize_node")


def finalize_node(state: PublicOpinionState, config: Optional[Dict] = None) -> StateUpdate:
    """
    Finalize node: Generate final user-facing answer.
    
    This node:
    1. Creates a clean markdown summary
    2. Lists available attachments
    3. Marks task as completed
    
    Args:
        state: Current graph state
        config: Configuration
    
    Returns:
        State updates with final_answer
    """
    task_id = state.get("task_id", "unknown")
    log_node_start(logger, "finalize", task_id)
    
    updates: StateUpdate = {}
    
    # Get data
    query = state.get("query", "")
    merged_result = state.get("merged_result", {})
    artifacts = state.get("artifacts", {})
    files = state.get("files", {})
    errors = state.get("errors", [])
    auto_selected_kbs = state.get("auto_selected_knowledge_bases", [])
    
    # Build final answer markdown
    lines = [
        "# 舆情分析报告摘要",
        "",
        f"**分析主题**: {query}",
        "",
    ]
    
    # Core conclusions
    conclusions = merged_result.get("core_conclusions", [])
    if conclusions:
        lines.append("## 核心结论")
        lines.append("")
        for i, c in enumerate(conclusions, 1):
            lines.append(f"{i}. {c}")
        lines.append("")
    
    # Risk points
    risks = merged_result.get("risk_points", [])
    if risks:
        lines.append("## 风险点")
        lines.append("")
        for r in risks:
            lines.append(f"- ⚠️ {r}")
        lines.append("")
    
    # Opportunities
    opportunities = merged_result.get("opportunities", [])
    if opportunities:
        lines.append("## 机会点")
        lines.append("")
        for o in opportunities:
            lines.append(f"- ✅ {o}")
        lines.append("")
    
    # Knowledge base usage
    if auto_selected_kbs:
        lines.append("## 知识库使用情况")
        lines.append("")
        for kb in auto_selected_kbs:
            kb_name = kb.get("name", kb.get("id", "未知"))
            lines.append(f"- 📚 {kb_name}")
        lines.append("")
    
    # Attachments
    if files:
        lines.append("## 报告附件")
        lines.append("")
        for path, info in files.items():
            filename = info.get("filename", path.split("/")[-1])
            lines.append(f"- 📎 {filename}")
        lines.append("")
    
    # Statistics
    stats = merged_result.get("stats", {})
    if stats:
        lines.append("## 分析统计")
        lines.append("")
        lines.append(f"- 公开信息来源: {stats.get('query_sources', 0)} 条")
        lines.append(f"- 媒体内容来源: {stats.get('media_sources', 0)} 条")
        lines.append(f"- 情感分析样本: {stats.get('insight_sources', 0)} 条")
        lines.append(f"- 知识库回答: {stats.get('kb_answers', 0)} 条")
        lines.append("")
    
    # Errors (if any)
    if errors:
        lines.append("## ⚠️ 注意事项")
        lines.append("")
        lines.append("分析过程中遇到以下问题，可能影响结果完整性：")
        for e in errors[:3]:  # Only show first 3 errors
            lines.append(f"- {e[:100]}")
        lines.append("")
    
    # Footer
    lines.append("---")
    lines.append(f"*任务ID: {task_id}*")
    
    final_answer = "\n".join(lines)
    updates["final_answer"] = final_answer
    
    # Mark completed
    add_progress(updates, Stage.COMPLETED)
    
    logger.info(f"[{task_id}] Finalize completed, answer length: {len(final_answer)}")
    log_node_end(logger, "finalize", task_id)
    
    return updates
