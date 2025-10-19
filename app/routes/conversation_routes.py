"""
会话管理API路由
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import os

from ..database.database import get_db
from ..database.models import Conversation, Message
from ..database.conversation_service import ConversationService
from ..services.conversational_agent import ConversationalAgent

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

router = APIRouter(prefix="/api/v1/conversations", tags=["Conversations"])


# ============================================================
# Pydantic 模型
# ============================================================

class CreateConversationRequest(BaseModel):
    """创建会话请求"""
    title: Optional[str] = "新对话"
    model: str = "deepseek-chat"
    temperature: float = 0.7
    max_tokens: int = 2000
    enable_rag: bool = False
    kb_name: Optional[str] = None
    rag_top_k: int = 3


class CreateConversationResponse(BaseModel):
    """创建会话响应"""
    session_id: str
    title: str
    model: str
    created_at: str


class SendMessageRequest(BaseModel):
    """发送消息请求"""
    message: str
    # 工具由Agent自动选择，无需用户指定


class SendMessageResponse(BaseModel):
    """发送消息响应"""
    session_id: str
    answer: str
    success: bool
    iterations: int
    execution_time: float
    rag_enabled: bool
    source_documents: List[Dict[str, Any]]
    steps: List[Dict[str, Any]]


class ConversationInfo(BaseModel):
    """会话信息"""
    session_id: str
    title: str
    model: str
    enable_rag: bool
    kb_name: Optional[str]
    message_count: int
    created_at: str
    updated_at: str


class MessageInfo(BaseModel):
    """消息信息"""
    id: int
    role: str
    content: str
    created_at: str


# ============================================================
# 工具和模型配置
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
# API 端点
# ============================================================

@router.post("/", response_model=CreateConversationResponse)
async def create_conversation(
    request: CreateConversationRequest,
    db: Session = Depends(get_db)
):
    """
    创建新会话
    
    功能:
    - 生成唯一的session_id
    - 配置模型和参数
    - 支持RAG集成
    """
    try:
        service = ConversationService(db)
        
        # 验证模型
        if request.model not in MODEL_CONFIGS:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的模型: {request.model}"
            )
        
        # 如果启用RAG,验证知识库
        if request.enable_rag and not request.kb_name:
            raise HTTPException(
                status_code=400,
                detail="启用RAG时必须指定知识库名称"
            )
        
        # 创建会话
        conversation = service.create_conversation(
            model=request.model,
            title=request.title,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            enable_rag=request.enable_rag,
            kb_name=request.kb_name,
            rag_top_k=request.rag_top_k
        )
        
        return CreateConversationResponse(
            session_id=conversation.session_id,
            title=conversation.title,
            model=conversation.model,
            created_at=conversation.created_at.isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"创建会话失败: {str(e)}"
        )


@router.post("/{session_id}/messages", response_model=SendMessageResponse)
async def send_message(
    session_id: str,
    request: SendMessageRequest,
    db: Session = Depends(get_db)
):
    """
    发送消息到会话
    
    功能:
    - 多轮对话支持，自动保持上下文
    - Agent自动判断并调用合适的工具（无需用户指定）
    - RAG集成（如果会话启用）
    - 自动保存对话历史
    
    工作流程:
    1. 用户发送消息
    2. Agent分析问题
    3. Agent自动选择需要的工具
    4. 执行工具并生成回答
    
    示例:
    ```json
    {
        "message": "帮我计算 123 * 456"
    }
    ```
    
    Agent会自动判断需要使用calculator工具，无需用户指定。
    """
    try:
        service = ConversationService(db)
        
        # 获取会话
        conversation = service.get_conversation(session_id)
        if not conversation:
            raise HTTPException(
                status_code=404,
                detail=f"会话不存在: {session_id}"
            )
        
        # 验证模型配置
        model_config = MODEL_CONFIGS.get(conversation.model)
        if not model_config or not model_config.get("api_key"):
            raise HTTPException(
                status_code=500,
                detail=f"模型 {conversation.model} 配置无效"
            )
        
        # 1. 保存用户消息
        service.add_message(
            session_id=session_id,
            role="user",
            content=request.message
        )
        
        # 2. 获取历史消息
        history = service.get_messages_as_dict(
            session_id=session_id,
            limit=20,  # 限制上下文长度
            include_system=False
        )
        
        # 3. 获取所有可用工具（Agent会自动选择）
        all_tools = get_available_tools()
        tools = list(all_tools.values())  # 提供所有工具给Agent
        
        # 4. 创建Agent并运行
        agent_config = {
            "api_key": model_config["api_key"],
            "base_url": model_config["base_url"],
            "model": conversation.model
        }
        
        agent = ConversationalAgent(
            tools=tools,
            llm_config=agent_config,
            max_iterations=10,
            temperature=conversation.temperature,
            enable_rag=conversation.enable_rag,
            kb_name=conversation.kb_name,
            rag_top_k=conversation.rag_top_k,
            verbose=True
        )
        
        result = await agent.run(
            user_message=request.message,
            conversation_history=history
        )
        
        # 5. 保存助手回复
        if result.get("success"):
            service.add_message(
                session_id=session_id,
                role="assistant",
                content=result["answer"],
                extra_data={
                    "iterations": result.get("iterations"),
                    "execution_time": result.get("execution_time"),
                    "steps": result.get("steps", [])
                }
            )
        
        return SendMessageResponse(
            session_id=session_id,
            answer=result.get("answer", ""),
            success=result.get("success", False),
            iterations=result.get("iterations", 0),
            execution_time=result.get("execution_time", 0),
            rag_enabled=result.get("rag_enabled", False),
            source_documents=result.get("source_documents", []),
            steps=result.get("steps", [])
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"发送消息失败: {str(e)}"
        )


@router.get("/", response_model=List[ConversationInfo])
async def list_conversations(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    列出所有会话
    """
    try:
        service = ConversationService(db)
        conversations = service.list_conversations(skip=skip, limit=limit)
        
        result = []
        for conv in conversations:
            result.append(ConversationInfo(
                session_id=conv.session_id,
                title=conv.title,
                model=conv.model,
                enable_rag=conv.enable_rag,
                kb_name=conv.kb_name,
                message_count=len(conv.messages),
                created_at=conv.created_at.isoformat(),
                updated_at=conv.updated_at.isoformat()
            ))
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取会话列表失败: {str(e)}"
        )


@router.get("/{session_id}")
async def get_conversation(
    session_id: str,
    db: Session = Depends(get_db)
):
    """
    获取会话详情
    """
    try:
        service = ConversationService(db)
        conversation = service.get_conversation(session_id)
        
        if not conversation:
            raise HTTPException(
                status_code=404,
                detail=f"会话不存在: {session_id}"
            )
        
        return {
            "session_id": conversation.session_id,
            "title": conversation.title,
            "model": conversation.model,
            "temperature": conversation.temperature,
            "max_tokens": conversation.max_tokens,
            "enable_rag": conversation.enable_rag,
            "kb_name": conversation.kb_name,
            "rag_top_k": conversation.rag_top_k,
            "message_count": len(conversation.messages),
            "created_at": conversation.created_at.isoformat(),
            "updated_at": conversation.updated_at.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取会话失败: {str(e)}"
        )


@router.get("/{session_id}/messages", response_model=List[MessageInfo])
async def get_messages(
    session_id: str,
    limit: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    获取会话的消息历史
    """
    try:
        service = ConversationService(db)
        
        # 验证会话存在
        conversation = service.get_conversation(session_id)
        if not conversation:
            raise HTTPException(
                status_code=404,
                detail=f"会话不存在: {session_id}"
            )
        
        messages = service.get_messages(session_id, limit=limit)
        
        return [
            MessageInfo(
                id=msg.id,
                role=msg.role,
                content=msg.content or "",
                created_at=msg.created_at.isoformat()
            )
            for msg in messages
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取消息历史失败: {str(e)}"
        )


@router.delete("/{session_id}")
async def delete_conversation(
    session_id: str,
    db: Session = Depends(get_db)
):
    """
    删除会话
    """
    try:
        service = ConversationService(db)
        
        if not service.delete_conversation(session_id):
            raise HTTPException(
                status_code=404,
                detail=f"会话不存在: {session_id}"
            )
        
        return {"message": "会话已删除", "session_id": session_id}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"删除会话失败: {str(e)}"
        )


@router.delete("/{session_id}/messages")
async def clear_messages(
    session_id: str,
    db: Session = Depends(get_db)
):
    """
    清空会话消息
    """
    try:
        service = ConversationService(db)
        
        # 验证会话存在
        conversation = service.get_conversation(session_id)
        if not conversation:
            raise HTTPException(
                status_code=404,
                detail=f"会话不存在: {session_id}"
            )
        
        count = service.clear_messages(session_id)
        
        return {
            "message": "消息已清空",
            "session_id": session_id,
            "deleted_count": count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"清空消息失败: {str(e)}"
        )


@router.patch("/{session_id}/title")
async def update_title(
    session_id: str,
    title: str,
    db: Session = Depends(get_db)
):
    """
    更新会话标题
    """
    try:
        service = ConversationService(db)
        
        if not service.update_conversation_title(session_id, title):
            raise HTTPException(
                status_code=404,
                detail=f"会话不存在: {session_id}"
            )
        
        return {
            "message": "标题已更新",
            "session_id": session_id,
            "title": title
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"更新标题失败: {str(e)}"
        )