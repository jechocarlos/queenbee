-- Add pragmatist to agent_type enum
-- Migration: 004_add_pragmatist_agent_type
-- Description: Add pragmatist agent type for implementation feasibility checking

-- Add 'pragmatist' value to the agent_type enum
ALTER TYPE agent_type ADD VALUE IF NOT EXISTS 'pragmatist';
