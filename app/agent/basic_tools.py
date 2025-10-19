"""
基础工具实现 - 常用工具集合
"""
import math
import json
from typing import Any, Dict, List
from datetime import datetime, timezone, timedelta
import httpx
from .tool_base import Tool, ToolOutput, ToolCategory
import os


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
    """网络搜索工具 - 使用 google.serper.dev API"""
    
    def __init__(self):
        super().__init__()
        # 2. 从环境变量读取API密钥
        self.api_key = os.getenv("SERPER_API_KEY")
        self.base_url = "https://google.serper.dev/search"

    def _get_name(self) -> str:
        return "web_search"
    
    def _get_description(self) -> str:
        return "在互联网上搜索信息。当需要获取最新信息、查找资料、了解实时数据时使用此工具。返回搜索结果列表。"
    
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
                    "description": "返回的最大自然搜索(organic)结果数量",
                    "default": 5
                }
            },
            "required": ["query"]
        }
    
    async def _execute(self, query: str, max_results: int = 5) -> ToolOutput:
        """执行搜索 (使用 Serper API)"""
        
        # 3. 检查API密钥是否存在
        if not self.api_key:
            return ToolOutput(
                success=False,
                result=None,
                error="SERPER_API_KEY 环境变量未设置"
            )
        
        # 4. 准备 Serper API 请求
        payload = {"q": query}
        headers = {
            'X-API-KEY': self.api_key,
            'Content-Type': 'application/json'
        }

        try:
            # 5. 异步调用API
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    self.base_url,
                    json=payload,
                    headers=headers
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # 6. 提取和格式化结果，使其对LLM更友好
                    formatted_results = []
                    
                    # 提取 Answer Box (如果有)
                    if data.get("answerBox"):
                        formatted_results.append({
                            "type": "answer_box",
                            "answer": data["answerBox"].get("answer") or data["answerBox"].get("snippet"),
                            "source": data["answerBox"].get("link")
                        })

                    # 提取 Knowledge Graph (如果有)
                    if data.get("knowledgeGraph"):
                        source_link = data["knowledgeGraph"].get("source", {}).get("link")
                        formatted_results.append({
                            "type": "knowledge_graph",
                            "title": data["knowledgeGraph"].get("title"),
                            "description": data["knowledgeGraph"].get("description"),
                            "source": source_link
                        })

                    # 提取 Organic Results
                    if data.get("organic"):
                        for item in data["organic"][:max_results]: # 遵守 max_results 限制
                            formatted_results.append({
                                "type": "organic_result",
                                "title": item.get("title"),
                                "snippet": item.get("snippet"),
                                "source": item.get("link")
                            })

                    if not formatted_results:
                        return ToolOutput(
                            success=True,
                            result="未找到相关搜索结果",
                            metadata={"query": query}
                        )
                    
                    return ToolOutput(
                        success=True,
                        result=formatted_results,
                        metadata={"query": query, "results_count": len(formatted_results)}
                    )
                else:
                    return ToolOutput(
                        success=False,
                        result=None,
                        error=f"搜索失败, Serper API 错误 (状态码: {response.status_code}): {response.text}"
                    )
                    
        except Exception as e:
            return ToolOutput(
                success=False,
                result=None,
                error=f"搜索时发生异常: {str(e)}"
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
        """获取当前时间 (UTC+8)"""
        try:
            # 1. 定义 UTC+8 时区对象
            tz_utc_plus_8 = timezone(timedelta(hours=8)) 
            
            # 2. 获取时区感知的 UTC+8 时间
            now_local = datetime.now(tz_utc_plus_8) 
            
            if format == "date":
                result = now_local.strftime("%Y-%m-%d")
            elif format == "time":
                result = now_local.strftime("%H:%M:%S")
            else:  # full
                result = {
                    # 确保返回的时间字符串带有 +08:00 标记
                    "datetime": now_local.isoformat(), 
                    "date": now_local.strftime("%Y-%m-%d"),
                    "time": now_local.strftime("%H:%M:%S"),
                    "weekday": now_local.strftime("%A"),
                    "timestamp": now_local.timestamp() 
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