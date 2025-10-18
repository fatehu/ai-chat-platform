"""
工具基类 - Agent工具系统的核心抽象
参考 LangChain Tools 设计模式
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List, Callable
from pydantic import BaseModel, Field
from enum import Enum
import json


class ToolCategory(str, Enum):
    """工具分类"""
    SEARCH = "search"
    CALCULATION = "calculation"
    FILE_OPERATION = "file_operation"
    DATA_ANALYSIS = "data_analysis"
    WEB_SCRAPING = "web_scraping"
    DATABASE = "database"
    COMMUNICATION = "communication"
    UTILITY = "utility"


class ToolInput(BaseModel):
    """工具输入基类"""
    pass


class ToolOutput(BaseModel):
    """工具输出基类"""
    success: bool = Field(description="工具执行是否成功")
    result: Any = Field(description="工具执行结果")
    error: Optional[str] = Field(default=None, description="错误信息")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="额外元数据")


class Tool(ABC):
    """
    工具基类 - 所有Agent工具必须继承此类
    
    设计原则：
    1. 单一职责：每个工具只做一件事
    2. 明确接口：清晰的输入输出定义
    3. 错误处理：优雅的异常捕获
    4. 可测试性：易于编写单元测试
    """
    
    def __init__(self):
        self.name = self._get_name()
        self.description = self._get_description()
        self.category = self._get_category()
        self.parameters = self._get_parameters()
    
    @abstractmethod
    def _get_name(self) -> str:
        """返回工具名称（用于LLM识别）"""
        pass
    
    @abstractmethod
    def _get_description(self) -> str:
        """返回工具描述（用于LLM理解何时使用）"""
        pass
    
    @abstractmethod
    def _get_category(self) -> ToolCategory:
        """返回工具分类"""
        pass
    
    @abstractmethod
    def _get_parameters(self) -> Dict[str, Any]:
        """
        返回工具参数定义（JSON Schema格式）
        用于LLM进行函数调用（Function Calling）
        """
        pass
    
    @abstractmethod
    async def _execute(self, **kwargs) -> ToolOutput:
        """
        执行工具的核心逻辑（子类必须实现）
        
        Args:
            **kwargs: 工具所需参数
            
        Returns:
            ToolOutput: 标准化输出
        """
        pass
    
    async def run(self, **kwargs) -> ToolOutput:
        """
        工具执行入口（带错误处理）
        
        Args:
            **kwargs: 工具参数
            
        Returns:
            ToolOutput: 执行结果
        """
        try:
            # 参数验证
            self._validate_parameters(kwargs)
            
            # 执行工具
            result = await self._execute(**kwargs)
            
            return result
            
        except Exception as e:
            return ToolOutput(
                success=False,
                result=None,
                error=f"{self.name} 执行失败: {str(e)}"
            )
    
    def _validate_parameters(self, params: Dict[str, Any]) -> None:
        """
        验证输入参数
        
        Args:
            params: 输入参数字典
            
        Raises:
            ValueError: 参数不合法时抛出
        """
        required_params = self.parameters.get("required", [])
        for param in required_params:
            if param not in params:
                raise ValueError(f"缺少必需参数: {param}")
    
    def to_function_schema(self) -> Dict[str, Any]:
        """
        转换为OpenAI Function Calling格式
        用于让LLM知道如何调用这个工具
        
        Returns:
            Dict: OpenAI function schema
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
            }
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "parameters": self.parameters
        }
    
    def __str__(self) -> str:
        return f"Tool({self.name})"
    
    def __repr__(self) -> str:
        return self.__str__()


class ToolRegistry:
    """
    工具注册中心 - 管理所有可用工具
    单例模式，全局唯一
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._tools = {}
        return cls._instance
    
    def register(self, tool: Tool) -> None:
        """
        注册工具
        
        Args:
            tool: Tool实例
        """
        if tool.name in self._tools:
            raise ValueError(f"工具 {tool.name} 已注册")
        
        self._tools[tool.name] = tool
        print(f"✓ 工具已注册: {tool.name} ({tool.category.value})")
    
    def get_tool(self, name: str) -> Optional[Tool]:
        """
        获取工具
        
        Args:
            name: 工具名称
            
        Returns:
            Tool实例或None
        """
        return self._tools.get(name)
    
    def list_tools(self, category: Optional[ToolCategory] = None) -> List[Tool]:
        """
        列出所有工具
        
        Args:
            category: 可选的分类过滤
            
        Returns:
            工具列表
        """
        if category:
            return [
                tool for tool in self._tools.values()
                if tool.category == category
            ]
        return list(self._tools.values())
    
    def get_all_function_schemas(self) -> List[Dict[str, Any]]:
        """
        获取所有工具的Function Schema
        用于传递给LLM进行工具选择
        
        Returns:
            List[Dict]: Function schemas列表
        """
        return [tool.to_function_schema() for tool in self._tools.values()]
    
    def clear(self) -> None:
        """清空所有注册的工具（用于测试）"""
        self._tools.clear()
    
    def __len__(self) -> int:
        return len(self._tools)
    
    def __contains__(self, name: str) -> bool:
        return name in self._tools


# 全局工具注册中心实例
tool_registry = ToolRegistry()