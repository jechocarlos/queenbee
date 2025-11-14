-- Add rate limit tracking for LLM providers
-- Version: 1.0.0
-- Date: November 14, 2025

-- Table to track rate limit resets for different providers
CREATE TABLE IF NOT EXISTS provider_rate_limits (
    id SERIAL PRIMARY KEY,
    provider VARCHAR(50) NOT NULL,
    model VARCHAR(255) NOT NULL,
    rate_limit_reset BIGINT NOT NULL,  -- Unix timestamp in milliseconds
    rate_limit_remaining INTEGER,
    rate_limit_limit INTEGER,
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    -- Ensure only one record per provider+model combination
    CONSTRAINT unique_provider_model UNIQUE (provider, model)
);

CREATE INDEX idx_provider_rate_limits_provider ON provider_rate_limits(provider);
CREATE INDEX idx_provider_rate_limits_reset ON provider_rate_limits(rate_limit_reset);

-- Insert default entry for OpenRouter (if not exists)
INSERT INTO provider_rate_limits (provider, model, rate_limit_reset, updated_at)
VALUES ('openrouter', 'default', 0, NOW())
ON CONFLICT (provider, model) DO NOTHING;
