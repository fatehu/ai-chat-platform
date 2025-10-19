"""
会话管理服务 - 重构版本
支持动态参数配置和灵活的RAG
"""
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from datetime import datetime
import json

from .models import Conversation, Message


class ConversationService:
    """
    会话管理服务
    
    重构要点：
    1. create_conversation 只创建基本会话，不接收配置参数
    2. add_message 支持动态配置参数（模型、RAG、Agent等）
    3. 提供获取消息配置的辅助方法
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_conversation(self, title: str = "新对话") -> Conversation:
        """
        创建新会话（简化版）
        
        Args:
            title: 会话标题
            
        Returns:
            创建的会话对象
        """
        conversation = Conversation(
            session_id=Conversation.generate_session_id(),
            title=title
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
        # 新增：动态配置参数
        model_config: Optional[Dict[str, Any]] = None,
        rag_config: Optional[Dict[str, Any]] = None,
        agent_config: Optional[Dict[str, Any]] = None,
        custom_data: Optional[Dict[str, Any]] = None
    ) -> Message:
        """
        添加消息到会话（重构版）
        
        Args:
            session_id: 会话ID
            role: 角色（user, assistant, tool, system）
            content: 消息内容
            tool_calls: 工具调用信息
            tool_call_id: 工具调用ID
            model_config: 模型配置 {"model": "deepseek-chat", "temperature": 0.7, "max_tokens": 2000}
            rag_config: RAG配置 {"enabled": True, "kb_name": "xxx", "top_k": 3, "context": "...", "source_documents": [...]}
            agent_config: Agent配置 {"enabled": True, "max_iterations": 10, "enable_tools": [...]}
            custom_data: 自定义数据
            
        Returns:
            创建的消息对象
        """
        # 构建extra_data
        extra_data = {}
        
        if model_config:
            extra_data["config"] = model_config
        
        if rag_config:
            extra_data["rag"] = rag_config
        
        if agent_config:
            extra_data["agent"] = agent_config
        
        if custom_data:
            extra_data["custom"] = custom_data
        
        # 创建消息
        message = Message(
            session_id=session_id,
            role=role,
            content=content,
            tool_calls=tool_calls,
            tool_call_id=tool_call_id,
            extra_data=extra_data if extra_data else None
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
        include_system: bool = True,
        include_config: bool = False
    ) -> List[Dict[str, Any]]:
        """
        获取消息历史（字典格式，用于LLM调用）
        
        Args:
            session_id: 会话ID
            limit: 限制消息数量
            include_system: 是否包含system消息
            include_config: 是否包含配置信息（在extra_data中）
            
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
            
            # 可选：添加配置信息
            if include_config and msg.extra_data:
                message_dict["extra_data"] = msg.extra_data
            
            result.append(message_dict)
        
        return result
    
    def get_last_user_message_config(self, session_id: str) -> Dict[str, Any]:
        """
        获取最后一条用户消息的配置
        用于继承上一次的配置
        
        Args:
            session_id: 会话ID
            
        Returns:
            配置字典
        """
        messages = self.db.query(Message).filter(
            Message.session_id == session_id,
            Message.role == "user"
        ).order_by(Message.created_at.desc()).limit(1).all()
        
        if messages and messages[0].extra_data:
            return {
                "model_config": messages[0].extra_data.get("config"),
                "rag_config": messages[0].extra_data.get("rag"),
                "agent_config": messages[0].extra_data.get("agent")
            }
        
        return {}
    
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
    
    def get_conversation_summary(self, session_id: str) -> Dict[str, Any]:
        """
        获取会话摘要信息
        包括消息数量、使用的模型、是否使用RAG等统计信息
        
        Args:
            session_id: 会话ID
            
        Returns:
            摘要信息
        """
        conversation = self.get_conversation(session_id)
        if not conversation:
            return None
        
        messages = self.get_messages(session_id)
        
        # 统计信息
        total_messages = len(messages)
        user_messages = sum(1 for msg in messages if msg.role == "user")
        assistant_messages = sum(1 for msg in messages if msg.role == "assistant")
        
        # 统计使用的模型
        models_used = set()
        rag_enabled_count = 0
        kb_names_used = set()
        
        for msg in messages:
            if msg.extra_data:
                if "config" in msg.extra_data and "model" in msg.extra_data["config"]:
                    models_used.add(msg.extra_data["config"]["model"])
                
                if "rag" in msg.extra_data and msg.extra_data["rag"].get("enabled"):
                    rag_enabled_count += 1
                    if "kb_name" in msg.extra_data["rag"]:
                        kb_names_used.add(msg.extra_data["rag"]["kb_name"])
        
        return {
            "session_id": session_id,
            "title": conversation.title,
            "created_at": conversation.created_at.isoformat(),
            "updated_at": conversation.updated_at.isoformat(),
            "statistics": {
                "total_messages": total_messages,
                "user_messages": user_messages,
                "assistant_messages": assistant_messages,
                "models_used": list(models_used),
                "rag_enabled_count": rag_enabled_count,
                "knowledge_bases_used": list(kb_names_used)
            }
        }