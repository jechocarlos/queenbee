# Inference Packs Configuration

## Overview

Inference packs allow you to configure different AI models for different use cases and assign them to specific agents. This gives you fine-grained control over which models handle which types of tasks.

## Architecture

```
Inference Packs (Model Configs)          Agent Assignments
─────────────────────────────         ─────────────────────
┌─────────────────────────┐            ┌──────────────────┐
│ reasoning               │            │ Queen            │
│  - gpt-oss-20b         │◄───────────┤  → standard      │
│  - extract_reasoning=T  │            └──────────────────┘
└─────────────────────────┘            ┌──────────────────┐
                                       │ Divergent        │
┌─────────────────────────┐            │  → web_search    │
│ web_search              │◄───────────┤                  │
│  - gpt-4o-mini-search   │            └──────────────────┘
│  - extract_reasoning=F  │            ┌──────────────────┐
└─────────────────────────┘            │ Convergent       │
                                       │  → reasoning     │
┌─────────────────────────┐◄───────────┤                  │
│ standard                │            └──────────────────┘
│  - gpt-oss-20b         │            ┌──────────────────┐
│  - extract_reasoning=F  │            │ Critical         │
└─────────────────────────┘◄───────────┤  → standard      │
                                       └──────────────────┘
                                       ┌──────────────────┐
                                       │ Summarizer       │
                                       │  → standard      │
                                       └──────────────────┘
```

## Configuration

### Step 1: Define Inference Packs

In `config.yaml`, define your model configurations:

```yaml
inference_packs:
  packs:
    reasoning:
      model: openai/gpt-oss-20b
      provider: openrouter
      extract_reasoning: true     # Extract from reasoning field
      temperature: 0.7
      max_tokens: 500
    
    standard:
      model: openai/gpt-oss-20b
      provider: openrouter
      extract_reasoning: false    # Use standard content field
      temperature: 0.7
      max_tokens: 500
    
    web_search:
      model: openai/gpt-4o-mini-search-preview
      provider: openrouter
      extract_reasoning: false
      temperature: 0.7
      max_tokens: 800
    
    fast:
      model: meta-llama/llama-3.1-8b-instruct:free
      provider: openrouter
      extract_reasoning: false
      temperature: 0.8
      max_tokens: 300
    
    local:
      model: llama3.1:8b
      provider: ollama
      extract_reasoning: false
      temperature: 0.7
      max_tokens: 500
```

### Step 2: Assign Packs to Agents

Map each agent to an inference pack:

```yaml
agent_inference:
  queen: standard           # Queen uses standard model
  divergent: web_search     # Divergent uses web search model
  convergent: reasoning     # Convergent uses reasoning model
  critical: standard        # Critical uses standard model
  summarizer: standard      # Summarizer uses standard model
```

## Inference Pack Parameters

### Required Fields

- **`model`**: Model identifier (e.g., `"openai/gpt-4o-mini"`, `"llama3.1:8b"`)
- **`provider`**: Either `"openrouter"` or `"ollama"`

### Optional Fields

- **`extract_reasoning`** (default: `true`): 
  - `true`: Extract content from reasoning field (for reasoning models like gpt-oss-20b)
  - `false`: Use standard content field
  
- **`temperature`** (default: `0.7`): 
  - Sampling temperature (0.0 = deterministic, 1.0 = creative)
  - Range: 0.0 to 1.0
  
- **`max_tokens`** (default: `0`): 
  - Maximum tokens to generate
  - `0` = no limit

## Use Cases

### 1. Reasoning-Focused Setup
Use reasoning models for deep analysis:

```yaml
inference_packs:
  packs:
    reasoning:
      model: openai/gpt-oss-20b
      provider: openrouter
      extract_reasoning: true
      temperature: 0.7
      max_tokens: 800

agent_inference:
  queen: reasoning
  divergent: reasoning
  convergent: reasoning
  critical: reasoning
  summarizer: reasoning
```

### 2. Specialized Agent Setup
Different models for different thinking styles:

```yaml
agent_inference:
  queen: standard              # Orchestration
  divergent: web_search        # Exploration with web search
  convergent: reasoning        # Deep synthesis
  critical: standard           # Validation
  summarizer: fast             # Quick summarization
```

### 3. Cost-Optimized Setup
Use fast/free models where appropriate:

```yaml
inference_packs:
  packs:
    premium:
      model: anthropic/claude-3.5-sonnet
      provider: openrouter
      extract_reasoning: false
      temperature: 0.7
      max_tokens: 1000
    
    economy:
      model: meta-llama/llama-3.1-8b-instruct:free
      provider: openrouter
      extract_reasoning: false
      temperature: 0.7
      max_tokens: 500

agent_inference:
  queen: economy              # Simple orchestration
  divergent: premium          # Creative exploration (premium)
  convergent: premium         # Complex synthesis (premium)
  critical: economy           # Validation (economy)
  summarizer: economy         # Summarization (economy)
```

### 4. Local-First Setup
Prefer local models with cloud fallback:

```yaml
inference_packs:
  packs:
    local:
      model: llama3.1:8b
      provider: ollama
      extract_reasoning: false
      temperature: 0.7
      max_tokens: 500
    
    cloud:
      model: openai/gpt-4o-mini
      provider: openrouter
      extract_reasoning: false
      temperature: 0.7
      max_tokens: 800

agent_inference:
  queen: local
  divergent: cloud      # Use cloud for exploration
  convergent: local
  critical: local
  summarizer: local
```

## Model Compatibility

### OpenRouter Models

**Reasoning Models** (set `extract_reasoning: true`):
- `openai/gpt-oss-20b` - Outputs reasoning process

**Standard Models** (set `extract_reasoning: false`):
- `anthropic/claude-3.5-sonnet`
- `openai/gpt-4o`
- `openai/gpt-4o-mini`
- `google/gemini-flash-1.5`
- `meta-llama/llama-3.1-8b-instruct:free`

**Search-Enhanced Models**:
- `openai/gpt-4o-mini-search-preview` - Web search capabilities

### Ollama Models

All Ollama models use `extract_reasoning: false`:
- `llama3.1:8b`
- `llama3.1:70b`
- `mistral:7b`
- `phi3:medium`
- `qwen2.5:latest`

## Best Practices

### 1. Match Models to Tasks

- **Exploration (Divergent)**: Use web search or creative models
  ```yaml
  divergent: web_search
  ```

- **Synthesis (Convergent)**: Use reasoning models
  ```yaml
  convergent: reasoning
  ```

- **Validation (Critical)**: Use standard models
  ```yaml
  critical: standard
  ```

- **Summarization (Summarizer)**: Use fast or standard models
  ```yaml
  summarizer: fast
  ```

### 2. Temperature Guidelines

- **Creative tasks** (divergent): 0.7-0.9
- **Analytical tasks** (convergent, critical): 0.5-0.7
- **Factual tasks** (summarizer): 0.3-0.5

### 3. Token Limits

- **Exploration**: 500-800 tokens (detailed exploration)
- **Synthesis**: 500-1000 tokens (comprehensive analysis)
- **Validation**: 300-500 tokens (focused critique)
- **Summarization**: 200-500 tokens (concise summary)

### 4. Cost Management

Order by cost (approximate):
1. **Ollama** (local) - Free
2. **Free models** (`:free` suffix) - Free with limits
3. **gpt-4o-mini** - Low cost
4. **gpt-4o** - Medium cost
5. **claude-3.5-sonnet** - Premium cost

### 5. Testing Strategy

Test new configurations incrementally:

```bash
# Test with simple query
queenbee-openrouter

You: What is 2+2?
# Verify all agents respond correctly

# Test with complex query
You: Explain the trade-offs of microservices vs monoliths
# Verify different models provide different perspectives
```

## Troubleshooting

### Agent Not Using Expected Model

Check logs for:
```
Agent divergent using inference pack 'web_search' with model openai/gpt-4o-mini-search-preview
```

If you see:
```
Inference pack 'web_search' not found for divergent, using defaults
```

→ Verify pack name matches in `inference_packs.packs` and `agent_inference`

### Empty Responses

For reasoning models, ensure `extract_reasoning: true`:
```yaml
reasoning:
  model: openai/gpt-oss-20b
  extract_reasoning: true  # ← Required for reasoning models
```

### Model Not Found

Check OpenRouter model availability:
- Visit https://openrouter.ai/models
- Verify model name exactly matches
- Check if model requires credits

### Rate Limits

Each model/provider has its own rate limits:
- Adjust `openrouter.requests_per_minute` in config
- Use mix of free and paid models to spread load

## Advanced Configuration

### Dynamic Pack Selection

You can create multiple named configurations:

```yaml
inference_packs:
  packs:
    # Development packs
    dev_fast:
      model: meta-llama/llama-3.1-8b-instruct:free
      provider: openrouter
      
    # Production packs
    prod_quality:
      model: anthropic/claude-3.5-sonnet
      provider: openrouter
      
    # Testing packs
    test_local:
      model: llama3.1:8b
      provider: ollama
```

Switch between environments by changing `agent_inference` mappings.

### Per-Agent Temperature Tuning

Fine-tune each agent's creativity:

```yaml
inference_packs:
  packs:
    creative:
      model: openai/gpt-4o
      temperature: 0.9        # High creativity
      
    analytical:
      model: openai/gpt-4o
      temperature: 0.5        # Low creativity
      
    factual:
      model: openai/gpt-4o
      temperature: 0.3        # Very deterministic

agent_inference:
  divergent: creative         # Creative exploration
  convergent: analytical      # Balanced analysis
  critical: factual           # Fact-based validation
```

## Migration Guide

### From Environment Variable Mode

**Before** (using `QUEENBEE_USE_OPENROUTER=1`):
```bash
queenbee-openrouter
# All agents use config.openrouter.model
```

**After** (using inference packs):
```yaml
# Define packs
inference_packs:
  packs:
    standard:
      model: openai/gpt-oss-20b
      provider: openrouter

# Assign all agents to standard
agent_inference:
  queen: standard
  divergent: standard
  convergent: standard
  critical: standard
  summarizer: standard
```

Result: **Same behavior, but now customizable per agent**

### From Single Model to Multiple Models

1. Define your target models as packs
2. Assign queen and summarizer to safe defaults first
3. Test with single agent override
4. Gradually migrate remaining agents

```yaml
# Step 1: Conservative start
agent_inference:
  queen: standard
  divergent: standard  # Test this first
  convergent: standard
  critical: standard
  summarizer: standard

# Step 2: Add variety after testing
agent_inference:
  queen: standard
  divergent: web_search     # ← Now using search
  convergent: reasoning     # ← Now using reasoning
  critical: standard
  summarizer: fast          # ← Now using fast model
```

## Examples

See `config.yaml` for a complete working example with all inference packs configured.

---

**Next Steps:**
- Review [OpenRouter Models](https://openrouter.ai/models) for available options
- See [Configuration Guide](getting-started.md) for general setup
- Check [Architecture Docs](architecture_update.md) for system design
