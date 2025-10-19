"""
会话管理服务
"""
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from datetime import datetime
import json

from .models import Conversation, Message


class ConversationService:
    """会话管理服务"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_conversation(
        self,
        model: str = "deepseek-chat",
        title: str = "新对话",
        temperature: float = 0.7,
        max_tokens: int = 2000,
        enable_rag: bool = False,
        kb_name: Optional[str] = None,
        rag_top_k: int = 3
    ) -> Conversation:
        """
        创建新会话
        
        Args:
            model: 使用的模型
            title: 会话标题
            temperature: 温度参数
            max_tokens: 最大token数
            enable_rag: 是否启用RAG
            kb_name: 知识库名称
            rag_top_k: RAG检索数量
            
        Returns:
            创建的会话对象
        """
        conversation = Conversation(
            session_id=Conversation.generate_session_id(),
            model=model,
            title=title,
            temperature=temperature,
            max_tokens=max_tokens,
            enable_rag=enable_rag,
            kb_name=kb_name,
            rag_top_k=rag_top_k
        )
        
        self.db.add(conversation)
        self.db.commit()
        self.db.refresh(conversation)
        
        return conversation
    
    def get_conversation(self, session_id: str) -> Optional[Conversation]:
        """获取会话"""
        return self.db.query(Conversation).filter(
            Conversation.session_id == session_id
        ).first()
    
    def list_conversations(
        self,
        skip: int = 0,
        limit: int = 50,
        order_by: str = "updated_at"
    ) -> List[Conversation]:
        """列出所有会话"""
        query = self.db.query(Conversation)
        
        if order_by == "created_at":
            query = query.order_by(Conversation.created_at.desc())
        else:
            query = query.order_by(Conversation.updated_at.desc())
        
        return query.offset(skip).limit(limit).all()
    
    def delete_conversation(self, session_id: str) -> bool:
        """删除会话"""
        conversation = self.get_conversation(session_id)
        if conversation:
            self.db.delete(conversation)
            self.db.commit()
            return True
        return False
    
    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        tool_calls: Optional[List[Dict]] = None,
        tool_call_id: Optional[str] = None,
        extra_data: Optional[Dict] = None
    ) -> Message:
        """
        添加消息到会话
        
        Args:
            session_id: 会话ID
            role: 角色（user, assistant, tool, system）
            content: 消息内容
            tool_calls: 工具调用信息
            tool_call_id: 工具调用ID
            extra_data: 元数据
            
        Returns:
            创建的消息对象
        """
        message = Message(
            session_id=session_id,
            role=role,
            content=content,
            tool_calls=tool_calls,
            tool_call_id=tool_call_id,
            extra_data=extra_data
        )
        
        self.db.add(message)
        
        # 更新会话的updated_at时间
        conversation = self.get_conversation(session_id)
        if conversation:
            conversation.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(message)
        
        return message
    
    def get_messages(
        self,
        session_id: str,
        limit: Optional[int] = None
    ) -> List[Message]:
        """
        获取会话的消息历史
        
        Args:
            session_id: 会话ID
            limit: 限制返回的消息数量（最近的N条）
            
        Returns:
            消息列表
        """
        query = self.db.query(Message).filter(
            Message.session_id == session_id
        ).order_by(Message.created_at.asc())
        
        if limit:
            # 获取最近的N条消息
            total = query.count()
            if total > limit:
                query = query.offset(total - limit)
        
        return query.all()
    
    def get_messages_as_dict(
        self,
        session_id: str,
        limit: Optional[int] = None,
        include_system: bool = True
    ) -> List[Dict[str, Any]]:
        """
        获取消息历史（字典格式，用于LLM调用）
        
        Args:
            session_id: 会话ID
            limit: 限制消息数量
            include_system: 是否包含system消息
            
        Returns:
            消息字典列表
        """
        messages = self.get_messages(session_id, limit)
        
        result = []
        for msg in messages:
            if not include_system and msg.role == "system":
                continue
            
            message_dict = {
                "role": msg.role,
                "content": msg.content
            }
            
            # 添加tool_calls信息
            if msg.tool_calls:
                message_dict["tool_calls"] = msg.tool_calls
            
            # 添加tool_call_id（用于tool消息）
            if msg.tool_call_id:
                message_dict["tool_call_id"] = msg.tool_call_id
            
            result.append(message_dict)
        
        return result
    
    def clear_messages(self, session_id: str) -> int:
        """清空会话消息"""
        count = self.db.query(Message).filter(
            Message.session_id == session_id
        ).delete()
        
        self.db.commit()
        return count
    
    def update_conversation_title(self, session_id: str, title: str) -> bool:
        """更新会话标题"""
        conversation = self.get_conversation(session_id)
        if conversation:
            conversation.title = title
            self.db.commit()
            return True
        return False