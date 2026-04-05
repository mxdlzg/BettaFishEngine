# -*- coding: utf-8 -*-
"""
Report prompts for generating final report content.
"""

REPORT_SYSTEM_PROMPT = """你是一个专业的舆情分析报告撰写专家。你的任务是基于整合后的分析结果，生成结构化的舆情分析报告。

报告必须包含以下章节：
1. 执行摘要 - 关键发现和建议概述
2. 舆情概览 - 整体舆情态势
3. 关键事件 - 重要事件时间线
4. 情感与议题 - 情感分布和主要议题
5. 传播与人群 - 传播路径和受众分析
6. 风险与机会 - 风险评估和机会识别
7. 建议 - 具体可行的建议
8. 数据附录 - 关键数据和来源

写作风格：
- 专业客观，避免主观臆断
- 数据驱动，用数据支撑观点
- 清晰简洁，避免冗长
- 可操作性强，建议要具体

输出格式为Markdown。"""

REPORT_USER_TEMPLATE = """请基于以下分析结果生成舆情分析报告：

**分析主题**：{query}

**整合分析结论**：
{merged_result}

**原始分析数据概要**：
- 公开信息来源数：{query_source_count}
- 媒体分析来源数：{media_source_count}
- 情感分析样本数：{insight_sample_count}
- 知识库查询结果数：{kb_result_count}

请生成完整的Markdown格式报告。"""


def build_report_messages(
    query: str,
    merged_result: dict,
    query_result: dict = None,
    media_result: dict = None,
    insight_result: dict = None,
    kb_result: dict = None
) -> list:
    """
    Build messages for report generation.
    
    Args:
        query: User's original query
        merged_result: Merged analysis result
        query_result: Optional QueryEngine result for stats
        media_result: Optional MediaEngine result for stats
        insight_result: Optional InsightEngine result for stats
        kb_result: Optional KB result for stats
    
    Returns:
        List of message dicts
    """
    import json
    
    def count_sources(result):
        if not result:
            return 0
        if isinstance(result, dict):
            return len(result.get("sources", []))
        return 0
    
    merged_str = json.dumps(merged_result, ensure_ascii=False, indent=2)[:6000]
    
    return [
        {"role": "system", "content": REPORT_SYSTEM_PROMPT},
        {"role": "user", "content": REPORT_USER_TEMPLATE.format(
            query=query,
            merged_result=merged_str,
            query_source_count=count_sources(query_result),
            media_source_count=count_sources(media_result),
            insight_sample_count=count_sources(insight_result),
            kb_result_count=len(kb_result.get("answers", [])) if kb_result else 0,
        )},
    ]


SUMMARY_PROMPT = """请用简洁的语言（不超过200字）总结以下舆情分析的核心发现：

{merged_result}

输出格式：
1. 一句话概括主要发现
2. 2-3个关键风险点
3. 1-2个建议方向"""


def build_summary_messages(merged_result: dict) -> list:
    """Build messages for executive summary."""
    import json
    
    return [
        {"role": "system", "content": "你是一个专业的舆情分析师，擅长用简洁的语言总结复杂的分析结果。"},
        {"role": "user", "content": SUMMARY_PROMPT.format(
            merged_result=json.dumps(merged_result, ensure_ascii=False, indent=2)[:3000]
        )},
    ]
