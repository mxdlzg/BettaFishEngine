# -*- coding: utf-8 -*-
"""
Merge prompts for combining analysis results.
"""

MERGE_SYSTEM_PROMPT = """你是一个舆情分析结果整合专家。你的任务是将多个分析引擎的结果和多轮讨论成果整合成统一的分析结论。

你需要输出一个JSON对象，包含：
- core_conclusions: 核心结论列表（3-5条最重要的发现）
- risk_points: 风险点列表（已识别的风险信号）
- opportunities: 机会点列表（可能的积极方向）
- key_evidence: 关键证据列表（支撑结论的重要证据，每条包含 title, source, summary）
- evidence_map: 证据来源分布（{来源类型: 证据数量}）
- stats: 统计信息

整合原则：
1. 去除重复信息，合并相似观点
2. 优先保留有多个来源支撑的结论
3. 明确标注不确定或有争议的部分
4. 确保结论可追溯到具体证据"""

MERGE_USER_TEMPLATE = """请整合以下舆情分析结果：

**分析主题**：{query}

**分析计划**：
{plan}

**公开信息分析（QueryEngine）**：
{query_result}

**媒体分析（MediaEngine）**：
{media_result}

**情感洞察分析（InsightEngine）**：
{insight_result}

**知识库查询结果**：
{kb_result}

**多轮讨论结果**：
第一轮：{forum_round_1}
第二轮：{forum_round_2}
第三轮：{forum_round_3}

请以JSON格式输出整合后的分析结论。"""


def build_merge_messages(
    query: str,
    plan: dict,
    query_result: dict,
    media_result: dict,
    insight_result: dict,
    kb_result: dict,
    forum_rounds: list
) -> list:
    """
    Build messages for merging results.
    
    Args:
        query: User's original query
        plan: Analysis plan
        query_result: QueryEngine result
        media_result: MediaEngine result
        insight_result: InsightEngine result
        kb_result: Knowledge base query result
        forum_rounds: List of forum round results
    
    Returns:
        List of message dicts
    """
    import json
    
    def to_str(d, max_len=2000):
        if isinstance(d, dict):
            return json.dumps(d, ensure_ascii=False, indent=2)[:max_len]
        return str(d)[:max_len]
    
    # Extract forum rounds
    round_1 = forum_rounds[0] if len(forum_rounds) > 0 else {}
    round_2 = forum_rounds[1] if len(forum_rounds) > 1 else {}
    round_3 = forum_rounds[2] if len(forum_rounds) > 2 else {}
    
    return [
        {"role": "system", "content": MERGE_SYSTEM_PROMPT},
        {"role": "user", "content": MERGE_USER_TEMPLATE.format(
            query=query,
            plan=to_str(plan, 500),
            query_result=to_str(query_result),
            media_result=to_str(media_result),
            insight_result=to_str(insight_result),
            kb_result=to_str(kb_result),
            forum_round_1=to_str(round_1, 1000),
            forum_round_2=to_str(round_2, 1000),
            forum_round_3=to_str(round_3, 1000),
        )},
    ]
