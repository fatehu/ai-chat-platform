"""
阿里云 DashScope Embedding 服务
使用 text-embedding-v2 模型
"""
import os
from typing import List
from openai import OpenAI


class EmbeddingService:
    """阿里云 DashScope Embedding 服务封装"""
    
    def __init__(self):
        """初始化 Embedding 服务"""
        self.api_key = os.getenv("DASHSCOPE_API_KEY")
        if not self.api_key:
            raise ValueError("DASHSCOPE_API_KEY 环境变量未设置")
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
        )
        self.model = "text-embedding-v2"
    
    def get_embedding(self, text: str) -> List[float]:
        """
        获取单个文本的向量
        
        Args:
            text: 输入文本
            
        Returns:
            向量列表
        """
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=text,
                encoding_format="float"
            )
            return response.data[0].embedding
        except Exception as e:
            raise Exception(f"获取向量失败: {str(e)}")
    
    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        批量获取文本向量
        
        Args:
            texts: 文本列表
            
        Returns:
            向量列表的列表
        """
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=texts,
                encoding_format="float"
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            raise Exception(f"批量获取向量失败: {str(e)}")
    
    def get_embedding_dimension(self) -> int:
        """
        获取向量维度
        text-embedding-v2 的维度是 1536
        """
        return 1536


# 创建全局实例
def get_embedding_service() -> EmbeddingService:
    """获取 Embedding 服务实例"""
    return EmbeddingService()