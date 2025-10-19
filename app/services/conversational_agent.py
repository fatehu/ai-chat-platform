"""
支持多轮对话的Agent - 重构版本
支持动态配置和灵活的RAG
"""
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
import httpx

from ..agent.tool_base import Tool
from ..services.rag_service import get_rag_service


class ConversationalAgent:
    """
    支持多轮对话的Agent（重构版）
    
    重构要点：
    1. 不再在初始化时固定RAG配置
    2. 每次运行时可以动态指定是否使用RAG和使用哪个知识库
    3. 支持更灵活的配置
    
    特点:
    1. 会话历史管理
    2. 动态RAG集成（每次消息可独立配置）
    3. Function Calling
    4. 上下文保持
    """
    
    def __init__(
        self,
        tools: List[Tool],
        llm_config: Dict[str, Any],
        max_iterations: int = 10,
        temperature: float = 0.7,
        verbose: bool = False
    ):
        """
        初始化Agent
        
        Args:
            tools: 可用工具列表
            llm_config: LLM配置
            max_iterations: 最大迭代次数
            temperature: 温度参数
            verbose: 是否打印详细日志
        """
        self.tools = {tool.name: tool for tool in tools}
        self.llm_config = llm_config
        self.max_iterations = max_iterations
        self.temperature = temperature
        self.verbose = verbose
        self.rag_service = get_rag_service()
    
    def _build_system_prompt(self, rag_context: Optional[str] = None) -> str:
        """构建系统提示词"""
        tool_descriptions = "\n".join([
            f"- {tool.name}: {tool.description}"
            for tool in self.tools.values()
        ])
        
        base_prompt = f"""你是一个智能助手,可以使用以下工具来帮助用户:

{tool_descriptions}

工作流程:
1. 仔细分析用户的问题
2. 如果需要工具,调用相应的函数
3. 根据工具返回的结果继续推理
4. 给出清晰准确的最终答案

注意:
- 使用工具时要准确传递参数
- 根据观察结果调整后续行动
- 保持对话连贯,记住之前的上下文
"""
        
        # 如果有RAG上下文,添加到系统提示词
        if rag_context:
            base_prompt += f"""

参考知识库内容:
{rag_context}

请优先使用上述知识库内容回答问题。如果知识库中没有相关信息,可以使用工具或基于你的知识回答。"""
        
        return base_prompt
    
    def _get_function_schemas(self) -> List[Dict[str, Any]]:
        """获取所有工具的Function Schema"""
        schemas = [tool.to_function_schema() for tool in self.tools.values()]
        
        # 添加"完成"函数
        schemas.append({
            "type": "function",
            "function": {
                "name": "finish",
                "description": "当你已经得出最终答案时调用此函数",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "answer": {
                            "type": "string",
                            "description": "给用户的最终答案"
                        }
                    },
                    "required": ["answer"]
                }
            }
        })
        
        return schemas
    
    async def _call_llm(
        self,
        messages: List[Dict[str, Any]],
        functions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """调用LLM"""
        api_key = self.llm_config.get("api_key")
        base_url = self.llm_config.get("base_url")
        model = self.llm_config.get("model", "deepseek-chat")
        
        payload = {
            "model": model,
            "messages": messages,
            "tools": functions,
            "tool_choice": "auto",
            "temperature": self.temperature
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                base_url,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json=payload
            )
            
            if response.status_code != 200:
                raise Exception(f"LLM调用失败: {response.text}")
            
            return response.json()
    
    async def _execute_tool(
        self,
        tool_name: str,
        tool_input: Dict[str, Any]
    ) -> str:
        """执行工具"""
        if tool_name not in self.tools:
            return json.dumps({
                "success": False,
                "error": f"工具 '{tool_name}' 不存在"
            }, ensure_ascii=False)
        
        tool = self.tools[tool_name]
        result = await tool.run(**tool_input)
        
        return json.dumps({
            "success": result.success,
            "result": result.result if result.success else None,
            "error": result.error if not result.success else None
        }, ensure_ascii=False)
    
    async def _get_rag_context(
        self,
        query: str,
        kb_name: str,
        top_k: int = 3
    ) -> Optional[Dict[str, Any]]:
        """
        获取RAG上下文（重构版）
        
        Args:
            query: 查询文本
            kb_name: 知识库名称
            top_k: 返回文档数量
            
        Returns:
            RAG结果
        """
        try:
            result = self.rag_service.rag_query(
                kb_name=kb_name,
                query=query,
                top_k=top_k
            )
            return result
        except Exception as e:
            if self.verbose:
                print(f"RAG检索失败: {str(e)}")
            return None
    
    async def run(
        self,
        user_message: str,
        conversation_history: List[Dict[str, Any]],
        # 新增：动态RAG配置
        enable_rag: bool = False,
        kb_name: Optional[str] = None,
        rag_top_k: int = 3
    ) -> Dict[str, Any]:
        """
        运行Agent处理用户消息（重构版）
        
        Args:
            user_message: 用户消息
            conversation_history: 会话历史
            enable_rag: 是否启用RAG（动态指定）
            kb_name: 知识库名称（动态指定）
            rag_top_k: RAG检索数量
            
        Returns:
            执行结果
        """
        start_time = datetime.now()
        steps = []
        
        # 1. 如果启用RAG,检索相关内容
        rag_context = None
        source_documents = []
        
        if enable_rag and kb_name:
            rag_result = await self._get_rag_context(user_message, kb_name, rag_top_k)
            if rag_result:
                rag_context = rag_result.get("context", "")
                source_documents = rag_result.get("source_documents", [])
                
                if self.verbose:
                    print(f"\n📚 RAG检索到 {len(source_documents)} 条相关文档")
                    print(f"知识库: {kb_name}")
        
        # 2. 构建消息列表
        messages = []
        
        # 添加系统提示词
        system_prompt = self._build_system_prompt(rag_context)
        messages.append({
            "role": "system",
            "content": system_prompt
        })
        
        # 添加历史消息
        messages.extend(conversation_history)
        
        # 添加当前用户消息
        messages.append({
            "role": "user",
            "content": user_message
        })
        
        # 3. 获取可用函数
        functions = self._get_function_schemas()
        
        iteration = 0
        
        if self.verbose:
            print(f"\n{'='*60}")
            print(f"Agent开始处理: {user_message}")
            if enable_rag:
                print(f"RAG模式: 启用 (知识库: {kb_name})")
            print(f"{'='*60}\n")
        
        try:
            while iteration < self.max_iterations:
                iteration += 1
                
                if self.verbose:
                    print(f"--- 迭代 {iteration} ---")
                
                # 调用LLM
                response = await self._call_llm(messages, functions)
                assistant_message = response["choices"][0]["message"]
                
                # 检查是否有工具调用
                if assistant_message.get("tool_calls"):
                    
                    # 关键修改：首先将LLM的回复（包含所有工具调用请求）添加到历史
                    messages.append(assistant_message)
                    
                    # 关键修改：遍历所有工具调用
                    tool_calls = assistant_message["tool_calls"]
                    
                    for tool_call in tool_calls:
                        function_name = tool_call["function"]["name"]
                        function_args = json.loads(tool_call["function"]["arguments"])
                        
                        if self.verbose:
                            print(f"🔧 调用工具: {function_name}")
                            print(f"参数: {function_args}")
                        
                        # 记录步骤
                        steps.append({
                            "iteration": iteration,
                            "action": function_name,
                            "input": function_args,
                            "timestamp": datetime.now().isoformat()
                        })
                        
                        # 检查是否是结束函数
                        if function_name == "finish":
                            final_answer = function_args.get("answer", "")
                            
                            if self.verbose:
                                print(f"✅ 最终答案: {final_answer}\n")
                            
                            # 注意：一旦遇到 finish，立即返回
                            return {
                                "success": True,
                                "answer": final_answer,
                                "steps": steps,
                                "iterations": iteration,
                                "execution_time": (datetime.now() - start_time).total_seconds(),
                                "rag_enabled": enable_rag,
                                "rag_kb_name": kb_name if enable_rag else None,
                                "source_documents": source_documents if enable_rag else [],
                                "messages_to_save": [
                                    {"role": "assistant", "content": final_answer}
                                ]
                            }
                        
                        # 执行工具
                        observation = await self._execute_tool(function_name, function_args)
                        
                        if self.verbose:
                            print(f"📝 观察: {observation}\n")
                        
                        # 假设 steps 列表是按顺序添加的，取最后一个
                        if steps:
                            steps[-1]["observation"] = observation
                        
                        # 关键修改：将 *当前工具* 的结果添加到消息历史
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call["id"],
                            "content": observation
                        })
                        
                    # 循环结束后，进入下一次迭代

                else:
                    # LLM直接回答
                    answer = assistant_message.get("content", "")
                    
                    if self.verbose:
                        print(f"✅ 直接回答: {answer}\n")
                    
                    return {
                        "success": True,
                        "answer": answer,
                        "steps": steps,
                        "iterations": iteration,
                        "execution_time": (datetime.now() - start_time).total_seconds(),
                        "rag_enabled": enable_rag,
                        "rag_kb_name": kb_name if enable_rag else None,
                        "source_documents": source_documents if enable_rag else [],
                        "messages_to_save": [
                            {"role": "assistant", "content": answer}
                        ]
                    }
            
            # 达到最大迭代次数
            return {
                "success": False,
                "answer": "抱歉,我在规定的步骤内未能得出答案",
                "steps": steps,
                "iterations": iteration,
                "execution_time": (datetime.now() - start_time).total_seconds(),
                "error": "达到最大迭代次数",
                "rag_enabled": enable_rag,
                "rag_kb_name": kb_name if enable_rag else None,
                "source_documents": source_documents if enable_rag else []
            }
            
        except Exception as e:
            return {
                "success": False,
                "answer": f"执行过程中发生错误: {str(e)}",
                "steps": steps,
                "iterations": iteration,
                "execution_time": (datetime.now() - start_time).total_seconds(),
                "error": str(e),
                "rag_enabled": enable_rag,
                "rag_kb_name": kb_name if enable_rag else None,
                "source_documents": source_documents if enable_rag else []
            }