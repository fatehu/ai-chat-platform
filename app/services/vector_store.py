"""
向量数据库服务 - 使用 ChromaDB
"""
import chromadb
from chromadb.config import Settings
from typing import List, Dict, Optional, Any
import uuid
from datetime import datetime
import hashlib
import os

# 从环境变量中获取 ChromaDB 连接信息
CHROMA_HOST = os.getenv("CHROMA_HOST")
CHROMA_PORT = os.getenv("CHROMA_PORT")


class VectorStoreService:
    """向量数据库服务封装"""
    
    def __init__(self, persist_directory: str = "./data/chroma"):
        """
        初始化向量数据库
        
        Args:
            persist_directory: 数据持久化目录
        """
        if CHROMA_HOST and CHROMA_PORT:
            self.client = chromadb.HttpClient(
                host=CHROMA_HOST,
                port=int(CHROMA_PORT),
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )

        else:
            # 否则，使用本地持久化客户端（作为回退）
            self.client = chromadb.PersistentClient(
                path=persist_directory,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            print(f"✓ VectorStoreService: Using local persistent client at {persist_directory}")
    
    
    def create_collection(
        self, 
        collection_name: str, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        创建向量集合
        """
        try:
            # 检查集合是否已存在
            try:
                self.client.get_collection(name=collection_name)
                raise ValueError(f"集合 '{collection_name}' 已存在")
            except Exception as e:
                # 集合不存在是正常情况，继续创建。
                if "Collection " in str(e) and " does not exist" in str(e):
                    pass
                else:
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
        """
        try:
            return self.client.get_collection(name=collection_name)
        except Exception as e:
            raise Exception(f"获取集合失败: {str(e)}")
    
    def list_collections(self) -> List[Dict[str, Any]]:
        """
        列出所有集合
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
        """
        try:
            collection = self.get_collection(collection_name)
            
            # 生成ID
            if ids is None:
                generated_ids = []
                for i, doc_content in enumerate(documents):
                    metadata = metadatas[i] if metadatas and i < len(metadatas) else {}
                    
                    # --- 修正后的 ID 生成逻辑 ---
                    # 优先使用唯一的 original_url 或 original_title
                    unique_doc_identifier = metadata.get("original_url") or metadata.get("original_title") or metadata.get("filename", "unknown_file")
                    
                    # 确保 ID 包含唯一文档源 + 块索引
                    chunk_index = metadata.get("chunk_index", i)

                    # 组合唯一标识符和块索引（内容长度用于二次保险，防止哈希碰撞）
                    unique_string_for_hash = f"{unique_doc_identifier}-{chunk_index}-{len(doc_content)}" 
                    
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
        """
        try:
            self.client.delete_collection(name=collection_name)
        except Exception as e:
            raise Exception(f"删除集合失败: {str(e)}")
    
    def get_collection_info(self, collection_name: str) -> Dict[str, Any]:
        """
        获取集合详细信息
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