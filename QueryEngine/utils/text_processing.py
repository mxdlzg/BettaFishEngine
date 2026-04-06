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
    
    策略：
    1. 找到真正的报告标题（带有中文或关键词的一级标题，后面是干净内容）
    2. 从该标题开始截取内容
    3. 清理残留的思考过程
    
    Args:
        text: 原始LLM输出
        
    Returns:
        清理后的Markdown报告
    """
    if not text:
        return ""
    
    # 如果报告很短，可能是只有结语，直接返回
    if len(text) < 500:
        return text
    
    lines = text.split('\n')
    
    # 垃圾内容特征
    garbage_markers = [
        '"type":', '"properties":', '"items":', '"schema"',
        'This matches', 'The instruction', '*However*', 'I will',
        'Let me analyze', 'Looking at', 'If I output', 'Given the',
        '*Wait', '*Actually', 'Since the', 'Self-Correction',
        'Final check', '**Plan', '**Drafting', '1. Title:',
        '2. Structure:', '3. Content:', '4. Length:', "Let's write."
    ]
    
    # 真正报告标题的特征（必须包含中文或特定关键词）
    report_title_keywords = [
        '【', '】', '报告', '分析', '调查', '研究', '舆情',
        '冲突', '态势', '评估', '综述', '观察'
    ]
    
    # 找所有一级标题
    title_positions = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith('# ') and not stripped.startswith('## '):
            title_content = stripped[2:]  # 去掉 "# "
            # 检查标题是否包含报告关键词
            has_keyword = any(kw in title_content for kw in report_title_keywords)
            # 检查标题是否包含中文
            has_chinese = any('\u4e00' <= c <= '\u9fff' for c in title_content)
            title_positions.append((i, has_keyword or has_chinese))
    
    # 策略1: 找第一个有关键词的干净标题
    real_start = -1
    for title_pos, has_keyword in title_positions:
        if not has_keyword:
            continue  # 跳过无关键词的标题（如纯 "# 深度研究报告"）
        
        title_line = lines[title_pos]
        
        # 检查后面15行内容是否干净
        is_clean = True
        found_content = False
        for j in range(title_pos + 1, min(title_pos + 15, len(lines))):
            check_line = lines[j].strip()
            if not check_line:
                continue
            
            # 检测JSON块开始
            if check_line.startswith('{'):
                is_clean = False
                break
            
            # 检测垃圾标记
            for marker in garbage_markers:
                if marker in check_line:
                    is_clean = False
                    break
            
            if not is_clean:
                break
            
            # 如果遇到正常报告内容，标记为干净
            if check_line.startswith('**报告') or check_line.startswith('**密级'):
                found_content = True
                break
            if check_line.startswith('##'):
                found_content = True
                break
            if check_line == '---':
                found_content = True
                break
        
        if is_clean and found_content:
            real_start = title_pos
            break
    
    # 策略2: 如果没找到，放宽条件找任何有关键词的标题
    if real_start == -1:
        for title_pos, has_keyword in title_positions:
            if has_keyword:
                # 只要标题本身看起来像报告标题就行
                real_start = title_pos
                break
    
    # 策略3: 如果仍然没找到，找内容标记
    if real_start == -1:
        content_markers = [
            '**报告生成时间', '**报告负责人', '**密级',
            '## 核心要点', '## 关键事实', '## 一、',
            '## 摘要', '## 概述', '## 执行摘要'
        ]
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            for marker in content_markers:
                if stripped.startswith(marker):
                    # 向前找一级标题
                    for j in range(i - 1, max(i - 30, -1), -1):
                        if lines[j].strip().startswith('# '):
                            real_start = j
                            break
                    if real_start == -1:
                        real_start = i
                    break
            if real_start != -1:
                break
    
    # 截取报告内容
    if real_start != -1 and real_start > 0:
        result_lines = lines[real_start:]
        result = '\n'.join(result_lines)
    else:
        # 没找到明确的开始位置，返回原内容（可能不需要清理）
        result = text
    
    # 后处理：清理残留的思考过程（只处理明确的英文思考内容）
    cleanup_patterns = [
        r'^This matches the data[\s\S]*?(?=\n#|\n\*\*|\Z)',
        r'^The instruction "[\s\S]*?(?=\n#|\n\*\*|\Z)',
        r'^\*However\*[\s\S]*?(?=\n#|\n\*\*|\Z)',
        r'^I will follow[\s\S]*?(?=\n#|\n\*\*|\Z)',
        r'^Let\'s write\.\s*',
    ]
    
    for pattern in cleanup_patterns:
        result = re.sub(pattern, '', result, flags=re.MULTILINE | re.IGNORECASE)
    
    # 清理多余的空行
    result = re.sub(r'\n{4,}', '\n\n\n', result)
    result = result.lstrip('\n')
    
    return result.strip()


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
        for block in reversed(json_blocks):
            try:
                json.loads(block)
                return block
            except:
                continue
        return json_blocks[-1]
    
    # 方法2: 查找 ```json 块
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

    return cleaned.strip()


def extract_clean_response(text: str) -> Dict[str, Any]:
    """
    提取并清理响应中的JSON内容

    Args:
        text: 原始响应文本

    Returns:
        解析后的JSON字典
    """
    cleaned_text = clean_json_tags(text)
    cleaned_text = remove_reasoning_from_output(cleaned_text)

    try:
        return json.loads(cleaned_text)
    except JSONDecodeError:
        pass

    fixed_text = fix_incomplete_json(cleaned_text)
    if fixed_text:
        try:
            return json.loads(fixed_text)
        except JSONDecodeError:
            pass

    json_pattern = r'\{.*\}'
    match = re.search(json_pattern, cleaned_text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except JSONDecodeError:
            pass

    return {}


def fix_incomplete_json(text: str) -> str:
    """
    尝试修复不完整的JSON字符串
    
    Args:
        text: 可能不完整的JSON字符串
        
    Returns:
        修复后的JSON字符串或原字符串
    """
    if not text:
        return text
    
    text = text.strip()
    
    # 计算未闭合的括号
    open_braces = text.count('{') - text.count('}')
    open_brackets = text.count('[') - text.count(']')
    
    # 如果已经平衡，直接返回
    if open_braces == 0 and open_brackets == 0:
        return text
    
    # 添加缺失的闭合括号
    text += ']' * open_brackets
    text += '}' * open_braces
    
    return text


def extract_json_from_text(text: str) -> List[Dict[str, Any]]:
    """
    从文本中提取所有JSON对象
    
    Args:
        text: 包含JSON的文本
        
    Returns:
        JSON对象列表
    """
    results = []
    
    # 查找所有JSON对象
    pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
    matches = re.findall(pattern, text)
    
    for match in matches:
        try:
            obj = json.loads(match)
            results.append(obj)
        except JSONDecodeError:
            continue
    
    return results


def validate_json_structure(obj: Dict[str, Any], required_keys: List[str]) -> bool:
    """
    验证JSON对象是否包含必需的键
    
    Args:
        obj: JSON对象
        required_keys: 必需的键列表
        
    Returns:
        是否有效
    """
    if not isinstance(obj, dict):
        return False
    
    return all(key in obj for key in required_keys)


def sanitize_text_for_json(text: str) -> str:
    """
    净化文本以便安全地嵌入JSON
    
    Args:
        text: 原始文本
        
    Returns:
        净化后的文本
    """
    if not text:
        return ""
    
    # 转义特殊字符
    text = text.replace('\\', '\\\\')
    text = text.replace('"', '\\"')
    text = text.replace('\n', '\\n')
    text = text.replace('\r', '\\r')
    text = text.replace('\t', '\\t')
    
    return text


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """
    截断文本到指定长度
    
    Args:
        text: 原始文本
        max_length: 最大长度
        suffix: 截断后缀
        
    Returns:
        截断后的文本
    """
    if not text or len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def split_into_chunks(text: str, chunk_size: int, overlap: int = 0) -> List[str]:
    """
    将文本分割成固定大小的块
    
    Args:
        text: 原始文本
        chunk_size: 每块大小
        overlap: 重叠大小
        
    Returns:
        文本块列表
    """
    if not text:
        return []
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap
        
        # 防止无限循环
        if overlap >= chunk_size:
            break
    
    return chunks


def count_tokens_estimate(text: str) -> int:
    """
    估算文本的token数量（粗略估计）
    
    Args:
        text: 文本
        
    Returns:
        估计的token数量
    """
    if not text:
        return 0
    
    # 粗略估计：中文按字符计算，英文按词计算
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
    english_words = len(re.findall(r'[a-zA-Z]+', text))
    
    # 大约4个英文字符为1个token
    return chinese_chars + english_words


def normalize_whitespace(text: str) -> str:
    """
    标准化文本中的空白字符
    
    Args:
        text: 原始文本
        
    Returns:
        标准化后的文本
    """
    if not text:
        return ""
    
    # 将多个空白字符替换为单个空格
    text = re.sub(r'[ \t]+', ' ', text)
    
    # 将多个换行替换为双换行
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text.strip()


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
    
    if last_space > max_length * 0.8:
        return truncated[:last_space] + "..."
    else:
        return truncated + "..."


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
        current_query = ""
        if search_results:
            current_query = "搜索查询"
        
        state.paragraphs[paragraph_index].research.add_search_results(
            current_query, search_results
        )
    
    return state


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
