"""
重构后的API使用示例
展示如何使用新的灵活配置和动态RAG功能
"""
import requests
import json

BASE_URL = "http://localhost:8000"


# ============================================================
# 示例1: 基础会话 - 动态配置模型和参数
# ============================================================

def example_basic_conversation():
    """示例：基础会话，每次消息使用不同的配置"""
    print("\n" + "="*60)
    print("示例1: 基础会话 - 动态配置")
    print("="*60)
    
    # 1. 创建会话（只需要标题）
    print("\n1. 创建会话...")
    response = requests.post(f"{BASE_URL}/api/v1/conversations/", json={
        "title": "Python学习助手"
    })
    session_id = response.json()["session_id"]
    print(f"   会话ID: {session_id}")
    
    # 2. 第一条消息：使用默认配置
    print("\n2. 发送第一条消息（默认配置）...")
    response = requests.post(
        f"{BASE_URL}/api/v1/conversations/{session_id}/messages",
        json={
            "message": "你好！",
            "model": "deepseek-chat",
            "temperature": 0.7
        }
    )
    print(f"   回复: {response.json()['assistant_message']['content'][:50]}...")
    
    # 3. 第二条消息：调高温度，获得更有创意的回答
    print("\n3. 发送第二条消息（高温度）...")
    response = requests.post(
        f"{BASE_URL}/api/v1/conversations/{session_id}/messages",
        json={
            "message": "给我讲个笑话",
            "model": "deepseek-chat",
            "temperature": 0.9  # 更高的温度
        }
    )
    print(f"   回复: {response.json()['assistant_message']['content'][:50]}...")
    
    # 4. 第三条消息：降低温度，获得更精确的回答
    print("\n4. 发送第三条消息（低温度）...")
    response = requests.post(
        f"{BASE_URL}/api/v1/conversations/{session_id}/messages",
        json={
            "message": "什么是Python？",
            "model": "deepseek-chat",
            "temperature": 0.3  # 更低的温度
        }
    )
    print(f"   回复: {response.json()['assistant_message']['content'][:100]}...")
    
    print("\n✅ 示例1完成")


# ============================================================
# 示例2: 动态RAG - 每次消息使用不同的知识库
# ============================================================

def example_dynamic_rag():
    """示例：动态RAG，灵活切换知识库"""
    print("\n" + "="*60)
    print("示例2: 动态RAG - 灵活切换知识库")
    print("="*60)
    
    # 1. 创建会话
    print("\n1. 创建会话...")
    response = requests.post(f"{BASE_URL}/api/v1/conversations/", json={
        "title": "多语言编程助手"
    })
    session_id = response.json()["session_id"]
    print(f"   会话ID: {session_id}")
    
    # 2. 第一条消息：使用Python知识库
    print("\n2. 使用Python知识库...")
    response = requests.post(
        f"{BASE_URL}/api/v1/conversations/{session_id}/messages",
        json={
            "message": "Python的装饰器如何使用？",
            "model": "deepseek-chat",
            "enable_rag": True,
            "kb_name": "python_docs",
            "rag_top_k": 3
        }
    )
    result = response.json()
    print(f"   回复: {result['assistant_message']['content'][:100]}...")
    if result.get("rag_info"):
        print(f"   RAG信息: 找到 {result['rag_info']['documents_found']} 个相关文档")
    
    # 3. 第二条消息：切换到Java知识库
    print("\n3. 切换到Java知识库...")
    response = requests.post(
        f"{BASE_URL}/api/v1/conversations/{session_id}/messages",
        json={
            "message": "Java的注解和Python的装饰器有什么区别？",
            "model": "deepseek-chat",
            "enable_rag": True,
            "kb_name": "java_docs",  # 不同的知识库
            "rag_top_k": 3
        }
    )
    result = response.json()
    print(f"   回复: {result['assistant_message']['content'][:100]}...")
    if result.get("rag_info"):
        print(f"   RAG信息: 找到 {result['rag_info']['documents_found']} 个相关文档")
    
    # 4. 第三条消息：不使用知识库，直接对话
    print("\n4. 不使用知识库...")
    response = requests.post(
        f"{BASE_URL}/api/v1/conversations/{session_id}/messages",
        json={
            "message": "总结一下我们讨论的内容",
            "model": "deepseek-chat",
            "enable_rag": False  # 不使用RAG
        }
    )
    result = response.json()
    print(f"   回复: {result['assistant_message']['content'][:100]}...")
    
    print("\n✅ 示例2完成")


# ============================================================
# 示例3: 智能选择RAG - 根据问题类型动态决定
# ============================================================

def example_smart_rag():
    """示例：智能选择是否使用RAG"""
    print("\n" + "="*60)
    print("示例3: 智能RAG - 根据问题自动选择")
    print("="*60)
    
    def should_use_rag(message):
        """判断是否需要使用RAG"""
        knowledge_keywords = ["什么是", "如何", "为什么", "原理", "解释", "定义"]
        return any(kw in message for kw in knowledge_keywords)
    
    def select_kb(message):
        """智能选择知识库"""
        message_lower = message.lower()
        if "python" in message_lower:
            return "python_docs"
        elif "java" in message_lower:
            return "java_docs"
        elif "算法" in message or "数据结构" in message:
            return "algorithms"
        return None
    
    # 创建会话
    print("\n1. 创建会话...")
    response = requests.post(f"{BASE_URL}/api/v1/conversations/", json={
        "title": "智能助手"
    })
    session_id = response.json()["session_id"]
    print(f"   会话ID: {session_id}")
    
    # 测试不同类型的问题
    test_questions = [
        "什么是Python的生成器？",  # 需要RAG + Python知识库
        "你好，今天天气怎么样？",  # 不需要RAG
        "Java的多态性原理是什么？",  # 需要RAG + Java知识库
        "快速排序的时间复杂度是多少？",  # 需要RAG + 算法知识库
    ]
    
    for i, question in enumerate(test_questions, 1):
        print(f"\n{i}. 问题: {question}")
        
        # 智能决定是否使用RAG
        use_rag = should_use_rag(question)
        kb_name = select_kb(question) if use_rag else None
        
        print(f"   决策: RAG={use_rag}, 知识库={kb_name}")
        
        # 发送消息
        payload = {
            "message": question,
            "model": "deepseek-chat",
            "enable_rag": use_rag
        }
        
        if use_rag and kb_name:
            payload["kb_name"] = kb_name
            payload["rag_top_k"] = 3
        
        response = requests.post(
            f"{BASE_URL}/api/v1/conversations/{session_id}/messages",
            json=payload
        )
        
        result = response.json()
        print(f"   回复: {result['assistant_message']['content'][:80]}...")
    
    print("\n✅ 示例3完成")


# ============================================================
# 示例4: Agent + 动态RAG
# ============================================================

def example_agent_with_rag():
    """示例：Agent模式配合动态RAG"""
    print("\n" + "="*60)
    print("示例4: Agent + 动态RAG")
    print("="*60)
    
    # 1. 创建会话
    print("\n1. 创建会话...")
    response = requests.post(f"{BASE_URL}/api/v1/conversations/", json={
        "title": "Agent助手"
    })
    session_id = response.json()["session_id"]
    print(f"   会话ID: {session_id}")
    
    # 2. Agent查询 + Python知识库
    print("\n2. Agent查询（使用Python知识库）...")
    response = requests.post(
        f"{BASE_URL}/api/v1/agent/conversation/{session_id}/query",
        json={
            "message": "帮我用Python写一个快速排序，并执行测试",
            "model": "deepseek-chat",
            "max_iterations": 10,
            "enable_tools": ["python_repl"],
            "enable_rag": True,
            "kb_name": "python_docs",
            "rag_top_k": 5
        }
    )
    
    result = response.json()
    print(f"   执行步骤: {result['iterations']} 步")
    print(f"   执行时间: {result['execution_time']:.2f}秒")
    print(f"   RAG: {result['rag_enabled']}, 知识库: {result.get('rag_kb_name')}")
    print(f"   回复: {result['answer'][:100]}...")
    
    # 3. Agent查询（不使用RAG）
    print("\n3. Agent查询（不使用RAG）...")
    response = requests.post(
        f"{BASE_URL}/api/v1/agent/conversation/{session_id}/query",
        json={
            "message": "现在几点了？",
            "model": "deepseek-chat",
            "enable_tools": ["get_current_time"],
            "enable_rag": False  # 不需要RAG
        }
    )
    
    result = response.json()
    print(f"   执行步骤: {result['iterations']} 步")
    print(f"   回复: {result['answer'][:100]}...")
    
    # 4. Agent查询（切换到算法知识库）
    print("\n4. Agent查询（切换到算法知识库）...")
    response = requests.post(
        f"{BASE_URL}/api/v1/agent/conversation/{session_id}/query",
        json={
            "message": "分析一下快速排序的时间复杂度，并用计算器验证",
            "model": "deepseek-chat",
            "enable_tools": ["calculator"],
            "enable_rag": True,
            "kb_name": "algorithms",  # 不同的知识库
            "rag_top_k": 3
        }
    )
    
    result = response.json()
    print(f"   执行步骤: {result['iterations']} 步")
    print(f"   RAG: {result['rag_enabled']}, 知识库: {result.get('rag_kb_name')}")
    print(f"   回复: {result['answer'][:100]}...")
    
    print("\n✅ 示例4完成")


# ============================================================
# 示例5: 模型切换 - 不同问题使用不同模型
# ============================================================

def example_model_switching():
    """示例：根据问题复杂度切换模型"""
    print("\n" + "="*60)
    print("示例5: 智能模型切换")
    print("="*60)
    
    # 创建会话
    print("\n1. 创建会话...")
    response = requests.post(f"{BASE_URL}/api/v1/conversations/", json={
        "title": "智能模型切换"
    })
    session_id = response.json()["session_id"]
    print(f"   会话ID: {session_id}")
    
    # 2. 简单问题 - 使用快速模型
    print("\n2. 简单问题（使用gpt-3.5-turbo）...")
    response = requests.post(
        f"{BASE_URL}/api/v1/conversations/{session_id}/messages",
        json={
            "message": "你好",
            "model": "gpt-3.5-turbo",
            "temperature": 0.7
        }
    )
    print(f"   模型: gpt-3.5-turbo")
    print(f"   回复: {response.json()['assistant_message']['content'][:50]}...")
    
    # 3. 复杂问题 - 使用强大模型
    print("\n3. 复杂问题（使用gpt-4-turbo-preview）...")
    response = requests.post(
        f"{BASE_URL}/api/v1/conversations/{session_id}/messages",
        json={
            "message": "请详细解释量子计算的原理，并分析其在密码学中的应用",
            "model": "gpt-4-turbo-preview",
            "temperature": 0.3,
            "max_tokens": 3000
        }
    )
    print(f"   模型: gpt-4-turbo-preview")
    print(f"   回复: {response.json()['assistant_message']['content'][:100]}...")
    
    # 4. 代码相关 - 使用DeepSeek
    print("\n4. 代码问题（使用deepseek-chat）...")
    response = requests.post(
        f"{BASE_URL}/api/v1/conversations/{session_id}/messages",
        json={
            "message": "写一个Python函数实现二分查找",
            "model": "deepseek-chat",
            "temperature": 0.2,
            "enable_rag": True,
            "kb_name": "python_docs"
        }
    )
    print(f"   模型: deepseek-chat")
    print(f"   回复: {response.json()['assistant_message']['content'][:100]}...")
    
    print("\n✅ 示例5完成")


# ============================================================
# 示例6: 查看会话统计信息
# ============================================================

def example_conversation_stats():
    """示例：查看会话的统计信息"""
    print("\n" + "="*60)
    print("示例6: 会话统计信息")
    print("="*60)
    
    # 创建会话并发送几条消息
    print("\n1. 创建会话并发送消息...")
    response = requests.post(f"{BASE_URL}/api/v1/conversations/", json={
        "title": "多模态测试"
    })
    session_id = response.json()["session_id"]
    
    # 发送几条不同配置的消息
    messages = [
        {"message": "Python是什么？", "enable_rag": True, "kb_name": "python_docs"},
        {"message": "Java是什么？", "enable_rag": True, "kb_name": "java_docs"},
        {"message": "你好", "enable_rag": False}
    ]
    
    for msg in messages:
        requests.post(
            f"{BASE_URL}/api/v1/conversations/{session_id}/messages",
            json={
                "message": msg["message"],
                "model": "deepseek-chat",
                "enable_rag": msg.get("enable_rag", False),
                "kb_name": msg.get("kb_name")
            }
        )
    
    # 2. 获取会话统计信息
    print("\n2. 查看会话统计...")
    response = requests.get(f"{BASE_URL}/api/v1/conversations/{session_id}")
    stats = response.json()
    
    print(f"\n会话信息:")
    print(f"   标题: {stats['title']}")
    print(f"   会话ID: {stats['session_id']}")
    print(f"   创建时间: {stats['created_at']}")
    print(f"\n统计信息:")
    print(f"   总消息数: {stats['statistics']['total_messages']}")
    print(f"   用户消息: {stats['statistics']['user_messages']}")
    print(f"   助手回复: {stats['statistics']['assistant_messages']}")
    print(f"   使用的模型: {stats['statistics']['models_used']}")
    print(f"   RAG使用次数: {stats['statistics']['rag_enabled_count']}")
    print(f"   使用的知识库: {stats['statistics']['knowledge_bases_used']}")
    
    print("\n✅ 示例6完成")


# ============================================================
# 主函数
# ============================================================

def main():
    """运行所有示例"""
    print("\n🚀 重构后的API使用示例")
    print("="*60)
    
    try:
        # 检查服务是否运行
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code != 200:
            print("❌ 服务未运行，请先启动API服务")
            return
        
        print("✅ API服务正常运行")
        
        # 运行示例
        examples = [
            ("基础会话 - 动态配置", example_basic_conversation),
            ("动态RAG - 灵活切换知识库", example_dynamic_rag),
            ("智能RAG - 自动选择", example_smart_rag),
            ("Agent + 动态RAG", example_agent_with_rag),
            ("智能模型切换", example_model_switching),
            ("会话统计信息", example_conversation_stats)
        ]
        
        for i, (name, func) in enumerate(examples, 1):
            print(f"\n{'='*60}")
            print(f"运行示例 {i}/{len(examples)}: {name}")
            print(f"{'='*60}")
            
            try:
                func()
            except Exception as e:
                print(f"❌ 示例执行失败: {str(e)}")
            
            input("\n按Enter继续...")
        
        print("\n" + "="*60)
        print("✅ 所有示例运行完成！")
        print("="*60)
        
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到API服务，请确保服务已启动")
        print(f"   URL: {BASE_URL}")


if __name__ == "__main__":
    main()