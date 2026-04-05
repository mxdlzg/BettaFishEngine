# -*- coding: utf-8 -*-
"""
LLM client for the LangGraph multi-agent system.

Provides unified access to OpenAI-compatible model services.
"""

import time
from typing import List, Dict, Any, Optional
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from multi_agents.settings import get_settings, Settings
from multi_agents.tools.logger import get_logger
from multi_agents.tools.json_utils import extract_json_from_llm_response

logger = get_logger("llm_client")


class LLMClient:
    """
    Unified LLM client for the multi-agent system.
    
    Provides consistent access to OpenAI-compatible model services
    with role-specific model selection, retry logic, and error handling.
    """
    
    def __init__(self, settings: Optional[Settings] = None):
        """
        Initialize the LLM client.
        
        Args:
            settings: Settings instance, or None to use global settings
        """
        self.settings = settings or get_settings()
        self.client = OpenAI(
            api_key=self.settings.openai_api_key,
            base_url=self.settings.openai_base_url,
            timeout=self.settings.request_timeout_sec
        )
        self._available_models: Optional[List[str]] = None
    
    def list_models(self) -> List[str]:
        """
        List available models from the API.
        
        Returns:
            List of model IDs
        """
        if self._available_models is None:
            try:
                response = self.client.models.list()
                self._available_models = [m.id for m in response.data]
                logger.info(f"Available models: {self._available_models}")
            except Exception as e:
                logger.error(f"Failed to list models: {e}")
                self._available_models = []
        return self._available_models
    
    def _get_model(self, role: str) -> str:
        """
        Get the model ID for a specific role.
        
        Args:
            role: One of 'planner', 'analysis', 'moderator', 'report'
        
        Returns:
            Model ID to use
        """
        model_map = {
            'planner': self.settings.llm_planner_model,
            'analysis': self.settings.llm_analysis_model,
            'moderator': self.settings.llm_moderator_model,
            'report': self.settings.llm_report_model,
        }
        
        model = model_map.get(role, "")
        
        # If no specific model configured, use the first available
        if not model:
            available = self.list_models()
            if available:
                model = available[0]
                logger.info(f"Using first available model for {role}: {model}")
            else:
                raise ValueError(f"No model configured for role '{role}' and no models available")
        
        return model
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30)
    )
    def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        role: str = "analysis",
        temperature: float = 0.2,
        max_tokens: int = 4000,
        **kwargs
    ) -> str:
        """
        Send a chat completion request.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model ID to use (overrides role-based selection)
            role: Role for model selection ('planner', 'analysis', 'moderator', 'report')
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            **kwargs: Additional arguments passed to the API
        
        Returns:
            The assistant's response content
        """
        if model is None:
            model = self._get_model(role)
        
        start_time = time.time()
        logger.info(f"Calling LLM: model={model}, role={role}, messages={len(messages)}")
        
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            
            content = response.choices[0].message.content or ""
            duration = time.time() - start_time
            logger.info(f"LLM response received in {duration:.2f}s, {len(content)} chars")
            
            return content
            
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise
    
    def json_chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        role: str = "analysis",
        temperature: float = 0.1,
        max_tokens: int = 4000,
        default: Any = None,
        **kwargs
    ) -> Any:
        """
        Send a chat request expecting JSON response.
        
        Attempts to parse the response as JSON with error recovery.
        
        Args:
            messages: List of message dicts
            model: Model ID to use
            role: Role for model selection
            temperature: Sampling temperature (lower for JSON)
            max_tokens: Maximum tokens in response
            default: Default value if parsing fails
            **kwargs: Additional arguments
        
        Returns:
            Parsed JSON object or default value
        """
        # Add JSON instruction to system message if not present
        if messages and messages[0]['role'] == 'system':
            if 'json' not in messages[0]['content'].lower():
                messages[0]['content'] += "\n\nRespond with valid JSON only, no additional text."
        
        response = self.chat(
            messages=messages,
            model=model,
            role=role,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
        
        result = extract_json_from_llm_response(response, default)
        if result is None and default is not None:
            logger.warning("Failed to parse JSON response, using default")
            return default
        
        return result
    
    def planner_chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        **kwargs
    ) -> str:
        """Chat with the planner model."""
        return self.chat(messages, role="planner", temperature=temperature, **kwargs)
    
    def analysis_chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        **kwargs
    ) -> str:
        """Chat with the analysis model."""
        return self.chat(messages, role="analysis", temperature=temperature, **kwargs)
    
    def moderator_chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.4,
        **kwargs
    ) -> str:
        """Chat with the moderator model."""
        return self.chat(messages, role="moderator", temperature=temperature, **kwargs)
    
    def report_chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 8000,
        **kwargs
    ) -> str:
        """Chat with the report model."""
        return self.chat(messages, role="report", temperature=temperature, max_tokens=max_tokens, **kwargs)


# Global client instance (lazy loaded)
_llm_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """Get the global LLM client instance."""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client
