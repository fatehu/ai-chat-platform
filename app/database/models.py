"""
数据库模型定义
"""
from sqlalchemy import Column, String, Text, DateTime, Integer, ForeignKey, Boolean, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from .database import Base


class Conversation(Base):
    """会话表 - 存储对话会话信息"""
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), unique=True, index=True, nullable=False)
    title = Column(String(200), default="新对话")
    model = Column(String(50), default="deepseek-chat")
    
    # 配置信息
    temperature = Column(Integer, default=0.7)
    max_tokens = Column(Integer, default=2000)
    
    # RAG配置
    enable_rag = Column(Boolean, default=False)
    kb_name = Column(String(100), nullable=True)
    rag_top_k = Column(Integer, default=3)
    
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
    """消息表 - 存储对话消息历史"""
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), ForeignKey("conversations.session_id"), index=True)
    
    # 消息内容
    role = Column(String(20), nullable=False)  # system, user, assistant, tool
    content = Column(Text)
    
    # Function Calling相关
    tool_calls = Column(JSON, nullable=True)  # 存储工具调用信息
    tool_call_id = Column(String(100), nullable=True)  # 工具调用ID
    
    # 元数据
    extra_data = Column(JSON, nullable=True)  # 额外的元数据（如RAG上下文）
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 关系
    conversation = relationship("Conversation", back_populates="messages")