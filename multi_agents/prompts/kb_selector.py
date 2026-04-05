# -*- coding: utf-8 -*-
"""
Knowledge base selector prompts.
"""

KB_SELECTOR_SYSTEM_PROMPT = """你是一个知识库选择专家。根据用户的查询和可用的知识库列表，选择最相关的知识库进行查询。

你需要输出一个JSON对象，包含：
- selected: 选中的知识库列表，每个元素包含 {id, name, reason}
- query_strategy: 建议的查询策略（"specific"精确查询 / "broad"广泛查询）
- expected_info: 期望从知识库获取的信息类型

选择原则：
1. 选择与查询主题最相关的知识库（1-3个）
2. 考虑知识库的内容覆盖范围
3. 如果没有相关知识库，返回空的selected列表
4. 优先选择专业领域匹配的知识库"""

KB_SELECTOR_USER_TEMPLATE = """请为以下查询选择合适的知识库：

**用户查询**：{query}

**分析计划**：
{plan}

**可用知识库列表**：
{knowledge_bases}

请以JSON格式输出选择结果。"""


def build_kb_selector_messages(query: str, plan: dict, knowledge_bases: list) -> list:
    """
    Build messages for knowledge base selection.
    
    Args:
        query: User's original query
        plan: Analysis plan from planner
        knowledge_bases: List of available knowledge bases
    
    Returns:
        List of message dicts
    """
    import json
    
    plan_str = json.dumps(plan, ensure_ascii=False, indent=2)
    kb_str = json.dumps(knowledge_bases, ensure_ascii=False, indent=2)
    
    return [
        {"role": "system", "content": KB_SELECTOR_SYSTEM_PROMPT},
        {"role": "user", "content": KB_SELECTOR_USER_TEMPLATE.format(
            query=query,
            plan=plan_str,
            knowledge_bases=kb_str
        )},
    ]
