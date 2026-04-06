from config import settings
from QueryEngine.agent import DeepSearchAgent

print('测试QueryEngine搜索...')
agent = DeepSearchAgent(config=settings)

# 直接测试搜索工具
result = agent.search_agency.basic_search_news('Israel Palestine conflict news', max_results=3)
print(f'搜索结果: {len(result.results)} 条')
for r in result.results[:3]:
    title = r.title[:60] if r.title else "无标题"
    print(f'  - {title}')
