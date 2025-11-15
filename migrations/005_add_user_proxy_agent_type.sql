-- Add user_proxy to agent_type enum
-- Migration: 005_add_user_proxy_agent_type
-- Description: Add user_proxy agent type for end-user perspective representation

-- Add 'user_proxy' value to the agent_type enum
ALTER TYPE agent_type ADD VALUE IF NOT EXISTS 'user_proxy';
