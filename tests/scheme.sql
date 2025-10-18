-- ============================================================
-- AI对话平台数据库Schema
-- 数据库: ai_chat_platform
-- ============================================================

-- 1. 对话会话表
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(500) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    model VARCHAR(100) DEFAULT 'deepseek-chat',
    kb_name VARCHAR(100),  -- 关联的知识库
    metadata JSONB,  -- 额外元数据
    is_archived BOOLEAN DEFAULT FALSE,
    message_count INTEGER DEFAULT 0
);

-- 2. 消息表
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'system', 'tool')),
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB,  -- 存储额外信息（如tokens使用、模型等）
    parent_id UUID REFERENCES messages(id),  -- 支持消息树结构
    
    -- Agent相关字段
    tool_calls JSONB,  -- Function Calling信息
    tool_call_id VARCHAR(100),  -- 工具调用ID
    
    -- RAG相关字段
    source_documents JSONB,  -- 来源文档
    
    CONSTRAINT fk_conversation FOREIGN KEY (conversation_id) 
        REFERENCES conversations(id) ON DELETE CASCADE
);

-- 3. 知识库元数据表（补充ChromaDB）
CREATE TABLE IF NOT EXISTS knowledge_bases (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    document_count INTEGER DEFAULT 0,
    collection_name VARCHAR(100) NOT NULL,  -- ChromaDB集合名
    embedding_model VARCHAR(100) DEFAULT 'text-embedding-v1',
    metadata JSONB
);

-- 4. Agent执行记录表
CREATE TABLE IF NOT EXISTS agent_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
    message_id UUID REFERENCES messages(id) ON DELETE CASCADE,
    query TEXT NOT NULL,
    result TEXT,
    steps JSONB,  -- 执行步骤详情
    iterations INTEGER,
    execution_time FLOAT,
    success BOOLEAN,
    error TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    tools_used TEXT[],  -- 使用的工具列表
    metadata JSONB
);

-- 5. 工具调用记录表
CREATE TABLE IF NOT EXISTS tool_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_execution_id UUID REFERENCES agent_executions(id) ON DELETE CASCADE,
    tool_name VARCHAR(100) NOT NULL,
    input JSONB NOT NULL,
    output JSONB,
    success BOOLEAN,
    error TEXT,
    execution_time FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- 索引优化
-- ============================================================

-- 对话索引
CREATE INDEX idx_conversations_created_at ON conversations(created_at DESC);
CREATE INDEX idx_conversations_kb_name ON conversations(kb_name);
CREATE INDEX idx_conversations_archived ON conversations(is_archived);

-- 消息索引
CREATE INDEX idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX idx_messages_created_at ON messages(created_at);
CREATE INDEX idx_messages_role ON messages(role);

-- Agent执行索引
CREATE INDEX idx_agent_executions_conversation_id ON agent_executions(conversation_id);
CREATE INDEX idx_agent_executions_created_at ON agent_executions(created_at);
CREATE INDEX idx_agent_executions_success ON agent_executions(success);

-- 工具执行索引
CREATE INDEX idx_tool_executions_agent_id ON tool_executions(agent_execution_id);
CREATE INDEX idx_tool_executions_tool_name ON tool_executions(tool_name);

-- ============================================================
-- 触发器：自动更新时间戳
-- ============================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_conversations_updated_at
    BEFORE UPDATE ON conversations
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_knowledge_bases_updated_at
    BEFORE UPDATE ON knowledge_bases
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- 触发器：自动更新消息计数
-- ============================================================

CREATE OR REPLACE FUNCTION update_message_count()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE conversations 
        SET message_count = message_count + 1,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = NEW.conversation_id;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE conversations 
        SET message_count = message_count - 1,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = OLD.conversation_id;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_message_count
    AFTER INSERT OR DELETE ON messages
    FOR EACH ROW
    EXECUTE FUNCTION update_message_count();

-- ============================================================
-- 示例数据（可选）
-- ============================================================

-- 插入测试对话
INSERT INTO conversations (title, model, metadata) 
VALUES 
    ('测试对话 - AI助手', 'deepseek-chat', '{"tags": ["test", "demo"]}'),
    ('RAG知识库问答', 'gpt-3.5-turbo', '{"tags": ["rag", "knowledge"]}');

-- 查询统计视图
CREATE OR REPLACE VIEW conversation_stats AS
SELECT 
    c.id,
    c.title,
    c.created_at,
    c.message_count,
    c.kb_name,
    COUNT(ae.id) as agent_executions_count,
    MAX(m.created_at) as last_message_at
FROM conversations c
LEFT JOIN messages m ON c.id = m.conversation_id
LEFT JOIN agent_executions ae ON c.id = ae.conversation_id
GROUP BY c.id, c.title, c.created_at, c.message_count, c.kb_name;