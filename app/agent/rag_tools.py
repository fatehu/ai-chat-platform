import json
from typing import Any, Dict, List, Optional
from pathlib import Path
import os
import asyncio

from .tool_base import Tool, ToolOutput, ToolCategory 
from ..services.rag_service import get_rag_service
from ..services.document_service import get_document_service

# 知识库管理和文本注入工具
class RAGManagementTool(Tool):
    """知识库管理和数据添加工具 - 用于创建、删除、列出知识库，以及直接添加文本内容（文本注入）。"""
    
    def _get_name(self) -> str:
        return "manage_knowledge_base"
    
    def _get_description(self) -> str:
        return "知识库（RAG）管理工具。可以创建、删除、列出所有知识库，或直接将文本内容分块后添加到指定知识库中（文本注入）。不用于搜索或文件上传。"
    
    def _get_category(self) -> ToolCategory:
        return ToolCategory.DATABASE
    
    def _get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "description": "操作类型：'create_kb'（创建知识库）、'delete_kb'（删除）、'list_kbs'（列出）、'add_text'（添加文本）",
                    "enum": ["create_kb", "delete_kb", "list_kbs", "add_text"]
                },
                "kb_name": {
                    "type": "string",
                    "description": "知识库名称（'list_kbs'操作时可选）"
                },
                "description": {
                    "type": "string",
                    "description": "创建知识库时的描述（仅 'create_kb' 需要）",
                    "default": ""
                },
                "text_content": {
                    "type": "string",
                    "description": "要添加到知识库的文本内容（仅 'add_text' 需要）"
                }
            },
            "required": ["operation"]
        }
    
    async def _execute(self, operation: str, kb_name: Optional[str] = None, description: str = "", text_content: str = "") -> ToolOutput:
        rag_service = get_rag_service()
        try:
            if operation == "create_kb":
                if not kb_name: raise ValueError("创建知识库时必须提供 kb_name")
                await asyncio.to_thread(rag_service.create_knowledge_base, kb_name, description)
                return ToolOutput(success=True, result=f"知识库创建成功: {kb_name}", metadata={"operation": operation})
            
            elif operation == "delete_kb":
                if not kb_name: raise ValueError("删除知识库时必须提供 kb_name")
                await asyncio.to_thread(rag_service.delete_knowledge_base, kb_name)
                return ToolOutput(success=True, result=f"知识库删除成功: {kb_name}", metadata={"operation": operation})

            elif operation == "list_kbs":
                result = await asyncio.to_thread(rag_service.list_knowledge_bases)
                formatted_list = [{
                    "name": kb["name"], 
                    "count": kb["count"], 
                    "description": kb["metadata"].get("description", "无")
                } for kb in result]
                return ToolOutput(success=True, result=formatted_list, metadata={"total": len(formatted_list), "operation": operation})
            
            elif operation == "add_text":
                if not kb_name or not text_content: raise ValueError("添加文本时必须提供 kb_name 和 text_content")
                result = await asyncio.to_thread(rag_service.add_text, kb_name, text_content)
                return ToolOutput(success=True, result=f"成功将 {result['chunks_count']} 个文本块添加到知识库 {kb_name}", metadata=result)

            else:
                return ToolOutput(success=False, result=None, error=f"不支持的操作类型: {operation}")

        except Exception as e:
            return ToolOutput(success=False, result=None, error=f"知识库管理操作失败: {str(e)}")

# 文档上传工具
class RAGDocumentUploadTool(Tool):
    """知识库文档上传工具 - 将文件（如md, pdf, txt）上传到知识库进行分块和向量化。"""
    
    def _get_name(self) -> str:
        return "upload_rag_document"
    
    def _get_description(self) -> str:
        return "将本地文件（例如 Markdown、PDF、TXT 等）内容读取并上传到指定的知识库中，进行文本分块、向量化和存储。需要文件路径和知识库名称。文件必须在 Agent 可访问的本地路径下。"
    
    def _get_category(self) -> ToolCategory:
        return ToolCategory.DATABASE
    
    def _get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "kb_name": {
                    "type": "string",
                    "description": "目标知识库名称"
                },
                "file_path": {
                    "type": "string",
                    "description": "本地文件路径，文件类型必须是系统支持的（例如：.md, .pdf, .txt）"
                }
            },
            "required": ["kb_name", "file_path"]
        }

    async def _execute(self, kb_name: str, file_path: str) -> ToolOutput:
        rag_service = get_rag_service()
        
        try:
            if not Path(file_path).exists():
                return ToolOutput(success=False, result=None, error=f"文件不存在: {file_path}")

            filename = Path(file_path).name
            file_type = Path(file_path).suffix[1:].lower() 

            if file_type not in ["pdf", "txt", "md"]:
                 return ToolOutput(success=False, result=None, error=f"不支持的文件类型: .{file_type}。目前仅支持：pdf, txt, md。")

            with open(file_path, 'rb') as f:
                file_content = f.read()

            # 异步执行文档上传
            result = await asyncio.to_thread(
                rag_service.upload_document,
                kb_name,
                file_content,
                filename,
                file_type
            )
            
            return ToolOutput(
                success=True,
                result=f"成功上传文件 '{filename}' 到知识库 '{kb_name}'，生成 {result['chunks_count']} 个文本块。",
                metadata=result
            )

        except Exception as e:
            return ToolOutput(success=False, result=None, error=f"文档上传失败: {str(e)}")

# 知识库搜索工具
class RAGSearchTool(Tool):
    """知识库搜索工具 - 在知识库中检索信息，返回相关的文档片段。"""
    
    def __init__(self, rag_service=None):
        self.rag_service = rag_service if rag_service else get_rag_service()
        super().__init__()
    
    def _get_name(self) -> str:
        return "knowledge_base_search"
    
    def _get_description(self) -> str:
        return "在知识库中搜索相关文档和信息。当需要查找已上传的文档、内部资料、历史记录时使用此工具。返回的文档片段中包含原始标题和链接等元数据。"
    
    def _get_category(self) -> ToolCategory:
        return ToolCategory.DATABASE
    
    def _get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "kb_name": {
                    "type": "string",
                    "description": "知识库名称"
                },
                "query": {
                    "type": "string",
                    "description": "搜索查询"
                },
                "top_k": {
                    "type": "integer",
                    "description": "返回的最大结果数量",
                    "default": 3
                }
            },
            "required": ["kb_name", "query"]
        }
    
    async def _execute(self, kb_name: str, query: str, top_k: int = 3) -> ToolOutput:
        try:
            result = await asyncio.to_thread(self.rag_service.search, kb_name, query, top_k)
            documents = []
            for item in result.get("results", []):
                # 限制内容长度，但确保元数据完整
                content_snippet = item.get("document", "")
                # if len(content_snippet) > 500:
                    # content_snippet = content_snippet[:500] + "..."
                    
                documents.append({
                    "content_snippet": content_snippet,
                    "metadata": item.get("metadata", {}), # 包含 original_title, original_url 等
                    "score": item.get("distance", 0)
                })
            
            return ToolOutput(
                success=True,
                result=documents,
                metadata={"kb_name": kb_name, "query": query, "count": len(documents)}
            )
            
        except Exception as e:
            return ToolOutput(success=False, result=None, error=f"知识库搜索错误: {str(e)}")