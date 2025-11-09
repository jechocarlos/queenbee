-- QueenBee Database Schema
-- Version: 1.0.0
-- Date: November 9, 2025

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create ENUM types
CREATE TYPE agent_type AS ENUM ('queen', 'divergent', 'convergent', 'critical');
CREATE TYPE agent_status AS ENUM ('active', 'idle', 'terminated');
CREATE TYPE session_status AS ENUM ('active', 'completed', 'terminated');
CREATE TYPE message_role AS ENUM ('user', 'queen', 'specialist');
CREATE TYPE memory_type AS ENUM ('working', 'reasoning', 'observation');
CREATE TYPE task_status AS ENUM ('pending', 'in_progress', 'completed', 'failed');

-- Sessions table
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    started_at TIMESTAMP NOT NULL DEFAULT NOW(),
    ended_at TIMESTAMP,
    status session_status NOT NULL DEFAULT 'active',
    
    CONSTRAINT check_ended_at CHECK (ended_at IS NULL OR ended_at >= started_at)
);

CREATE INDEX idx_sessions_status ON sessions(status);
CREATE INDEX idx_sessions_started_at ON sessions(started_at DESC);

-- Agents table
CREATE TABLE agents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    type agent_type NOT NULL,
    status agent_status NOT NULL DEFAULT 'active',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    last_activity_at TIMESTAMP NOT NULL DEFAULT NOW(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    system_prompt TEXT NOT NULL,
    configuration JSONB,
    
    CONSTRAINT check_last_activity CHECK (last_activity_at >= created_at)
);

CREATE INDEX idx_agents_session_id ON agents(session_id);
CREATE INDEX idx_agents_status ON agents(status);
CREATE INDEX idx_agents_type ON agents(type);
CREATE INDEX idx_agents_last_activity ON agents(last_activity_at);

-- Chat history table
CREATE TABLE chat_history (
    id SERIAL PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    agent_id UUID REFERENCES agents(id) ON DELETE SET NULL,
    role message_role NOT NULL,
    content TEXT NOT NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    metadata JSONB
);

CREATE INDEX idx_chat_history_session_id ON chat_history(session_id);
CREATE INDEX idx_chat_history_timestamp ON chat_history(timestamp);
CREATE INDEX idx_chat_history_agent_id ON chat_history(agent_id) WHERE agent_id IS NOT NULL;

-- Agent memory table (private to each agent)
CREATE TABLE agent_memory (
    id SERIAL PRIMARY KEY,
    agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    memory_type memory_type NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_agent_memory_agent_id ON agent_memory(agent_id);
CREATE INDEX idx_agent_memory_session_id ON agent_memory(session_id);
CREATE INDEX idx_agent_memory_type ON agent_memory(memory_type);

-- Agent knowledge table (accumulated learnings)
CREATE TABLE agent_knowledge (
    id SERIAL PRIMARY KEY,
    agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    knowledge_type VARCHAR(100) NOT NULL,
    content TEXT NOT NULL,
    confidence_score FLOAT CHECK (confidence_score >= 0 AND confidence_score <= 1),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    last_accessed_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    CONSTRAINT check_accessed_at CHECK (last_accessed_at >= created_at)
);

CREATE INDEX idx_agent_knowledge_agent_id ON agent_knowledge(agent_id);
CREATE INDEX idx_agent_knowledge_type ON agent_knowledge(knowledge_type);
CREATE INDEX idx_agent_knowledge_last_accessed ON agent_knowledge(last_accessed_at);

-- Tasks table
CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    assigned_by UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    assigned_to UUID[] NOT NULL,
    description TEXT NOT NULL,
    status task_status NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP,
    result TEXT,
    
    CONSTRAINT check_completed_at CHECK (completed_at IS NULL OR completed_at >= created_at),
    CONSTRAINT check_assigned_to_not_empty CHECK (array_length(assigned_to, 1) > 0)
);

CREATE INDEX idx_tasks_session_id ON tasks(session_id);
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_assigned_by ON tasks(assigned_by);
CREATE INDEX idx_tasks_created_at ON tasks(created_at DESC);

-- Function to update last_activity_at timestamp
CREATE OR REPLACE FUNCTION update_agent_activity()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE agents
    SET last_activity_at = NOW()
    WHERE id = NEW.agent_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to update agent activity on memory writes
CREATE TRIGGER trigger_update_activity_on_memory
AFTER INSERT ON agent_memory
FOR EACH ROW
EXECUTE FUNCTION update_agent_activity();

-- Trigger to update agent activity on knowledge writes
CREATE TRIGGER trigger_update_activity_on_knowledge
AFTER INSERT OR UPDATE ON agent_knowledge
FOR EACH ROW
EXECUTE FUNCTION update_agent_activity();

-- Function to clean up terminated sessions
CREATE OR REPLACE FUNCTION cleanup_old_sessions(days_old INTEGER DEFAULT 30)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM sessions
    WHERE status = 'terminated'
      AND ended_at < NOW() - (days_old || ' days')::INTERVAL;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Grant permissions (adjust as needed)
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO queenbee;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO queenbee;

-- Insert initial data (optional)
-- This will be handled by the application during session creation

COMMENT ON TABLE sessions IS 'User sessions with the QueenBee system';
COMMENT ON TABLE agents IS 'Agent instances (Queen and specialists)';
COMMENT ON TABLE chat_history IS 'Shared conversation history visible to user';
COMMENT ON TABLE agent_memory IS 'Private agent memory per session';
COMMENT ON TABLE agent_knowledge IS 'Accumulated agent knowledge within session';
COMMENT ON TABLE tasks IS 'Tasks assigned to specialists';
