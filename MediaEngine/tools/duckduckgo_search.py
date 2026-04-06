# -*- coding: utf-8 -*-
"""
DuckDuckGo多模态搜索适配器 - 用于MediaEngine

提供与BochaMultimodalSearch相同的接口，但使用免费的DuckDuckGo搜索
"""

import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

# 尝试导入新版ddgs包，如果不存在则尝试旧版
try:
    from ddgs import DDGS
except ImportError:
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        raise ImportError("ddgs或duckduckgo-search库未安装，请运行 `pip install ddgs` 进行安装。")

from loguru import logger


@dataclass
class WebpageResult:
    """网页搜索结果"""
    name: str
    url: str
    snippet: str
    display_url: Optional[str] = None
    date_last_crawled: Optional[str] = None


@dataclass
class ImageResult:
    """图片搜索结果"""
    name: str
    content_url: str
    host_page_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None


@dataclass
class ModalCardResult:
    """模态卡结构化数据结果（DuckDuckGo不支持，保留接口兼容）"""
    card_type: str
    content: Dict[str, Any]


@dataclass
class DuckDuckGoMediaResponse:
    """封装DuckDuckGo搜索的完整返回结果，兼容BochaResponse接口"""
    query: str
    conversation_id: Optional[str] = None
    answer: Optional[str] = None
    follow_ups: List[str] = field(default_factory=list)
    webpages: List[WebpageResult] = field(default_factory=list)
    images: List[ImageResult] = field(default_factory=list)
    modal_cards: List[ModalCardResult] = field(default_factory=list)


class DuckDuckGoMultimodalSearch:
    """
    DuckDuckGo多模态搜索客户端
    提供与BochaMultimodalSearch相同的接口
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        初始化DuckDuckGo客户端
        Args:
            api_key: 不需要，保留以兼容Bocha接口
        """
        self._ddgs = DDGS()
        logger.info("DuckDuckGoMultimodalSearch 初始化完成")

    def _search_text(
        self,
        query: str,
        max_results: int = 10,
        timelimit: Optional[str] = None,
        region: str = "wt-wt"
    ) -> DuckDuckGoMediaResponse:
        """
        执行文本搜索
        """
        try:
            results = list(self._ddgs.text(
                query,
                region=region,
                safesearch="off",
                timelimit=timelimit,
                max_results=max_results
            ))
            
            webpages = []
            for item in results:
                webpages.append(WebpageResult(
                    name=item.get('title', ''),
                    url=item.get('href', ''),
                    snippet=item.get('body', ''),
                    display_url=item.get('href', ''),
                    date_last_crawled=None
                ))
            
            return DuckDuckGoMediaResponse(
                query=query,
                webpages=webpages
            )
            
        except Exception as e:
            logger.error(f"DuckDuckGo文本搜索错误: {e}")
            return DuckDuckGoMediaResponse(query=query)

    def _search_images(
        self,
        query: str,
        max_results: int = 10
    ) -> DuckDuckGoMediaResponse:
        """
        执行图片搜索
        """
        try:
            results = list(self._ddgs.images(
                query,
                region="wt-wt",
                safesearch="off",
                max_results=max_results
            ))
            
            images = []
            for item in results:
                images.append(ImageResult(
                    name=item.get('title', ''),
                    content_url=item.get('image', ''),
                    host_page_url=item.get('url', ''),
                    thumbnail_url=item.get('thumbnail', ''),
                    width=item.get('width'),
                    height=item.get('height')
                ))
            
            return DuckDuckGoMediaResponse(
                query=query,
                images=images
            )
            
        except Exception as e:
            logger.error(f"DuckDuckGo图片搜索错误: {e}")
            return DuckDuckGoMediaResponse(query=query)

    def _search_news(
        self,
        query: str,
        max_results: int = 10,
        timelimit: Optional[str] = None
    ) -> DuckDuckGoMediaResponse:
        """
        执行新闻搜索
        """
        try:
            results = list(self._ddgs.news(
                query,
                region="wt-wt",
                safesearch="off",
                timelimit=timelimit,
                max_results=max_results
            ))
            
            webpages = []
            for item in results:
                webpages.append(WebpageResult(
                    name=item.get('title', ''),
                    url=item.get('url', ''),
                    snippet=item.get('body', ''),
                    display_url=item.get('source', ''),
                    date_last_crawled=item.get('date', '')
                ))
            
            return DuckDuckGoMediaResponse(
                query=query,
                webpages=webpages
            )
            
        except Exception as e:
            logger.error(f"DuckDuckGo新闻搜索错误: {e}, 尝试网页搜索...")
            # 尝试网页搜索作为备选
            return self._search_text(query, max_results, timelimit)

    # --- Agent 可用的工具方法 (与Bocha接口兼容) ---

    def comprehensive_search(self, query: str, max_results: int = 10) -> DuckDuckGoMediaResponse:
        """
        【工具】全面综合搜索: 执行一次包含网页、图片的综合搜索。
        """
        logger.info(f"--- TOOL: DuckDuckGo全面综合搜索 (query: {query}) ---")
        
        # 获取网页结果
        text_response = self._search_text(query, max_results=max_results)
        
        # 获取图片结果
        image_response = self._search_images(query, max_results=5)
        
        return DuckDuckGoMediaResponse(
            query=query,
            webpages=text_response.webpages,
            images=image_response.images
        )

    def web_search_only(self, query: str, max_results: int = 15) -> DuckDuckGoMediaResponse:
        """
        【工具】纯网页搜索: 只获取网页链接和摘要。
        """
        logger.info(f"--- TOOL: DuckDuckGo纯网页搜索 (query: {query}) ---")
        return self._search_text(query, max_results=max_results)

    def search_for_structured_data(self, query: str) -> DuckDuckGoMediaResponse:
        """
        【工具】结构化数据查询
        注意: DuckDuckGo不支持模态卡，返回普通搜索结果
        """
        logger.info(f"--- TOOL: DuckDuckGo结构化数据查询 (query: {query}) ---")
        return self._search_text(query, max_results=5)

    def search_last_24_hours(self, query: str) -> DuckDuckGoMediaResponse:
        """
        【工具】搜索24小时内信息
        """
        logger.info(f"--- TOOL: DuckDuckGo搜索24小时内信息 (query: {query}) ---")
        return self._search_news(query, timelimit="d")

    def search_last_week(self, query: str) -> DuckDuckGoMediaResponse:
        """
        【工具】搜索本周信息
        """
        logger.info(f"--- TOOL: DuckDuckGo搜索本周信息 (query: {query}) ---")
        return self._search_news(query, timelimit="w")


def get_media_search_agency(retriever: str = "duckduckgo", api_key: Optional[str] = None):
    """
    工厂函数: 根据配置返回对应的搜索代理
    
    Args:
        retriever: 搜索引擎类型 ("duckduckgo", "bocha" 或 "anspire")
        api_key: API密钥
    
    Returns:
        搜索代理实例
    """
    if retriever.lower() == "bocha":
        from MediaEngine.tools.search import BochaMultimodalSearch
        return BochaMultimodalSearch(api_key=api_key)
    elif retriever.lower() == "anspire":
        from MediaEngine.tools.search import AnspireAISearch
        return AnspireAISearch(api_key=api_key)
    else:
        return DuckDuckGoMultimodalSearch()


# 测试代码
if __name__ == "__main__":
    print("测试DuckDuckGo多模态搜索...")
    
    agency = DuckDuckGoMultimodalSearch()
    
    # 测试全面搜索
    print("\n1. 全面综合搜索:")
    result = agency.comprehensive_search("巴以冲突 最新动态", max_results=3)
    print(f"找到 {len(result.webpages)} 条网页结果, {len(result.images)} 张图片")
    for r in result.webpages:
        print(f"  - {r.name[:50]}...")
    
    # 测试24小时新闻
    print("\n2. 24小时新闻:")
    result = agency.search_last_24_hours("以色列")
    print(f"找到 {len(result.webpages)} 条新闻")
    
    print("\n测试完成!")
