# -*- coding: utf-8 -*-
"""
Report node for the LangGraph public opinion workflow.

Generates final report files using ReportEngine.
"""

from typing import Dict, Any, Optional

from multi_agents.state import PublicOpinionState, StateUpdate
from multi_agents.tools.progress import add_progress, Stage
from multi_agents.tools.logger import get_logger, log_node_start, log_node_end
from multi_agents.tools.engine_bridge import get_engine_bridge
from multi_agents.tools.llm_client import get_llm_client
from multi_agents.prompts.report import build_report_messages

logger = get_logger("report_node")


def report_node(state: PublicOpinionState, config: Optional[Dict] = None) -> StateUpdate:
    """
    Report node: Generate final report.
    
    This node:
    1. Takes merged results
    2. Calls ReportEngine or generates report via LLM
    3. Creates HTML/PDF/Markdown output
    
    Args:
        state: Current graph state
        config: Configuration
    
    Returns:
        State updates with report_result
    """
    task_id = state.get("task_id", "unknown")
    log_node_start(logger, "report", task_id)
    
    updates: StateUpdate = {}
    add_progress(updates, Stage.REPORT_GENERATING)
    
    query = state.get("query", "")
    merged_result = state.get("merged_result", {})
    query_result = state.get("query_result", {})
    media_result = state.get("media_result", {})
    insight_result = state.get("insight_result", {})
    kb_result = state.get("kb_result", {})
    
    try:
        # Try to use ReportEngine bridge
        bridge = get_engine_bridge()
        result = bridge.run_report_engine(query, merged_result, {"task_id": task_id})
        
        # If ReportEngine failed or returned empty, use LLM fallback
        if not result.get("html_path"):
            result = _generate_report_via_llm(
                query, merged_result, query_result, media_result, insight_result, kb_result, task_id
            )
        
        updates["report_result"] = result
        
        logger.info(
            f"[{task_id}] Report generated: "
            f"HTML={bool(result.get('html_path'))}, "
            f"PDF={bool(result.get('pdf_path'))}"
        )
        
    except Exception as e:
        logger.exception(f"[{task_id}] Report generation failed: {e}")
        
        # Use LLM fallback
        try:
            result = _generate_report_via_llm(
                query, merged_result, query_result, media_result, insight_result, kb_result, task_id
            )
            updates["report_result"] = result
        except Exception as e2:
            logger.exception(f"[{task_id}] LLM report fallback also failed: {e2}")
            updates["report_result"] = {
                "summary_text": f"报告生成失败: {str(e)}",
                "html_path": "",
                "pdf_path": "",
                "docx_path": "",
                "md_path": "",
                "chart_paths": [],
                "manifest": {"error": str(e)},
            }
        
        updates["errors"] = state.get("errors", []) + [f"Report error: {str(e)}"]
    
    log_node_end(logger, "report", task_id)
    return updates


def _generate_report_via_llm(
    query: str,
    merged_result: Dict,
    query_result: Dict,
    media_result: Dict,
    insight_result: Dict,
    kb_result: Dict,
    task_id: str
) -> Dict[str, Any]:
    """
    Generate report content via LLM when ReportEngine is unavailable.
    
    Args:
        query: User's query
        merged_result: Merged analysis result
        query_result: QueryEngine result
        media_result: MediaEngine result
        insight_result: InsightEngine result
        kb_result: KB result
        task_id: Task ID
    
    Returns:
        Report result dict
    """
    from pathlib import Path
    from multi_agents.settings import get_settings
    from multi_agents.tools.artifacts import ensure_task_dir, write_text_file
    
    settings = get_settings()
    
    # Build report prompt
    messages = build_report_messages(
        query=query,
        merged_result=merged_result,
        query_result=query_result,
        media_result=media_result,
        insight_result=insight_result,
        kb_result=kb_result,
    )
    
    # Call LLM for report content
    llm_client = get_llm_client()
    report_content = llm_client.report_chat(
        messages=messages,
        max_tokens=8000,
    )
    
    # Save report
    task_dir = ensure_task_dir(settings.report_output_dir, task_id)
    
    # Save markdown
    md_path = task_dir / "report.md"
    write_text_file(md_path, report_content)
    
    # Generate simple HTML
    html_content = _markdown_to_simple_html(report_content, query)
    html_path = task_dir / "report.html"
    write_text_file(html_path, html_content)
    
    return {
        "summary_text": report_content[:1000],
        "html_path": str(html_path),
        "pdf_path": "",  # PDF requires additional tooling
        "docx_path": "",
        "md_path": str(md_path),
        "chart_paths": [],
        "manifest": {
            "task_id": task_id,
            "query": query,
            "generated_by": "llm_fallback",
        },
    }


def _markdown_to_simple_html(markdown: str, title: str) -> str:
    """Convert markdown to simple HTML."""
    import re
    
    # Basic markdown to HTML conversion
    html = markdown
    
    # Headers
    html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
    html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
    
    # Bold and italic
    html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
    html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)
    
    # Lists
    html = re.sub(r'^- (.+)$', r'<li>\1</li>', html, flags=re.MULTILINE)
    html = re.sub(r'^(\d+)\. (.+)$', r'<li>\2</li>', html, flags=re.MULTILINE)
    
    # Paragraphs
    html = re.sub(r'\n\n', '</p><p>', html)
    
    # Wrap in HTML template
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - 舆情分析报告</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; line-height: 1.6; }}
        h1 {{ color: #1a1a1a; border-bottom: 2px solid #eee; padding-bottom: 10px; }}
        h2 {{ color: #333; margin-top: 30px; }}
        h3 {{ color: #555; }}
        li {{ margin: 5px 0; }}
        strong {{ color: #d32f2f; }}
    </style>
</head>
<body>
    <p>{html}</p>
</body>
</html>"""
