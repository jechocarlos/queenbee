-- Add quantifier to agent_type enum
-- Migration: 006_add_quantifier_agent_type
-- Description: Add quantifier agent type for metrics and data-driven analysis

-- Add 'quantifier' value to the agent_type enum
ALTER TYPE agent_type ADD VALUE IF NOT EXISTS 'quantifier';
