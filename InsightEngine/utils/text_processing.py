"""
文本处理工具函数
用于清理LLM输出、解析JSON等
"""

import re
import json
from typing import Dict, Any, List
from json.decoder import JSONDecodeError


def clean_json_tags(text: str) -> str:
    """
    清理文本中的JSON标签
    
    Args:
        text: 原始文本
        
    Returns:
        清理后的文本
    """
    # 移除```json 和 ```标签
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*$', '', text)
    text = re.sub(r'```', '', text)
    
    return text.strip()


def clean_markdown_tags(text: str) -> str:
    """
    清理文本中的Markdown标签
    
    Args:
        text: 原始文本
        
    Returns:
        清理后的文本
    """
    # 移除```markdown 和 ```标签
    text = re.sub(r'```markdown\s*', '', text)
    text = re.sub(r'```\s*$', '', text)
    text = re.sub(r'```', '', text)
    
    return text.strip()


def remove_reasoning_from_output(text: str) -> str:
    """
    移除输出中的推理过程文本（增强版）
    专门处理reasoning模型输出的复杂思维过程
    
    Args:
        text: 原始文本
        
    Returns:
        清理后的文本
    """
    if not text:
        return ""
    
    # 首先尝试找到最终的JSON输出
    # reasoning模型通常会在思维过程后输出最终的JSON
    
    # 方法1: 找最后一个完整的JSON对象或数组
    json_blocks = []
    brace_count = 0
    bracket_count = 0
    current_block = ""
    in_json = False
    
    for char in text:
        if char == '{':
            if not in_json:
                in_json = True
                current_block = ""
            brace_count += 1
            current_block += char
        elif char == '[' and not in_json:
            in_json = True
            bracket_count += 1
            current_block = char
        elif char == ']' and in_json and bracket_count > 0:
            bracket_count -= 1
            current_block += char
            if bracket_count == 0 and brace_count == 0:
                json_blocks.append(current_block)
                current_block = ""
                in_json = False
        elif char == '}':
            brace_count -= 1
            current_block += char
            if brace_count == 0 and bracket_count == 0:
                json_blocks.append(current_block)
                current_block = ""
                in_json = False
        elif in_json:
            current_block += char
    
    # 如果找到了JSON块，返回最后一个（通常是最终答案）
    if json_blocks:
        # 验证最后一个块是否是有效JSON
        for block in reversed(json_blocks):
            try:
                json.loads(block)
                return block
            except:
                continue
        # 如果都无效，返回最后一个块尝试修复
        return json_blocks[-1]
    
    # 方法2: 查找明确的JSON标记
    # 查找 ```json 块
    json_block_match = re.search(r'```json\s*([\s\S]*?)\s*```', text)
    if json_block_match:
        return json_block_match.group(1).strip()
    
    # 方法3: 移除已知的思维过程标记
    thinking_markers = [
        r'\*\*Plan:\*\*.*?(?=\{|\[|$)',
        r'\*\*Drafting.*?\*\*.*?(?=\{|\[|$)',
        r'\*\*Execution.*?\*\*.*?(?=\{|\[|$)',
        r'\*Wait,.*?(?=\{|\[|$)',
        r'\*Actually,.*?(?=\{|\[|$)',
        r'Thinking Process:.*?(?=\{|\[|$)',
        r'Self-Correction.*?(?=\{|\[|$)',
        r'\*Decision:.*?(?=\{|\[|$)',
        r'\*Final.*?(?=\{|\[|$)',
        r'Looking at.*?(?=\{|\[|$)',
        r'I need to.*?(?=\{|\[|$)',
        r'Let me.*?(?=\{|\[|$)',
    ]
    
    cleaned = text
    for pattern in thinking_markers:
        cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE | re.DOTALL)
    
    # 方法4: 查找JSON开始位置
    json_start = -1
    for i, char in enumerate(cleaned):
        if char in '{[':
            # 检查这是否像是实际的JSON开始（不是思维过程中的括号）
            # 通过检查后续内容是否有JSON结构特征
            remaining = cleaned[i:]
            if re.match(r'^\s*[\{\[][\s\S]*[\}\]]\s*$', remaining[:min(200, len(remaining))]):
                json_start = i
                break
            elif char == '{' and '"' in remaining[:50]:
                json_start = i
                break
            elif char == '[' and '{' in remaining[:50]:
                json_start = i
                break
    
    if json_start != -1:
        return cleaned[json_start:].strip()
    
    # 如果所有方法都失败，返回清理后的文本
    return cleaned.strip()


def extract_clean_response(text: str) -> Dict[str, Any]:
    """
    提取并清理响应中的JSON内容
    
    Args:
        text: 原始响应文本
        
    Returns:
        解析后的JSON字典
    """
    # 清理文本
    cleaned_text = clean_json_tags(text)
    cleaned_text = remove_reasoning_from_output(cleaned_text)
    
    # 尝试直接解析
    try:
        return json.loads(cleaned_text)
    except JSONDecodeError:
        pass
    
    # 尝试修复不完整的JSON
    fixed_text = fix_incomplete_json(cleaned_text)
    if fixed_text:
        try:
            return json.loads(fixed_text)
        except JSONDecodeError:
            pass
    
    # 尝试查找JSON对象
    json_pattern = r'\{.*\}'
    match = re.search(json_pattern, cleaned_text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except JSONDecodeError:
            pass
    
    # 尝试查找JSON数组
    array_pattern = r'\[.*\]'
    match = re.search(array_pattern, cleaned_text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except JSONDecodeError:
            pass
    
    # 如果所有方法都失败，返回错误信息
    print(f"无法解析JSON响应: {cleaned_text[:200]}...")
    return {"error": "JSON解析失败", "raw_text": cleaned_text}


def fix_incomplete_json(text: str) -> str:
    """
    修复不完整的JSON响应
    
    Args:
        text: 原始文本
        
    Returns:
        修复后的JSON文本，如果无法修复则返回空字符串
    """
    # 移除多余的逗号和空白
    text = re.sub(r',\s*}', '}', text)
    text = re.sub(r',\s*]', ']', text)
    
    # 检查是否已经是有效的JSON
    try:
        json.loads(text)
        return text
    except JSONDecodeError:
        pass
    
    # 检查是否缺少开头的数组符号
    if text.strip().startswith('{') and not text.strip().startswith('['):
        # 如果以对象开始，尝试包装成数组
        if text.count('{') > 1:
            # 多个对象，包装成数组
            text = '[' + text + ']'
        else:
            # 单个对象，包装成数组
            text = '[' + text + ']'
    
    # 检查是否缺少结尾的数组符号
    if text.strip().endswith('}') and not text.strip().endswith(']'):
        # 如果以对象结束，尝试包装成数组
        if text.count('}') > 1:
            # 多个对象，包装成数组
            text = '[' + text + ']'
        else:
            # 单个对象，包装成数组
            text = '[' + text + ']'
    
    # 检查括号是否匹配
    open_braces = text.count('{')
    close_braces = text.count('}')
    open_brackets = text.count('[')
    close_brackets = text.count(']')
    
    # 修复不匹配的括号
    if open_braces > close_braces:
        text += '}' * (open_braces - close_braces)
    if open_brackets > close_brackets:
        text += ']' * (open_brackets - close_brackets)
    
    # 验证修复后的JSON是否有效
    try:
        json.loads(text)
        return text
    except JSONDecodeError:
        # 如果仍然无效，尝试更激进的修复
        return fix_aggressive_json(text)


def fix_aggressive_json(text: str) -> str:
    """
    更激进的JSON修复方法
    
    Args:
        text: 原始文本
        
    Returns:
        修复后的JSON文本
    """
    # 查找所有可能的JSON对象
    objects = re.findall(r'\{[^{}]*\}', text)
    
    if len(objects) >= 2:
        # 如果有多个对象，包装成数组
        return '[' + ','.join(objects) + ']'
    elif len(objects) == 1:
        # 如果只有一个对象，包装成数组
        return '[' + objects[0] + ']'
    else:
        # 如果没有找到对象，返回空数组
        return '[]'


def update_state_with_search_results(search_results: List[Dict[str, Any]], 
                                   paragraph_index: int, state: Any) -> Any:
    """
    将搜索结果更新到状态中
    
    Args:
        search_results: 搜索结果列表
        paragraph_index: 段落索引
        state: 状态对象
        
    Returns:
        更新后的状态对象
    """
    if 0 <= paragraph_index < len(state.paragraphs):
        # 获取最后一次搜索的查询（假设是当前查询）
        current_query = ""
        if search_results:
            # 从搜索结果推断查询（这里需要改进以获取实际查询）
            current_query = "搜索查询"
        
        # 添加搜索结果到状态
        state.paragraphs[paragraph_index].research.add_search_results(
            current_query, search_results
        )
    
    return state


def validate_json_schema(data: Dict[str, Any], required_fields: List[str]) -> bool:
    """
    验证JSON数据是否包含必需字段
    
    Args:
        data: 要验证的数据
        required_fields: 必需字段列表
        
    Returns:
        验证是否通过
    """
    return all(field in data for field in required_fields)


def truncate_content(content: str, max_length: int = 20000) -> str:
    """
    截断内容到指定长度
    
    Args:
        content: 原始内容
        max_length: 最大长度
        
    Returns:
        截断后的内容
    """
    if len(content) <= max_length:
        return content
    
    # 尝试在单词边界截断
    truncated = content[:max_length]
    last_space = truncated.rfind(' ')
    
    if last_space > max_length * 0.8:  # 如果最后一个空格位置合理
        return truncated[:last_space] + "..."
    else:
        return truncated + "..."


def format_search_results_for_prompt(search_results: List[Dict[str, Any]], 
                                   max_length: int = 20000) -> List[str]:
    """
    格式化搜索结果用于提示词
    
    Args:
        search_results: 搜索结果列表
        max_length: 每个结果的最大长度
        
    Returns:
        格式化后的内容列表
    """
    formatted_results = []
    
    for result in search_results:
        content = result.get('content', '')
        if content:
            truncated_content = truncate_content(content, max_length)
            formatted_results.append(truncated_content)
    
    return formatted_results
