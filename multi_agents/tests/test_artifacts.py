# -*- coding: utf-8 -*-
"""Tests for artifacts management."""

import pytest
import os
import tempfile
from pathlib import Path


class TestArtifactsManager:
    """Test suite for artifacts management."""
    
    def test_create_artifact_entry(self):
        """Test creating artifact metadata entry."""
        from multi_agents.tools.artifacts import ArtifactsManager
        
        manager = ArtifactsManager()
        
        entry = manager.create_entry(
            filename="report.md",
            content_type="text/markdown",
            size=1024
        )
        
        assert entry["filename"] == "report.md"
        assert entry["content_type"] == "text/markdown"
        assert entry["size"] == 1024
        assert "created_at" in entry
    
    def test_add_file_to_state(self):
        """Test adding file reference to state."""
        from multi_agents.tools.artifacts import add_file_to_state
        
        state = {"files": {}}
        
        new_state = add_file_to_state(
            state,
            "report.md",
            "/path/to/report.md",
            "text/markdown"
        )
        
        assert "report.md" in new_state["files"]
        assert new_state["files"]["report.md"]["path"] == "/path/to/report.md"
    
    def test_multiple_files(self):
        """Test adding multiple files to state."""
        from multi_agents.tools.artifacts import add_file_to_state
        
        state = {"files": {}}
        
        state = add_file_to_state(state, "report.md", "/path/report.md", "text/markdown")
        state = add_file_to_state(state, "report.html", "/path/report.html", "text/html")
        state = add_file_to_state(state, "report.pdf", "/path/report.pdf", "application/pdf")
        
        assert len(state["files"]) == 3
        assert "report.md" in state["files"]
        assert "report.html" in state["files"]
        assert "report.pdf" in state["files"]


class TestFileOperations:
    """Test actual file operations."""
    
    def test_save_markdown_file(self):
        """Test saving markdown content to file."""
        from multi_agents.tools.artifacts import ArtifactsManager
        
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ArtifactsManager(output_dir=tmpdir)
            
            content = "# Test Report\n\nThis is a test."
            filepath = manager.save_markdown(content, "test_report.md")
            
            assert os.path.exists(filepath)
            with open(filepath, "r", encoding="utf-8") as f:
                saved_content = f.read()
            assert saved_content == content
    
    def test_save_html_file(self):
        """Test saving HTML content to file."""
        from multi_agents.tools.artifacts import ArtifactsManager
        
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ArtifactsManager(output_dir=tmpdir)
            
            content = "<html><body><h1>Test</h1></body></html>"
            filepath = manager.save_html(content, "test_report.html")
            
            assert os.path.exists(filepath)
            assert filepath.endswith(".html")
    
    def test_ensure_output_directory(self):
        """Test that output directory is created if not exists."""
        from multi_agents.tools.artifacts import ArtifactsManager
        
        with tempfile.TemporaryDirectory() as tmpdir:
            nested_dir = os.path.join(tmpdir, "nested", "output")
            manager = ArtifactsManager(output_dir=nested_dir)
            
            manager.ensure_output_dir()
            
            assert os.path.exists(nested_dir)


class TestURLGeneration:
    """Test public URL generation for artifacts."""
    
    def test_generate_public_url(self):
        """Test generating public URL for artifact."""
        from multi_agents.tools.artifacts import ArtifactsManager
        
        manager = ArtifactsManager(
            output_dir="/data/outputs",
            base_url="http://example.com/outputs"
        )
        
        url = manager.get_public_url("report.pdf")
        
        assert url == "http://example.com/outputs/report.pdf"
    
    def test_generate_url_with_task_prefix(self):
        """Test URL generation with task ID prefix."""
        from multi_agents.tools.artifacts import ArtifactsManager
        
        manager = ArtifactsManager(
            output_dir="/data/outputs",
            base_url="http://example.com/outputs"
        )
        
        url = manager.get_public_url("task-001/report.pdf")
        
        assert url == "http://example.com/outputs/task-001/report.pdf"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
