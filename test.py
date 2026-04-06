# -*- coding: utf-8 -*-
# test_full.py - 完整测试脚本
import sys
import os

# 清除DEBUG环境变量（避免与系统变量冲突）
if "DEBUG" in os.environ:
    del os.environ["DEBUG"]

sys.path.insert(0, os.getcwd())

from QueryEngine.agent import DeepSearchAgent
from datetime import datetime

print("=" * 70)
print(f"测试开始: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 70)

# 初始化Agent
agent = DeepSearchAgent()
print(f"✓ Agent初始化成功")
print(f"  - LLM模型: {agent.llm_client.model_name}")
print(f"  - 搜索工具: {agent.search_tool_name}")
print(f"  - 输出目录: {agent.config.OUTPUT_DIR}")

# 确保输出目录存在
os.makedirs(agent.config.OUTPUT_DIR, exist_ok=True)

# 测试主题
query = "AI技术发展"
print(f"\n测试主题: {query}")
print("-" * 70)

# 运行研究，导出所有格式
export_formats = ['md', 'html', 'docx']  # 可添加 'pdf' 如果安装了相关库
result = agent.research(query, save_report=True, export_formats=export_formats)

print("\n" + "=" * 70)
print("测试完成!")
print("=" * 70)

# 检查生成的文件
print(f"\n报告长度: {len(result)} 字符")

# 检查目录
if "## 目录" in result:
    print("✓ 报告包含目录")
else:
    print("✗ 报告不包含目录")

# 检查outputs目录
print(f"\n生成的文件:")
for item in os.listdir(agent.config.OUTPUT_DIR):
    item_path = os.path.join(agent.config.OUTPUT_DIR, item)
    if os.path.isdir(item_path):
        print(f"  📁 {item}/")
        for f in os.listdir(item_path):
            fpath = os.path.join(item_path, f)
            if os.path.isfile(fpath):
                size = os.path.getsize(fpath)
                print(f"     - {f}: {size:,} bytes")

print(f"\n测试结束: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")