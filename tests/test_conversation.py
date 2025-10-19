"""
多轮对话API完整测试脚本
演示所有核心功能
"""
import requests
import json
import time
from typing import Dict, Any

BASE_URL = "http://localhost:8000"


class ConversationClient:
    """对话客户端封装"""
    
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
        print(f"   标题: {data['title']}")
        print(f"   模型: {data['model']}\n")
        return session_id
    
    def send_message(
        self,
        session_id: str,
        message: str
    ) -> Dict[str, Any]:
        """发送消息（工具由Agent自动选择）"""
        print(f"👤 用户: {message}")
        
        payload = {"message": message}  # 只需要消息，工具自动选择
        
        response = self.session.post(
            f"{self.base_url}/api/v1/conversations/{session_id}/messages",
            json=payload
        )
        response.raise_for_status()
        data = response.json()
        
        print(f"🤖 助手: {data['answer']}")
        print(f"   迭代次数: {data['iterations']}")
        print(f"   执行时间: {data['execution_time']:.2f}秒")
        
        if data.get('steps'):
            print(f"   执行步骤:")
            for step in data['steps']:
                print(f"      - {step['action']}: {step.get('input', {})}")
        
        print()
        return data
    
    def get_messages(self, session_id: str) -> list:
        """获取消息历史"""
        response = self.session.get(
            f"{self.base_url}/api/v1/conversations/{session_id}/messages"
        )
        response.raise_for_status()
        return response.json()
    
    def list_conversations(self) -> list:
        """列出所有会话"""
        response = self.session.get(
            f"{self.base_url}/api/v1/conversations/"
        )
        response.raise_for_status()
        return response.json()
    
    def delete_conversation(self, session_id: str):
        """删除会话"""
        response = self.session.delete(
            f"{self.base_url}/api/v1/conversations/{session_id}"
        )
        response.raise_for_status()
        print(f"🗑️  会话已删除: {session_id}\n")


def test_basic_conversation():
    """测试1: 基础多轮对话"""
    print("=" * 60)
    print("测试1: 基础多轮对话")
    print("=" * 60)
    
    client = ConversationClient()
    
    # 创建会话
    session_id = client.create_conversation(
        title="基础对话测试"
    )
    
    # 多轮对话
    client.send_message(session_id, "你好!请介绍一下你自己")
    client.send_message(session_id, "我刚才问了你什么?")
    client.send_message(session_id, "很好,记住我叫张三")
    client.send_message(session_id, "我叫什么名字?")
    
    # 查看历史
    messages = client.get_messages(session_id)
    print(f"📜 消息历史 ({len(messages)}条):")
    for msg in messages:
        print(f"   {msg['role']}: {msg['content'][:50]}...")
    print()


def test_calculator_tool():
    """测试2: 使用计算器工具（自动选择）"""
    print("=" * 60)
    print("测试2: 计算器工具（Agent自动选择）")
    print("=" * 60)
    
    client = ConversationClient()
    session_id = client.create_conversation(
        title="计算器测试"
    )
    
    # Agent会自动判断需要使用calculator
    client.send_message(session_id, "帮我计算 1234 * 5678")
    client.send_message(session_id, "再帮我算一下刚才结果的平方根")


def test_time_tools():
    """测试3: 时间相关工具（自动选择）"""
    print("=" * 60)
    print("测试3: 时间工具（Agent自动选择）")
    print("=" * 60)
    
    client = ConversationClient()
    session_id = client.create_conversation(
        title="时间工具测试"
    )
    
    client.send_message(session_id, "现在几点了?")
    client.send_message(session_id, "3小时后是几点?")


def test_multiple_tools():
    """测试4: Agent自动组合多个工具"""
    print("=" * 60)
    print("测试4: 组合工具使用（Agent自动判断）")
    print("=" * 60)
    
    client = ConversationClient()
    session_id = client.create_conversation(
        title="组合工具测试"
    )
    
    # Agent会自动判断需要time和calculator工具
    client.send_message(
        session_id,
        "现在是几点?帮我计算100小时后是几点,并告诉我相当于多少天"
    )


def test_unit_converter():
    """测试5: 单位转换（自动选择）"""
    print("=" * 60)
    print("测试5: 单位转换（Agent自动选择）")
    print("=" * 60)
    
    client = ConversationClient()
    session_id = client.create_conversation(
        title="单位转换测试"
    )
    
    client.send_message(session_id, "100摄氏度等于多少华氏度?")
    client.send_message(session_id, "那100华氏度呢?")


def test_text_analysis():
    """测试6: 文本分析（自动选择）"""
    print("=" * 60)
    print("测试6: 文本分析（Agent自动选择）")
    print("=" * 60)
    
    client = ConversationClient()
    session_id = client.create_conversation(
        title="文本分析测试"
    )
    
    text = """
    人工智能是计算机科学的一个分支。它企图了解智能的实质,
    并生产出一种新的能以人类智能相似的方式做出反应的智能机器。
    该领域的研究包括机器人、语言识别、图像识别、自然语言处理和专家系统等。
    """
    
    client.send_message(session_id, f"请分析以下文本:{text}")


def test_rag_conversation():
    """测试7: 启用RAG的对话"""
    print("=" * 60)
    print("测试7: RAG对话")
    print("=" * 60)
    
    client = ConversationClient()
    
    # 首先创建知识库并上传文档
    print("准备知识库...")
    
    # 创建知识库
    kb_response = requests.post(
        f"{BASE_URL}/api/v1/rag/knowledge-bases",
        json={"kb_name": "test_kb", "description": "测试知识库"}
    )
    
    if kb_response.status_code == 200 or kb_response.status_code == 400:
        # 添加测试文本
        requests.post(
            f"{BASE_URL}/api/v1/rag/add-text",
            json={
                "kb_name": "test_kb",
                "text": """
                公司产品说明:
                产品A: 智能手机,价格2999元,具有高清摄像头和长续航能力。
                产品B: 平板电脑,价格3999元,配备大屏幕和强大处理器。
                产品C: 智能手表,价格1299元,支持健康监测和消息提醒。
                
                促销活动:
                - 产品A限时优惠,现价2699元
                - 购买产品B赠送保护套
                - 产品C买二送一
                """
            }
        )
        print("✅ 知识库准备完成\n")
    
    # 创建启用RAG的会话
    session_id = client.create_conversation(
        title="RAG对话测试",
        enable_rag=True,
        kb_name="test_kb"
    )
    
    # 基于知识库的对话
    result = client.send_message(
        session_id,
        "产品A的价格是多少?"
    )
    
    if result.get('source_documents'):
        print("📚 参考文档:")
        for doc in result['source_documents']:
            print(f"   - {doc['content'][:100]}...")
        print()
    
    client.send_message(
        session_id,
        "产品B和产品C呢?"
    )
    
    client.send_message(
        session_id,
        "有什么促销活动吗?"
    )


def test_conversation_management():
    """测试8: 会话管理"""
    print("=" * 60)
    print("测试8: 会话管理")
    print("=" * 60)
    
    client = ConversationClient()
    
    # 创建多个会话
    session1 = client.create_conversation(title="会话1")
    session2 = client.create_conversation(title="会话2")
    session3 = client.create_conversation(title="会话3")
    
    # 向不同会话发送消息
    client.send_message(session1, "我在会话1")
    client.send_message(session2, "我在会话2")
    client.send_message(session3, "我在会话3")
    
    # 列出所有会话
    conversations = client.list_conversations()
    print(f"📋 会话列表 ({len(conversations)}个):")
    for conv in conversations:
        print(f"   - {conv['title']}: {conv['session_id'][:16]}... "
              f"({conv['message_count']}条消息)")
    print()
    
    # 删除测试会话
    client.delete_conversation(session1)
    client.delete_conversation(session2)
    client.delete_conversation(session3)


def test_complex_scenario():
    """测试9: 复杂场景 - Agent自动选择多工具"""
    print("=" * 60)
    print("测试9: 复杂场景（Agent自动判断所需工具）")
    print("=" * 60)
    
    client = ConversationClient()
    session_id = client.create_conversation(
        title="复杂场景测试"
    )
    
    # 场景: 用户询问时间，然后计算
    client.send_message(session_id, "我需要规划一次旅行。首先,现在是几点?")
    client.send_message(session_id, "如果我6小时后出发,到达时间是几点?")
    client.send_message(session_id, "帮我计算如果温度是25摄氏度,换算成华氏度是多少?")
    client.send_message(session_id, "总结一下我问了哪些问题?")


def test_error_handling():
    """测试10: 错误处理"""
    print("=" * 60)
    print("测试10: 错误处理")
    print("=" * 60)
    
    client = ConversationClient()
    
    # 测试不存在的会话
    try:
        client.send_message("invalid_session_id", "测试消息")
    except requests.exceptions.HTTPError as e:
        print(f"✅ 正确捕获错误: {e.response.status_code} - 会话不存在\n")
    
    # 测试正常场景（工具自动选择）
    session_id = client.create_conversation(title="错误测试")
    result = client.send_message(session_id, "你好")
    print(f"✅ 正常处理: {result['answer'][:50]}...\n")


def run_all_tests():
    """运行所有测试"""
    print("\n" + "🚀" * 30)
    print("开始运行完整测试套件")
    print("🚀" * 30 + "\n")
    
    tests = [
        ("基础对话", test_basic_conversation),
        ("计算器工具", test_calculator_tool),
        ("时间工具", test_time_tools),
        ("组合工具", test_multiple_tools),
        ("单位转换", test_unit_converter),
        ("文本分析", test_text_analysis),
        ("RAG对话", test_rag_conversation),
        ("会话管理", test_conversation_management),
        ("复杂场景", test_complex_scenario),
        ("错误处理", test_error_handling),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            test_func()
            passed += 1
            print(f"✅ {name} - 通过\n")
        except Exception as e:
            failed += 1
            print(f"❌ {name} - 失败: {str(e)}\n")
        
        time.sleep(1)  # 避免请求过快
    
    print("\n" + "=" * 60)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    # 检查服务是否运行
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            print("✅ 服务正在运行\n")
            
            # 运行所有测试
            run_all_tests()
        else:
            print(f"❌ 服务状态异常: {response.status_code}")
    except requests.exceptions.ConnectionError:
        print(f"❌ 无法连接到服务: {BASE_URL}")
        print("请确保服务正在运行: docker-compose up -d")