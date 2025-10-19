"""
数据库模型定义 - 重构版本
支持动态参数配置和灵活的RAG
"""
from sqlalchemy import Column, String, Text, DateTime, Integer, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from .database import Base


class Conversation(Base):
    """
    会话表 - 存储对话会话信息
    
    重构要点：
    1. 只保留会话的基本信息（id, session_id, title, 时间戳）
    2. 不再存储模型配置、RAG配置等参数
    3. 所有配置参数都在Message级别动态指定
    """
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), unique=True, index=True, nullable=False)
    title = Column(String(200), default="新对话")
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")

    @staticmethod
    def generate_session_id():
        """生成唯一的session_id"""
        return f"session_{uuid.uuid4().hex[:16]}"


class Message(Base):
    """
    消息表 - 存储对话消息历史
    
    重构要点：
    1. 在extra_data中存储每条消息的配置参数
    2. 支持动态的RAG配置
    3. 可以存储RAG检索到的上下文和来源文档
    
    extra_data 字段结构示例：
    {
        "config": {
            "model": "deepseek-chat",
            "temperature": 0.7,
            "max_tokens": 2000
        },
        "rag": {
            "enabled": true,
            "kb_name": "my_knowledge_base",
            "top_k": 3,
            "context": "检索到的上下文内容...",
            "source_documents": [...]
        },
        "agent": {
            "enabled": true,
            "max_iterations": 10,
            "enable_tools": ["calculator", "web_search"]
        }
    }
    """
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), ForeignKey("conversations.session_id"), index=True)
    
    # 消息内容
    role = Column(String(20), nullable=False)  # system, user, assistant, tool
    content = Column(Text)
    
    # Function Calling相关
    tool_calls = Column(JSON, nullable=True)  # 存储工具调用信息
    tool_call_id = Column(String(100), nullable=True)  # 工具调用ID
    
    # 元数据和配置（重构重点）
    extra_data = Column(JSON, nullable=True)
    # extra_data 可以包含：
    # - config: 模型配置（model, temperature, max_tokens等）
    # - rag: RAG配置和结果（enabled, kb_name, top_k, context, source_documents）
    # - agent: Agent配置（enabled, max_iterations, enable_tools）
    # - custom: 其他自定义数据
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 关系
    conversation = relationship("Conversation", back_populates="messages")
    
    @property
    def model_config(self):
        """获取模型配置"""
        if self.extra_data and "config" in self.extra_data:
            return self.extra_data["config"]
        return None
    
    @property
    def rag_config(self):
        """获取RAG配置"""
        if self.extra_data and "rag" in self.extra_data:
            return self.extra_data["rag"]
        return None
    
    @property
    def agent_config(self):
        """获取Agent配置"""
        if self.extra_data and "agent" in self.extra_data:
            return self.extra_data["agent"]
        return None
