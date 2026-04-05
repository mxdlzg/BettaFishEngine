# -*- coding: utf-8 -*-
"""
Planner prompts for generating analysis plans.
"""

PLANNER_SYSTEM_PROMPT = """你是一个舆情分析规划师。根据用户的查询，制定详细的分析计划。

你需要输出一个JSON格式的分析计划，包含以下字段：
- topic: 分析主题
- entity: 主要分析对象
- region: 地理范围
- time_scope: 时间范围（如"最近7天"、"2024年1月至今"等）
- focus_dimensions: 关注维度列表（如["事件动态", "情感分析", "传播路径", "风险信号", "关键人物"]）
- report_priority: 报告优先级（comprehensive/quick/risk_focused）
- needs_kb: 是否需要查询知识库（true/false）
- analysis_goal: 分析目标描述

请确保计划具有可执行性和针对性。"""

PLANNER_USER_TEMPLATE = """请为以下舆情分析任务制定详细计划：

**用户查询**：{query}

**已提取的信息**：
{extracted_info}

请以JSON格式输出分析计划。"""


def build_planner_messages(query: str, extracted_info: dict) -> list:
    """
    Build messages for planner prompt.
    
    Args:
        query: User's original query
        extracted_info: Information extracted by intake
    
    Returns:
        List of message dicts
    """
    import json
    
    info_str = json.dumps(extracted_info, ensure_ascii=False, indent=2)
    
    return [
        {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
        {"role": "user", "content": PLANNER_USER_TEMPLATE.format(
            query=query,
            extracted_info=info_str
        )},
    ]
