"""
Unified OpenAI-compatible LLM client for the Query Engine, with retry support.
Uses requests library for better compatibility with various endpoints.
Enhanced with robust streaming support and connection recovery.
"""

import os
import sys
import json
import re
import time
from datetime import datetime
from typing import Any, Dict, Optional, Generator
from loguru import logger
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
utils_dir = os.path.join(project_root, "utils")
if utils_dir not in sys.path:
    sys.path.append(utils_dir)

try:
    from retry_helper import with_retry, LLM_RETRY_CONFIG
except ImportError:
    def with_retry(config=None):
        def decorator(func):
            return func
        return decorator

    LLM_RETRY_CONFIG = None


class StreamingConnectionError(Exception):
    """流式连接断开异常，包含已接收的部分数据"""
    def __init__(self, message: str, partial_content: str = ""):
        super().__init__(message)
        self.partial_content = partial_content


class LLMClient:
    """Requests-based wrapper around the OpenAI-compatible chat completion API."""

    def __init__(self, api_key: str, model_name: str, base_url: Optional[str] = None):
        if not api_key:
            raise ValueError("Query Engine LLM API key is required.")
        if not model_name:
            raise ValueError("Query Engine model name is required.")

        self.api_key = api_key
        self.base_url = base_url.rstrip('/') if base_url else "https://api.openai.com/v1"
        self.model_name = model_name
        self.provider = model_name
        timeout_fallback = os.getenv("LLM_REQUEST_TIMEOUT") or os.getenv("QUERY_ENGINE_REQUEST_TIMEOUT") or "1800"
        try:
            self.timeout = float(timeout_fallback)
        except ValueError:
            self.timeout = 1800.0
        
        # Prepare headers for requests
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Connection": "keep-alive",
            "Accept": "text/event-stream"
        }
        
        # Create a session with retry adapter for better connection handling
        self.session = requests.Session()
        
        # Configure retry strategy for transient failures
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["POST"],
            raise_on_status=False
        )
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=10,
            pool_maxsize=10
        )
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        self.session.headers.update(self.headers)

    @with_retry(LLM_RETRY_CONFIG)
    def invoke(self, system_prompt: str, user_prompt: str, **kwargs) -> str:
        """
        非流式调用LLM，返回完整响应
        
        Args:
            system_prompt: 系统提示词
            user_prompt: 用户提示词
            **kwargs: 额外参数（temperature, top_p等）
            
        Returns:
            完整的响应字符串
        """
        current_time = datetime.now().strftime("%Y年%m月%d日%H时%M分")
        time_prefix = f"今天的实际时间是{current_time}"
        if user_prompt:
            user_prompt = f"{time_prefix}\n{user_prompt}"
        else:
            user_prompt = time_prefix
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        allowed_keys = {"temperature", "top_p", "presence_penalty", "frequency_penalty"}
        extra_params = {key: value for key, value in kwargs.items() if key in allowed_keys and value is not None}
        
        timeout = kwargs.get("timeout", self.timeout)

        payload = {
            "model": self.model_name,
            "messages": messages,
            "stream": False,
            **extra_params
        }

        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=payload,
                timeout=timeout
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get("choices") and len(data["choices"]) > 0:
                message = data["choices"][0].get("message", {})
                # Handle reasoning models (content: null, reasoning: "...")
                content = message.get("content") or message.get("reasoning", "")
                
                # 如果是reasoning格式（包含Thinking Process等），尝试提取最终答案
                if content and ("Thinking Process:" in content or "Final Decision:" in content):
                    # 尝试提取最终输出（通常在思维过程之后）
                    lines = content.split('\n')
                    output_started = False
                    final_lines = []
                    
                    for line in lines:
                        # 跳过明显的思维过程标记
                        if any(marker in line for marker in ["Thinking Process:", "Self-Correction", "**Plan:**", "**Drafting", "**Execution:**", "**Refinement:**", "*Wait,", "*Actually,", "*Decision:", "*Final"]):
                            continue
                        # 当遇到非元文本内容时，开始收集
                        if line.strip() and not line.strip().startswith('*') and not line.strip().startswith('-'):
                            output_started = True
                        if output_started:
                            final_lines.append(line)
                    
                    # 如果提取到了内容，使用提取的内容
                    if final_lines:
                        extracted = '\n'.join(final_lines).strip()
                        # 再次清理：如果内容以数字开头（如"1. ", "2. "），可能还是思维过程
                        if not extracted.startswith(('1.', '2.', '3.', '4.', '5.')):
                            content = extracted
                
                return self.validate_response(content)
            return ""
        except Exception as e:
            logger.error(f"非流式请求失败: {str(e)}")
            raise e

    def _make_streaming_request(self, messages: list, extra_params: dict, timeout: float):
        """
        创建流式请求，返回response对象
        """
        payload = {
            "model": self.model_name,
            "messages": messages,
            "stream": True,
            **extra_params
        }
        
        # Use tuple timeout: (connect_timeout, read_timeout)
        connect_timeout = min(timeout, 60)  # Max 60s for connection
        read_timeout = timeout  # Full timeout for reading stream
        
        response = self.session.post(
            f"{self.base_url}/chat/completions",
            json=payload,
            timeout=(connect_timeout, read_timeout),
            stream=True
        )
        response.raise_for_status()
        return response

    def stream_invoke(self, system_prompt: str, user_prompt: str, **kwargs) -> Generator[str, None, None]:
        """
        流式调用LLM，逐步返回响应内容（基于requests的SSE解析）
        增强版：支持连接断开时的部分内容保存和活跃性检测
        
        Args:
            system_prompt: 系统提示词
            user_prompt: 用户提示词
            **kwargs: 额外参数（temperature, top_p等）
            
        Yields:
            响应文本块（str）
        """
        current_time = datetime.now().strftime("%Y年%m月%d日%H时%M分")
        time_prefix = f"今天的实际时间是{current_time}"
        if user_prompt:
            user_prompt = f"{time_prefix}\n{user_prompt}"
        else:
            user_prompt = time_prefix
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        allowed_keys = {"temperature", "top_p", "presence_penalty", "frequency_penalty"}
        extra_params = {key: value for key, value in kwargs.items() if key in allowed_keys and value is not None}
        
        timeout = kwargs.get("timeout", self.timeout)
        
        # 流式响应的最大无活动时间（秒）
        max_inactivity = kwargs.get("max_inactivity", 300)  # 默认5分钟无活动视为超时
        
        # 跟踪已收到的内容
        received_chunks = []
        last_activity_time = time.time()
        
        try:
            response = self._make_streaming_request(messages, extra_params, timeout)
            
            # Parse SSE (Server-Sent Events) stream with improved error handling
            buffer = ""
            for line in response.iter_lines(decode_unicode=False):
                last_activity_time = time.time()
                
                if not line:
                    continue
                    
                try:
                    line_text = line.decode('utf-8').strip()
                except UnicodeDecodeError:
                    # 跳过无效的UTF-8
                    continue
                
                # SSE format: "data: {...}"
                if line_text.startswith("data: "):
                    data_str = line_text[6:]  # Remove "data: " prefix
                    
                    # Check for stream end marker
                    if data_str == "[DONE]":
                        break
                    
                    try:
                        chunk_data = json.loads(data_str)
                        
                        if chunk_data.get("choices") and len(chunk_data["choices"]) > 0:
                            delta = chunk_data["choices"][0].get("delta", {})
                            
                            # Handle content or reasoning fields
                            content = delta.get("content") or delta.get("reasoning", "")
                            
                            if content:
                                received_chunks.append(content)
                                yield content
                                
                    except json.JSONDecodeError as e:
                        logger.debug(f"跳过无效JSON块: {data_str[:50]}...")
                        continue
                        
        except (requests.exceptions.ChunkedEncodingError, 
                requests.exceptions.ConnectionError,
                ConnectionResetError) as e:
            # 连接断开，但可能已经收到了部分内容
            if received_chunks:
                partial_content = ''.join(received_chunks)
                logger.warning(f"流式连接中断，已收到 {len(partial_content)} 字符的部分内容")
                # 抛出带有部分内容的异常
                raise StreamingConnectionError(str(e), partial_content)
            else:
                logger.error(f"流式请求失败（无部分内容）: {str(e)}")
                raise
                
        except requests.exceptions.Timeout as e:
            if received_chunks:
                partial_content = ''.join(received_chunks)
                logger.warning(f"流式请求超时，已收到 {len(partial_content)} 字符的部分内容")
                raise StreamingConnectionError(str(e), partial_content)
            else:
                logger.error(f"流式请求超时: {str(e)}")
                raise
                
        except Exception as e:
            if received_chunks:
                partial_content = ''.join(received_chunks)
                logger.warning(f"流式请求异常，已收到 {len(partial_content)} 字符的部分内容: {str(e)}")
                raise StreamingConnectionError(str(e), partial_content)
            else:
                logger.error(f"流式请求失败: {str(e)}")
                raise
    
    def stream_invoke_with_recovery(self, system_prompt: str, user_prompt: str, 
                                     max_retries: int = 3, **kwargs) -> str:
        """
        带有恢复机制的流式调用，连接断开时尝试恢复或返回部分内容
        
        Args:
            system_prompt: 系统提示词
            user_prompt: 用户提示词
            max_retries: 最大重试次数
            **kwargs: 额外参数
            
        Returns:
            完整或部分的响应字符串
        """
        all_content = []
        last_partial = ""
        
        for attempt in range(max_retries):
            try:
                # 如果有之前的部分内容，调整prompt要求继续
                if last_partial:
                    continuation_prompt = f"{user_prompt}\n\n[继续之前的输出，已有内容如下，请直接继续：]\n{last_partial[-500:]}"
                    current_prompt = continuation_prompt
                else:
                    current_prompt = user_prompt
                
                chunks = []
                for chunk in self.stream_invoke(system_prompt, current_prompt, **kwargs):
                    chunks.append(chunk)
                
                # 成功完成
                if last_partial:
                    # 合并之前的内容和新内容
                    new_content = ''.join(chunks)
                    return last_partial + new_content
                else:
                    return ''.join(chunks)
                    
            except StreamingConnectionError as e:
                # 保存部分内容
                if e.partial_content:
                    if last_partial:
                        last_partial += e.partial_content
                    else:
                        last_partial = e.partial_content
                    logger.info(f"第 {attempt + 1} 次尝试中断，已累积 {len(last_partial)} 字符")
                
                if attempt < max_retries - 1:
                    wait_time = 30 * (attempt + 1)  # 递增等待时间
                    logger.info(f"等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
                else:
                    # 最后一次重试也失败，返回已有的部分内容
                    if last_partial:
                        logger.warning(f"达到最大重试次数，返回部分内容 ({len(last_partial)} 字符)")
                        return last_partial
                    raise
                    
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = 30 * (attempt + 1)
                    logger.warning(f"第 {attempt + 1} 次尝试失败: {e}，等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
                else:
                    if last_partial:
                        logger.warning(f"达到最大重试次数，返回部分内容 ({len(last_partial)} 字符)")
                        return last_partial
                    raise
        
        # 不应该到达这里
        return last_partial if last_partial else ""
    
    @with_retry(LLM_RETRY_CONFIG)
    def stream_invoke_to_string(self, system_prompt: str, user_prompt: str, **kwargs) -> str:
        """
        流式调用LLM并安全地拼接为完整字符串
        增强版：支持连接恢复和部分内容保存
        
        Args:
            system_prompt: 系统提示词
            user_prompt: 用户提示词
            **kwargs: 额外参数（temperature, top_p等）
            
        Returns:
            完整的响应字符串
        """
        # 使用带恢复机制的流式调用
        try:
            content = self.stream_invoke_with_recovery(system_prompt, user_prompt, max_retries=3, **kwargs)
            
            if content:
                # 清理reasoning模型的思维过程
                content = self._clean_reasoning_content(content)
            
            return content
            
        except StreamingConnectionError as e:
            # 如果有部分内容，清理并返回
            if e.partial_content:
                logger.warning(f"使用部分内容 ({len(e.partial_content)} 字符)")
                return self._clean_reasoning_content(e.partial_content)
            raise
        except Exception as e:
            logger.error(f"流式拼接失败: {str(e)}")
            raise
    
    def _clean_reasoning_content(self, content: str) -> str:
        """
        清理reasoning模型的思维过程，提取实际内容
        增强版：支持中英文思维过程标记，从末尾向前搜索有效内容
        """
        if not content:
            return ""
        
        # 方法1: 首先尝试查找最后一个有效的JSON块（最可靠的方法）
        json_start = -1
        json_end = -1
        brace_count = 0
        bracket_count = 0
        
        # 从后向前扫描找JSON
        for i in range(len(content) - 1, -1, -1):
            char = content[i]
            if char == '}':
                if json_end == -1:
                    json_end = i
                brace_count += 1
            elif char == '{':
                brace_count -= 1
                if brace_count == 0 and json_end != -1:
                    json_start = i
                    break
            elif char == ']' and json_end == -1:
                json_end = i
                bracket_count += 1
            elif char == '[' and bracket_count > 0:
                bracket_count -= 1
                if bracket_count == 0 and json_end != -1:
                    json_start = i
                    break
        
        if json_start != -1 and json_end != -1:
            potential_json = content[json_start:json_end + 1]
            try:
                json.loads(potential_json)
                return potential_json
            except:
                pass
            
        # 检查是否包含思维过程标记（中英文）
        thinking_markers = [
            # 英文标记
            "Thinking Process:", "Final Decision:", "*Wait,", "**Plan:**", 
            "**Drafting", "*Actually,", "*Decision:", "*Final",
            # 中文标记
            "好的，用户", "用户让我", "首先，我需要", "我需要", "考虑到",
            "让我", "我来", "接下来", "然后", "最后",
        ]
        
        has_thinking = any(marker in content for marker in thinking_markers)
        
        if not has_thinking:
            return content.strip()
        
        # 方法2: 从末尾查找实际内容（非思维过程的文本）
        lines = content.split('\n')
        
        # 从后向前找有效内容
        result_lines = []
        found_content = False
        
        # 思维过程的标记模式（中英文）
        meta_patterns = [
            # 英文模式
            r'^\s*Thinking Process:',
            r'^\s*\d+\.\s+\*\*',  # 1. **xxx**
            r'^\s*\*Wait,',
            r'^\s*\*Actually,',
            r'^\s*\*Decision:',
            r'^\s*\*Final',
            r'^\s*\*Self-Correction',
            r'^\s*\*\*Plan:\*\*',
            r'^\s*\*\*Drafting',
            r'^\s*\*\*Execution',
            r'^\s*\*\*Refinement',
            r'^\s*\*\*Decision:',
            r'^\s*\*\*Goal:',
            r'^\s*\*\*Content:',
            r'^\s*\*\*Format:',
            r'^\s*\*\*Length:',
            r'^\s*Let\'s',
            r'^\s*Wait,',
            r'^\s*Actually,',
            r'^\s*Okay,',
            r'^\s*I will',
            r'^\s*I should',
            r'^\s*I need to',
            r'^\s*Looking at',
            r'^\s*This (is|means|implies)',
            # 中文模式
            r'^\s*好的[，,]',
            r'^\s*用户(让|说|问|要)',
            r'^\s*首先[，,]',
            r'^\s*我需要',
            r'^\s*让我',
            r'^\s*接下来',
            r'^\s*然后',
            r'^\s*最后',
            r'^\s*考虑到',
            r'^\s*根据',
            r'^\s*所以',
            r'^\s*因此',
            r'^\s*现在',
        ]
        
        # 从后向前遍历
        for line in reversed(lines):
            stripped = line.strip()
            
            # 空行跳过
            if not stripped:
                if found_content:
                    result_lines.insert(0, line)
                continue
            
            # 检查是否是思维过程行
            is_meta = False
            for pattern in meta_patterns:
                if re.match(pattern, stripped, re.IGNORECASE):
                    is_meta = True
                    break
            
            # 检查是否是编号的思维步骤
            if re.match(r'^\d+\.\s+\*\*', stripped):
                is_meta = True
            
            # 检查是否是列表形式的思维过程
            if stripped.startswith('*') and ':' in stripped[:50]:
                is_meta = True
                
            if is_meta and found_content:
                # 已经找到了有效内容，遇到思维过程就停止
                break
            elif is_meta:
                continue
            else:
                # 这是有效内容
                found_content = True
                result_lines.insert(0, line)
        
        if result_lines:
            cleaned = '\n'.join(result_lines).strip()
            if len(cleaned) > 0:
                return cleaned
        
        # 如果清理失败，返回原始内容
        return content.strip()

    @staticmethod
    def validate_response(response: Optional[str]) -> str:
        if response is None:
            return ""
        return response.strip()

    def get_model_info(self) -> Dict[str, Any]:
        return {
            "provider": self.provider,
            "model": self.model_name,
            "api_base": self.base_url or "default",
        }
