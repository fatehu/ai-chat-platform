"""
Agent API路由 - 重构版本
支持会话模式和动态RAG配置
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
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
from ..database.database import get_db
from ..database.conversation_service import ConversationService
from ..services.conversational_agent import ConversationalAgent

router = APIRouter(prefix="/api/v1/agent", tags=["Agent"])


# ============================================================
# Pydantic模型定义
# ============================================================

class AgentQueryRequest(BaseModel):
    """Agent查询请求（无状态）"""
    query: str
    model: str = "deepseek-chat"
    temperature: float = 0.7
    max_iterations: int = 10
    verbose: bool = True
    enable_tools: Optional[List[str]] = None
    # 新增：RAG配置
    enable_rag: bool = False
    kb_name: Optional[str] = None
    rag_top_k: int = 3


class AgentConversationRequest(BaseModel):
    """
    Agent会话请求（重构版）
    
    支持：
    1. 会话历史
    2. 动态RAG配置
    3. 工具选择
    """
    message: str
    model: str = "deepseek-chat"
    temperature: float = 0.7
    max_iterations: int = 10
    verbose: bool = True
    enable_tools: Optional[List[str]] = None
    
    # 动态RAG配置
    enable_rag: bool = False
    kb_name: Optional[str] = None
    rag_top_k: int = 3


class AgentQueryResponse(BaseModel):
    """Agent查询响应"""
    success: bool
    answer: str
    steps: List[Dict[str, Any]]
    iterations: int
    execution_time: float
    rag_enabled: bool
    rag_kb_name: Optional[str] = None
    source_documents: List[Dict[str, Any]] = []
    error: Optional[str] = None


class AgentConversationResponse(BaseModel):
    """Agent会话响应"""
    session_id: str
    success: bool
    answer: str
    steps: List[Dict[str, Any]]
    iterations: int
    execution_time: float
    rag_enabled: bool
    rag_kb_name: Optional[str] = None
    source_documents: List[Dict[str, Any]] = []
    error: Optional[str] = None


class ToolInfo(BaseModel):
    """工具信息"""
    name: str
    description: str
    category: str
    parameters: Dict[str, Any]


# ============================================================
# 模型配置映射
# ============================================================

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
    Agent查询接口（无状态）
    
    使用ReAct模式智能处理任务
    支持动态RAG配置
    
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
        llm_config["model"] = model_name
        
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
        
        # 如果启用RAG，需要先检索
        rag_context = None
        source_documents = []
        
        if request.enable_rag and request.kb_name:
            try:
                rag_service = get_rag_service()
                rag_result = rag_service.rag_query(
                    kb_name=request.kb_name,
                    query=request.query,
                    top_k=request.rag_top_k
                )
                rag_context = rag_result.get("context", "")
                source_documents = rag_result.get("source_documents", [])
                
                # 将RAG上下文添加到查询中
                enhanced_query = f"""请基于以下参考知识回答问题：

参考知识：
{rag_context}

用户问题：{request.query}"""
                
                result = await agent.run(enhanced_query)
            except Exception as e:
                print(f"RAG检索失败: {str(e)}")
                result = await agent.run(request.query)
        else:
            result = await agent.run(request.query)
        
        # 添加RAG信息到结果
        result["rag_enabled"] = request.enable_rag
        result["rag_kb_name"] = request.kb_name if request.enable_rag else None
        result["source_documents"] = source_documents
        
        return AgentQueryResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Agent执行失败: {str(e)}"
        )


@router.post("/conversation/{session_id}/query", response_model=AgentConversationResponse)
async def agent_conversation_query(
    session_id: str,
    request: AgentConversationRequest,
    db: Session = Depends(get_db)
):
    """
    Agent会话查询接口（重构版）
    
    特点：
    1. 支持多轮对话
    2. 每次消息可以动态配置RAG
    3. 保存对话历史
    4. 支持工具调用
    
    工作流程：
    1. 获取会话历史
    2. 如果启用RAG，检索知识库
    3. 使用ConversationalAgent处理
    4. 保存消息和结果
    """
    try:
        # 验证会话
        service = ConversationService(db)
        conversation = service.get_conversation(session_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        # 验证模型配置
        model_name = request.model
        if model_name not in MODEL_CONFIGS:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的模型: {model_name}"
            )
        
        llm_config = MODEL_CONFIGS[model_name]
        llm_config["model"] = model_name
        
        if not llm_config.get("api_key"):
            raise HTTPException(
                status_code=500,
                detail=f"模型 {model_name} 的API密钥未设置"
            )
        
        # 获取工具
        all_tools = get_available_tools()
        
        if request.enable_tools:
            tools = [
                all_tools[tool_name]
                for tool_name in request.enable_tools
                if tool_name in all_tools
            ]
        else:
            tools = list(all_tools.values())
        
        # 创建ConversationalAgent
        agent = ConversationalAgent(
            tools=tools,
            llm_config=llm_config,
            max_iterations=request.max_iterations,
            temperature=request.temperature,
            verbose=request.verbose
        )
        
        # 获取会话历史
        conversation_history = service.get_messages_as_dict(session_id)
        
        # 运行Agent（传入动态RAG配置）
        result = await agent.run(
            user_message=request.message,
            conversation_history=conversation_history,
            enable_rag=request.enable_rag,
            kb_name=request.kb_name,
            rag_top_k=request.rag_top_k
        )
        
        # 保存用户消息
        model_config = {
            "model": request.model,
            "temperature": request.temperature
        }
        
        rag_config = None
        if request.enable_rag and request.kb_name:
            rag_config = {
                "enabled": True,
                "kb_name": request.kb_name,
                "top_k": request.rag_top_k,
                "source_documents": result.get("source_documents", [])
            }
        
        agent_config = {
            "enabled": True,
            "max_iterations": request.max_iterations,
            "enable_tools": request.enable_tools or list(all_tools.keys())
        }
        
        service.add_message(
            session_id=session_id,
            role="user",
            content=request.message,
            model_config=model_config,
            rag_config=rag_config,
            agent_config=agent_config
        )
        
        # 保存助手回复
        service.add_message(
            session_id=session_id,
            role="assistant",
            content=result["answer"],
            model_config=model_config,
            custom_data={
                "agent_steps": result.get("steps", []),
                "iterations": result.get("iterations", 0),
                "execution_time": result.get("execution_time", 0)
            }
        )
        
        # 构建响应
        response_data = {
            "session_id": session_id,
            **result
        }
        
        return AgentConversationResponse(**response_data)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Agent会话查询失败: {str(e)}"
        )


@router.get("/tools", response_model=List[ToolInfo])
async def list_tools():
    """列出所有可用工具"""
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
    """获取特定工具的详细信息"""
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
        "version": "2.0.0",
        "features": [
            "stateless_query",
            "conversational_mode",
            "dynamic_rag",
            "function_calling",
            "multi_tools"
        ],
        "available_tools": len(tools),
        "tools": list(tools.keys())
    }