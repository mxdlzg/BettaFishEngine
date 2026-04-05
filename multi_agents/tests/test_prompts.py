# -*- coding: utf-8 -*-
"""Tests for prompt templates."""

import pytest


class TestIntakePrompt:
    """Test suite for intake prompt."""
    
    def test_prompt_generation(self):
        """Test intake prompt generation."""
        from multi_agents.prompts.intake import build_intake_messages
        
        messages = build_intake_messages("分析人工智能舆情")
        
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert "分析人工智能舆情" in messages[1]["content"]
    
    def test_prompt_with_special_characters(self):
        """Test prompt handles special characters."""
        from multi_agents.prompts.intake import build_intake_messages
        
        query = "分析《人工智能》相关'舆情'"
        messages = build_intake_messages(query)
        
        assert "人工智能" in messages[1]["content"]


class TestPlannerPrompt:
    """Test suite for planner prompt."""
    
    def test_prompt_generation(self):
        """Test planner prompt generation."""
        from multi_agents.prompts.planner import build_planner_messages
        
        messages = build_planner_messages(
            query="人工智能发展趋势",
            extracted_info={"topic": "AI", "entity": "人工智能"}
        )
        
        assert len(messages) >= 2
        assert messages[0]["role"] == "system"
    
    def test_prompt_without_context(self):
        """Test planner prompt without optional context."""
        from multi_agents.prompts.planner import build_planner_messages
        
        messages = build_planner_messages(query="测试查询", extracted_info={})
        
        assert "测试查询" in messages[1]["content"]


class TestKBSelectorPrompt:
    """Test suite for KB selector prompt."""
    
    def test_prompt_with_kb_list(self):
        """Test KB selector prompt with KB list."""
        from multi_agents.prompts.kb_selector import build_kb_selector_messages
        
        kb_list = [
            {"id": "kb-001", "name": "政策库", "description": "政策文档"},
            {"id": "kb-002", "name": "行业库", "description": "行业数据"},
        ]
        
        messages = build_kb_selector_messages(
            query="人工智能政策",
            plan={"topic": "AI"},
            knowledge_bases=kb_list
        )
        
        assert len(messages) >= 2
        # KB info should be in the prompt
        full_content = str(messages)
        assert "政策库" in full_content or "kb-001" in full_content


class TestModeratorPrompt:
    """Test suite for moderator prompt."""
    
    def test_round_1_prompt(self):
        """Test moderator prompt for round 1."""
        from multi_agents.prompts.moderator import build_moderator_round_1_messages
        
        messages = build_moderator_round_1_messages(
            query="人工智能舆情",
            query_result={},
            media_result={},
            insight_result={},
            kb_result={}
        )
        
        assert len(messages) >= 2
        # Should reference round 1
        full_content = str(messages)
        assert "第一轮" in full_content or "1" in full_content
    
    def test_subsequent_round_prompt(self):
        """Test moderator prompt for subsequent rounds."""
        from multi_agents.prompts.moderator import build_moderator_round_2_messages
        
        messages = build_moderator_round_2_messages(
            query="人工智能舆情",
            round_1_result={"round_summary": "初步分析结果"},
            query_result={},
            media_result={},
            insight_result={},
            kb_result={}
        )
        
        full_content = str(messages)
        assert "初步分析结果" in full_content or "round_summary" in full_content


class TestMergePrompt:
    """Test suite for merge prompt."""
    
    def test_merge_prompt_generation(self):
        """Test merge prompt with all inputs."""
        from multi_agents.prompts.merge import build_merge_messages
        
        messages = build_merge_messages(
            query="人工智能舆情",
            plan={"topic": "AI"},
            query_result={"summary": "网络搜索结果..."},
            media_result={"summary": "媒体分析结果..."},
            insight_result={"summary": "洞察分析结果..."},
            kb_result={"answers": []},
            forum_rounds=[{"round_summary": "论坛讨论结果..."}]
        )
        
        assert len(messages) >= 2
        full_content = str(messages)
        assert "人工智能舆情" in full_content


class TestReportPrompt:
    """Test suite for report prompt."""
    
    def test_report_prompt_generation(self):
        """Test report prompt generation."""
        from multi_agents.prompts.report import build_report_messages
        
        messages = build_report_messages(
            query="人工智能舆情分析",
            merged_result={"core_conclusions": ["结论1"]}
        )
        
        assert len(messages) >= 2
        full_content = str(messages)
        assert "人工智能舆情分析" in full_content
    
    def test_report_prompt_format_requirements(self):
        """Test that report prompt includes format requirements."""
        from multi_agents.prompts.report import build_report_messages
        
        messages = build_report_messages(
            query="测试",
            merged_result={"core_conclusions": []}
        )
        
        full_content = str(messages).lower()
        # Should mention markdown or report format
        assert "markdown" in full_content or "报告" in str(messages) or "格式" in str(messages)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
