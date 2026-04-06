# -*- coding: utf-8 -*-
"""
DuckDuckGo搜索工具 - 免费替代Tavily的搜索引擎

版本: 1.1
提供与TavilyNewsAgency相同的接口,但使用免费的DuckDuckGo搜索
"""

import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta

# 尝试导入新版ddgs包，如果不存在则尝试旧版
try:
    from ddgs import DDGS
except ImportError:
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        raise ImportError("ddgs或duckduckgo-search库未安装，请运行 `pip install ddgs` 进行安装。")


@dataclass
class SearchResult:
    """搜索结果数据类"""
    title: Optional[str] = None
    url: Optional[str] = None
    content: Optional[str] = None
    score: Optional[float] = None
    raw_content: Optional[str] = None
    published_date: Optional[str] = None


@dataclass
class ImageResult:
    """图片搜索结果"""
    url: Optional[str] = None
    description: Optional[str] = None


@dataclass
class DuckDuckGoResponse:
    """DuckDuckGo搜索响应"""
    query: Optional[str] = None
    answer: Optional[str] = None
    results: List[SearchResult] = field(default_factory=list)
    images: List[ImageResult] = field(default_factory=list)
    response_time: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "query": self.query,
            "answer": self.answer,
            "results": [
                {
                    "title": r.title,
                    "url": r.url,
                    "content": r.content,
                    "score": r.score,
                    "published_date": r.published_date
                } for r in self.results
            ],
            "images": [{"url": i.url, "description": i.description} for i in self.images],
            "response_time": self.response_time
        }


class DuckDuckGoNewsAgency:
    """
    DuckDuckGo新闻搜索代理
    
    提供与TavilyNewsAgency相同的接口,支持:
    - basic_search_news: 基础新闻搜索
    - deep_search_news: 深度搜索(更多结果)
    - search_news_last_24_hours: 24小时内新闻
    - search_news_last_week: 一周内新闻
    - search_images_for_news: 图片搜索
    - search_news_by_date: 日期范围搜索
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        初始化DuckDuckGo客户端
        Args:
            api_key: 不需要,保留以兼容Tavily接口
        """
        self._ddgs = DDGS()
    
    def _search_news(
        self,
        query: str,
        max_results: int = 10,
        timelimit: Optional[str] = None,
        region: str = "wt-wt"
    ) -> DuckDuckGoResponse:
        """
        内部新闻搜索方法
        
        Args:
            query: 搜索关键词
            max_results: 最大结果数
            timelimit: 时间限制 (d=天, w=周, m=月)
            region: 地区代码
        """
        start_time = datetime.now()
        
        try:
            results = list(self._ddgs.news(
                query,
                region=region,
                safesearch="off",
                timelimit=timelimit,
                max_results=max_results
            ))
            
            search_results = []
            for item in results:
                search_results.append(SearchResult(
                    title=item.get('title', ''),
                    url=item.get('url', ''),
                    content=item.get('body', ''),
                    score=0.8,  # DuckDuckGo不提供分数,使用默认值
                    published_date=item.get('date', '')
                ))
            
            response_time = (datetime.now() - start_time).total_seconds()
            
            return DuckDuckGoResponse(
                query=query,
                answer=None,
                results=search_results,
                response_time=response_time
            )
            
        except Exception as e:
            print(f"DuckDuckGo新闻搜索错误: {e}, 尝试网页搜索...")
            # 尝试网页搜索作为备选
            return self._search_text(query, max_results, timelimit, region)
    
    def _search_text(
        self,
        query: str,
        max_results: int = 10,
        timelimit: Optional[str] = None,
        region: str = "wt-wt"
    ) -> DuckDuckGoResponse:
        """
        内部文本搜索方法(网页搜索)
        """
        start_time = datetime.now()
        
        try:
            results = list(self._ddgs.text(
                query,
                region=region,
                safesearch="off",
                timelimit=timelimit,
                max_results=max_results
            ))
            
            search_results = []
            for item in results:
                search_results.append(SearchResult(
                    title=item.get('title', ''),
                    url=item.get('href', ''),
                    content=item.get('body', ''),
                    score=0.8
                ))
            
            response_time = (datetime.now() - start_time).total_seconds()
            
            return DuckDuckGoResponse(
                query=query,
                results=search_results,
                response_time=response_time
            )
            
        except Exception as e:
            print(f"DuckDuckGo搜索错误: {e}")
            return DuckDuckGoResponse(query=query, results=[])

    # --- Agent 可用的工具方法 (与Tavily接口兼容) ---

    def basic_search_news(self, query: str, max_results: int = 7) -> DuckDuckGoResponse:
        """
        【工具】基础新闻搜索: 执行一次标准、快速的新闻搜索。
        """
        return self._search_news(query, max_results=max_results)

    def deep_search_news(self, query: str, max_results: int = 15) -> DuckDuckGoResponse:
        """
        【工具】深度新闻搜索: 对主题进行全面的深度分析，返回更多结果。
        """
        return self._search_news(query, max_results=max_results)

    def search_news_last_24_hours(self, query: str, max_results: int = 10) -> DuckDuckGoResponse:
        """
        【工具】24小时新闻搜索: 获取过去24小时内的最新动态。
        """
        return self._search_news(query, max_results=max_results, timelimit="d")

    def search_news_last_week(self, query: str, max_results: int = 10) -> DuckDuckGoResponse:
        """
        【工具】一周新闻搜索: 获取过去一周的主要报道。
        """
        return self._search_news(query, max_results=max_results, timelimit="w")

    def search_images_for_news(self, query: str, max_results: int = 5) -> DuckDuckGoResponse:
        """
        【工具】图片搜索: 查找与新闻主题相关的图片。
        """
        start_time = datetime.now()
        
        try:
            results = list(self._ddgs.images(
                query,
                region="wt-wt",
                safesearch="off",
                max_results=max_results
            ))
            
            image_results = []
            for item in results:
                image_results.append(ImageResult(
                    url=item.get('image', ''),
                    description=item.get('title', '')
                ))
            
            response_time = (datetime.now() - start_time).total_seconds()
            
            return DuckDuckGoResponse(
                query=query,
                images=image_results,
                response_time=response_time
            )
            
        except Exception as e:
            print(f"DuckDuckGo图片搜索错误: {e}")
            return DuckDuckGoResponse(query=query, images=[])

    def search_news_by_date(
        self,
        query: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        max_results: int = 10
    ) -> DuckDuckGoResponse:
        """
        【工具】日期范围新闻搜索: 在指定日期范围内搜索新闻。
        
        注意: DuckDuckGo不支持精确日期范围,使用时间限制作为近似
        """
        # DuckDuckGo不支持精确日期,使用月度限制作为近似
        return self._search_news(query, max_results=max_results, timelimit="m")


def get_search_agency(retriever: str = "duckduckgo", api_key: Optional[str] = None):
    """
    工厂函数: 根据配置返回对应的搜索代理
    
    Args:
        retriever: 搜索引擎类型 ("duckduckgo" 或 "tavily")
        api_key: API密钥 (Tavily需要)
    
    Returns:
        搜索代理实例
    """
    if retriever.lower() == "tavily":
        from QueryEngine.tools.search import TavilyNewsAgency
        return TavilyNewsAgency(api_key=api_key)
    else:
        return DuckDuckGoNewsAgency()


# 测试代码
if __name__ == "__main__":
    print("测试DuckDuckGo新闻搜索...")
    
    agency = DuckDuckGoNewsAgency()
    
    # 测试基础搜索
    print("\n1. 基础新闻搜索:")
    result = agency.basic_search_news("巴以冲突", max_results=3)
    print(f"找到 {len(result.results)} 条结果")
    for r in result.results:
        print(f"  - {r.title[:50]}... ({r.published_date})")
    
    # 测试24小时搜索
    print("\n2. 24小时新闻:")
    result = agency.search_news_last_24_hours("以色列", max_results=3)
    print(f"找到 {len(result.results)} 条结果")
    
    print("\n测试完成!")
