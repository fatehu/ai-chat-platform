"""
RAG 服务 - 整合 Embedding、向量数据库和文档处理
"""
from typing import List, Dict, Any, Optional
from .embedding_service import EmbeddingService
from .vector_store import VectorStoreService
from .document_service import DocumentService


class RAGService:
    """RAG 服务封装"""
    
    def __init__(
        self,
        embedding_service: EmbeddingService,
        vector_store: VectorStoreService,
        document_service: DocumentService
    ):
        """
        初始化 RAG 服务
        
        Args:
            embedding_service: Embedding 服务
            vector_store: 向量数据库服务
            document_service: 文档服务
        """
        self.embedding_service = embedding_service
        self.vector_store = vector_store
        self.document_service = document_service
    
    def create_knowledge_base(
        self,
        kb_name: str,
        description: str = ""
    ) -> Dict[str, Any]:
        """
        创建知识库（向量集合）
        
        Args:
            kb_name: 知识库名称
            description: 描述
            
        Returns:
            创建结果
        """
        try:
            metadata = {
                "description": description,
                "type": "knowledge_base"
            }
            self.vector_store.create_collection(kb_name, metadata)
            return {
                "success": True,
                "kb_name": kb_name,
                "message": f"知识库 '{kb_name}' 创建成功"
            }
        except Exception as e:
            raise Exception(f"创建知识库失败: {str(e)}")
    
    def upload_document(
        self,
        kb_name: str,
        file_content: bytes,
        filename: str,
        file_type: str
    ) -> Dict[str, Any]:
        """
        上传文档到知识库
        
        Args:
            kb_name: 知识库名称
            file_content: 文件内容
            filename: 文件名
            file_type: 文件类型 (pdf, txt, md)
            
        Returns:
            上传结果
        """
        try:
            # 1. 保存文件
            file_path = self.document_service.save_file(file_content, filename)
            
            # 2. 处理文档（提取文本、分块）
            documents = self.document_service.process_document(
                file_path,
                file_type,
                metadata={"filename": filename}
            )
            
            # 3. 获取文本块
            texts = [doc["text"] for doc in documents]
            metadatas = [doc["metadata"] for doc in documents]
            
            # 4. 生成向量
            # embeddings = self.embedding_service.get_embeddings(texts)
 
            # # 5. 存储到向量数据库
            # doc_ids = self.vector_store.add_documents(
            #     collection_name=kb_name,
            #     documents=texts,
            #     embeddings=embeddings,
            #     metadatas=metadatas
            # )
             # 4. 分批生成向量以避免API限制
            BATCH_SIZE = 25  # 根据API的限制设置
            all_embeddings = []
            
            for i in range(0, len(texts), BATCH_SIZE):
                batch_texts = texts[i:i + BATCH_SIZE]
                batch_embeddings = self.embedding_service.get_embeddings(batch_texts)
                all_embeddings.extend(batch_embeddings)
                print(f"为文档 '{filename}' 生成向量: 处理批次 {i // BATCH_SIZE + 1}，包含 {len(batch_texts)} 个文本块")
            
            # 5. 存储到向量数据库
            doc_ids = self.vector_store.add_documents(
                collection_name=kb_name,
                documents=texts,
                embeddings=all_embeddings, # 使用分批生成的完整向量列表
                metadatas=metadatas
            )
            
            return {
                "success": True,
                "kb_name": kb_name,
                "filename": filename,
                "chunks_count": len(texts),
                "doc_ids": doc_ids,
                "message": f"文档 '{filename}' 上传成功，共 {len(texts)} 个文本块"
            }
        except Exception as e:
            raise Exception(f"上传文档失败: {str(e)}")
    
    def add_text(
        self,
        kb_name: str,
        text: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        直接添加文本到知识库
        
        Args:
            kb_name: 知识库名称
            text: 文本内容
            metadata: 元数据
            
        Returns:
            添加结果
        """
        try:
            # 1. 分割文本
            chunks = self.document_service.split_text(text)
            
            # 2. 准备元数据
            metadatas = []
            for i, chunk in enumerate(chunks):
                chunk_metadata = {
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "source": "direct_text"
                }
                if metadata:
                    chunk_metadata.update(metadata)
                metadatas.append(chunk_metadata)
            
            # 3. 生成向量
            # embeddings = self.embedding_service.get_embeddings(chunks)
            
            # 4. 存储到向量数据库
            # doc_ids = self.vector_store.add_documents(
            #     collection_name=kb_name,
            #     documents=chunks,
            #     embeddings=embeddings,
            #     metadatas=metadatas
            # )
            
            # 3. 分批生成向量
            BATCH_SIZE = 25
            all_embeddings = []
            
            for i in range(0, len(chunks), BATCH_SIZE):
                batch_chunks = chunks[i:i + BATCH_SIZE]
                batch_embeddings = self.embedding_service.get_embeddings(batch_chunks)
                all_embeddings.extend(batch_embeddings)
                print(f"为直接添加的文本生成向量: 处理批次 {i // BATCH_SIZE + 1}，包含 {len(batch_chunks)} 个文本块")

            # 4. 存储到向量数据库
            doc_ids = self.vector_store.add_documents(
                collection_name=kb_name,
                documents=chunks,
                embeddings=all_embeddings, # 使用分批生成的完整向量列表
                metadatas=metadatas
            )

            return {
                "success": True,
                "kb_name": kb_name,
                "chunks_count": len(chunks),
                "doc_ids": doc_ids,
                "message": f"文本添加成功，共 {len(chunks)} 个文本块"
            }
        except Exception as e:
            raise Exception(f"添加文本失败: {str(e)}")
    
    def search(
        self,
        kb_name: str,
        query: str,
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        在知识库中搜索相关文档
        
        Args:
            kb_name: 知识库名称
            query: 查询文本
            top_k: 返回结果数量
            
        Returns:
            搜索结果
        """
        try:
            # 1. 生成查询向量
            query_embedding = self.embedding_service.get_embedding(query)
            
            # 2. 向量检索
            results = self.vector_store.query(
                collection_name=kb_name,
                query_embedding=query_embedding,
                n_results=top_k
            )
            
            return {
                "success": True,
                "kb_name": kb_name,
                "query": query,
                "results": results["results"],
                "count": results["count"]
            }
        except Exception as e:
            raise Exception(f"搜索失败: {str(e)}")
    
    def rag_query(
        self,
        kb_name: str,
        query: str,
        top_k: int = 3
    ) -> Dict[str, Any]:
        """
        RAG 查询：检索相关文档并返回上下文
        用于与 LLM 结合生成答案
        
        Args:
            kb_name: 知识库名称
            query: 查询问题
            top_k: 返回文档数量
            
        Returns:
            查询结果和上下文
        """
        try:
            # 搜索相关文档
            search_results = self.search(kb_name, query, top_k)
            
            # 构建上下文
            context_parts = []
            formatted_documents = [] # 用于存储格式化后的文档
            for i, result in enumerate(search_results["results"], 1):
                context_parts.append(f"[文档{i}]\n{result['document']}\n")
            
                # 将文档结构统一为 Agent 期望的结构
                formatted_documents.append({
                    "content": result['document'], # <--- **关键修改：将 'document' 映射到 'content'**
                    "metadata": result.get('metadata', {}) # 包含元数据
                })

            context = "\n".join(context_parts)
            
            return {
                "success": True,
                "kb_name": kb_name,
                "query": query,
                "context": context,
                # "source_documents": search_results["results"],
                "source_documents": formatted_documents,
                "count": search_results["count"]
            }
        except Exception as e:
            raise Exception(f"RAG查询失败: {str(e)}")
    
    def list_knowledge_bases(self) -> List[Dict[str, Any]]:
        """
        列出所有知识库
        
        Returns:
            知识库列表
        """
        try:
            return self.vector_store.list_collections()
        except Exception as e:
            raise Exception(f"列出知识库失败: {str(e)}")
    
    def get_knowledge_base_info(self, kb_name: str) -> Dict[str, Any]:
        """
        获取知识库信息
        
        Args:
            kb_name: 知识库名称
            
        Returns:
            知识库信息
        """
        try:
            return self.vector_store.get_collection_info(kb_name)
        except Exception as e:
            raise Exception(f"获取知识库信息失败: {str(e)}")
    
    def delete_knowledge_base(self, kb_name: str) -> Dict[str, Any]:
        """
        删除知识库
        
        Args:
            kb_name: 知识库名称
            
        Returns:
            删除结果
        """
        try:
            self.vector_store.delete_collection(kb_name)
            return {
                "success": True,
                "kb_name": kb_name,
                "message": f"知识库 '{kb_name}' 删除成功"
            }
        except Exception as e:
            raise Exception(f"删除知识库失败: {str(e)}")


# 创建全局实例
def get_rag_service() -> RAGService:
    """获取 RAG 服务实例"""
    from .embedding_service import get_embedding_service
    from .vector_store import get_vector_store
    from .document_service import get_document_service
    
    return RAGService(
        embedding_service=get_embedding_service(),
        vector_store=get_vector_store(),
        document_service=get_document_service()
    )