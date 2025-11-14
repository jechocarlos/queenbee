# OpenRouter Integration

## Overview

QueenBee now supports OpenRouter as an alternative LLM provider, giving you access to premium models like Claude, GPT-4, and others while maintaining the same agent orchestration architecture.

## Architecture

### Provider Selection

QueenBee uses environment variable detection to choose between Ollama (local) and OpenRouter (cloud):

- **`queenbee`** command: Uses Ollama (local LLM)
- **`queenbee-openrouter`** command: Sets `QUEENBEE_USE_OPENROUTER=1` and uses OpenRouter API

Both commands share the same codebase, configuration, and database - only the LLM provider changes.

### Implementation Details

#### Configuration

**`src/queenbee/config/loader.py`**:
- Added `OpenRouterConfig` class with fields: `api_key`, `model`, `timeout`, `base_url`
- Extends main `Config` class with `openrouter: OpenRouterConfig` field
- Supports environment variable substitution: `${OPENROUTER_API_KEY:}`

**`config.yaml`**:
```yaml
openrouter:
  api_key: ${OPENROUTER_API_KEY:}
  model: anthropic/claude-3.5-sonnet
  timeout: 300
  base_url: https://openrouter.ai/api/v1
```

#### LLM Client

**`src/queenbee/llm/openrouter.py`**:
- `OpenRouterClient` class wraps Agno's `OpenAIChat` model
- Uses OpenRouter endpoint: `https://openrouter.ai/api/v1`
- Supports both streaming and non-streaming responses
- Methods:
  - `generate(prompt, stream=False)`: Text completion
  - `chat(messages, stream=False)`: Chat completion
  - `is_available()`: Health check
  - `list_models()`: Available models (if supported)

#### Agent Integration

**`src/queenbee/agents/base.py`**:
```python
# Detect provider from environment
if os.environ.get('QUEENBEE_USE_OPENROUTER'):
    from queenbee.llm.openrouter import OpenRouterClient
    self.llm = OpenRouterClient(config.openrouter)
else:
    self.llm = OllamaClient(config.ollama)

# Maintain backward compatibility
self.ollama = self.llm
```

All agents (Queen, Divergent, Convergent, Critical, Summarizer) automatically use the selected provider without code changes.

#### CLI Entry Point

**`src/queenbee/cli/openrouter_main.py`**:
```python
import os
os.environ['QUEENBEE_USE_OPENROUTER'] = '1'

from queenbee.cli.main import main

def main_openrouter() -> int:
    return main()
```

Simple wrapper that sets environment variable and delegates to main CLI.

**`pyproject.toml`**:
```toml
[project.scripts]
queenbee = "queenbee.cli.main:main"
queenbee-openrouter = "queenbee.cli.openrouter_main:main_openrouter"
```

## Usage

### Setup

1. **Get OpenRouter API key**: Sign up at [OpenRouter](https://openrouter.ai/)

2. **Configure environment**:
```bash
echo "OPENROUTER_API_KEY=your_key_here" >> .env
```

3. **Install/Update package**:
```bash
pip install -e .
```

### Running

**Start with OpenRouter**:
```bash
queenbee-openrouter
```

**Switch back to Ollama**:
```bash
queenbee
```

### Model Selection

Edit `config.yaml` to change the OpenRouter model:

```yaml
openrouter:
  model: anthropic/claude-3.5-sonnet  # Default
  # model: openai/gpt-4-turbo
  # model: anthropic/claude-3-opus
  # model: meta-llama/llama-3.1-70b-instruct
```

See [OpenRouter models](https://openrouter.ai/models) for available options.

## Testing

All existing tests pass with OpenRouter integration:
- **223 tests passed**
- **2 tests skipped**
- **66% code coverage**

Test fixtures automatically include OpenRouter configuration:

```python
openrouter:
  api_key: test_api_key
  model: anthropic/claude-3.5-sonnet
  timeout: 300
  base_url: https://openrouter.ai/api/v1
```

## Benefits

### OpenRouter Advantages
- Access to premium models (Claude, GPT-4, etc.)
- No local GPU required
- Automatic model updates
- Pay-per-use pricing
- Multiple model options

### Ollama Advantages
- Complete privacy (local execution)
- No API costs
- Offline capability
- Full control over models
- No rate limits

## Design Principles

1. **Minimal Code Changes**: Provider selection via environment variable
2. **Backward Compatibility**: All existing code works unchanged
3. **Unified Interface**: Both providers implement same methods
4. **Easy Switching**: Change provider with different command
5. **Configuration Driven**: Model selection in `config.yaml`

## Future Enhancements

Potential improvements:
- Runtime provider switching (without restart)
- Multi-provider support (use different providers for different agents)
- Provider fallback (try OpenRouter if Ollama fails)
- Cost tracking for OpenRouter usage
- Model selection per agent type
