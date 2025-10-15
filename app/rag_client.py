"""
AI Chat Platform with RAG - Python 客户端示例
展示如何使用 Python 调用 RAG API
"""
import requests
from typing import List, Dict, Any, Optional
import json


class RAGClient:
    """RAG API 客户端封装"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        """
        初始化客户端
        
        Args:
            base_url: API 服务地址
        """
        self.base_url = base_url
        self.session = requests.Session()
    
    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        response = self.session.get(f"{self.base_url}/health")
        response.raise_for_status()
        return response.json()
    
    def create_knowledge_base(
        self, 
        kb_name: str, 
        description: str = ""
    ) -> Dict[str, Any]:
        """
        创建知识库
        
        Args:
            kb_name: 知识库名称
            description: 描述
            
        Returns:
            创建结果
        """
        data = {
            "kb_name": kb_name,
            "description": description
        }
        response = self.session.post(
            f"{self.base_url}/api/v1/rag/knowledge-bases",
            json=data
        )
        response.raise_for_status()
        return response.json()
    
    def list_knowledge_bases(self) -> List[Dict[str, Any]]:
        """
        列出所有知识库
        
        Returns:
            知识库列表
        """
        response = self.session.get(
            f"{self.base_url}/api/v1/rag/knowledge-bases"
        )
        response.raise_for_status()
        return response.json()["knowledge_bases"]
    
    def get_knowledge_base_info(self, kb_name: str) -> Dict[str, Any]:
        """
        获取知识库信息
        
        Args:
            kb_name: 知识库名称
            
        Returns:
            知识库信息
        """
        response = self.session.get(
            f"{self.base_url}/api/v1/rag/knowledge-bases/{kb_name}"
        )
        response.raise_for_status()
        return response.json()
    
    def delete_knowledge_base(self, kb_name: str) -> Dict[str, Any]:
        """
        删除知识库
        
        Args:
            kb_name: 知识库名称
            
        Returns:
            删除结果
        """
        response = self.session.delete(
            f"{self.base_url}/api/v1/rag/knowledge-bases/{kb_name}"
        )
        response.raise_for_status()
        return response.json()
    
    def add_text(
        self,
        kb_name: str,
        text: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        添加文本到知识库
        
        Args:
            kb_name: 知识库名称
            text: 文本内容
            metadata: 元数据
            
        Returns:
            添加结果
        """
        data = {
            "kb_name": kb_name,
            "text": text,
            "metadata": metadata
        }
        response = self.session.post(
            f"{self.base_url}/api/v1/rag/add-text",
            json=data
        )
        response.raise_for_status()
        return response.json()
    
    def upload_document(
        self,
        kb_name: str,
        file_path: str
    ) -> Dict[str, Any]:
        """
        上传文档到知识库
        
        Args:
            kb_name: 知识库名称
            file_path: 文件路径
            
        Returns:
            上传结果
        """
        with open(file_path, 'rb') as f:
            files = {'file': f}
            data = {'kb_name': kb_name}
            response = self.session.post(
                f"{self.base_url}/api/v1/rag/upload",
                files=files,
                data=data
            )
        response.raise_for_status()
        return response.json()
    
    def search(
        self,
        kb_name: str,
        query: str,
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        搜索相关文档
        
        Args:
            kb_name: 知识库名称
            query: 查询文本
            top_k: 返回结果数量
            
        Returns:
            搜索结果
        """
        data = {
            "kb_name": kb_name,
            "query": query,
            "top_k": top_k
        }
        response = self.session.post(
            f"{self.base_url}/api/v1/rag/search",
            json=data
        )
        response.raise_for_status()
        return response.json()
    
    def rag_query(
        self,
        kb_name: str,
        query: str,
        top_k: int = 3
    ) -> Dict[str, Any]:
        """
        RAG 查询（仅检索，不调用 LLM）
        
        Args:
            kb_name: 知识库名称
            query: 查询问题
            top_k: 返回文档数量
            
        Returns:
            查询结果和上下文
        """
        data = {
            "kb_name": kb_name,
            "query": query,
            "top_k": top_k
        }
        response = self.session.post(
            f"{self.base_url}/api/v1/rag/query",
            json=data
        )
        response.raise_for_status()
        return response.json()
    
    def rag_chat(
        self,
        kb_name: str,
        query: str,
        model: str = "gpt-3.5-turbo",
        top_k: int = 3,
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> Dict[str, Any]:
        """
        RAG 聊天（检索 + LLM 生成）
        
        Args:
            kb_name: 知识库名称
            query: 用户问题
            model: 模型名称
            top_k: 检索文档数量
            temperature: 温度参数
            max_tokens: 最大生成长度
            
        Returns:
            生成的答案和来源文档
        """
        data = {
            "kb_name": kb_name,
            "query": query,
            "model": model,
            "top_k": top_k,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        response = self.session.post(
            f"{self.base_url}/api/v1/rag-chat",
            json=data
        )
        response.raise_for_status()
        return response.json()
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        model: str = "gpt-3.5-turbo",
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> Dict[str, Any]:
        """
        普通聊天（不使用 RAG）
        
        Args:
            messages: 消息列表
            model: 模型名称
            temperature: 温度参数
            max_tokens: 最大生成长度
            
        Returns:
            生成的回复
        """
        data = {
            "messages": messages,
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        response = self.session.post(
            f"{self.base_url}/api/v1/chat",
            json=data
        )
        response.raise_for_status()
        return response.json()


# ============================================================
# 使用示例
# ============================================================

def example_1_basic_workflow():
    """示例1: 基本工作流程"""
    print("\n" + "="*60)
    print("示例1: 基本 RAG 工作流程")
    print("="*60)
    
    client = RAGClient()
    kb_name = "ai_tutorial"
    
    # 1. 创建知识库
    print("\n1. 创建知识库...")
    result = client.create_knowledge_base(
        kb_name=kb_name,
        description="人工智能教程知识库"
    )
    print(f"✅ {result['message']}")
    
    # 2. 添加文本
    print("\n2. 添加文本内容...")
    texts = [
        "机器学习是人工智能的一个分支，它使计算机能够从数据中学习。",
        "深度学习使用多层神经网络来学习数据的层次化表示。",
        "自然语言处理（NLP）是让计算机理解和生成人类语言的技术。"
    ]
    
    for text in texts:
        result = client.add_text(kb_name=kb_name, text=text)
        print(f"   添加了 {result['chunks_count']} 个文本块")
    
    # 3. 查看知识库信息
    print("\n3. 查看知识库信息...")
    info = client.get_knowledge_base_info(kb_name)
    print(f"   知识库: {info['name']}")
    print(f"   文档数: {info['count']}")
    
    # 4. 搜索
    print("\n4. 搜索相关文档...")
    search_result = client.search(
        kb_name=kb_name,
        query="什么是深度学习？",
        top_k=2
    )
    print(f"   找到 {search_result['count']} 个相关文档")
    for i, doc in enumerate(search_result['results'], 1):
        print(f"\n   文档 {i}:")
        print(f"   内容: {doc['document'][:50]}...")
        print(f"   距离: {doc['distance']:.4f}")
    
    # 5. 清理
    print("\n5. 清理知识库...")
    result = client.delete_knowledge_base(kb_name)
    print(f"✅ {result['message']}")


def example_2_rag_chat():
    """示例2: RAG 聊天"""
    print("\n" + "="*60)
    print("示例2: RAG 聊天（需要配置 LLM API）")
    print("="*60)
    
    client = RAGClient()
    kb_name = "product_docs"
    
    try:
        # 创建知识库
        print("\n1. 创建产品文档知识库...")
        client.create_knowledge_base(
            kb_name=kb_name,
            description="产品使用文档"
        )
        
        # 添加产品文档
        print("\n2. 添加产品文档...")
        docs = [
            """产品名称：智能音箱 Pro
            特点：支持语音控制、智能家居联动、高保真音质
            价格：299元""",
            
            """使用方法：
            1. 连接电源
            2. 下载配套APP
            3. 扫描二维码配对
            4. 说出唤醒词"小智小智"即可开始使用""",
            
            """常见问题：
            Q: 无法连接网络怎么办？
            A: 检查WiFi设置，确保2.4GHz频段开启
            
            Q: 音质不好？
            A: 在APP中调整均衡器设置"""
        ]
        
        for doc in docs:
            client.add_text(kb_name=kb_name, text=doc)
        
        # RAG 聊天
        print("\n3. 开始 RAG 聊天...")
        print("\n⚠️  此步骤需要配置 LLM API")
        
        questions = [
            "这个产品多少钱？",
            "如何使用这个产品？",
            "连不上网怎么办？"
        ]
        
        for question in questions:
            print(f"\n问题: {question}")
            try:
                result = client.rag_chat(
                    kb_name=kb_name,
                    query=question,
                    model="gpt-3.5-turbo",
                    top_k=2
                )
                print(f"回答: {result['answer']}")
                print(f"参考了 {len(result['source_documents'])} 个文档")
            except Exception as e:
                print(f"❌ 错误: {str(e)}")
                print("提示: 请确保配置了 OPENAI_API_KEY 或 DEEPSEEK_API_KEY")
                break
        
    finally:
        # 清理
        print("\n4. 清理知识库...")
        try:
            client.delete_knowledge_base(kb_name)
            print("✅ 清理完成")
        except:
            pass


def example_3_document_upload():
    """示例3: 文档上传"""
    print("\n" + "="*60)
    print("示例3: 文档上传（需要准备测试文件）")
    print("="*60)
    
    client = RAGClient()
    kb_name = "document_kb"
    
    # 这里需要准备一个测试文件
    # 例如创建一个简单的文本文件
    test_file = "test_document.txt"
    
    # 创建测试文件
    with open(test_file, "w", encoding="utf-8") as f:
        f.write("""人工智能发展简史

人工智能（AI）的概念最早在1956年的达特茅斯会议上提出。
经过几十年的发展，AI 经历了多次起伏。

近年来，深度学习的突破使得 AI 在多个领域取得了显著进展，
包括计算机视觉、自然语言处理、语音识别等。

未来，AI 将继续深入到各行各业，改变我们的生活方式。""")
    
    try:
        # 创建知识库
        print("\n1. 创建知识库...")
        client.create_knowledge_base(kb_name=kb_name)
        
        # 上传文档
        print(f"\n2. 上传文档: {test_file}")
        result = client.upload_document(
            kb_name=kb_name,
            file_path=test_file
        )
        print(f"✅ {result['message']}")
        print(f"   文件: {result['filename']}")
        print(f"   文本块: {result['chunks_count']}")
        
        # 搜索
        print("\n3. 搜索文档内容...")
        search_result = client.search(
            kb_name=kb_name,
            query="AI的发展历史",
            top_k=3
        )
        
        for i, doc in enumerate(search_result['results'], 1):
            print(f"\n   结果 {i}:")
            print(f"   {doc['document']}")
        
    finally:
        # 清理
        print("\n4. 清理...")
        try:
            client.delete_knowledge_base(kb_name)
            import os
            os.remove(test_file)
            print("✅ 清理完成")
        except:
            pass


def main():
    """主函数"""
    print("\n" + "="*60)
    print("AI Chat Platform with RAG - Python 客户端示例")
    print("="*60)
    
    # 检查服务是否运行
    client = RAGClient()
    try:
        health = client.health_check()
        print(f"\n✅ 服务状态: {health['status']}")
        print(f"   版本: {health['version']}")
    except Exception as e:
        print(f"\n❌ 无法连接到服务: {str(e)}")
        print("   请确保服务已启动（运行 docker-compose up 或 uvicorn app.main:app）")
        return
    
    # 运行示例
    examples = [
        ("基本工作流程", example_1_basic_workflow),
        ("RAG 聊天", example_2_rag_chat),
        ("文档上传", example_3_document_upload)
    ]
    
    print("\n可用的示例:")
    for i, (name, _) in enumerate(examples, 1):
        print(f"{i}. {name}")
    print(f"{len(examples) + 1}. 运行所有示例")
    
    choice = input("\n请选择要运行的示例 (1-4): ")
    
    try:
        choice = int(choice)
        if 1 <= choice <= len(examples):
            examples[choice - 1][1]()
        elif choice == len(examples) + 1:
            for name, func in examples:
                func()
        else:
            print("无效的选择")
    except ValueError:
        print("无效的输入")
    except Exception as e:
        print(f"\n❌ 运行示例时出错: {str(e)}")


if __name__ == "__main__":
    main()