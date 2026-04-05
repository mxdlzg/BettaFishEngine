# -*- coding: utf-8 -*-
"""
JSON utilities for the LangGraph multi-agent system.

Provides safe JSON parsing and serialization with error recovery.
"""

import json
import re
from typing import Any, Optional, Union
from json_repair import repair_json


def safe_json_loads(text: str, default: Any = None) -> Any:
    """
    Safely parse JSON text with error recovery.
    
    Attempts multiple strategies:
    1. Direct JSON parsing
    2. Extract JSON from markdown code blocks
    3. Use json_repair library for malformed JSON
    
    Args:
        text: Text to parse as JSON
        default: Default value if parsing fails
    
    Returns:
        Parsed JSON object or default value
    """
    if not text or not isinstance(text, str):
        return default
    
    text = text.strip()
    
    # Strategy 1: Direct parsing
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # Strategy 2: Extract from markdown code blocks
    patterns = [
        r'```json\s*([\s\S]*?)\s*```',
        r'```\s*([\s\S]*?)\s*```',
        r'\{[\s\S]*\}',
        r'\[[\s\S]*\]'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            try:
                json_str = match.group(1) if '```' in pattern else match.group(0)
                return json.loads(json_str.strip())
            except json.JSONDecodeError:
                continue
    
    # Strategy 3: Use json_repair
    try:
        repaired = repair_json(text)
        if repaired:
            return json.loads(repaired)
    except Exception:
        pass
    
    return default


def safe_json_dumps(data: Any, indent: int = 2, ensure_ascii: bool = False) -> str:
    """
    Safely serialize data to JSON string.
    
    Args:
        data: Data to serialize
        indent: Indentation level (default: 2)
        ensure_ascii: Whether to escape non-ASCII characters
    
    Returns:
        JSON string or empty object string on failure
    """
    try:
        return json.dumps(data, indent=indent, ensure_ascii=ensure_ascii, default=str)
    except (TypeError, ValueError):
        return "{}"


def extract_json_from_llm_response(text: str, default: Any = None) -> Any:
    """
    Extract JSON from an LLM response that may contain additional text.
    
    Args:
        text: LLM response text
        default: Default value if extraction fails
    
    Returns:
        Extracted JSON object or default value
    """
    if not text:
        return default
    
    # Try to find JSON in the response
    result = safe_json_loads(text, None)
    if result is not None:
        return result
    
    # Try to find the first { or [ and parse from there
    for start_char, end_char in [('{', '}'), ('[', ']')]:
        start_idx = text.find(start_char)
        if start_idx != -1:
            # Find the matching end
            depth = 0
            for i, char in enumerate(text[start_idx:], start=start_idx):
                if char == start_char:
                    depth += 1
                elif char == end_char:
                    depth -= 1
                    if depth == 0:
                        json_str = text[start_idx:i+1]
                        result = safe_json_loads(json_str, None)
                        if result is not None:
                            return result
                        break
    
    return default


def merge_json_objects(*objects: dict) -> dict:
    """
    Merge multiple JSON-like dictionaries.
    
    Later objects override earlier ones for duplicate keys.
    
    Args:
        *objects: Dictionaries to merge
    
    Returns:
        Merged dictionary
    """
    result = {}
    for obj in objects:
        if isinstance(obj, dict):
            result.update(obj)
    return result


def truncate_json_string(data: Any, max_length: int = 10000) -> str:
    """
    Serialize to JSON and truncate if necessary.
    
    Args:
        data: Data to serialize
        max_length: Maximum string length
    
    Returns:
        JSON string, truncated with '...' if necessary
    """
    json_str = safe_json_dumps(data)
    if len(json_str) > max_length:
        return json_str[:max_length-3] + "..."
    return json_str
