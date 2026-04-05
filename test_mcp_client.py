# -*- coding: utf-8 -*-
"""Test MCP client with fixed parsing."""

from multi_agents.tools.mcp_client import MCPClient

client = MCPClient()
print('Testing MCP client with fixed parsing...')

# Test listing knowledge bases
print('\n1. Listing knowledge bases...')
kbs = client.list_knowledge_bases()
print(f'Found {len(kbs)} knowledge bases:')
for kb in kbs[:5]:  # Show first 5
    kb_name = kb.get('name', '')
    kb_id = kb.get('id', '')
    docs = kb.get('stats', {}).get('documents', 0)
    print(f'  - {kb_name} ({kb_id}) - {docs} docs')

# Test querying
if kbs:
    # Find Israel and Palestine KBs
    israel_kb = None
    palestine_kb = None
    for kb in kbs:
        name = kb.get('name', '')
        if 'Israel' in name or '以色列' in name or 'ZFuqf5xt' in kb.get('id', ''):
            israel_kb = kb
        if 'Palestine' in name or '巴勒斯坦' in name or 'rerIzPtv' in kb.get('id', ''):
            palestine_kb = kb
    
    if israel_kb:
        print(f'\n2. Querying Israel KB for conflict info...')
        results = client.query_knowledge_base(israel_kb['id'], '巴以冲突最新态势', top_k=3)
        print(f'Got {len(results)} results')
        for i, result in enumerate(results, 1):
            content = result.get('content', '')[:300]
            print(f'  Result {i}: {content}...')
