-- Add web_searcher to agent_type enum
-- Migration: 003_add_web_searcher_agent_type
-- Description: Add web_searcher agent type for web search capability

-- Add 'web_searcher' value to the agent_type enum
ALTER TYPE agent_type ADD VALUE IF NOT EXISTS 'web_searcher';
