"""
Agent功能测试脚本
运行方式: python test_agent.py
"""
import asyncio
import sys
import os
sys.path.append('.')

from dotenv import load_dotenv
load_dotenv()

from app.agent.agent_core import ReactAgent, AgentConfig
from app.agent.basic_tools import (
    CalculatorTool,
    DateTimeTool,
    PythonREPLTool,
    WebSearchTool
)


# 测试用例
TEST_CASES = [
    {
        "name": "简单计算",
        "query": "帮我计算 (123 + 456) * 789 的结果",
        "expected_tool": "calculator"
    },
    {
        "name": "获取时间",
        "query": "现在几点了？今天是星期几？",
        "expected_tool": "get_current_time"
    },
    {
        "name": "Python代码执行",
        "query": "用Python计算1到100的和",
        "expected_tool": "python_repl"
    },
    {
        "name": "复杂推理",
        "query": "如果一个正方形的边长是5，那么它的面积是多少？然后告诉我这个面积的平方根是多少。",
        "expected_tool": "calculator"
    },
    {
        "name": "多步骤任务",
        "query": "现在是几点？然后帮我计算从现在开始，3小时后是几点（假设现在是下午2点）。",
        "expected_tool": ["get_current_time", "calculator"]
    }
]


async def test_agent_basic():
    """测试Agent基本功能"""
    print("\n" + "="*70)
    print("  测试1: Agent基本功能")
    print("="*70)
    
    # 配置LLM（使用DeepSeek）
    llm_config = {
        "api_key": os.getenv("DEEPSEEK_API_KEY"),
        "base_url": os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1/chat/completions")
    }
    
    if not llm_config["api_key"]:
        print("❌ 错误: DEEPSEEK_API_KEY 未设置")
        print("请在 .env 文件中设置 DEEPSEEK_API_KEY")
        return
    
    # 创建工具列表
    tools = [
        CalculatorTool(),
        DateTimeTool(),
        PythonREPLTool(),
    ]
    
    # 创建Agent配置
    config = AgentConfig(
        max_iterations=5,
        model="deepseek-chat",
        temperature=0.7,
        verbose=True
    )
    
    # 创建Agent
    agent = ReactAgent(
        tools=tools,
        llm_config=llm_config,
        config=config
    )
    
    # 测试简单查询
    query = "帮我计算 155 * 2 的结果"
    print(f"\n📝 用户问题: {query}\n")
    
    result = await agent.run(query)
    
    print(f"\n{'='*70}")
    print(f"执行结果:")
    print(f"  成功: {result['success']}")
    print(f"  答案: {result['answer']}")
    print(f"  迭代次数: {result['iterations']}")
    print(f"  执行时间: {result['execution_time']:.2f}秒")
    if result.get('error'):
        print(f"  错误: {result['error']}")
    print(f"{'='*70}\n")


async def test_agent_with_multiple_tools():
    """测试Agent使用多个工具"""
    print("\n" + "="*70)
    print("  测试2: Agent使用多个工具")
    print("="*70)
    
    llm_config = {
        "api_key": os.getenv("DEEPSEEK_API_KEY"),
        "base_url": os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1/chat/completions")
    }
    
    if not llm_config["api_key"]:
        print("❌ 错误: DEEPSEEK_API_KEY 未设置")
        return
    
    tools = [
        CalculatorTool(),
        DateTimeTool(),
        PythonREPLTool(),
    ]
    
    config = AgentConfig(
        max_iterations=10,
        model="deepseek-chat",
        temperature=0.7,
        verbose=True
    )
    
    agent = ReactAgent(
        tools=tools,
        llm_config=llm_config,
        config=config
    )
    
    # 需要多步推理的问题
    query = "现在是几点？然后用Python计算一个列表[10, 20, 30, 40, 50]的平均值。"
    print(f"\n📝 用户问题: {query}\n")
    
    result = await agent.run(query)
    
    print(f"\n{'='*70}")
    print(f"执行结果:")
    print(f"  成功: {result['success']}")
    print(f"  答案: {result['answer']}")
    print(f"  迭代次数: {result['iterations']}")
    print(f"  执行时间: {result['execution_time']:.2f}秒")
    print(f"\n  执行步骤:")
    for i, step in enumerate(result['steps'], 1):
        print(f"    步骤{i}:")
        print(f"      动作: {step.get('action', 'N/A')}")
        print(f"      输入: {step.get('action_input', 'N/A')}")
        if step.get('observation'):
            obs = step['observation']
            if len(obs) > 100:
                obs = obs[:100] + "..."
            print(f"      观察: {obs}")
    print(f"{'='*70}\n")


async def test_all_cases():
    """运行所有测试用例"""
    print("\n" + "="*70)
    print("  测试3: 批量测试用例")
    print("="*70)
    
    llm_config = {
        "api_key": os.getenv("DEEPSEEK_API_KEY"),
        "base_url": os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1/chat/completions")
    }
    
    if not llm_config["api_key"]:
        print("❌ 错误: DEEPSEEK_API_KEY 未设置")
        return
    
    tools = [
        CalculatorTool(),
        DateTimeTool(),
        PythonREPLTool(),
    ]
    
    config = AgentConfig(
        max_iterations=10,
        model="deepseek-chat",
        temperature=0.7,
        verbose=False  # 批量测试时关闭详细日志
    )
    
    results = []
    
    for i, test_case in enumerate(TEST_CASES[:3], 1):  # 只测试前3个用例
        print(f"\n--- 测试用例 {i}/{3}: {test_case['name']} ---")
        print(f"问题: {test_case['query']}")
        
        agent = ReactAgent(
            tools=tools,
            llm_config=llm_config,
            config=config
        )
        
        result = await agent.run(test_case['query'])
        
        results.append({
            "name": test_case['name'],
            "success": result['success'],
            "iterations": result['iterations'],
            "time": result['execution_time']
        })
        
        print(f"结果: {'✓ 成功' if result['success'] else '✗ 失败'}")
        print(f"答案: {result['answer'][:100]}...")
        print(f"迭代: {result['iterations']} 次, 耗时: {result['execution_time']:.2f}秒")
    
    # 汇总统计
    print(f"\n{'='*70}")
    print("测试统计:")
    success_count = sum(1 for r in results if r['success'])
    print(f"  总计: {len(results)} 个测试")
    print(f"  成功: {success_count} 个")
    print(f"  失败: {len(results) - success_count} 个")
    avg_time = sum(r['time'] for r in results) / len(results)
    print(f"  平均耗时: {avg_time:.2f}秒")
    print(f"{'='*70}\n")


async def main():
    """主测试函数"""
    print("="*70)
    print("  Agent系统测试套件")
    print("="*70)
    
    # 检查环境变量
    if not os.getenv("DEEPSEEK_API_KEY"):
        print("\n❌ 错误: DEEPSEEK_API_KEY 环境变量未设置")
        print("\n请按以下步骤操作:")
        print("1. 复制 .env.example 到 .env")
        print("2. 在 .env 文件中填入你的 DEEPSEEK_API_KEY")
        print("3. 重新运行测试")
        return
    
    # 运行测试
    try:
        await test_agent_basic()
        await test_agent_with_multiple_tools()
        await test_all_cases()
        
        print("\n" + "="*70)
        print("  ✓ 所有测试完成")
        print("="*70)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())