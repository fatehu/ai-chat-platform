"""
Agent核心引擎 - 实现ReAct模式（Reasoning + Acting）

ReAct模式流程：
1. Thought（思考）: Agent分析问题，决定下一步动作
2. Action（行动）: Agent选择并执行工具
3. Observation（观察）: 获取工具执行结果
4. ...（循环直到得出最终答案）
5. Answer（回答）: 给出最终答案

参考：
- ReAct论文: https://arxiv.org/abs/2210.03629
- LangChain AgentExecutor
"""
import json
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from enum import Enum
import httpx
from datetime import datetime

from .tool_base import Tool, tool_registry


class AgentAction(BaseModel):
    """Agent动作"""
    tool: str  # 工具名称
    tool_input: Dict[str, Any]  # 工具输入
    log: str  # 推理日志


class AgentFinish(BaseModel):
    """Agent完成"""
    output: str  # 最终答案
    log: str  # 推理日志


class AgentStep(BaseModel):
    """Agent执行步骤"""
    thought: str  # 思考过程
    action: Optional[str] = None  # 动作（工具名称）
    action_input: Optional[Dict[str, Any]] = None  # 动作输入
    observation: Optional[str] = None  # 观察结果
    timestamp: str  # 时间戳


class AgentConfig(BaseModel):
    """Agent配置"""
    max_iterations: int = 100  # 最大迭代次数
    max_execution_time: int = 300  # 最大执行时间（秒）
    model: str = "deepseek-chat"  # 使用的LLM模型
    temperature: float = 0.7  # 温度参数
    verbose: bool = True  # 是否打印详细日志


class ReactAgent:
    """
    ReAct Agent实现
    
    特点：
    1. 使用Function Calling让LLM选择工具
    2. 支持多轮推理和工具调用
    3. 详细的执行日志
    4. 错误处理和超时控制
    """
    
    def __init__(
        self,
        tools: List[Tool],
        llm_config: Dict[str, Any],
        config: AgentConfig = AgentConfig()
    ):
        """
        初始化Agent
        
        Args:
            tools: 可用工具列表
            llm_config: LLM配置（api_key, base_url等）
            config: Agent配置
        """
        self.tools = {tool.name: tool for tool in tools}
        self.llm_config = llm_config
        self.config = config
        self.steps: List[AgentStep] = []
        
    def _build_system_prompt(self) -> str:
        """构建系统提示词"""
        tool_descriptions = "\n".join([
            f"- {tool.name}: {tool.description}"
            for tool in self.tools.values()
        ])
        
        return f"""你是一个智能助手，可以使用以下工具来帮助用户解决问题：

{tool_descriptions}

工作流程：
1. 仔细分析用户的问题
2. 思考需要使用哪个工具（或者已经可以回答）
3. 如果需要工具，调用相应的函数
4. 根据工具返回的结果继续推理
5. 重复上述过程直到能够给出最终答案

注意事项：
- 使用工具时要准确传递参数
- 根据观察结果调整后续行动
- 如果工具返回错误，考虑使用其他工具或方法
- 当你有足够信息时，给出清晰的最终答案
"""
    
    def _get_function_schemas(self) -> List[Dict[str, Any]]:
        """获取所有工具的Function Schema"""
        schemas = [tool.to_function_schema() for tool in self.tools.values()]
        
        # 添加"完成"函数，让Agent知道何时结束
        schemas.append({
            "type": "function",
            "function": {
                "name": "finish",
                "description": "当你已经得出最终答案时调用此函数。返回给用户的完整答案。",
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
        messages: List[Dict[str, str]],
        functions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        调用LLM
        
        Args:
            messages: 对话历史
            functions: 可用函数列表
            
        Returns:
            LLM响应
        """
        api_key = self.llm_config.get("api_key")
        base_url = self.llm_config.get("base_url")
        
        payload = {
            "model": self.config.model,
            "messages": messages,
            "tools": functions,
            "tool_choice": "auto",
            "temperature": self.config.temperature
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
        """
        执行工具
        
        Args:
            tool_name: 工具名称
            tool_input: 工具输入
            
        Returns:
            工具执行结果（字符串格式）
        """
        if tool_name not in self.tools:
            return f"错误：工具 '{tool_name}' 不存在"
        
        tool = self.tools[tool_name]
        result = await tool.run(**tool_input)
        
        if result.success:
            return json.dumps({
                "success": True,
                "result": result.result
            }, ensure_ascii=False)
        else:
            return json.dumps({
                "success": False,
                "error": result.error
            }, ensure_ascii=False)
    
    async def run(self, query: str) -> Dict[str, Any]:
        """
        运行Agent处理用户查询
        
        Args:
            query: 用户问题
            
        Returns:
            执行结果
        """
        start_time = datetime.now()
        self.steps = []
        
        # 构建初始消息
        messages = [
            {"role": "system", "content": self._build_system_prompt()},
            {"role": "user", "content": query}
        ]
        
        functions = self._get_function_schemas()
        iteration = 0
        
        if self.config.verbose:
            print(f"\n{'='*60}")
            print(f"Agent开始处理: {query}")
            print(f"{'='*60}\n")
        
        try:
            while iteration < self.config.max_iterations:
                iteration += 1
                
                if self.config.verbose:
                    print(f"--- 迭代 {iteration} ---")
                
                # 调用LLM
                response = await self._call_llm(messages, functions)
                assistant_message = response["choices"][0]["message"]
                
                # 检查是否有工具调用
                if assistant_message.get("tool_calls"):
                    tool_call = assistant_message["tool_calls"][0]
                    function_name = tool_call["function"]["name"]
                    function_args = json.loads(tool_call["function"]["arguments"])
                    
                    if self.config.verbose:
                        print(f"思考: 我需要使用工具 '{function_name}'")
                        print(f"参数: {function_args}")
                    
                    # 检查是否是结束函数
                    if function_name == "finish":
                        final_answer = function_args.get("answer", "")
                        
                        self.steps.append(AgentStep(
                            thought="我已经得出最终答案",
                            action="finish",
                            action_input={"answer": final_answer},
                            observation=None,
                            timestamp=datetime.now().isoformat()
                        ))
                        
                        if self.config.verbose:
                            print(f"✓ 最终答案: {final_answer}\n")
                        
                        return {
                            "success": True,
                            "answer": final_answer,
                            "steps": [step.dict() for step in self.steps],
                            "iterations": iteration,
                            "execution_time": (datetime.now() - start_time).total_seconds()
                        }
                    
                    # 执行工具
                    observation = await self._execute_tool(function_name, function_args)
                    
                    if self.config.verbose:
                        print(f"观察: {observation}\n")
                    
                    # 记录步骤
                    self.steps.append(AgentStep(
                        thought=f"使用工具 {function_name}",
                        action=function_name,
                        action_input=function_args,
                        observation=observation,
                        timestamp=datetime.now().isoformat()
                    ))
                    
                    # 将工具结果添加到消息历史
                    messages.append(assistant_message)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "content": observation
                    })
                    
                else:
                    # LLM直接回答（未使用Function Calling）
                    answer = assistant_message.get("content", "")
                    
                    if self.config.verbose:
                        print(f"✓ 直接回答: {answer}\n")
                    
                    return {
                        "success": True,
                        "answer": answer,
                        "steps": [step.dict() for step in self.steps],
                        "iterations": iteration,
                        "execution_time": (datetime.now() - start_time).total_seconds()
                    }
            
            # 达到最大迭代次数
            return {
                "success": False,
                "answer": "抱歉，我在规定的步骤内未能得出答案",
                "steps": [step.dict() for step in self.steps],
                "iterations": iteration,
                "execution_time": (datetime.now() - start_time).total_seconds(),
                "error": "达到最大迭代次数"
            }
            
        except Exception as e:
            return {
                "success": False,
                "answer": f"执行过程中发生错误: {str(e)}",
                "steps": [step.dict() for step in self.steps],
                "iterations": iteration,
                "execution_time": (datetime.now() - start_time).total_seconds(),
                "error": str(e)
            }