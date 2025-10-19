import asyncio
import httpx

async def test_tools():
    """测试扩展工具"""
    base_url = "http://localhost:8000"
    
    # 测试1: 获取工具列表
    print("测试1: 获取工具列表...")
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{base_url}/api/v1/agent/tools")
        tools = response.json()
        print(f"✓ 找到 {len(tools)} 个工具")
        
        # 检查扩展工具是否存在
        tool_names = [t["name"] for t in tools]
        extended_tool_names = [
            "read_file", "write_file", "process_csv",
            "convert_data_format", "calculate_statistics", "extract_urls",
            "http_request", "generate_random", "encode_decode", "validate_email"
        ]
        
        for tool_name in extended_tool_names:
            if tool_name in tool_names:
                print(f"  ✓ {tool_name}")
            else:
                print(f"  ✗ {tool_name} 未找到")
    
    # 测试2: 使用数据统计工具
    print("\n测试2: 数据统计工具...")
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{base_url}/api/v1/agent/query",
            json={
                "query": "计算这些数的平均值: 10, 20, 30, 40, 50",
                "enable_tools": ["calculate_statistics"]
            }
        )
        result = response.json()
        print(f"✓ Agent回答: {result['answer']}")
    
    # 测试3: 使用邮箱验证工具
    print("\n测试3: 邮箱验证工具...")
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{base_url}/api/v1/agent/query",
            json={
                "query": "验证邮箱 test@example.com 是否有效",
                "enable_tools": ["validate_email"]
            }
        )
        result = response.json()
        print(f"✓ Agent回答: {result['answer']}")

if __name__ == "__main__":
    asyncio.run(test_tools())