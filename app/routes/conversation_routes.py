"""
会话管理 API 路由 - 重构版本
支持动态参数配置和灵活的RAG
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from ..database.database import get_db
from ..database.conversation_service import ConversationService
from ..services.rag_service import get_rag_service
import httpx
import os

router = APIRouter(prefix="/api/v1/conversations", tags=["Conversations"])


# ============================================================
# Pydantic 模型定义
# ============================================================

class CreateConversationRequest(BaseModel):
    """创建会话请求（简化版）"""
    title: Optional[str] = "新对话"


class CreateConversationResponse(BaseModel):
    """创建会话响应"""
    session_id: str
    title: str
    created_at: str
    message: str


class SendMessageRequest(BaseModel):
    """
    发送消息请求（重构版）
    
    重构要点：
    1. 每次发送消息都可以指定模型配置
    2. 每次发送消息都可以独立决定是否使用RAG
    3. 支持Agent配置
    """
    message: str
    
    # 模型配置（可选，不指定则使用默认值）
    model: Optional[str] = "deepseek-chat"
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 2000
    
    # RAG配置（可选）
    enable_rag: Optional[bool] = False
    kb_name: Optional[str] = None
    rag_top_k: Optional[int] = 3
    
    # Agent配置（可选）
    enable_agent: Optional[bool] = False
    agent_max_iterations: Optional[int] = 10
    agent_enable_tools: Optional[List[str]] = None


class SendMessageResponse(BaseModel):
    """发送消息响应"""
    session_id: str
    user_message: Dict[str, Any]
    assistant_message: Dict[str, Any]
    rag_info: Optional[Dict[str, Any]] = None
    agent_info: Optional[Dict[str, Any]] = None


class ConversationInfo(BaseModel):
    """会话信息"""
    session_id: str
    title: str
    created_at: str
    updated_at: str
    message_count: int


class MessageInfo(BaseModel):
    """消息信息"""
    id: int
    role: str
    content: str
    created_at: str
    has_config: bool
    has_rag: bool
    has_agent: bool


# ============================================================
# 模型配置
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
    },
    # DashScope 模型配置 (Qwen系列)
    "qwen-turbo": {
        "api_key": os.getenv("DASHSCOPE_API_KEY"),
        "base_url": os.getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
    },
    "qwen-plus": {
        "api_key": os.getenv("DASHSCOPE_API_KEY"),
        "base_url": os.getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
    },
    "qwen-max": {
        "api_key": os.getenv("DASHSCOPE_API_KEY"),
        "base_url": os.getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
    }
}


# ============================================================
# API 端点
# ============================================================

@router.post("/", response_model=CreateConversationResponse)
async def create_conversation(
    request: CreateConversationRequest,
    db: Session = Depends(get_db)
):
    """
    创建新会话（简化版）
    
    重构说明：
    - 不再需要指定模型、温度等参数
    - 这些参数将在每次发送消息时动态指定
    """
    try:
        service = ConversationService(db)
        conversation = service.create_conversation(title=request.title)
        
        return CreateConversationResponse(
            session_id=conversation.session_id,
            title=conversation.title,
            created_at=conversation.created_at.isoformat(),
            message="会话创建成功"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{session_id}/messages", response_model=SendMessageResponse)
async def send_message(
    session_id: str,
    request: SendMessageRequest,
    db: Session = Depends(get_db)
):
    """
    发送消息到会话（重构版）
    
    重构亮点：
    1. 每次发送都可以指定不同的模型配置
    2. 可以动态决定是否使用RAG和使用哪个知识库
    3. 支持Agent模式
    
    工作流程：
    1. 验证会话是否存在
    2. 如果启用RAG，检索知识库
    3. 构建消息历史（包含RAG上下文）
    4. 调用LLM生成回复
    5. 保存用户消息和助手回复（包含配置和RAG信息）
    """
    try:
        service = ConversationService(db)
        
        # 1. 验证会话
        conversation = service.get_conversation(session_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        # 2. 验证模型配置
        if request.model not in MODEL_CONFIGS:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的模型: {request.model}"
            )
        
        llm_config = MODEL_CONFIGS[request.model]
        if not llm_config.get("api_key"):
            raise HTTPException(
                status_code=500,
                detail=f"模型 {request.model} 的API密钥未设置"
            )
        
        # 3. RAG检索（如果启用）
        rag_context = None
        source_documents = []
        rag_info = None
        
        if request.enable_rag and request.kb_name:
            try:
                rag_service = get_rag_service()
                rag_result = rag_service.rag_query(
                    kb_name=request.kb_name,
                    query=request.message,
                    top_k=request.rag_top_k
                )
                
                rag_context = rag_result.get("context", "")
                source_documents = rag_result.get("source_documents", [])
                
                rag_info = {
                    "enabled": True,
                    "kb_name": request.kb_name,
                    "top_k": request.rag_top_k,
                    "documents_found": len(source_documents)
                }
                
            except Exception as e:
                print(f"RAG检索失败: {str(e)}")
                # RAG失败不影响对话，继续执行
        
        # 4. 构建消息历史
        history_messages = service.get_messages_as_dict(session_id)
        
        # 构建LLM请求消息
        llm_messages = []
        
        # 添加系统提示（如果有RAG上下文）
        if rag_context:
            system_prompt = f"""你是一个智能助手。请根据以下参考知识回答用户的问题。

参考知识：
{rag_context}

回答要求：
1. 优先使用参考知识中的信息
2. 如果参考知识中没有相关信息，可以使用你的知识回答
3. 回答要准确、清晰、有条理"""
            
            llm_messages.append({
                "role": "system",
                "content": system_prompt
            })
        
        # 添加历史消息
        llm_messages.extend(history_messages)
        
        # 添加当前用户消息
        llm_messages.append({
            "role": "user",
            "content": request.message
        })
        
        # 5. 调用LLM
        payload = {
            "model": request.model,
            "messages": llm_messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                llm_config["base_url"],
                headers={
                    "Authorization": f"Bearer {llm_config['api_key']}",
                    "Content-Type": "application/json"
                },
                json=payload
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"LLM调用失败: {response.text}"
                )
            
            result = response.json()
            assistant_content = result["choices"][0]["message"]["content"]
        
        # 6. 保存用户消息（包含配置）
        model_config = {
            "model": request.model,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens
        }
        
        rag_config = None
        if request.enable_rag and request.kb_name:
            rag_config = {
                "enabled": True,
                "kb_name": request.kb_name,
                "top_k": request.rag_top_k,
                "context": rag_context[:500] if rag_context else None,  # 只保存前500字符
                "source_documents": source_documents
            }
        
        user_msg = service.add_message(
            session_id=session_id,
            role="user",
            content=request.message,
            model_config=model_config,
            rag_config=rag_config
        )
        
        # 7. 保存助手回复
        assistant_msg = service.add_message(
            session_id=session_id,
            role="assistant",
            content=assistant_content,
            model_config=model_config
        )
        
        # 8. 构建响应
        return SendMessageResponse(
            session_id=session_id,
            user_message={
                "id": user_msg.id,
                "role": user_msg.role,
                "content": user_msg.content,
                "created_at": user_msg.created_at.isoformat()
            },
            assistant_message={
                "id": assistant_msg.id,
                "role": assistant_msg.role,
                "content": assistant_msg.content,
                "created_at": assistant_msg.created_at.isoformat()
            },
            rag_info=rag_info
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"发送消息失败: {str(e)}")


@router.get("/", response_model=List[ConversationInfo])
async def list_conversations(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """列出所有会话"""
    try:
        service = ConversationService(db)
        conversations = service.list_conversations(skip=skip, limit=limit)
        
        result = []
        for conv in conversations:
            result.append(ConversationInfo(
                session_id=conv.session_id,
                title=conv.title,
                created_at=conv.created_at.isoformat(),
                updated_at=conv.updated_at.isoformat(),
                message_count=len(conv.messages)
            ))
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{session_id}")
async def get_conversation(
    session_id: str,
    db: Session = Depends(get_db)
):
    """获取会话详情（包含统计信息）"""
    try:
        service = ConversationService(db)
        summary = service.get_conversation_summary(session_id)
        
        if not summary:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        return summary
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{session_id}/messages", response_model=List[MessageInfo])
async def get_messages(
    session_id: str,
    limit: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """获取会话的消息历史"""
    try:
        service = ConversationService(db)
        
        # 验证会话
        conversation = service.get_conversation(session_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        messages = service.get_messages(session_id, limit=limit)
        
        result = []
        for msg in messages:
            result.append(MessageInfo(
                id=msg.id,
                role=msg.role,
                content=msg.content,
                created_at=msg.created_at.isoformat(),
                has_config=msg.extra_data and "config" in msg.extra_data if msg.extra_data else False,
                has_rag=msg.extra_data and "rag" in msg.extra_data if msg.extra_data else False,
                has_agent=msg.extra_data and "agent" in msg.extra_data if msg.extra_data else False
            ))
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{session_id}")
async def delete_conversation(
    session_id: str,
    db: Session = Depends(get_db)
):
    """删除会话"""
    try:
        service = ConversationService(db)
        success = service.delete_conversation(session_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        return {"message": "会话删除成功", "session_id": session_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{session_id}/title")
async def update_title(
    session_id: str,
    title: str,
    db: Session = Depends(get_db)
):
    """更新会话标题"""
    try:
        service = ConversationService(db)
        success = service.update_conversation_title(session_id, title)
        
        if not success:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        return {"message": "标题更新成功", "session_id": session_id, "title": title}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{session_id}/messages")
async def clear_messages(
    session_id: str,
    db: Session = Depends(get_db)
):
    """清空会话消息"""
    try:
        service = ConversationService(db)
        
        # 验证会话
        conversation = service.get_conversation(session_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        count = service.clear_messages(session_id)
        
        return {
            "message": "消息清空成功",
            "session_id": session_id,
            "cleared_count": count
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))