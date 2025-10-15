from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import httpx
import os
import json
from datetime import datetime
from dotenv import load_dotenv

# 导入 RAG 路由和服务
from app.routes.rag_routes import router as rag_router
from app.services.rag_service import get_rag_service

# 加载环境变量
load_dotenv()

# ----------------------------------------------------------------------
# 核心配置：模型映射
# ----------------------------------------------------------------------
MODEL_CONFIGS = {
    # OpenAI 模型配置
    "gpt-3.5-turbo": {
        "api_key": os.getenv("OPENAI_API_KEY"),
        "base_url": os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1/chat/completions"),
        "vendor": "OpenAI"
    },
    "gpt-4-turbo-preview": {
        "api_key": os.getenv("OPENAI_API_KEY"),
        "base_url": os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1/chat/completions"),
        "vendor": "OpenAI"
    },
    # DeepSeek 模型配置
    "deepseek-chat": {
        "api_key": os.getenv("DEEPSEEK_API_KEY"),
        "base_url": os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1/chat/completions"),
        "vendor": "DeepSeek"
    },
    "deepseek-reasoner": {
        "api_key": os.getenv("DEEPSEEK_API_KEY"),
        "base_url": os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1/chat/completions"),
        "vendor": "DeepSeek"
    }
}


app = FastAPI(
    title="AI Chat Platform API with RAG",
    description="核心对话API服务（支持RAG）",
    version="2.0.0"
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册 RAG 路由
app.include_router(rag_router)

# ============================================================
# Pydantic 模型
# ============================================================

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]
    model: str = "gpt-3.5-turbo" 
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 1000

class ChatResponse(BaseModel):
    message: str
    model: str
    usage: Dict[str, Any]
    vendor: str
    timestamp: str

class RAGChatRequest(BaseModel):
    """RAG 聊天请求"""
    kb_name: str  # 知识库名称
    query: str  # 用户问题
    model: str = "gpt-3.5-turbo"
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 1000
    top_k: Optional[int] = 3  # 检索文档数量

class RAGChatResponse(BaseModel):
    """RAG 聊天响应"""
    answer: str
    model: str
    kb_name: str
    source_documents: List[Dict[str, Any]]
    usage: Dict[str, Any]
    vendor: str
    timestamp: str

# ============================================================
# API 端点
# ============================================================

@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {
        "status": "healthy",
        "service": "ai-chat-api-with-rag",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "2.0.0",
        "features": ["chat", "rag"]
    }


@app.post("/api/v1/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    核心对话接口：根据请求的模型动态选择 API 服务商和密钥。
    """
    
    # 1. 模型选择和配置获取
    model_name = request.model
    config = MODEL_CONFIGS.get(model_name)
    
    if not config:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的模型: {model_name}。请使用以下支持的模型：{list(MODEL_CONFIGS.keys())}"
        )

    api_key = config["api_key"]
    base_url = config["base_url"]
    vendor = config["vendor"]
    
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail=f"模型 {model_name} (供应商: {vendor}) 的 API 密钥未设置或无效。"
        )
    
    # 2. 准备请求数据
    llm_request_payload = {
        "model": model_name,
        "messages": [{"role": msg.role, "content": msg.content} for msg in request.messages],
        "temperature": request.temperature,
        "max_tokens": request.max_tokens
    }
    
    # 3. 调用 API
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                base_url,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json=llm_request_payload
            )
            
            # 4. 错误处理
            if response.status_code != 200:
                print(f"[{vendor} API Error {response.status_code}]: {response.text}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"{vendor} API错误: {response.text}"
                )
            
            # 5. 成功响应解析
            result = response.json()
            
            return ChatResponse(
                message=result["choices"][0]["message"]["content"],
                model=result.get("model", model_name),
                usage=result.get("usage", {}),
                vendor=vendor,
                timestamp=datetime.utcnow().isoformat()
            )
            
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail=f"请求 {vendor} API 超时"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"处理请求时发生未知错误: {str(e)}"
        )


@app.post("/api/v1/rag-chat", response_model=RAGChatResponse)
async def rag_chat(request: RAGChatRequest):
    """
    RAG 聊天接口：结合知识库检索和 LLM 生成答案
    
    流程：
    1. 从知识库检索相关文档
    2. 构建带上下文的提示词
    3. 调用 LLM 生成答案
    """
    
    try:
        # 1. RAG 查询：检索相关文档
        rag_service = get_rag_service()
        rag_result = rag_service.rag_query(
            kb_name=request.kb_name,
            query=request.query,
            top_k=request.top_k
        )
        
        context = rag_result["context"]
        source_documents = rag_result["source_documents"]
        
        # 2. 构建提示词
        system_prompt = """你是一个智能助手。请根据提供的参考文档回答用户的问题。
如果参考文档中没有相关信息，请明确告知用户。
请始终基于参考文档的内容进行回答，不要编造信息。"""
        
        user_prompt = f"""参考文档：
{context}

用户问题：{request.query}

请基于上述参考文档回答用户的问题。"""
        
        # 3. 调用 LLM
        chat_request = ChatRequest(
            messages=[
                Message(role="system", content=system_prompt),
                Message(role="user", content=user_prompt)
            ],
            model=request.model,
            temperature=request.temperature,
            max_tokens=request.max_tokens
        )
        
        chat_response = await chat(chat_request)
        
        # 4. 返回结果
        return RAGChatResponse(
            answer=chat_response.message,
            model=chat_response.model,
            kb_name=request.kb_name,
            source_documents=source_documents,
            usage=chat_response.usage,
            vendor=chat_response.vendor,
            timestamp=chat_response.timestamp
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"RAG 聊天失败: {str(e)}"
        )


@app.get("/")
async def root():
    """根路径欢迎信息"""
    return {
        "message": "欢迎使用AI聊天平台API (支持RAG)",
        "version": "2.0.0",
        "supported_models": list(MODEL_CONFIGS.keys()),
        "endpoints": {
            "docs": "/docs",
            "health": "/health",
            "chat": "/api/v1/chat",
            "rag_chat": "/api/v1/rag-chat",
            "rag_api": "/api/v1/rag"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)