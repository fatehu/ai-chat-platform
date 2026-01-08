import chromadb

# --- 配置 ---
COLLECTION_NAME = "your_knowledge_base_name"  # 替换成要导出的知识库名称
CHROMA_HOST = 'localhost'  # ChromaDB 服务的主机名 (根据 docker-compose.yml)
CHROMA_PORT = 8002          # ChromaDB 服务映射到宿主机的端口 (根据 docker-compose.yml)
# ------------

try:
    # 连接到正在运行的 ChromaDB 服务
    client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
    print(f"成功连接到 ChromaDB at {CHROMA_HOST}:{CHROMA_PORT}")

    # 获取集合
    collection = client.get_collection(name=COLLECTION_NAME)
    print(f"成功获取知识库 (集合): {COLLECTION_NAME}")

    # 获取集合中的所有数据
    # include 参数指定了需要获取的数据种类
    print("正在获取所有数据块...")
    all_data = collection.get(
        include=["documents", "metadatas", "embeddings"] # 根据需要选择
    )
    print(f"成功获取 {len(all_data.get('ids', []))} 个数据块。")

    # 处理获取到的数据 (示例：打印前几个)
    ids = all_data.get('ids', [])
    documents = all_data.get('documents', [])
    metadatas = all_data.get('metadatas', [])
    embeddings = all_data.get('embeddings', []) # 注意：embeddings 可能非常大

    num_to_show = 5
    print(f"\n显示前 {min(num_to_show, len(ids))} 个数据块示例:")
    for i in range(min(num_to_show, len(ids))):
        print("-" * 20)
        print(f"ID: {ids[i]}")
        print(f"Document: {documents[i][:100]}...") # 显示部分文本
        print(f"Metadata: {metadatas[i]}")
        # print(f"Embedding (前5维): {embeddings[i][:5]}...") # 嵌入向量通常很长，选择性显示

    # 可以在这里将 all_data 保存到文件，例如 JSON
    # import json
    # with open(f"{COLLECTION_NAME}_export.json", "w", encoding="utf-8") as f:
    #    # 注意：直接序列化 embeddings 可能导致 JSON 文件非常大
    #    json.dump({"ids": ids, "documents": documents, "metadatas": metadatas}, f, ensure_ascii=False, indent=2)
    # print(f"\n已将 IDs, Documents, Metadatas 导出到 {COLLECTION_NAME}_export.json")

except Exception as e:
    print(f"操作失败: {e}")