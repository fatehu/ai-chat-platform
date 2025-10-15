"""
向量数据库服务 - 使用 ChromaDB
"""
import chromadb
from chromadb.config import Settings
from typing import List, Dict, Optional, Any
import uuid
from datetime import datetime
import hashlib


class VectorStoreService:
    """向量数据库服务封装"""
    
    def __init__(self, persist_directory: str = "./data/chroma"):
        """
        初始化向量数据库
        
        Args:
            persist_directory: 数据持久化目录
        """
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
    
    def create_collection(
        self, 
        collection_name: str, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        创建向量集合
        
        Args:
            collection_name: 集合名称
            metadata: 集合元数据（如文件信息）
        """
        try:
            # 检查集合是否已存在
            try:
                self.client.get_collection(name=collection_name)
                raise ValueError(f"集合 '{collection_name}' 已存在")
            except Exception:
                pass
            
            # 创建新集合
            self.client.create_collection(
                name=collection_name,
                metadata=metadata or {
                    "created_at": datetime.utcnow().isoformat()
                }
            )
        except ValueError:
            raise
        except Exception as e:
            raise Exception(f"创建集合失败: {str(e)}")
    
    def get_collection(self, collection_name: str):
        """
        获取集合
        
        Args:
            collection_name: 集合名称
            
        Returns:
            Collection 对象
        """
        try:
            return self.client.get_collection(name=collection_name)
        except Exception as e:
            raise Exception(f"获取集合失败: {str(e)}")
    
    def list_collections(self) -> List[Dict[str, Any]]:
        """
        列出所有集合
        
        Returns:
            集合信息列表
        """
        try:
            collections = self.client.list_collections()
            return [
                {
                    "name": col.name,
                    "count": col.count(),
                    "metadata": col.metadata
                }
                for col in collections
            ]
        except Exception as e:
            raise Exception(f"列出集合失败: {str(e)}")
    
    def add_documents(
        self,
        collection_name: str,
        documents: List[str],
        embeddings: List[List[float]],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None
    ) -> List[str]:
        """
        向集合添加文档
        
        Args:
            collection_name: 集合名称
            documents: 文档文本列表
            embeddings: 向量列表
            metadatas: 元数据列表
            ids: 文档ID列表（如不提供则自动生成）
            
        Returns:
            文档ID列表
        """
        try:
            collection = self.get_collection(collection_name)
            
            # 生成ID
            if ids is None:
                # ids = [str(uuid.uuid4()) for _ in documents]
                generated_ids = []
                for i, doc_content in enumerate(documents):
                    # 尝试从元数据获取文件名和块索引，提供默认值以确保稳定性
                    metadata = metadatas[i] if metadatas and i < len(metadatas) else {}
                    filename = metadata.get("filename", "unknown_file")
                    chunk_index = metadata.get("chunk_index", i)
                    
                    # 创建一个用于哈希的唯一字符串
                    unique_string_for_hash = f"{filename}-{chunk_index}-{doc_content}"
                    
                    # 使用 SHA256 生成一个固定的哈希值作为ID
                    doc_id = hashlib.sha256(unique_string_for_hash.encode('utf-8')).hexdigest()
                    generated_ids.append(doc_id)
                ids = generated_ids
            
            # 准备元数据
            if metadatas is None:
                metadatas = [{"index": i} for i in range(len(documents))]
            
            # 添加文档
            collection.add(
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas,
                ids=ids
            )
            
            return ids
        except Exception as e:
            raise Exception(f"添加文档失败: {str(e)}")
    
    def query(
        self,
        collection_name: str,
        query_embedding: List[float],
        n_results: int = 5,
        where: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        查询相似文档
        
        Args:
            collection_name: 集合名称
            query_embedding: 查询向量
            n_results: 返回结果数量
            where: 过滤条件
            
        Returns:
            查询结果
        """
        try:
            collection = self.get_collection(collection_name)
            
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where
            )
            
            # 格式化结果
            formatted_results = []
            if results['documents'] and len(results['documents']) > 0:
                for i in range(len(results['documents'][0])):
                    formatted_results.append({
                        "document": results['documents'][0][i],
                        "metadata": results['metadatas'][0][i] if results['metadatas'] else {},
                        "distance": results['distances'][0][i] if results['distances'] else None,
                        "id": results['ids'][0][i]
                    })
            
            return {
                "results": formatted_results,
                "count": len(formatted_results)
            }
        except Exception as e:
            raise Exception(f"查询失败: {str(e)}")
    
    def delete_collection(self, collection_name: str) -> None:
        """
        删除集合
        
        Args:
            collection_name: 集合名称
        """
        try:
            self.client.delete_collection(name=collection_name)
        except Exception as e:
            raise Exception(f"删除集合失败: {str(e)}")
    
    def get_collection_info(self, collection_name: str) -> Dict[str, Any]:
        """
        获取集合详细信息
        
        Args:
            collection_name: 集合名称
            
        Returns:
            集合信息
        """
        try:
            collection = self.get_collection(collection_name)
            return {
                "name": collection.name,
                "count": collection.count(),
                "metadata": collection.metadata
            }
        except Exception as e:
            raise Exception(f"获取集合信息失败: {str(e)}")


# 创建全局实例
def get_vector_store() -> VectorStoreService:
    """获取向量数据库实例"""
    return VectorStoreService()