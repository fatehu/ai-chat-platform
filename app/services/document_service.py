"""
文档处理服务 - 文件上传和文本分块
"""
import os
from typing import List, Dict, Any
from pathlib import Path
import pypdf
from langchain_text_splitters import RecursiveCharacterTextSplitter
import re
import json

class DocumentService:
    """文档处理服务"""
    
    def __init__(self, upload_dir: str = "./data/uploads"):
        """
        初始化文档服务
        
        Args:
            upload_dir: 文件上传目录
        """
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化文本分割器
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,  # 每块大小
            chunk_overlap=200,  # 块之间的重叠
            length_function=len,
            separators=["\n\n", "\n", "。", "！", "？", ".", "!", "?", " ", ""]
        )
    
    def save_file(self, file_content: bytes, filename: str) -> str:
        """
        保存上传的文件
        
        Args:
            file_content: 文件内容
            filename: 文件名
            
        Returns:
            保存后的文件路径
        """
        try:
            file_path = self.upload_dir / filename
            with open(file_path, "wb") as f:
                f.write(file_content)
            return str(file_path)
        except Exception as e:
            raise Exception(f"保存文件失败: {str(e)}")
    
    def extract_text_from_pdf(self, file_path: str) -> str:
        """
        从PDF文件提取文本
        
        Args:
            file_path: PDF文件路径
            
        Returns:
            提取的文本
        """
        try:
            text = ""
            with open(file_path, "rb") as file:
                pdf_reader = pypdf.PdfReader(file)
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
            return text
        except Exception as e:
            raise Exception(f"提取PDF文本失败: {str(e)}")
    
    def extract_text_from_txt(self, file_path: str) -> str:
        """
        从文本文件读取内容
        
        Args:
            file_path: 文本文件路径
            
        Returns:
            文件内容
        """
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                return file.read()
        except Exception as e:
            raise Exception(f"读取文本文件失败: {str(e)}")
    
    def extract_text(self, file_path: str, file_type: str) -> str:
        """
        根据文件类型提取文本
        
        Args:
            file_path: 文件路径
            file_type: 文件类型 (pdf, txt, md)
            
        Returns:
            提取的文本
        """
        if file_type.lower() == "pdf":
            return self.extract_text_from_pdf(file_path)
        elif file_type.lower() in ["txt", "md"]:
            return self.extract_text_from_txt(file_path)
        else:
            raise ValueError(f"不支持的文件类型: {file_type}")
    
    def split_text(self, text: str) -> List[str]:
        """
        分割文本为块
        
        Args:
            text: 输入文本
            
        Returns:
            文本块列表
        """
        try:
            chunks = self.text_splitter.split_text(text)
            return chunks
        except Exception as e:
            raise Exception(f"分割文本失败: {str(e)}")
    def _process_markdown_with_metadata(
        self, 
        text: str, 
        base_metadata: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """处理带有内嵌元数据标记的 Markdown 文件"""
        
        documents = []
        # 定义匹配 <metadata_json_start>...<metadata_json_end> 及其后续内容的正则表达式
        pattern = re.compile(r'<metadata_json_start>(.*?)\s*<metadata_json_end>\s*(.*?)((?=<metadata_json_start>)|$)', re.DOTALL)
        
        matches = list(pattern.finditer(text))
        
        if not matches:
            # 如果没有匹配到标记，则将整个文件作为一个文档处理
            chunks = self.split_text(text)
            for i, chunk in enumerate(chunks):
                 doc_metadata = base_metadata.copy()
                 doc_metadata.update({"chunk_index": i, "total_chunks": len(chunks)})
                 documents.append({"text": chunk, "metadata": doc_metadata})
            return documents

        for match in matches:
            json_str = match.group(1).strip()
            content = match.group(2).strip()
            
            try:
                doc_metadata = json.loads(json_str)
            except json.JSONDecodeError:
                doc_metadata = {}

            # 将内容分块
            chunks = self.split_text(content)
            
            # 为每个块附加元数据
            for i, chunk in enumerate(chunks):
                final_metadata = base_metadata.copy()
                final_metadata.update(doc_metadata) # 包含 original_title, original_url 等信息
                final_metadata.update({
                    "chunk_index": i,
                    "total_chunks": len(chunks)
                })
                
                documents.append({
                    "text": chunk,
                    "metadata": final_metadata
                })

        return documents
    
    def process_document(
        self, 
        file_path: str, 
        file_type: str,
        metadata: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """
        处理文档：提取文本、分块、添加元数据
        
        Args:
            file_path: 文件路径
            file_type: 文件类型
            metadata: 额外的元数据
            
        Returns:
            处理后的文档块列表，每个块包含 text 和 metadata
        """
        try:
            # --- 关键修改：处理 MD 文件时调用特殊解析器 ---
            base_metadata = {
                "file_path": file_path,
                "file_type": file_type,
            }
            if metadata:
                base_metadata.update(metadata)

            if file_type.lower() == "md":
                # 对于 Markdown 文件，先提取文本
                text = self.extract_text_from_txt(file_path)
                # 使用专门的解析器处理内嵌元数据
                documents = self._process_markdown_with_metadata(text, base_metadata)
                return documents
            
            # 提取文本 (PDF, TXT)
            text = self.extract_text(file_path, file_type)
            
            # 分割文本
            chunks = self.split_text(text)
            
            # 为每个块添加元数据
            documents = []
            for i, chunk in enumerate(chunks):
                doc_metadata = {
                    "file_path": file_path,
                    "file_type": file_type,
                    "chunk_index": i,
                    "total_chunks": len(chunks)
                }
                
                # 合并额外的元数据
                if metadata:
                    doc_metadata.update(metadata)
                
                documents.append({
                    "text": chunk,
                    "metadata": doc_metadata
                })
            
            return documents
        except Exception as e:
            raise Exception(f"处理文档失败: {str(e)}")
    
    def list_files(self) -> List[Dict[str, Any]]:
        """
        列出所有上传的文件
        
        Returns:
            文件信息列表
        """
        try:
            files = []
            for file_path in self.upload_dir.iterdir():
                if file_path.is_file():
                    files.append({
                        "filename": file_path.name,
                        "size": file_path.stat().st_size,
                        "path": str(file_path)
                    })
            return files
        except Exception as e:
            raise Exception(f"列出文件失败: {str(e)}")


# 创建全局实例
def get_document_service() -> DocumentService:
    """获取文档服务实例"""
    return DocumentService()