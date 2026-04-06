# -*- coding: utf-8 -*-
"""
完整流程测试 - 监控每个步骤并记录问题
"""
import os
import sys
import time
import json
from datetime import datetime
from dotenv import load_dotenv

# 解决Windows编码问题
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 加载环境变量
load_dotenv()

# 设置路径
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# 测试记录
test_results = {
    "start_time": None,
    "end_time": None,
    "total_duration": 0,
    "steps": [],
    "errors": [],
    "warnings": [],
    "success": False
}

def log_step(step_name, status, duration=0, details=""):
    """记录步骤"""
    step = {
        "step": step_name,
        "status": status,
        "duration_sec": round(duration, 2),
        "details": details,
        "timestamp": datetime.now().strftime("%H:%M:%S")
    }
    test_results["steps"].append(step)
    
    icon = "[OK]" if status == "success" else "[FAIL]" if status == "error" else "[WARN]"
    print(f"{icon} {step_name} ({duration:.1f}s) - {details[:80] if details else status}")

def log_error(error_msg, context=""):
    """记录错误"""
    test_results["errors"].append({
        "error": error_msg,
        "context": context,
        "timestamp": datetime.now().strftime("%H:%M:%S")
    })
    print(f"[ERROR] {error_msg}")

def log_warning(warn_msg):
    """记录警告"""
    test_results["warnings"].append({
        "warning": warn_msg,
        "timestamp": datetime.now().strftime("%H:%M:%S")
    })

print("=" * 70)
print("BettaFish 完整流程测试")
print("=" * 70)
print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("")

test_results["start_time"] = datetime.now().isoformat()

# ============ 步骤1: 测试环境配置 ============
print("\n[步骤1] 检查环境配置...")
step_start = time.time()

required_vars = [
    "QUERY_ENGINE_API_KEY",
    "QUERY_ENGINE_BASE_URL", 
    "QUERY_ENGINE_MODEL_NAME",
    "MEDIA_ENGINE_API_KEY",
    "INSIGHT_ENGINE_API_KEY",
    "REPORT_ENGINE_API_KEY"
]

missing_vars = []
for var in required_vars:
    if not os.getenv(var):
        missing_vars.append(var)

if missing_vars:
    log_step("环境变量检查", "error", time.time()-step_start, f"缺失: {missing_vars}")
    log_error(f"缺失环境变量: {missing_vars}")
else:
    log_step("环境变量检查", "success", time.time()-step_start, "所有必需变量已配置")

# ============ 步骤2: 测试LLM连接 ============
print("\n[步骤2] 测试LLM连接...")
step_start = time.time()

try:
    from QueryEngine.llms import LLMClient
    
    client = LLMClient(
        api_key=os.getenv("QUERY_ENGINE_API_KEY"),
        base_url=os.getenv("QUERY_ENGINE_BASE_URL"),
        model_name=os.getenv("QUERY_ENGINE_MODEL_NAME")
    )
    
    # 快速测试
    response = client.invoke(
        "You are a helpful assistant.",
        "Say 'OK' if you can hear me.",
        timeout=30
    )
    
    if response and len(response) > 0:
        log_step("LLM连接测试", "success", time.time()-step_start, f"响应长度: {len(response)} chars")
    else:
        log_step("LLM连接测试", "warning", time.time()-step_start, "响应为空")
        log_warning("LLM返回空响应")
        
except Exception as e:
    log_step("LLM连接测试", "error", time.time()-step_start, str(e)[:100])
    log_error(str(e), "LLM连接")

# ============ 步骤3: 测试搜索工具 ============
print("\n[步骤3] 测试DuckDuckGo搜索...")
step_start = time.time()

try:
    from QueryEngine.tools.duckduckgo_search import DuckDuckGoNewsAgency
    
    search = DuckDuckGoNewsAgency()
    result = search.basic_search_news("Israel Palestine conflict 2026", max_results=3)
    
    if result and result.results:
        log_step("DuckDuckGo搜索", "success", time.time()-step_start, f"返回 {len(result.results)} 条结果")
    else:
        log_step("DuckDuckGo搜索", "warning", time.time()-step_start, "无搜索结果")
        log_warning("搜索返回空结果")
        
except Exception as e:
    log_step("DuckDuckGo搜索", "error", time.time()-step_start, str(e)[:100])
    log_error(str(e), "搜索工具")

# ============ 步骤4: 测试QueryEngine初始化 ============
print("\n[步骤4] 测试QueryEngine初始化...")
step_start = time.time()

try:
    from QueryEngine.agent import DeepSearchAgent
    
    agent = DeepSearchAgent()
    log_step("QueryEngine初始化", "success", time.time()-step_start, f"搜索工具: {agent.search_tool_name}")
    
except Exception as e:
    log_step("QueryEngine初始化", "error", time.time()-step_start, str(e)[:100])
    log_error(str(e), "QueryEngine初始化")
    agent = None

# ============ 步骤5: 生成报告结构 ============
if agent:
    print("\n[步骤5] 生成报告结构...")
    step_start = time.time()
    
    try:
        # 手动调用报告结构生成
        from QueryEngine.nodes import ReportStructureNode
        from QueryEngine.state import State
        
        agent.state = State()
        agent.state.set_query("分析2026年巴以冲突最新舆情态势")
        
        structure_node = ReportStructureNode(agent.llm_client)
        result = structure_node.run(agent.state)
        
        paragraphs = agent.state.get_paragraphs()
        if paragraphs:
            log_step("报告结构生成", "success", time.time()-step_start, f"生成 {len(paragraphs)} 个段落")
            for i, p in enumerate(paragraphs, 1):
                print(f"    段落{i}: {p.get('title', 'N/A')}")
        else:
            log_step("报告结构生成", "warning", time.time()-step_start, "未生成段落")
            log_warning("报告结构为空")
            
    except Exception as e:
        log_step("报告结构生成", "error", time.time()-step_start, str(e)[:100])
        log_error(str(e), "报告结构生成")

# ============ 步骤6: 完整报告生成 ============
if agent:
    print("\n[步骤6] 生成完整报告 (这可能需要5-10分钟)...")
    step_start = time.time()
    
    try:
        # 重新初始化agent
        agent = DeepSearchAgent()
        
        # 执行完整研究
        report_path = agent.research("分析2026年巴以冲突最新舆情态势")
        
        duration = time.time() - step_start
        
        if report_path and os.path.exists(report_path):
            file_size = os.path.getsize(report_path) / 1024
            log_step("完整报告生成", "success", duration, f"文件: {report_path}, 大小: {file_size:.1f}KB")
            test_results["report_path"] = report_path
            test_results["report_size_kb"] = round(file_size, 2)
            test_results["success"] = True
        else:
            log_step("完整报告生成", "error", duration, "报告文件未生成")
            log_error("报告文件未生成", "完整报告")
            
    except Exception as e:
        log_step("完整报告生成", "error", time.time()-step_start, str(e)[:100])
        log_error(str(e), "完整报告生成")

# ============ 汇总测试结果 ============
test_results["end_time"] = datetime.now().isoformat()
test_results["total_duration"] = sum(s["duration_sec"] for s in test_results["steps"])

print("\n" + "=" * 70)
print("测试结果汇总")
print("=" * 70)

# 统计
success_count = len([s for s in test_results["steps"] if s["status"] == "success"])
error_count = len([s for s in test_results["steps"] if s["status"] == "error"])
warning_count = len([s for s in test_results["steps"] if s["status"] == "warning"])

print(f"总耗时: {test_results['total_duration']:.1f} 秒 ({test_results['total_duration']/60:.1f} 分钟)")
print(f"步骤统计: {success_count} 成功, {error_count} 失败, {warning_count} 警告")
print(f"错误数: {len(test_results['errors'])}")
print(f"警告数: {len(test_results['warnings'])}")

if test_results["errors"]:
    print("\n错误详情:")
    for err in test_results["errors"]:
        print(f"  - [{err['timestamp']}] {err['context']}: {err['error'][:100]}")

if test_results.get("report_path"):
    print(f"\n生成的报告: {test_results['report_path']}")
    print(f"报告大小: {test_results.get('report_size_kb', 0):.1f} KB")

# 保存测试结果到JSON
result_file = os.path.join(current_dir, "test_results.json")
with open(result_file, 'w', encoding='utf-8') as f:
    json.dump(test_results, f, ensure_ascii=False, indent=2)
print(f"\n测试结果已保存: {result_file}")

# 最终状态
if test_results["success"]:
    print("\n[SUCCESS] 测试通过!")
else:
    print("\n[FAILED] 测试存在问题，请检查错误详情")
