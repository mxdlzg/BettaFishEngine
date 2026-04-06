"""完整舆情分析测试"""
import sys
import time
import os
sys.path.insert(0, '.')

from datetime import datetime
from loguru import logger

# 设置日志
logger.add("test_full_run.log", rotation="10 MB", level="DEBUG")

def run_test():
    """运行完整测试"""
    start_time = time.time()
    
    print("=" * 60)
    print("舆情分析系统完整测试")
    print("=" * 60)
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    try:
        # 导入 Agent
        from QueryEngine import DeepSearchAgent
        
        print("[1/4] 初始化 Agent...")
        agent = DeepSearchAgent()
        print(f"      ✅ Agent 初始化成功")
        print(f"      - 模型: {agent.config.QUERY_ENGINE_MODEL_NAME}")
        print(f"      - API: {agent.config.QUERY_ENGINE_BASE_URL}")
        print(f"      - 输出目录: {agent.config.OUTPUT_DIR}")
        print()
        
        # 执行研究
        query = "巴以冲突最新进展"
        print(f"[2/4] 开始研究: {query}")
        print("      请耐心等待，这可能需要几分钟...")
        
        research_start = time.time()
        
        # 执行研究并导出多种格式
        report = agent.research(
            query=query, 
            save_report=True,
            export_formats=['md', 'html']  # 导出Markdown和HTML
        )
        
        research_time = time.time() - research_start
        
        print(f"      ✅ 研究完成! 耗时: {research_time:.1f} 秒")
        print()
        
        # 检查报告
        print("[3/4] 检查报告质量...")
        print(f"      - 报告长度: {len(report)} 字符")
        
        # 检查垃圾内容
        has_garbage = False
        garbage_markers = ['"type":', 'This matches', 'I will follow', '*However*']
        for marker in garbage_markers:
            if marker in report:
                print(f"      ⚠️ 警告: 报告包含垃圾内容: {marker}")
                has_garbage = True
        
        if not has_garbage:
            print(f"      ✅ 报告不包含垃圾内容")
        
        # 检查输出文件
        print()
        print("[4/4] 检查输出文件...")
        output_dir = agent.config.OUTPUT_DIR
        files = os.listdir(output_dir)
        report_files = [f for f in files if f.startswith('deep_search_report_')]
        
        if report_files:
            # 找最新的文件
            latest_files = sorted(report_files, reverse=True)[:3]
            for f in latest_files:
                filepath = os.path.join(output_dir, f)
                size = os.path.getsize(filepath)
                print(f"      - {f}: {size} bytes")
        
        # 总结
        print()
        print("=" * 60)
        total_time = time.time() - start_time
        print(f"测试完成! 总耗时: {total_time:.1f} 秒 ({total_time/60:.1f} 分钟)")
        print(f"报告长度: {len(report)} 字符")
        print("=" * 60)
        
        # 显示报告前500字符
        print()
        print("报告预览 (前500字符):")
        print("-" * 40)
        print(report[:500])
        print("-" * 40)
        
        return True
        
    except Exception as e:
        import traceback
        print(f"❌ 测试失败: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = run_test()
    sys.exit(0 if success else 1)
