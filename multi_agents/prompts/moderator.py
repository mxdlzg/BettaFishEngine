# -*- coding: utf-8 -*-
"""
Moderator prompts for forum discussion rounds.
"""

MODERATOR_SYSTEM_PROMPT = """你是一个舆情分析论坛的主持人。你的任务是综合多个分析引擎的结果，进行多轮讨论式分析。

每一轮讨论，你需要：
1. 总结当前各方的分析结果
2. 识别分析结果中的冲突或矛盾
3. 指出证据不足的地方
4. 提出需要进一步调查的方向
5. 形成阶段性结论

输出JSON格式，包含以下字段：
- round_summary: 本轮讨论摘要
- conflicts: 发现的冲突或矛盾列表
- missing_evidence: 缺失的证据列表
- followup_suggestions: 后续建议列表
- intermediate_conclusion: 阶段性结论

请保持客观、严谨，确保分析的深度和广度。"""

MODERATOR_ROUND_1_TEMPLATE = """这是第一轮综合分析讨论。

**分析主题**：{query}

**公开信息分析结果（QueryEngine）**：
{query_result}

**媒体分析结果（MediaEngine）**：
{media_result}

**情感洞察分析结果（InsightEngine）**：
{insight_result}

**知识库查询结果**：
{kb_result}

请进行第一轮综合审阅，重点关注各分析结果的一致性和完整性。以JSON格式输出。"""

MODERATOR_ROUND_2_TEMPLATE = """这是第二轮深度分析讨论。

**分析主题**：{query}

**第一轮讨论结果**：
{round_1_result}

**补充信息**：
- 公开信息分析：{query_result}
- 媒体分析：{media_result}
- 情感洞察：{insight_result}
- 知识库结果：{kb_result}

请进行第二轮分析，重点关注：
1. 第一轮发现的冲突如何解决
2. 缺失证据是否有补充
3. 深入挖掘风险信号和机会点

以JSON格式输出。"""

MODERATOR_ROUND_3_TEMPLATE = """这是第三轮最终讨论，需要形成共识结论。

**分析主题**：{query}

**第一轮讨论结果**：
{round_1_result}

**第二轮讨论结果**：
{round_2_result}

**完整分析数据**：
- 公开信息分析：{query_result}
- 媒体分析：{media_result}
- 情感洞察：{insight_result}
- 知识库结果：{kb_result}

请进行最终轮讨论，形成：
1. 综合性的最终结论
2. 明确的风险评估
3. 可行的建议方向
4. 剩余的不确定性说明

以JSON格式输出。"""


def build_moderator_round_1_messages(
    query: str,
    query_result: dict,
    media_result: dict,
    insight_result: dict,
    kb_result: dict
) -> list:
    """Build messages for forum round 1."""
    import json
    
    def to_str(d):
        if isinstance(d, dict):
            return json.dumps(d, ensure_ascii=False, indent=2)[:3000]
        return str(d)[:3000]
    
    return [
        {"role": "system", "content": MODERATOR_SYSTEM_PROMPT},
        {"role": "user", "content": MODERATOR_ROUND_1_TEMPLATE.format(
            query=query,
            query_result=to_str(query_result),
            media_result=to_str(media_result),
            insight_result=to_str(insight_result),
            kb_result=to_str(kb_result),
        )},
    ]


def build_moderator_round_2_messages(
    query: str,
    round_1_result: dict,
    query_result: dict,
    media_result: dict,
    insight_result: dict,
    kb_result: dict
) -> list:
    """Build messages for forum round 2."""
    import json
    
    def to_str(d):
        if isinstance(d, dict):
            return json.dumps(d, ensure_ascii=False, indent=2)[:2000]
        return str(d)[:2000]
    
    return [
        {"role": "system", "content": MODERATOR_SYSTEM_PROMPT},
        {"role": "user", "content": MODERATOR_ROUND_2_TEMPLATE.format(
            query=query,
            round_1_result=to_str(round_1_result),
            query_result=to_str(query_result),
            media_result=to_str(media_result),
            insight_result=to_str(insight_result),
            kb_result=to_str(kb_result),
        )},
    ]


def build_moderator_round_3_messages(
    query: str,
    round_1_result: dict,
    round_2_result: dict,
    query_result: dict,
    media_result: dict,
    insight_result: dict,
    kb_result: dict
) -> list:
    """Build messages for forum round 3."""
    import json
    
    def to_str(d):
        if isinstance(d, dict):
            return json.dumps(d, ensure_ascii=False, indent=2)[:1500]
        return str(d)[:1500]
    
    return [
        {"role": "system", "content": MODERATOR_SYSTEM_PROMPT},
        {"role": "user", "content": MODERATOR_ROUND_3_TEMPLATE.format(
            query=query,
            round_1_result=to_str(round_1_result),
            round_2_result=to_str(round_2_result),
            query_result=to_str(query_result),
            media_result=to_str(media_result),
            insight_result=to_str(insight_result),
            kb_result=to_str(kb_result),
        )},
    ]
