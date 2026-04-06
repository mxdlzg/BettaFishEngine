# -*- coding: utf-8 -*-
"""
快速测试LLM响应
"""
import os
import time
from QueryEngine.llms import LLMClient

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()

# 初始化LLM客户端
client = LLMClient(
    api_key=os.getenv("QUERY_ENGINE_API_KEY"),
    base_url=os.getenv("QUERY_ENGINE_BASE_URL"),
    model_name=os.getenv("QUERY_ENGINE_MODEL_NAME")
)

print("=" * 60)
print("测试 LLM 响应速度和内容清理")
print("=" * 60)

# 测试简单提示
system_prompt = "You are a helpful assistant."
user_prompt = "Generate a JSON array with 3 topic titles about Israel-Palestine conflict. Return ONLY the JSON, no explanation."

print(f"\n发送提示词...")
start_time = time.time()

try:
    response = client.invoke(system_prompt, user_prompt, timeout=60)
    elapsed = time.time() - start_time
    
    print(f"\n✅ 响应成功 (耗时: {elapsed:.2f}秒)")
    print(f"\n响应内容 ({len(response)} 字符):")
    print("-" * 60)
    print(response[:500])  # 只显示前500字符
    if len(response) > 500:
        print(f"\n... (省略 {len(response) - 500} 字符)")
    print("-" * 60)
    
    # 检查是否包含reasoning内容
    if any(marker in response for marker in ["Thinking Process:", "**Plan:**", "*Wait,", "*Decision:"]):
        print("\n⚠️ 警告：响应包含 reasoning 思维过程！")
    else:
        print("\n✅ 响应内容干净，无 reasoning 痕迹")
        
except Exception as e:
    print(f"\n❌ 错误: {str(e)}")
