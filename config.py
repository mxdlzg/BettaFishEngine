# -*- coding: utf-8 -*-
"""
BettaFish舆情分析系统配置文件

此模块使用 pydantic-settings 管理全局配置，支持从环境变量和 .env 文件自动加载。
"""

from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field, ConfigDict
from typing import Optional, Literal
from loguru import logger


# 计算 .env 优先级：优先当前工作目录，其次项目根目录
PROJECT_ROOT: Path = Path(__file__).resolve().parent
CWD_ENV: Path = Path.cwd() / ".env"
ENV_FILE: str = str(CWD_ENV if CWD_ENV.exists() else (PROJECT_ROOT / ".env"))


class Settings(BaseSettings):
    """
    全局配置；支持 .env 和环境变量自动加载。
    """
    # ================== Flask 服务器配置 ====================
    HOST: str = Field("0.0.0.0", description="BettaFish 服务主机地址")
    PORT: int = Field(5000, description="Flask服务器端口号")

    # ====================== 数据库配置 ======================
    DB_DIALECT: str = Field("postgresql", description="数据库类型: mysql 或 postgresql")
    DB_HOST: str = Field("", description="数据库主机")
    DB_PORT: int = Field(3306, description="数据库端口号")
    DB_USER: str = Field("", description="数据库用户名")
    DB_PASSWORD: str = Field("", description="数据库密码")
    DB_NAME: str = Field("", description="数据库名称")
    DB_CHARSET: str = Field("utf8mb4", description="数据库字符集")
    
    # ======================= 统一LLM配置 =======================
    # 如果所有Agent使用同一个LLM服务，只需配置这三项
    LLM_API_KEY: Optional[str] = Field(None, description="统一LLM API密钥")
    LLM_API_BASE: Optional[str] = Field(None, description="统一LLM服务地址")
    LLM_API_MODEL: Optional[str] = Field(None, description="统一LLM模型名称")
    
    # ======================= 分引擎LLM配置 =======================
    # Insight Agent
    INSIGHT_ENGINE_API_KEY: Optional[str] = Field(None, description="Insight Agent API密钥")
    INSIGHT_ENGINE_BASE_URL: Optional[str] = Field(None, description="Insight Agent BaseUrl")
    INSIGHT_ENGINE_MODEL_NAME: Optional[str] = Field(None, description="Insight Agent 模型名称")
    
    # Media Agent
    MEDIA_ENGINE_API_KEY: Optional[str] = Field(None, description="Media Agent API密钥")
    MEDIA_ENGINE_BASE_URL: Optional[str] = Field(None, description="Media Agent BaseUrl")
    MEDIA_ENGINE_MODEL_NAME: Optional[str] = Field(None, description="Media Agent 模型名称")
    
    # Query Agent
    QUERY_ENGINE_API_KEY: Optional[str] = Field(None, description="Query Agent API密钥")
    QUERY_ENGINE_BASE_URL: Optional[str] = Field(None, description="Query Agent BaseUrl")
    QUERY_ENGINE_MODEL_NAME: Optional[str] = Field(None, description="Query Agent 模型名称")
    
    # Report Agent
    REPORT_ENGINE_API_KEY: Optional[str] = Field(None, description="Report Agent API密钥")
    REPORT_ENGINE_BASE_URL: Optional[str] = Field(None, description="Report Agent BaseUrl")
    REPORT_ENGINE_MODEL_NAME: Optional[str] = Field(None, description="Report Agent 模型名称")

    # MindSpider Agent
    MINDSPIDER_API_KEY: Optional[str] = Field(None, description="MindSpider Agent API密钥")
    MINDSPIDER_BASE_URL: Optional[str] = Field(None, description="MindSpider Agent BaseUrl")
    MINDSPIDER_MODEL_NAME: Optional[str] = Field(None, description="MindSpider Agent 模型名称")
    
    # Forum Host
    FORUM_HOST_API_KEY: Optional[str] = Field(None, description="Forum Host API密钥")
    FORUM_HOST_BASE_URL: Optional[str] = Field(None, description="Forum Host BaseUrl")
    FORUM_HOST_MODEL_NAME: Optional[str] = Field(None, description="Forum Host 模型名称")
    
    # SQL Keyword Optimizer
    KEYWORD_OPTIMIZER_API_KEY: Optional[str] = Field(None, description="Keyword Optimizer API密钥")
    KEYWORD_OPTIMIZER_BASE_URL: Optional[str] = Field(None, description="Keyword Optimizer BaseUrl")
    KEYWORD_OPTIMIZER_MODEL_NAME: Optional[str] = Field(None, description="Keyword Optimizer 模型名称")
    
    # ================== 搜索工具配置 ====================
    SEARCH_TOOL_TYPE: str = Field("duckduckgo", description="搜索工具类型: duckduckgo, AnspireAPI, BochaAPI, tavily")
    
    # Tavily
    TAVILY_API_KEY: Optional[str] = Field(None, description="Tavily API密钥")

    # Bocha
    BOCHA_BASE_URL: Optional[str] = Field("https://api.bocha.cn/v1/ai-search", description="Bocha AI搜索BaseUrl")
    BOCHA_WEB_SEARCH_API_KEY: Optional[str] = Field(None, description="Bocha API密钥")

    # Anspire
    ANSPIRE_BASE_URL: Optional[str] = Field("https://plugin.anspire.cn/api/ntsearch/search", description="Anspire AI搜索BaseUrl")
    ANSPIRE_API_KEY: Optional[str] = Field(None, description="Anspire API密钥")

    # ================== MCP知识库配置 ====================
    ALB_MCP_URL: Optional[str] = Field(None, description="MCP知识库服务地址")
    ALB_MCP_TOKEN: Optional[str] = Field(None, description="MCP访问令牌")
    
    # ================== 搜索参数配置 ====================
    DEFAULT_SEARCH_HOT_CONTENT_LIMIT: int = Field(100, description="热榜内容默认最大数")
    DEFAULT_SEARCH_TOPIC_GLOBALLY_LIMIT_PER_TABLE: int = Field(50, description="按表全局话题最大数")
    DEFAULT_SEARCH_TOPIC_BY_DATE_LIMIT_PER_TABLE: int = Field(100, description="按日期话题最大数")
    DEFAULT_GET_COMMENTS_FOR_TOPIC_LIMIT: int = Field(500, description="单话题评论最大数")
    DEFAULT_SEARCH_TOPIC_ON_PLATFORM_LIMIT: int = Field(200, description="平台搜索话题最大数")
    MAX_SEARCH_RESULTS_FOR_LLM: int = Field(50, description="供LLM用搜索结果最大数")
    MAX_HIGH_CONFIDENCE_SENTIMENT_RESULTS: int = Field(0, description="高置信度情感分析最大数")
    MAX_REFLECTIONS: int = Field(3, description="最大反思次数")
    MAX_PARAGRAPHS: int = Field(6, description="最大段落数")
    SEARCH_TIMEOUT: int = Field(240, description="单次搜索请求超时（秒）")
    MAX_CONTENT_LENGTH: int = Field(500000, description="搜索最大内容长度")
    SEARCH_CONTENT_MAX_LENGTH: int = Field(20000, description="用于提示的最长搜索内容长度")
    MAX_SEARCH_RESULTS: int = Field(20, description="最大搜索结果数")
    
    # ================== 输出配置 ====================
    OUTPUT_DIR: str = Field("outputs", description="报告输出目录")
    CHAPTER_OUTPUT_DIR: str = Field("outputs/chapters", description="章节JSON输出目录")
    DOCUMENT_IR_OUTPUT_DIR: str = Field("outputs/ir", description="整本IR输出目录")
    LOG_FILE: str = Field("logs/report.log", description="日志输出文件")
    SAVE_INTERMEDIATE_STATES: bool = Field(True, description="是否保存中间状态")
    PUBLIC_REPORT_BASE_URL: Optional[str] = Field(None, description="公开报告访问基础URL")
    
    # ================== 运行时配置 ====================
    DEBUG: int = Field(0, description="调试模式: 0=关闭, 1=开启")
    REQUEST_TIMEOUT_SEC: int = Field(120, description="请求超时时间（秒）")
    MAX_RETRIES: int = Field(3, description="最大重试次数")
    RETRIEVER: str = Field("duckduckgo", description="检索器类型: duckduckgo 或 tavily")
    
    model_config = ConfigDict(
        env_file=ENV_FILE,
        env_prefix="",
        case_sensitive=False,
        extra="allow"
    )
    
    def get_engine_config(self, engine_name: str) -> dict:
        """
        获取指定引擎的LLM配置，支持回退到统一配置
        
        Args:
            engine_name: 引擎名称 (query, media, insight, report, mindspider, forum_host, keyword_optimizer)
        
        Returns:
            包含 api_key, base_url, model_name 的配置字典
        """
        engine_map = {
            'query': ('QUERY_ENGINE', 'Query'),
            'media': ('MEDIA_ENGINE', 'Media'),
            'insight': ('INSIGHT_ENGINE', 'Insight'),
            'report': ('REPORT_ENGINE', 'Report'),
            'mindspider': ('MINDSPIDER', 'MindSpider'),
            'forum_host': ('FORUM_HOST', 'ForumHost'),
            'keyword_optimizer': ('KEYWORD_OPTIMIZER', 'KeywordOptimizer'),
        }
        
        if engine_name.lower() not in engine_map:
            raise ValueError(f"未知的引擎名称: {engine_name}")
        
        prefix, display_name = engine_map[engine_name.lower()]
        
        # 获取引擎特定配置
        api_key = getattr(self, f'{prefix}_API_KEY', None)
        base_url = getattr(self, f'{prefix}_BASE_URL', None)
        model_name = getattr(self, f'{prefix}_MODEL_NAME', None)
        
        # 回退到统一配置
        if not api_key:
            api_key = self.LLM_API_KEY
        if not base_url:
            base_url = self.LLM_API_BASE
        if not model_name:
            model_name = self.LLM_API_MODEL
        
        return {
            'api_key': api_key,
            'base_url': base_url,
            'model_name': model_name,
        }


# 创建全局配置实例
settings = Settings()


def reload_settings() -> Settings:
    """
    重新加载配置
    
    从 .env 文件和环境变量重新加载配置，更新全局 settings 实例。
    
    Returns:
        Settings: 新创建的配置实例
    """
    global settings
    settings = Settings()
    return settings
