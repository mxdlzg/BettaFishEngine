# -*- coding: utf-8 -*-
"""Tests for artifacts management."""

import pytest
import os
import tempfile
from pathlib import Path


class TestArtifactsBasics:
    """Test suite for artifacts management."""
    
    def test_ensure_task_dir(self):
        """Test that task directory is created."""
        from multi_agents.tools.artifacts import ensure_task_dir
        
        with tempfile.TemporaryDirectory() as tmpdir:
            task_dir = ensure_task_dir(base_dir=Path(tmpdir), task_id="test-001")
            
            assert task_dir.exists()
            assert "test-001" in str(task_dir)
    
    def test_write_text_file(self):
        """Test writing text file."""
        from multi_agents.tools.artifacts import write_text_file
        
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "test.txt"
            write_text_file(filepath, "Hello, world!")
            
            assert filepath.exists()
            assert filepath.read_text() == "Hello, world!"
    
    def test_add_file_to_state(self):
        """Test adding file to state."""
        from multi_agents.tools.artifacts import add_file_to_state
        
        state = {"files": {}}
        
        new_state = add_file_to_state(
            state,
            name="report.md",
            path="/path/to/report.md",
            media_type="text/markdown"
        )
        
        assert "report.md" in new_state["files"]


class TestFileOperations:
    """Test actual file operations."""
    
    def test_save_to_task_dir(self):
        """Test saving content to task directory."""
        from multi_agents.tools.artifacts import ensure_task_dir, write_text_file
        
        with tempfile.TemporaryDirectory() as tmpdir:
            task_dir = ensure_task_dir(base_dir=Path(tmpdir), task_id="test-002")
            
            content = "# Test Report\n\nThis is a test."
            filepath = task_dir / "report.md"
            write_text_file(filepath, content)
            
            assert filepath.exists()
            assert filepath.read_text() == content
    
    def test_get_media_type(self):
        """Test media type detection."""
        from multi_agents.tools.artifacts import MEDIA_TYPES
        
        assert MEDIA_TYPES[".md"] == "text/markdown"
        assert MEDIA_TYPES[".html"] == "text/html"
        assert MEDIA_TYPES[".pdf"] == "application/pdf"


class TestURLGeneration:
    """Test public URL generation for artifacts."""
    
    def test_generate_public_url(self):
        """Test generating public URL for artifact."""
        from multi_agents.tools.artifacts import build_public_url
        
        url = build_public_url(
            filename="report.pdf",
            task_id="test-001",
            base_url="http://example.com/outputs"
        )
        
        assert "report.pdf" in url
        assert "test-001" in url
    
    def test_url_without_task_prefix(self):
        """Test URL generation without task prefix."""
        from multi_agents.tools.artifacts import build_public_url
        
        url = build_public_url(
            filename="report.pdf",
            base_url="http://example.com/outputs"
        )
        
        assert "report.pdf" in url


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
