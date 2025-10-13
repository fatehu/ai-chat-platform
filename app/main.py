from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import httpx
import os
import json
from datetime import datetime

# ----------------------------------------------------------------------
# 核心配置：模型映射
# ----------------------------------------------------------------------
# 这是一个查找表，用于根据模型名称动态获取配置。
# 注意：确保你的 docker-compose.yml 传递了这些环境变量！
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
    title="AI Chat Platform API",
    description="核心对话API服务",
    version="1.0.0"
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 请求模型
class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]
    # 将默认模型改为 None，要求用户明确指定，以避免混淆
    model: str = "gpt-3.5-turbo" 
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 1000

class ChatResponse(BaseModel):
    message: str
    model: str
    usage: Dict[str, Any]
    vendor: str
    timestamp: str

# 健康检查接口
@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {
        "status": "healthy",
        "service": "ai-chat-api",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }

# 核心对话接口
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
                # 打印详细错误信息到控制台，便于调试
                print(f"[{vendor} API Error {response.status_code}]: {response.text}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"{vendor} API错误: {response.text}"
                )
            
            # 5. 成功响应解析
            result = response.json()
            
            return ChatResponse(
                message=result["choices"][0]["message"]["content"],
                model=result.get("model", model_name), # 使用响应中的模型名，如果不存在则用请求的模型名
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

# 根路径
@app.get("/")
async def root():
    """根路径欢迎信息"""
    return {
        "message": "欢迎使用AI聊天平台API",
        "supported_models": list(MODEL_CONFIGS.keys()),
        "docs": "/docs",
        "health": "/health",
        "chat_endpoint": "/api/v1/chat"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)