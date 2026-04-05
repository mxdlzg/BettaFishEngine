# -*- coding: utf-8 -*-
"""
Intake prompts for extracting structured query information.
"""

INTAKE_SYSTEM_PROMPT = """你是一个舆情分析任务解析助手。你的任务是从用户的查询中提取关键信息，以便后续的舆情分析。

请从用户输入中提取以下信息：
- topic: 主题/话题
- entity: 涉及的主要实体（公司、人物、产品等）
- region: 地理范围（全球/中国/特定地区）
- time_scope: 时间范围（最近一周/一个月/具体日期等）
- analysis_goal: 分析目标（了解舆情/风险评估/竞品分析等）
- report_expectation: 报告期望（简要概述/详细分析/风险警示等）

输出JSON格式。如果某个字段无法从输入中提取，使用合理的默认值。"""

INTAKE_USER_TEMPLATE = """请分析以下用户查询，提取结构化信息：

用户查询：{query}

请以JSON格式输出结果。"""


def build_intake_messages(query: str) -> list:
    """
    Build messages for intake prompt.
    
    Args:
        query: User's original query
    
    Returns:
        List of message dicts
    """
    return [
        {"role": "system", "content": INTAKE_SYSTEM_PROMPT},
        {"role": "user", "content": INTAKE_USER_TEMPLATE.format(query=query)},
    ]
