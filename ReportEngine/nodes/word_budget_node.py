"""
章节篇幅规划节点。
"""

from __future__ import annotations

import json
from typing import Any, Dict, List

from loguru import logger

from ..core import TemplateSection
from ..prompts import (
    SYSTEM_PROMPT_WORD_BUDGET,
    build_word_budget_prompt,
)
from ..utils.json_parser import RobustJSONParser, JSONParseError
from .base_node import BaseNode


class WordBudgetNode(BaseNode):
    """
    规划各章节字数与重点。

    输出总字数、全局写作准则以及每章/小节的 target/min/max 字数约束。
    """

    def __init__(self, llm_client):
        """仅记录LLM客户端引用，方便run阶段发起请求"""
        super().__init__(llm_client, "WordBudgetNode")
        # 初始化鲁棒JSON解析器，启用所有修复策略
        self.json_parser = RobustJSONParser(
            enable_json_repair=True,
            enable_llm_repair=False,  # 可以根据需要启用LLM修复
            max_repair_attempts=3,
        )

    def run(
        self,
        sections: List[TemplateSection],
        design: Dict[str, Any],
        reports: Dict[str, str],
        forum_logs: str,
        query: str,
        template_overview: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        """
        根据设计稿和所有素材规划章节字数，让LLM写作时有明确篇幅目标。

        参数:
            sections: 模板章节列表。
            design: 布局节点返回的设计稿（title/toc/hero等）。
            reports: 三引擎报告映射。
            forum_logs: 论坛日志原文。
            query: 用户查询词。
            template_overview: 可选的模板概览，含章节元信息。

        返回:
            dict: 章节篇幅规划结果，包含 `totalWords`、`globalGuidelines` 与逐章 `chapters`。
        """
        # 输入中除了章节骨架外，还包含布局节点输出，方便约束篇幅时参考视觉主次
        payload = {
            "query": query,
            "design": design,
            "sections": [section.to_dict() for section in sections],
            "templateOverview": template_overview
            or {
                "title": sections[0].title if sections else "",
                "chapters": [section.to_dict() for section in sections],
            },
            "reports": reports,
            "forumLogs": forum_logs,
        }
        user = build_word_budget_prompt(payload)
        response = self.llm_client.stream_invoke_to_string(
            SYSTEM_PROMPT_WORD_BUDGET,
            user,
            temperature=0.25,
            top_p=0.85,
        )
        if not response or not response.strip():
            logger.warning("章节字数规划LLM返回空内容，使用本地兜底规划")
            return self._build_fallback_plan(sections)
        plan = self._parse_response(response)
        logger.info("章节字数规划已生成")
        return plan

    def _build_fallback_plan(self, sections: List[TemplateSection]) -> Dict[str, Any]:
        chapter_count = max(1, len(sections))
        total_words = max(4000, chapter_count * 900)
        per_chapter = max(600, total_words // chapter_count)
        chapters = []
        for section in sections:
            outline = section.outline if isinstance(section.outline, list) and section.outline else [section.title]
            chapters.append(
                {
                    "chapterId": section.chapter_id,
                    "title": section.title,
                    "targetWords": per_chapter,
                    "minWords": max(300, int(per_chapter * 0.5)),
                    "maxWords": int(per_chapter * 1.3),
                    "emphasis": outline[:3],
                    "rationale": "LLM篇幅规划为空时使用的本地兜底规划。",
                    "sections": [
                        {
                            "title": item,
                            "targetWords": max(200, per_chapter // max(1, len(outline))),
                            "minWords": 100,
                            "maxWords": max(300, per_chapter),
                            "notes": "按模板小节均衡展开。",
                        }
                        for item in outline
                    ],
                }
            )
        return {
            "totalWords": total_words,
            "tolerance": 0.3,
            "globalGuidelines": ["优先保证结构完整和事实准确，内容不足时可用简洁分析兜底。"],
            "chapters": chapters,
        }

    def _parse_response(self, raw: str) -> Dict[str, Any]:
        """
        将LLM输出的JSON文本转为字典，失败时提示规划异常。

        使用鲁棒JSON解析器进行多重修复尝试：
        1. 清理markdown标记和思考内容
        2. 本地语法修复（括号平衡、逗号补全、控制字符转义等）
        3. 使用json_repair库进行高级修复
        4. 可选的LLM辅助修复

        参数:
            raw: LLM返回值，可能包含```包裹、思考内容等。

        返回:
            dict: 合法的篇幅规划JSON。

        异常:
            ValueError: 当响应为空或JSON解析失败时抛出。
        """
        try:
            result = self.json_parser.parse(
                raw,
                context_name="篇幅规划",
                expected_keys=["totalWords", "globalGuidelines", "chapters"],
            )
            # 验证关键字段的类型
            if not isinstance(result.get("totalWords"), (int, float)):
                logger.warning("篇幅规划缺少totalWords字段或类型错误，使用默认值")
                result.setdefault("totalWords", 10000)
            if not isinstance(result.get("globalGuidelines"), list):
                logger.warning("篇幅规划缺少globalGuidelines字段或类型错误，使用空列表")
                result.setdefault("globalGuidelines", [])
            if not isinstance(result.get("chapters"), (list, dict)):
                logger.warning("篇幅规划缺少chapters字段或类型错误，使用空列表")
                result.setdefault("chapters", [])
            return result
        except JSONParseError as exc:
            # 转换为原有的异常类型以保持向后兼容
            raise ValueError(f"篇幅规划JSON解析失败: {exc}") from exc


__all__ = ["WordBudgetNode"]
