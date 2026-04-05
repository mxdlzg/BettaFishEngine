# -*- coding: utf-8 -*-
"""Tests for prompt templates."""

import pytest


class TestIntakePrompt:
    """Test suite for intake prompt."""
    
    def test_prompt_generation(self):
        """Test intake prompt generation."""
        from multi_agents.prompts.intake import get_intake_prompt
        
        prompt = get_intake_prompt("分析人工智能舆情")
        
        assert "分析人工智能舆情" in prompt
        assert len(prompt) > 0
    
    def test_prompt_with_special_characters(self):
        """Test prompt handles special characters."""
        from multi_agents.prompts.intake import get_intake_prompt
        
        query = "分析《人工智能》相关'舆情'"
        prompt = get_intake_prompt(query)
        
        assert "人工智能" in prompt


class TestPlannerPrompt:
    """Test suite for planner prompt."""
    
    def test_prompt_generation(self):
        """Test planner prompt generation."""
        from multi_agents.prompts.planner import get_planner_prompt
        
        prompt = get_planner_prompt(
            query="人工智能发展趋势",
            context="近期AI相关新闻增多"
        )
        
        assert "人工智能发展趋势" in prompt
        assert "近期AI相关新闻增多" in prompt
    
    def test_prompt_without_context(self):
        """Test planner prompt without optional context."""
        from multi_agents.prompts.planner import get_planner_prompt
        
        prompt = get_planner_prompt(query="测试查询")
        
        assert "测试查询" in prompt


class TestKBSelectorPrompt:
    """Test suite for KB selector prompt."""
    
    def test_prompt_with_kb_list(self):
        """Test KB selector prompt with KB list."""
        from multi_agents.prompts.kb_selector import get_kb_selector_prompt
        
        kb_list = [
            {"id": "kb-001", "name": "政策库", "description": "政策文档"},
            {"id": "kb-002", "name": "行业库", "description": "行业数据"},
        ]
        
        prompt = get_kb_selector_prompt(
            query="人工智能政策",
            available_kbs=kb_list
        )
        
        assert "政策库" in prompt
        assert "行业库" in prompt
        assert "人工智能政策" in prompt


class TestModeratorPrompt:
    """Test suite for moderator prompt."""
    
    def test_round_1_prompt(self):
        """Test moderator prompt for round 1."""
        from multi_agents.prompts.moderator import get_moderator_prompt
        
        prompt = get_moderator_prompt(
            round_num=1,
            query="人工智能舆情",
            previous_outputs=[]
        )
        
        assert "第1轮" in prompt or "Round 1" in prompt or "1" in prompt
    
    def test_subsequent_round_prompt(self):
        """Test moderator prompt for subsequent rounds."""
        from multi_agents.prompts.moderator import get_moderator_prompt
        
        previous = [
            {"round": 1, "summary": "初步分析结果"}
        ]
        
        prompt = get_moderator_prompt(
            round_num=2,
            query="人工智能舆情",
            previous_outputs=previous
        )
        
        assert "初步分析结果" in prompt


class TestMergePrompt:
    """Test suite for merge prompt."""
    
    def test_merge_prompt_generation(self):
        """Test merge prompt with all inputs."""
        from multi_agents.prompts.merge import get_merge_prompt
        
        prompt = get_merge_prompt(
            query="人工智能舆情",
            query_result="网络搜索结果...",
            media_result="媒体分析结果...",
            insight_result="洞察分析结果...",
            kb_result="知识库结果...",
            forum_result="论坛讨论结果..."
        )
        
        assert "网络搜索结果" in prompt
        assert "媒体分析结果" in prompt
        assert "洞察分析结果" in prompt
        assert "知识库结果" in prompt
        assert "论坛讨论结果" in prompt


class TestReportPrompt:
    """Test suite for report prompt."""
    
    def test_report_prompt_generation(self):
        """Test report prompt generation."""
        from multi_agents.prompts.report import get_report_prompt
        
        prompt = get_report_prompt(
            query="人工智能舆情分析",
            merged_analysis="综合分析内容..."
        )
        
        assert "人工智能舆情分析" in prompt
        assert "综合分析内容" in prompt
    
    def test_report_prompt_format_requirements(self):
        """Test that report prompt includes format requirements."""
        from multi_agents.prompts.report import get_report_prompt
        
        prompt = get_report_prompt(
            query="测试",
            merged_analysis="测试内容"
        )
        
        # Should mention markdown or report format
        assert "markdown" in prompt.lower() or "报告" in prompt or "格式" in prompt


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
