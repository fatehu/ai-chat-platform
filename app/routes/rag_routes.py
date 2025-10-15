"""
RAG 相关的 API 路由
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from ..services.rag_service import get_rag_service

router = APIRouter(prefix="/api/v1/rag", tags=["RAG"])


# ============================================================
# Pydantic 模型定义
# ============================================================

class CreateKnowledgeBaseRequest(BaseModel):
    """创建知识库请求"""
    kb_name: str
    description: Optional[str] = ""


class AddTextRequest(BaseModel):
    """添加文本请求"""
    kb_name: str
    text: str
    metadata: Optional[Dict[str, Any]] = None


class SearchRequest(BaseModel):
    """搜索请求"""
    kb_name: str
    query: str
    top_k: Optional[int] = 5


class RAGQueryRequest(BaseModel):
    """RAG查询请求"""
    kb_name: str
    query: str
    top_k: Optional[int] = 3


# ============================================================
# API 端点
# ============================================================

@router.post("/knowledge-bases")
async def create_knowledge_base(request: CreateKnowledgeBaseRequest):
    """
    创建知识库
    """
    try:
        rag_service = get_rag_service()
        result = rag_service.create_knowledge_base(
            kb_name=request.kb_name,
            description=request.description
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/knowledge-bases")
async def list_knowledge_bases():
    """
    列出所有知识库
    """
    try:
        rag_service = get_rag_service()
        result = rag_service.list_knowledge_bases()
        return {"knowledge_bases": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/knowledge-bases/{kb_name}")
async def get_knowledge_base_info(kb_name: str):
    """
    获取知识库详细信息
    """
    try:
        rag_service = get_rag_service()
        result = rag_service.get_knowledge_base_info(kb_name)
        return result
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/knowledge-bases/{kb_name}")
async def delete_knowledge_base(kb_name: str):
    """
    删除知识库
    """
    try:
        rag_service = get_rag_service()
        result = rag_service.delete_knowledge_base(kb_name)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload")
async def upload_document(
    kb_name: str = Form(...),
    file: UploadFile = File(...)
):
    """
    上传文档到知识库
    支持的文件类型: PDF, TXT, MD
    """
    try:
        # 验证文件类型
        file_ext = file.filename.split(".")[-1].lower()
        if file_ext not in ["pdf", "txt", "md"]:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件类型: {file_ext}。支持的类型: pdf, txt, md"
            )
        
        # 读取文件内容
        file_content = await file.read()
        
        # 上传文档
        rag_service = get_rag_service()
        result = rag_service.upload_document(
            kb_name=kb_name,
            file_content=file_content,
            filename=file.filename,
            file_type=file_ext
        )
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/add-text")
async def add_text(request: AddTextRequest):
    """
    直接添加文本到知识库
    """
    try:
        rag_service = get_rag_service()
        result = rag_service.add_text(
            kb_name=request.kb_name,
            text=request.text,
            metadata=request.metadata
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search")
async def search(request: SearchRequest):
    """
    在知识库中搜索相关文档
    """
    try:
        rag_service = get_rag_service()
        result = rag_service.search(
            kb_name=request.kb_name,
            query=request.query,
            top_k=request.top_k
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/query")
async def rag_query(request: RAGQueryRequest):
    """
    RAG查询：检索相关文档并返回上下文
    用于与LLM结合生成答案
    """
    try:
        rag_service = get_rag_service()
        result = rag_service.rag_query(
            kb_name=request.kb_name,
            query=request.query,
            top_k=request.top_k
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))