"""
基础工具实现 - 常用工具集合
"""
import math
import json
from typing import Any, Dict, List
from datetime import datetime
import httpx
from .tool_base import Tool, ToolOutput, ToolCategory


class CalculatorTool(Tool):
    """计算器工具 - 执行数学计算"""
    
    def _get_name(self) -> str:
        return "calculator"
    
    def _get_description(self) -> str:
        return "执行数学计算。支持基本运算（+、-、*、/）、幂运算（**）、开方（sqrt）等。输入一个数学表达式，返回计算结果。"
    
    def _get_category(self) -> ToolCategory:
        return ToolCategory.CALCULATION
    
    def _get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "要计算的数学表达式，例如：'2 + 3 * 4'、'sqrt(16)'、'2 ** 10'"
                }
            },
            "required": ["expression"]
        }
    
    async def _execute(self, expression: str) -> ToolOutput:
        """执行计算"""
        try:
            # 安全的数学函数白名单
            safe_dict = {
                "sqrt": math.sqrt,
                "pow": math.pow,
                "sin": math.sin,
                "cos": math.cos,
                "tan": math.tan,
                "log": math.log,
                "pi": math.pi,
                "e": math.e,
                "abs": abs,
                "round": round,
            }
            
            # 使用eval但限制命名空间（安全措施）
            result = eval(expression, {"__builtins__": {}}, safe_dict)
            
            return ToolOutput(
                success=True,
                result=result,
                metadata={
                    "expression": expression,
                    "result_type": type(result).__name__
                }
            )
        except Exception as e:
            return ToolOutput(
                success=False,
                result=None,
                error=f"计算错误: {str(e)}"
            )


class WebSearchTool(Tool):
    """网络搜索工具 - 使用DuckDuckGo搜索（无需API密钥）"""
    
    def _get_name(self) -> str:
        return "web_search"
    
    def _get_description(self) -> str:
        return "在互联网上搜索信息。当需要获取最新信息、查找资料、了解实时数据时使用此工具。返回搜索结果摘要。"
    
    def _get_category(self) -> ToolCategory:
        return ToolCategory.SEARCH
    
    def _get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索关键词或问题"
                },
                "max_results": {
                    "type": "integer",
                    "description": "返回的最大结果数量",
                    "default": 5
                }
            },
            "required": ["query"]
        }
    
    async def _execute(self, query: str, max_results: int = 5) -> ToolOutput:
        """执行搜索"""
        try:
            # 使用DuckDuckGo的HTML搜索（简单实现）
            url = "https://html.duckduckgo.com/html/"
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    url,
                    data={"q": query}
                )
                
                if response.status_code == 200:
                    # 简化的搜索结果解析（实际项目中使用专业的搜索API）
                    return ToolOutput(
                        success=True,
                        result=f"搜索'{query}'的结果已找到（演示模式：实际项目中应集成真实搜索API）",
                        metadata={
                            "query": query,
                            "search_engine": "DuckDuckGo",
                            "note": "演示版本，建议集成 SerpAPI 或 Brave Search API"
                        }
                    )
                else:
                    return ToolOutput(
                        success=False,
                        result=None,
                        error=f"搜索失败，HTTP状态码: {response.status_code}"
                    )
                    
        except Exception as e:
            return ToolOutput(
                success=False,
                result=None,
                error=f"搜索错误: {str(e)}"
            )


class KnowledgeBaseTool(Tool):
    """知识库搜索工具 - 利用现有RAG系统"""
    
    def __init__(self, rag_service=None):
        self.rag_service = rag_service
        super().__init__()
    
    def _get_name(self) -> str:
        return "knowledge_base_search"
    
    def _get_description(self) -> str:
        return "在知识库中搜索相关文档和信息。当需要查找已上传的文档、内部资料、历史记录时使用此工具。"
    
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
        """执行知识库搜索"""
        try:
            if not self.rag_service:
                return ToolOutput(
                    success=False,
                    result=None,
                    error="RAG服务未初始化"
                )
            
            # 调用现有的RAG服务
            result = self.rag_service.search(
                kb_name=kb_name,
                query=query,
                top_k=top_k
            )
            
            # 格式化结果
            documents = []
            for item in result.get("results", []):
                documents.append({
                    "content": item.get("document", ""),
                    "metadata": item.get("metadata", {}),
                    "score": item.get("distance", 0)
                })
            
            return ToolOutput(
                success=True,
                result=documents,
                metadata={
                    "kb_name": kb_name,
                    "query": query,
                    "count": len(documents)
                }
            )
            
        except Exception as e:
            return ToolOutput(
                success=False,
                result=None,
                error=f"知识库搜索错误: {str(e)}"
            )


class DateTimeTool(Tool):
    """日期时间工具 - 获取当前时间信息"""
    
    def _get_name(self) -> str:
        return "get_current_time"
    
    def _get_description(self) -> str:
        return "获取当前日期和时间信息。当需要知道现在是几点、今天是星期几、当前日期等信息时使用。"
    
    def _get_category(self) -> ToolCategory:
        return ToolCategory.UTILITY
    
    def _get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "format": {
                    "type": "string",
                    "description": "时间格式，可选: 'full'(完整)、'date'(仅日期)、'time'(仅时间)",
                    "default": "full"
                }
            },
            "required": []
        }
    
    async def _execute(self, format: str = "full") -> ToolOutput:
        """获取当前时间"""
        try:
            now = datetime.now()
            
            if format == "date":
                result = now.strftime("%Y-%m-%d")
            elif format == "time":
                result = now.strftime("%H:%M:%S")
            else:  # full
                result = {
                    "datetime": now.strftime("%Y-%m-%d %H:%M:%S"),
                    "date": now.strftime("%Y-%m-%d"),
                    "time": now.strftime("%H:%M:%S"),
                    "weekday": now.strftime("%A"),
                    "timestamp": now.timestamp()
                }
            
            return ToolOutput(
                success=True,
                result=result,
                metadata={"format": format}
            )
            
        except Exception as e:
            return ToolOutput(
                success=False,
                result=None,
                error=f"获取时间错误: {str(e)}"
            )


class PythonREPLTool(Tool):
    """Python代码执行工具 - 执行简单的Python代码（受限环境）"""
    
    def _get_name(self) -> str:
        return "python_repl"
    
    def _get_description(self) -> str:
        return "执行Python代码。用于数据处理、简单分析、格式转换等。注意：运行在受限环境中，不支持文件系统操作和网络请求。"
    
    def _get_category(self) -> ToolCategory:
        return ToolCategory.DATA_ANALYSIS
    
    def _get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "要执行的Python代码"
                }
            },
            "required": ["code"]
        }
    
    async def _execute(self, code: str) -> ToolOutput:
        """执行Python代码"""
        try:
            # 创建受限的执行环境
            local_vars = {}
            global_vars = {
                "__builtins__": {
                    "print": print,
                    "len": len,
                    "range": range,
                    "str": str,
                    "int": int,
                    "float": float,
                    "list": list,
                    "dict": dict,
                    "sum": sum,
                    "min": min,
                    "max": max,
                    "sorted": sorted,
                }
            }
            
            # 执行代码
            exec(code, global_vars, local_vars)
            
            # 获取结果（如果有的话）
            result = local_vars.get("result", "代码执行成功（无返回值）")
            
            return ToolOutput(
                success=True,
                result=result,
                metadata={
                    "code_length": len(code),
                    "variables": list(local_vars.keys())
                }
            )
            
        except Exception as e:
            return ToolOutput(
                success=False,
                result=None,
                error=f"代码执行错误: {str(e)}"
            )