"""
RAG 功能测试脚本
按步骤测试各个功能模块
"""
import requests
import json
from pathlib import Path

# 配置
BASE_URL = "http://localhost:8000"
KB_NAME = "test_kb"


def print_response(title, response):
    """打印响应"""
    print(f"\n{'='*60}")
    print(f"【{title}】")
    print(f"{'='*60}")
    print(f"状态码: {response.status_code}")
    if response.status_code == 200:
        print(f"响应: {json.dumps(response.json(), ensure_ascii=False, indent=2)}")
    else:
        print(f"错误: {response.text}")
    print(f"{'='*60}\n")


def test_1_health_check():
    """测试1: 健康检查"""
    print("\n🔍 测试1: 健康检查")
    response = requests.get(f"{BASE_URL}/health")
    print_response("健康检查", response)
    return response.status_code == 200


def test_2_create_knowledge_base():
    """测试2: 创建知识库"""
    print("\n📚 测试2: 创建知识库")
    data = {
        "kb_name": KB_NAME,
        "description": "测试知识库"
    }
    response = requests.post(
        f"{BASE_URL}/api/v1/rag/knowledge-bases",
        json=data
    )
    print_response("创建知识库", response)
    return response.status_code == 200


def test_3_list_knowledge_bases():
    """测试3: 列出所有知识库"""
    print("\n📋 测试3: 列出所有知识库")
    response = requests.get(f"{BASE_URL}/api/v1/rag/knowledge-bases")
    print_response("列出知识库", response)
    return response.status_code == 200


def test_4_add_text():
    """测试4: 添加文本到知识库"""
    print("\n✍️ 测试4: 添加文本到知识库")
    
    # 添加一些测试文本
    texts = [
        """人工智能（Artificial Intelligence，AI）是计算机科学的一个分支，
        它企图了解智能的实质，并生产出一种新的能以人类智能相似的方式做出反应的智能机器。
        该领域的研究包括机器人、语言识别、图像识别、自然语言处理和专家系统等。""",
        
        """深度学习是机器学习的一个子领域，它基于人工神经网络进行学习。
        深度学习模型能够学习多层次的表示，从而能够处理复杂的模式识别任务。
        常见的深度学习模型包括卷积神经网络（CNN）和循环神经网络（RNN）。""",
        
        """自然语言处理（NLP）是人工智能和语言学领域的分支学科。
        它研究如何让计算机理解、处理和生成人类语言。
        NLP的应用包括机器翻译、情感分析、文本摘要、问答系统等。"""
    ]
    
    for i, text in enumerate(texts, 1):
        data = {
            "kb_name": KB_NAME,
            "text": text,
            "metadata": {"source": f"test_text_{i}"}
        }
        response = requests.post(
            f"{BASE_URL}/api/v1/rag/add-text",
            json=data
        )
        print_response(f"添加文本 {i}", response)
        if response.status_code != 200:
            return False
    
    return True


def test_5_get_kb_info():
    """测试5: 获取知识库信息"""
    print("\n📊 测试5: 获取知识库信息")
    response = requests.get(f"{BASE_URL}/api/v1/rag/knowledge-bases/{KB_NAME}")
    print_response("知识库信息", response)
    return response.status_code == 200


def test_6_search():
    """测试6: 搜索相关文档"""
    print("\n🔎 测试6: 搜索相关文档")
    
    queries = [
        "什么是人工智能？",
        "深度学习有哪些应用？",
        "NLP是什么？"
    ]
    
    for query in queries:
        data = {
            "kb_name": KB_NAME,
            "query": query,
            "top_k": 2
        }
        response = requests.post(
            f"{BASE_URL}/api/v1/rag/search",
            json=data
        )
        print_response(f"搜索: {query}", response)
        if response.status_code != 200:
            return False
    
    return True


def test_7_rag_query():
    """测试7: RAG 查询"""
    print("\n💬 测试7: RAG 查询")
    data = {
        "kb_name": KB_NAME,
        "query": "什么是深度学习？它有什么特点？",
        "top_k": 2
    }
    response = requests.post(
        f"{BASE_URL}/api/v1/rag/query",
        json=data
    )
    print_response("RAG查询", response)
    return response.status_code == 200


def test_8_rag_chat():
    """测试8: RAG 聊天（需要配置 LLM API）"""
    print("\n🤖 测试8: RAG 聊天")
    print("⚠️  此测试需要配置 LLM API（OpenAI 或 DeepSeek）")
    
    user_input = input("是否执行 RAG 聊天测试？(y/n): ")
    if user_input.lower() != 'y':
        print("跳过 RAG 聊天测试")
        return True
    
    data = {
        "kb_name": KB_NAME,
        "query": "请详细介绍一下深度学习，指出我给了你什么数据",
        "model": "deepseek-chat",  # 根据你的配置修改
        "top_k": 3
    }
    
    response = requests.post(
        f"{BASE_URL}/api/v1/rag-chat",
        json=data
    )
    print_response("RAG聊天", response)
    return response.status_code == 200


def test_9_upload_document():
    """测试9: 上传文档（需要准备测试文件）"""
    print("\n📄 测试9: 上传文档")
    print("⚠️  此测试需要准备一个测试文件（PDF/TXT/MD）")
    
    user_input = input("是否执行文档上传测试？(y/n): ")
    if user_input.lower() != 'y':
        print("跳过文档上传测试")
        return True
    
    file_path = input("请输入测试文件路径: ")
    if not Path(file_path).exists():
        print(f"文件不存在: {file_path}")
        return False
    
    with open(file_path, 'rb') as f:
        files = {'file': f}
        data = {'kb_name': KB_NAME}
        response = requests.post(
            f"{BASE_URL}/api/v1/rag/upload",
            files=files,
            data=data
        )
    
    print_response("上传文档", response)
    return response.status_code == 200


def test_10_cleanup():
    """测试10: 清理（删除测试知识库）"""
    print("\n🧹 测试10: 清理测试数据")
    
    user_input = input("是否删除测试知识库？(y/n): ")
    if user_input.lower() != 'y':
        print("保留测试知识库")
        return True
    
    response = requests.delete(f"{BASE_URL}/api/v1/rag/knowledge-bases/{KB_NAME}")
    print_response("删除知识库", response)
    return response.status_code == 200


def main():
    """主测试流程"""
    print("="*60)
    print("RAG 功能测试脚本")
    print("="*60)
    
    tests = [
        ("健康检查", test_1_health_check),
        ("创建知识库", test_2_create_knowledge_base),
        ("列出知识库", test_3_list_knowledge_bases),
        ("添加文本", test_4_add_text),
        ("获取知识库信息", test_5_get_kb_info),
        ("搜索文档", test_6_search),
        ("RAG查询", test_7_rag_query),
        ("RAG聊天", test_8_rag_chat),
        ("上传文档", test_9_upload_document),
        ("清理测试数据", test_10_cleanup)
    ]
    
    results = []
    
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ 测试失败: {name}")
            print(f"错误: {str(e)}")
            results.append((name, False))
            
            user_input = input("\n是否继续下一个测试？(y/n): ")
            if user_input.lower() != 'y':
                break
    
    # 输出测试总结
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)
    
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{status} - {name}")
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    print(f"\n总计: {passed}/{total} 测试通过")
    print("="*60)


if __name__ == "__main__":
    main()