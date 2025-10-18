"""
工具系统测试脚本
运行方式: python test_tools.py
"""
import asyncio
import sys
sys.path.append('.')

from app.agent.tool_base import tool_registry, ToolRegistry
from app.agent.basic_tools import (
    CalculatorTool,
    WebSearchTool,
    DateTimeTool,
    PythonREPLTool,
    KnowledgeBaseTool
)


async def test_calculator():
    """测试计算器工具"""
    print("\n" + "="*50)
    print("测试: 计算器工具")
    print("="*50)
    
    tool = CalculatorTool()
    
    # 测试用例
    test_cases = [
        "2 + 3 * 4",
        "sqrt(16)",
        "2 ** 10",
        "pi * 2",
        "sin(0)",
        "100 / 3",
    ]
    
    for expr in test_cases:
        result = await tool.run(expression=expr)
        if result.success:
            print(f"✓ {expr} = {result.result}")
        else:
            print(f"✗ {expr}: {result.error}")


async def test_datetime():
    """测试日期时间工具"""
    print("\n" + "="*50)
    print("测试: 日期时间工具")
    print("="*50)
    
    tool = DateTimeTool()
    
    # 测试完整格式
    result = await tool.run(format="full")
    if result.success:
        print(f"✓ 完整时间信息:")
        for key, value in result.result.items():
            print(f"  {key}: {value}")
    else:
        print(f"✗ 错误: {result.error}")
    
    # 测试仅日期
    result = await tool.run(format="date")
    if result.success:
        print(f"✓ 日期: {result.result}")
    
    # 测试仅时间
    result = await tool.run(format="time")
    if result.success:
        print(f"✓ 时间: {result.result}")


async def test_python_repl():
    """测试Python REPL工具"""
    print("\n" + "="*50)
    print("测试: Python REPL工具")
    print("="*50)
    
    tool = PythonREPLTool()
    
    # 测试用例
    test_cases = [
        {
            "name": "列表求和",
            "code": "numbers = [1, 2, 3, 4, 5]\nresult = sum(numbers)"
        },
        {
            "name": "字符串处理",
            "code": "text = 'hello world'\nresult = text.upper()"
        },
        {
            "name": "数据分析",
            "code": "data = [10, 20, 30, 40, 50]\nresult = {'min': min(data), 'max': max(data), 'avg': sum(data)/len(data)}"
        }
    ]
    
    for case in test_cases:
        print(f"\n测试: {case['name']}")
        result = await tool.run(code=case['code'])
        if result.success:
            print(f"✓ 结果: {result.result}")
        else:
            print(f"✗ 错误: {result.error}")


async def test_web_search():
    """测试网络搜索工具"""
    print("\n" + "="*50)
    print("测试: 网络搜索工具")
    print("="*50)
    
    tool = WebSearchTool()
    
    result = await tool.run(query="Python programming", max_results=3)
    if result.success:
        print(f"✓ 搜索结果: {result.result}")
        print(f"  元数据: {result.metadata}")
    else:
        print(f"✗ 错误: {result.error}")


async def test_tool_registry():
    """测试工具注册中心"""
    print("\n" + "="*50)
    print("测试: 工具注册中心")
    print("="*50)
    
    # 清空注册表
    registry = ToolRegistry()
    registry.clear()
    
    # 注册工具
    tools = [
        CalculatorTool(),
        DateTimeTool(),
        PythonREPLTool(),
        WebSearchTool(),
    ]
    
    for tool in tools:
        registry.register(tool)
    
    # 测试获取工具
    print(f"\n已注册工具数量: {len(registry)}")
    print("\n工具列表:")
    for tool in registry.list_tools():
        print(f"  - {tool.name} ({tool.category.value}): {tool.description[:50]}...")
    
    # 测试获取Function Schema
    print("\n生成Function Schema (用于LLM):")
    schemas = registry.get_all_function_schemas()
    print(f"  共 {len(schemas)} 个工具可供LLM调用")
    
    # 测试工具查找
    calc_tool = registry.get_tool("calculator")
    if calc_tool:
        print(f"\n✓ 成功获取工具: {calc_tool.name}")
        result = await calc_tool.run(expression="5 * 5")
        print(f"  测试执行: 5 * 5 = {result.result}")


async def test_function_schema_generation():
    """测试Function Schema生成（用于LLM Function Calling）"""
    print("\n" + "="*50)
    print("测试: Function Schema生成")
    print("="*50)
    
    tool = CalculatorTool()
    schema = tool.to_function_schema()
    
    print("\nFunction Schema (OpenAI格式):")
    import json
    print(json.dumps(schema, indent=2, ensure_ascii=False))


async def main():
    """主测试函数"""
    print("="*60)
    print("  工具系统测试套件")
    print("="*60)
    
    # 运行所有测试
    await test_calculator()
    await test_datetime()
    await test_python_repl()
    await test_web_search()
    await test_tool_registry()
    await test_function_schema_generation()
    
    print("\n" + "="*60)
    print("  测试完成")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())