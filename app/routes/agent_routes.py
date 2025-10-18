"""
Agent API路由
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import os

from ..agent.agent_core import ReactAgent, AgentConfig
from ..agent.basic_tools import (
    CalculatorTool,
    DateTimeTool,
    PythonREPLTool,
    WebSearchTool,
    KnowledgeBaseTool
)

from ..agent.advanced_tools import (
    WeatherTool,
    TextAnalysisTool,
    JSONParserTool,
    TimerTool,
    UnitConverterTool
)

from ..services.rag_service import get_rag_service

router = APIRouter(prefix="/api/v1/agent", tags=["Agent"])


# ============================================================
# Pydantic模型定义
# ============================================================

class AgentQueryRequest(BaseModel):
    """Agent查询请求"""
    query: str
    model: str = "deepseek-chat"
    temperature: float = 0.7
    max_iterations: int = 10
    verbose: bool = True
    enable_tools: Optional[List[str]] = None  # 启用的工具列表


class AgentQueryResponse(BaseModel):
    """Agent查询响应"""
    success: bool
    answer: str
    steps: List[Dict[str, Any]]
    iterations: int
    execution_time: float
    error: Optional[str] = None


class ToolInfo(BaseModel):
    """工具信息"""
    name: str
    description: str
    category: str
    parameters: Dict[str, Any]


# ============================================================
# 工具配置映射
# ============================================================

# 模型配置映射（从环境变量读取）
MODEL_CONFIGS = {
    "gpt-3.5-turbo": {
        "api_key": os.getenv("OPENAI_API_KEY"),
        "base_url": os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1/chat/completions"),
    },
    "gpt-4-turbo-preview": {
        "api_key": os.getenv("OPENAI_API_KEY"),
        "base_url": os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1/chat/completions"),
    },
    "deepseek-chat": {
        "api_key": os.getenv("DEEPSEEK_API_KEY"),
        "base_url": os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1/chat/completions"),
    },
    "deepseek-reasoner": {
        "api_key": os.getenv("DEEPSEEK_API_KEY"),
        "base_url": os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1/chat/completions"),
    }
}


def get_available_tools() -> Dict[str, Any]:
    """获取所有可用工具"""
    rag_service = get_rag_service()
    
    tools = {
        "calculator": CalculatorTool(),
        "get_current_time": DateTimeTool(),
        "python_repl": PythonREPLTool(),
        "web_search": WebSearchTool(),
        "knowledge_base_search": KnowledgeBaseTool(rag_service=rag_service),
        "get_weather": WeatherTool(),
        "analyze_text": TextAnalysisTool(),
        "parse_json": JSONParserTool(),
        "time_calculator": TimerTool(),
        "convert_unit": UnitConverterTool()
    }
    
    return tools


# ============================================================
# API端点
# ============================================================

@router.post("/query", response_model=AgentQueryResponse)
async def agent_query(request: AgentQueryRequest):
    """
    Agent查询接口 - 智能助手处理复杂任务
    
    使用ReAct模式：
    1. Agent分析问题
    2. 选择合适的工具
    3. 执行工具获取信息
    4. 综合信息给出答案
    
    示例问题：
    - "帮我计算 123 * 456 的结果"
    - "现在几点了？"
    - "执行Python代码：计算1到100的和"
    - "搜索Python编程的最佳实践"
    """
    try:
        # 验证模型配置
        model_name = request.model
        if model_name not in MODEL_CONFIGS:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的模型: {model_name}"
            )
        
        llm_config = MODEL_CONFIGS[model_name]
        if not llm_config.get("api_key"):
            raise HTTPException(
                status_code=500,
                detail=f"模型 {model_name} 的API密钥未设置"
            )
        
        # 获取工具
        all_tools = get_available_tools()
        
        # 根据请求筛选工具
        if request.enable_tools:
            tools = [
                all_tools[tool_name]
                for tool_name in request.enable_tools
                if tool_name in all_tools
            ]
        else:
            # 默认启用所有工具
            tools = list(all_tools.values())
        
        # 创建Agent配置
        config = AgentConfig(
            max_iterations=request.max_iterations,
            model=model_name,
            temperature=request.temperature,
            verbose=request.verbose
        )
        
        # 创建并运行Agent
        agent = ReactAgent(
            tools=tools,
            llm_config=llm_config,
            config=config
        )
        
        result = await agent.run(request.query)
        
        return AgentQueryResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Agent执行失败: {str(e)}"
        )


@router.get("/tools", response_model=List[ToolInfo])
async def list_tools():
    """
    列出所有可用工具
    """
    try:
        tools = get_available_tools()
        
        tool_infos = []
        for tool in tools.values():
            tool_infos.append(ToolInfo(
                name=tool.name,
                description=tool.description,
                category=tool.category.value,
                parameters=tool.parameters
            ))
        
        return tool_infos
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取工具列表失败: {str(e)}"
        )


@router.get("/tools/{tool_name}")
async def get_tool_info(tool_name: str):
    """
    获取特定工具的详细信息
    """
    try:
        tools = get_available_tools()
        
        if tool_name not in tools:
            raise HTTPException(
                status_code=404,
                detail=f"工具 '{tool_name}' 不存在"
            )
        
        tool = tools[tool_name]
        
        return ToolInfo(
            name=tool.name,
            description=tool.description,
            category=tool.category.value,
            parameters=tool.parameters
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取工具信息失败: {str(e)}"
        )


@router.get("/health")
async def agent_health():
    """Agent服务健康检查"""
    tools = get_available_tools()
    
    return {
        "status": "healthy",
        "service": "agent",
        "available_tools": len(tools),
        "tools": list(tools.keys())
    }