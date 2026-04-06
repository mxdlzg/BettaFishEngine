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


def clean_markdown_report(text: str) -> str:
    """
    清理Markdown报告中的LLM思考过程和JSON schema垃圾内容
    专门针对reasoning模型输出的报告格式化（增强版）
    
    Args:
        text: 原始LLM输出
        
    Returns:
        清理后的Markdown报告
    """
    if not text:
        return ""
    
    # ========== 预处理：移除已知的垃圾模式 ==========
    
    # 移除 JSON schema 块（通常在开头）
    # 匹配 { "type": "array" ... } 或 { "type": "object" ... } 格式的 JSON schema
    json_schema_pattern = r'^\s*\{\s*\n?\s*"type"\s*:\s*"(?:array|object)"[\s\S]*?\}\s*\n'
    text = re.sub(json_schema_pattern, '', text, flags=re.MULTILINE)
    
    # 移除内联的 JSON schema（在标题同行）
    # 如 "# 深度研究报告{ "type": "array" ...}"
    inline_schema_pattern = r'(\#[^\n{]*)\{[^}]*"type"\s*:\s*"(?:array|object)"[^}]*\}'
    text = re.sub(inline_schema_pattern, r'\1', text)
    
    # 移除思考过程段落（英文）
    thinking_patterns = [
        r'This matches the data structure[\s\S]*?(?=\n\n#|\n\n\*\*|\Z)',
        r'The instruction "You will[\s\S]*?(?=\n\n#|\n\n\*\*|\Z)',
        r'\*However\*,? the \*System[\s\S]*?(?=\n\n#|\n\n\*\*|\Z)',
        r'I will follow the System[\s\S]*?(?=\n\n#|\n\n\*\*|\Z)',
        r'I will ignore that specific[\s\S]*?(?=\n\n#|\n\n\*\*|\Z)',
        r'Given the role "Senior[\s\S]*?(?=\n\n#|\n\n\*\*|\Z)',
        r'If I output JSON[\s\S]*?(?=\n\n#|\n\n\*\*|\Z)',
        r'This looks like \*I\*[\s\S]*?(?=\n\n#|\n\n\*\*|\Z)',
        r'`"You will be given[\s\S]*?(?=\n\n#|\n\n\*\*|\Z)',
        r"Let's write\.\s*\n",
        r'\d+\.\s+Title:[\s\S]*?(?=\n\n#|\Z)',
        r'\d+\.\s+Structure:[\s\S]*?(?=\n\n#|\Z)',
        r'\d+\.\s+Content:[\s\S]*?(?=\n\n#|\Z)',
        r'\d+\.\s+Length:[\s\S]*?(?=\n\n#|\Z)',
    ]
    
    for pattern in thinking_patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.DOTALL)
    
    lines = text.split('\n')
    
    # ========== 策略0: 检查 "标题 + 垃圾 + 真正报告" 模式 ==========
    title_indices = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith('#') and not stripped.startswith('##'):
            title_indices.append(i)
    
    # 垃圾内容特征
    garbage_markers = [
        'This matches', 'The instruction', '*However', 'I will', 'Let me',
        'Looking at', 'If I output', 'Given the', '*Wait', '*Actually',
        'Since the', '"type":', '"properties":', '"items":', '"schema"',
        'Self-Correction', 'Final check', '**Plan', '**Drafting',
    ]
    
    real_report_start = -1
    for title_idx in title_indices:
        is_followed_by_garbage = False
        
        for j in range(title_idx + 1, min(title_idx + 8, len(lines))):
            check_line = lines[j].strip()
            if not check_line:
                continue
            
            # 检测 JSON schema 特征
            if check_line.startswith('{') or check_line.startswith('"type"'):
                is_followed_by_garbage = True
                break
            
            # 检测思考过程特征
            for marker in garbage_markers:
                if marker in check_line:
                    is_followed_by_garbage = True
                    break
            
            if is_followed_by_garbage:
                break
            
            # 如果后面是正常内容，这是好的标题
            if check_line == '---' or check_line.startswith('**报告'):
                break
            # 检查是否有中文内容（真正的报告内容）
            if any('\u4e00' <= c <= '\u9fff' for c in check_line):
                # 确保不是中文思考过程
                chinese_thinking = ['好的', '让我', '首先', '我需要', '用户', '分析']
                is_chinese_thinking = any(ct in check_line for ct in chinese_thinking)
                if not is_chinese_thinking:
                    break
        
        if not is_followed_by_garbage:
            real_report_start = title_idx
            break
    
    if real_report_start != -1:
        cleaned_lines = lines[real_report_start:]
        result = '\n'.join(cleaned_lines)
        # 最终清理
        return _final_cleanup(result)
    
    # ========== 策略1: 寻找真正的报告标题 ==========
    report_title_patterns = [
        r'^#\s+【.*?】',
        r'^#\s+深度(?:研究|分析|调查)报告',
        r'^#\s+\d{4}年.*?(?:分析|报告|调查)',
        r'^#\s+(?:关于|针对|对于).*?(?:的)?(?:分析|报告)',
        r'^#\s+新闻分析',
        r'^#\s+舆情(?:分析|报告)',
        r'^#\s+.*?(?:全面|综合).*?(?:分析|报告)',
    ]
    
    report_start_index = -1
    
    for i, line in enumerate(lines):
        line_stripped = line.strip()
        for pattern in report_title_patterns:
            if re.match(pattern, line_stripped):
                has_garbage = False
                for j in range(i + 1, min(i + 5, len(lines))):
                    check = lines[j].strip()
                    if check.startswith('{') or '"type":' in check:
                        has_garbage = True
                        break
                    for marker in garbage_markers[:10]:
                        if check.startswith(marker):
                            has_garbage = True
                            break
                
                if not has_garbage:
                    report_start_index = i
                    break
        if report_start_index != -1:
            break
    
    if report_start_index != -1:
        cleaned_lines = lines[report_start_index:]
        result = '\n'.join(cleaned_lines)
        return _final_cleanup(result)
    
    # ========== 策略2: 查找内容标记 ==========
    content_markers = [
        '**报告生成时间',
        '**报告负责人',
        '**密级',
        '## 核心要点',
        '## 关键事实',
        '## 一、',
        '## 1.',
        '## 摘要',
        '## 概述',
    ]
    
    for i, line in enumerate(lines):
        line_stripped = line.strip()
        for marker in content_markers:
            if line_stripped.startswith(marker):
                # 往前找标题
                for j in range(i - 1, max(i - 15, -1), -1):
                    prev_line = lines[j].strip()
                    if prev_line.startswith('#') and not prev_line.startswith('##'):
                        # 检查这个标题到当前位置之间是否有垃圾
                        has_garbage = False
                        for k in range(j + 1, i):
                            check = lines[k].strip()
                            if '"type":' in check or check.startswith('{'):
                                has_garbage = True
                                break
                        
                        if not has_garbage:
                            report_start_index = j
                            break
                
                if report_start_index == -1:
                    report_start_index = i
                break
        if report_start_index != -1:
            break
    
    if report_start_index != -1:
        cleaned_lines = lines[report_start_index:]
        result = '\n'.join(cleaned_lines)
        return _final_cleanup(result)
    
    # ========== 策略3: 兜底 - 直接清理垃圾 ==========
    result = text
    return _final_cleanup(result)


def _final_cleanup(text: str) -> str:
    """最终清理：移除残留的垃圾内容"""
    if not text:
        return ""
    
    # 移除残留的英文思考过程
    cleanup_patterns = [
        r'This matches[\s\S]*?\n\n',
        r'The instruction[\s\S]*?\n\n',
        r'\*However\*[\s\S]*?\n\n',
        r'I will follow[\s\S]*?\n\n',
        r'Given the role[\s\S]*?\n\n',
        r"Let's write\.\s*",
        r'\d+\.\s+Title:.*?\n',
        r'\d+\.\s+Structure:.*?\n',
        r'\d+\.\s+Content:.*?\n',
        r'\d+\.\s+Length:.*?\n',
    ]
    
    for pattern in cleanup_patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)
    
    # 清理多余的空行
    text = re.sub(r'\n{4,}', '\n\n\n', text)
    text = text.lstrip('\n')
    
    return text.strip()


def _is_garbage_line(line: str) -> bool:
    """检查一行是否是垃圾内容"""
    line = line.strip()
    if not line:
        return False
    
    # JSON schema 特征
    if line.startswith('{') or line.startswith('"type"'):
        return True
    if '"properties":' in line or '"items":' in line:
        return True
    
    # 英文思考过程特征
    thinking_markers = [
        'This matches', 'The instruction', '*However', 'I will',
        'Let me', 'Looking at', 'If I output', 'Given the',
        '*Wait', '*Actually', 'Since the', 'Self-Correction',
    ]
    
    for marker in thinking_markers:
        if line.startswith(marker):
            return True
    
    return False


# 保持向后兼容的旧函数名
def clean_markdown_report_legacy(text: str) -> str:
    """旧版清理函数（保持向后兼容）"""
    return clean_markdown_report(text)


# ========== 以下是原来的策略2代码，已整合到上面 ==========

def _clean_markdown_report_strategy2(lines: list, report_start_index: int) -> int:
    """策略2: 如果没有找到特定标题模式，查找任何 Markdown 标题"""
    if report_start_index != -1:
        return report_start_index
    
    thinking_markers = [
        'This matches', 'The instruction', '*However*', '*Wait',
        'I will', 'Let me', 'Looking at', '*Actually',
        '**Plan', '**Drafting', '**Execution', '*Decision',
        'If I output', 'Given the', 'I must', 'I should',
        'The', 'This', 'If', 'Given', 'Since', 'So',
        '*Self-Correction', '*Final check', '*Wait,',
    ]
    
    for i, line in enumerate(lines):
        line_stripped = line.strip()
        
        if not line_stripped:
            continue
        
        if line_stripped.startswith('{') or line_stripped.startswith('"'):
            continue
        if '"type":' in line_stripped or '"properties":' in line_stripped:
            continue
        if '"items":' in line_stripped or '"schema"' in line_stripped.lower():
            continue
        
        is_thinking = False
            for marker in thinking_markers:
                if line_stripped.startswith(marker):
                    is_thinking = True
                    break
            
            if is_thinking:
                continue
            
            # 检查是否是有效的 Markdown 标题（以#开头）
            if line_stripped.startswith('#'):
                # 确保标题后面有实际内容（不是空标题或 JSON 描述）
                title_content = line_stripped.lstrip('#').strip()
                if title_content and not title_content.startswith('{'):
                    # 验证后面不是垃圾
                    has_garbage = False
                    for j in range(i + 1, min(i + 3, len(lines))):
                        check = lines[j].strip() if j < len(lines) else ""
                        if check.startswith('{') or '"type":' in check:
                            has_garbage = True
                            break
                    
                    if has_garbage:
                        continue
                    
                    # 包含中文字符 或 以常见报告关键词开头
                    has_chinese = any('\u4e00' <= c <= '\u9fff' for c in title_content)
                    report_keywords = ['报告', '分析', '调查', '研究', '核心', '要点', 
                                       '摘要', '背景', '事件', '结论', '建议', 'Report',
                                       'Analysis', 'Summary', '概述', '生成时间']
                    has_report_keyword = any(kw in title_content for kw in report_keywords)
                    
                    if has_chinese or has_report_keyword:
                        report_start_index = i
                        break
    
    # 策略3: 查找特定的报告内容标记
    if report_start_index == -1:
        # 查找常见的报告内容开始标记
        content_markers = [
            '**报告生成时间',
            '**报告负责人',
            '**密级',
            '## 核心要点',
            '## 关键事实',
            '## 一、',
            '## 1.',
        ]
        
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            for marker in content_markers:
                if line_stripped.startswith(marker):
                    # 往前找标题
                    for j in range(i - 1, max(i - 10, -1), -1):
                        if lines[j].strip().startswith('#'):
                            # 检查这个标题和当前位置之间是否有垃圾
                            has_garbage = False
                            for k in range(j + 1, i):
                                check = lines[k].strip()
                                if check.startswith('{') or '"type":' in check:
                                    has_garbage = True
                                    break
                            
                            if not has_garbage:
                                report_start_index = j
                                break
                    
                    if report_start_index == -1:
                        report_start_index = i
                    break
            if report_start_index != -1:
                break
    
    # 策略4: 如果找到开始位置，从该位置开始截取
    if report_start_index != -1:
        cleaned_lines = lines[report_start_index:]
        result = '\n'.join(cleaned_lines)
    else:
        # 如果所有策略都失败，尝试直接移除已知的垃圾模式
        result = text
        
        # 移除 JSON schema 块
        result = re.sub(r'\{\s*"type"\s*:\s*"(?:array|object)"[\s\S]*?\}\s*\n', '', result)
        
        # 移除思考过程段落（以特定标记开头的段落）
        thinking_paragraph_patterns = [
            r'This matches the data structure[\s\S]*?(?=\n\n|\n#|$)',
            r'The instruction[\s\S]*?(?=\n\n|\n#|$)',
            r'\*However\*[\s\S]*?(?=\n\n|\n#|$)',
            r'\*Wait[\s\S]*?(?=\n\n|\n#|$)',
            r'I will follow[\s\S]*?(?=\n\n|\n#|$)',
            r'Let me[\s\S]*?(?=\n\n|\n#|$)',
            r'Looking at[\s\S]*?(?=\n\n|\n#|$)',
            r'\*Actually[\s\S]*?(?=\n\n|\n#|$)',
            r'Self-Correction[\s\S]*?(?=\n\n|\n#|$)',
        ]
        
        for pattern in thinking_paragraph_patterns:
            result = re.sub(pattern, '', result, flags=re.IGNORECASE)
    
    # 清理多余的空行（保留最多2个连续空行）
    result = re.sub(r'\n{4,}', '\n\n\n', result)
    
    # 清理开头的空行
    result = result.lstrip('\n')
    
    return result.strip()


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
