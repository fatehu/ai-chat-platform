"""
RAG 对话测试函数
确保 Agent 在启用 RAG 时能正确检索知识库内容并进行回答。

依赖于 ConversationClient 类 (来自您之前的测试脚本) 和 RAG API 端点。
"""

import requests
import time
from typing import Dict, Any, List

# 假设 BASE_URL 和 ConversationClient 已在文件开头定义
BASE_URL = "http://localhost:8000"

class ConversationClient:
    """（简化版，仅包含 RAG 测试所需方法）"""
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.session = requests.Session()

    def create_conversation(
        self,
        title: str = "测试对话",
        model: str = "deepseek-chat",
        enable_rag: bool = False,
        kb_name: str = None
    ) -> str:
        """创建会话"""
        response = self.session.post(
            f"{self.base_url}/api/v1/conversations/",
            json={
                "title": title,
                "model": model,
                "enable_rag": enable_rag,
                "kb_name": kb_name,
                "temperature": 0.7
            }
        )
        response.raise_for_status()
        data = response.json()
        session_id = data["session_id"]
        print(f"✅ 会话已创建: {session_id}")
        print(f"  标题: {data['title']}")
        print(f"  模型: {data['model']}")
        print(f"  启用RAG: {enable_rag}\n")
        return session_id
    
    def send_message(
        self,
        session_id: str,
        message: str
    ) -> Dict[str, Any]:
        """发送消息"""
        print(f"👤 用户: {message}")
        response = self.session.post(
            f"{self.base_url}/api/v1/conversations/{session_id}/messages",
            json={"message": message}
        )
        response.raise_for_status()
        data = response.json()
        
        print(f"🤖 助手: {data['answer']}")
        print(f"  执行时间: {data['execution_time']:.2f}秒")
        
        if data.get('source_documents'):
            print(f"📚 参考文档 ({len(data['source_documents'])} 条):")
            # **注意：这里使用了兼容性检查，以解决之前 'content' 或 'document' 的冲突**
            for doc in data['source_documents']:
                content = doc.get('content') or doc.get('document') or doc.get('page_content')
                print(f"    - 内容片段: {content[:80]}...")
            print()
            
        return data

    def delete_conversation(self, session_id: str):
        """删除会话"""
        self.session.delete(f"{self.base_url}/api/v1/conversations/{session_id}")
        print(f"🗑️  会话已删除: {session_id}")
        
    def prepare_knowledge_base(self, kb_name: str) -> bool:
        """创建知识库并添加测试数据"""
        print(f"🛠️  准备知识库 '{kb_name}'...")
        
        # 1. 创建或确保知识库存在 (忽略 400 错误,因为它可能表示已存在)
        requests.post(
            f"{BASE_URL}/api/v1/rag/knowledge-bases",
            json={"kb_name": kb_name, "description": "Agent RAG 测试数据"}
        )
        
        # 2. 添加测试文本
        text = """
            核心产品信息:
            产品 A: 智能手机,价格2999元,具有高清摄像头。
            产品 B: 笔记本电脑,价格6999元,用于专业图形处理。
            产品 C: 智能手表,价格1299元,支持运动追踪和心率监测。
            
            技术支持:
            所有产品享有两年质保。技术支持热线: 400-888-999。
        """
        
        response = requests.post(
            f"{BASE_URL}/api/v1/rag/add-text",
            json={
                "kb_name": kb_name,
                "text": text,
                "metadata": {"source": "test_script_data"}
            }
        )
        
        if response.status_code != 200:
            print(f"❌ 添加知识库文本失败: {response.text}")
            return False
            
        print("✅ 知识库准备完成\n")
        return True
    
    def cleanup_knowledge_base(self, kb_name: str):
        """删除测试知识库"""
        requests.delete(f"{BASE_URL}/api/v1/rag/knowledge-bases/{kb_name}")
        print(f"🧹 知识库 '{kb_name}' 已清理\n")

    
def test_rag_conversation():
    """测试 Agent 启用 RAG 后的对话能力"""
    TEST_KB_NAME = "agent_test_kb"
    client = ConversationClient()
    
    print("=" * 60)
    print("测试: Agent RAG 对话能力")
    print("=" * 60)
    
    try:
        # 1. 准备知识库
        if not client.prepare_knowledge_base(TEST_KB_NAME):
            return

        # 2. 创建启用 RAG 的会话
        session_id = client.create_conversation(
            title="RAG Agent 测试",
            enable_rag=True,
            kb_name=TEST_KB_NAME
        )
        
        # 3. 发送需要 RAG 的问题
        user_query = "产品B的主要特点和价格是多少?"
        result = client.send_message(session_id, user_query)
        
        # 4. 验证结果
        final_answer = result['answer']
        source_docs = result.get('source_documents', [])

        is_passed = True
        
        if "6999" not in final_answer and "笔记本电脑" not in final_answer:
            print("❌ 验证失败: 答案未提及产品B的关键信息（价格/类型）")
            is_passed = False
            
        if not source_docs or len(source_docs) == 0:
            print("❌ 验证失败: 未返回任何参考文档")
            is_passed = False
            
        # 清理
        client.delete_conversation(session_id)
        
        if is_passed:
            print("✅ RAG Agent 对话 - 通过\n")
            return True
        else:
            print("❌ RAG Agent 对话 - 失败\n")
            return False

    except requests.exceptions.HTTPError as e:
        print(f"❌ 测试失败: 发生 HTTP 错误: {e}")
        print(f"错误详情: {e.response.text}")
        return False
    except Exception as e:
        print(f"❌ 测试失败: 发生未知错误: {str(e)}")
        return False
    finally:
        # 确保清理知识库 (可选，但推荐)
        client.cleanup_knowledge_base(TEST_KB_NAME)


if __name__ == "__main__":
    test_rag_conversation()