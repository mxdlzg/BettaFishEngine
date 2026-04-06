# -*- coding: utf-8 -*-
"""
快速测试 - 只运行QueryEngine，生成简短报告
"""
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 设置Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# 临时修改配置以加快测试
os.environ["MAX_PARAGRAPHS"] = "2"  # 只生成2个段落
os.environ["MAX_REFLECTIONS"] = "1"  # 只进行1轮反思

print("=" * 70)
print("快速测试：QueryEngine 报告生成")
print("=" * 70)
print(f"配置: 2个段落, 1轮反思")
print(f"主题: 巴以冲突最新态势")
print(f"开始时间: {datetime.now().strftime('%H:%M:%S')}")
print("")

try:
    from QueryEngine.agent import DeepSearchAgent
    
    # 初始化Agent
    print("初始化QueryEngine...")
    agent = DeepSearchAgent()
    print("✅ 初始化成功")
    print("")
    
    # 执行研究
    print("开始生成报告...")
    start_time = datetime.now()
    
    report_path = agent.research("分析2026年巴以冲突最新态势")
    
    end_time = datetime.now()
    elapsed = (end_time - start_time).total_seconds()
    
    print("")
    print("=" * 70)
    print(f"✅ 报告生成完成！")
    print(f"耗时: {elapsed:.1f} 秒")
    print(f"报告路径: {report_path}")
    print("=" * 70)
    
    # 显示报告前200行
    if os.path.exists(report_path):
        print("\n报告预览 (前50行):")
        print("-" * 70)
        with open(report_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for i, line in enumerate(lines[:50], 1):
                print(f"{i:3d}: {line}", end='')
        print("\n" + "-" * 70)
        print(f"完整报告共 {len(lines)} 行")
    
except Exception as e:
    print(f"\n❌ 错误: {str(e)}")
    import traceback
    traceback.print_exc()
