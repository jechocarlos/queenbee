# QueenBee 🐝

**Intelligent Multi-Agent Orchestration System**

![Tests](https://img.shields.io/badge/tests-223%20passed-brightgreen)
![Coverage](https://img.shields.io/badge/coverage-70%25-yellow)
![Python](https://img.shields.io/badge/python-3.14-blue)
![License](https://img.shields.io/badge/license-MIT-blue)

QueenBee is a sophisticated agent orchestration platform that coordinates specialized AI agents to solve complex problems through collaborative thinking. Every query is analyzed by a team of experts using divergent exploration, convergent synthesis, and critical validation.

## 📑 Table of Contents

- [What Makes QueenBee Different?](#-what-makes-queenbee-different)
- [Key Features](#-key-features)
- [Quick Start](#-quick-start)
- [Usage Examples](#-usage-examples)
- [Configuration](#️-configuration)
  - [Inference Packs](#inference-packs-advanced-model-configuration)
  - [LLM Provider Setup](#llm-provider-setup)
- [Architecture](#️-architecture)
- [Development](#-development)
- [Deployment](#-deployment)
- [Documentation](#-documentation)
- [Contributing](#-contributing)
- [Roadmap](#️-roadmap)

---

## 🎯 What Makes QueenBee Different?

**Every Request Gets Full Team Analysis** - No matter how simple or complex your question, QueenBee delegates to a team of specialized agents who collaborate in real-time:

- **🌟 Divergent Thinker**: Explores multiple perspectives and creative approaches
- **🔗 Convergent Thinker**: Synthesizes insights and prioritizes solutions  
- **🔍 Critical Thinker**: Validates reasoning and identifies risks
- **📋 Summarizer**: Generates rolling updates and final synthesis

**Live Progress Updates** - Watch agents think and contribute in real-time with rolling summaries that show emerging insights as the discussion unfolds.

**Flexible AI Providers** - Choose between local (Ollama) or cloud (OpenRouter) LLMs:
- **Ollama**: Private, free, runs locally
- **OpenRouter**: Access Claude, GPT-4, and premium models

---

## ✨ Key Features

### Core Capabilities
- 🎯 **Intelligent Query Classification**: Automatically routes simple vs complex questions
- 🧠 **Multi-Agent Collaboration**: Specialized agents contribute based on expertise relevance
- 🧩 **Smart Contribution System**: Agents only speak when they add genuine value (see [docs/agent-contribution-intelligence.md](docs/agent-contribution-intelligence.md))
- 📊 **Real-Time Insights**: Live rolling summaries show progress during discussion
- ⚡ **Streaming Responses**: Token-by-token updates for immediate feedback
- 🔄 **Async Processing**: Specialists run in parallel background workers
- 💾 **Persistent State**: PostgreSQL-backed memory, tasks, and knowledge

### Agent Expertise System
- 🤖 **10 Specialized Agents**: Each with distinct expertise and contribution triggers
  - **Queen**: Orchestrates and synthesizes final responses
  - **Classifier**: Routes queries as SIMPLE or COMPLEX
  - **Divergent**: Explores options and challenges assumptions
  - **Convergent**: Synthesizes insights into actionable recommendations
  - **Critical**: Validates reasoning and identifies risks
  - **Pragmatist**: Reality-checks feasibility and resources
  - **UserProxy**: Advocates for user needs and experience
  - **Quantifier**: Demands data and concrete metrics
  - **Summarizer**: Generates rolling updates and synthesis
  - **WebSearcher**: Fetches current information when needed

### LLM Provider Support
- 🏠 **Ollama** (Local): Privacy-focused, free, full control
- ☁️ **OpenRouter** (Cloud): Premium models (Claude, GPT-4, etc.)
- 🔄 **Seamless Switching**: Change providers without losing history
- 🛡️ **Smart Rate Limiting**: Built-in protection against API limits

### Developer Experience
- 💬 **Interactive CLI**: Rich terminal UI with live updates
- 🔍 **Full History**: Review entire conversations with `history` command
- 🧪 **Well-Tested**: 223 passing tests, 70% coverage
- 📚 **Comprehensive Docs**: Architecture, API, and deployment guides

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.14+** (or 3.10+)
- **Docker & Docker Compose** (v2.0+)
- **PostgreSQL 14+** (via Docker or external)
- **LLM Provider** (choose one):
  - **Ollama** for local/private deployment
  - **OpenRouter API key** for cloud models (Claude, GPT-4, etc.)

### Installation

1. **Clone and Setup**
```bash
git clone https://github.com/jechocarlos/queenbee.git
cd queenbee
cp .env.example .env
```

2. **Choose Your LLM Provider**

**Option A: Local with Ollama (Private & Free)**
```bash
# Start infrastructure
docker-compose -f docker-compose.local.yml up -d

# Pull your preferred model
docker exec -it queenbee-ollama ollama pull llama3.1:8b
```

**Option B: Cloud with OpenRouter (Premium Models)**
```bash
# Add API key to .env
echo "OPENROUTER_API_KEY=sk-or-v1-..." >> .env

# Start database only
docker-compose -f docker-compose.remote.yml up -d
```

3. **Install & Initialize**
```bash
# Install QueenBee
pip install -e .

# Run database migrations
python scripts/migrate.py

# Verify installation
queenbee --version
```

4. **Launch**
```bash
# With Ollama (local)
queenbee

# With OpenRouter (cloud)
queenbee-openrouter
```

### CLI Commands

Once running, use these commands:

```bash
# Start a new conversation
You: <your question>

# View conversation history
history

# Clear current session
clear

# Exit application
exit / quit
```

---

## 💡 Usage Examples

### Simple Query
```
You: What's the capital of France?

Queen is thinking...
🐝 Starting Live Collaborative Discussion...

[🔗 Convergent: thinking, 🌟 Divergent: thinking, 🔍 Critical: thinking]

🔗 Convergent #1
Paris is the capital of France, serving as the political, economic, and 
cultural center since 987 CE...

🌟 Divergent #1  
Let me explore different angles: Paris is not just politically significant
but also a global fashion, art, and culinary capital...

🔍 Critical #1
Confirmed: Paris has been France's capital for over 1,000 years. No 
significant risks or alternative interpretations...

────────────────────────────────────────────────────────────────────────────────
📝 FINAL SUMMARY
Paris is the capital of France, both politically and culturally. It has served 
this role since the late 10th century and is a major global center for art, 
fashion, and commerce.
────────────────────────────────────────────────────────────────────────────────

✓ Discussion complete!
```

### Complex Analysis
```
You: Should I use microservices or a monolith for my startup?

Queen is thinking...
🐝 Starting Live Collaborative Discussion...

💭 Rolling Summary (updating every 10s)
The team is analyzing architectural trade-offs. Divergent explores multiple 
patterns, Convergent synthesizes recommendations for MVP speed, Critical 
identifies operational complexity risks...

[Multiple rounds of discussion...]

────────────────────────────────────────────────────────────────────────────────
📝 FINAL SUMMARY
For a startup, begin with a well-structured modular monolith to validate 
product-market fit quickly while maintaining clean boundaries. This approach 
provides:

1. Faster initial development (single codebase, shared resources)
2. Easier debugging and deployment (one application to manage)
3. Lower operational complexity (no distributed systems overhead)
4. Clear extraction path (modules become microservices when needed)

Extract microservices only when you face specific scaling bottlenecks (e.g., 
one module needs different compute resources) or team bottlenecks (separate 
teams need independent deployment). Key trade-off: operational complexity vs 
development velocity. Start simple, extract as needed.
────────────────────────────────────────────────────────────────────────────────

✓ Discussion complete!
```

---

## ⚙️ Configuration

### Inference Packs (Advanced Model Configuration)

QueenBee supports **inference packs** - named model configurations that you can assign to specific agents:

```yaml
# config.yaml - Define inference packs for different use cases
inference_packs:
  openrouter:
    default_pack: standard
    packs:
      reasoning:
        model: openai/gpt-oss-20b
        extract_reasoning: true
        temperature: 0.3
        max_tokens: 3000
      
      standard:
        model: qwen/qwen3-vl-8b-instruct
        extract_reasoning: false
        temperature: 0.0
        max_tokens: 2000
      
      web_search:
        model: openai/gpt-4o-mini-search-preview
        extract_reasoning: false
        temperature: 0.1
        max_tokens: 5000
      
      fast:
        model: google/gemini-2.5-flash-lite
        extract_reasoning: false
        temperature: 0.1
        max_tokens: 500
  
  ollama:
    default_pack: standard
    packs:
      standard:
        model: llama3.1:8b
        extract_reasoning: false
        temperature: 0.7
        max_tokens: 2000
      
      reasoning:
        model: llama3.1:8b
        extract_reasoning: false
        temperature: 0.5
        max_tokens: 2000
      
      fast:
        model: qwen2.5:3b
        extract_reasoning: false
        temperature: 0.3
        max_tokens: 2000

# Agent inference pack assignments
agent_inference:
  queen: standard
  classifier: fast
  divergent: reasoning
  convergent: reasoning
  critical: standard
  pragmatist: reasoning
  user_proxy: standard
  quantifier: reasoning
  summarizer: standard
  web_searcher: web_search
```

**Benefits:**
- 🎯 Different models for different thinking styles
- 🔍 Web search for exploration, reasoning for analysis
- 💰 Mix free and premium models to optimize cost
- 🏠 Combine local (Ollama) and cloud (OpenRouter) models

**Important**: The `max_tokens` in inference pack definitions are model defaults. The actual token limits used by agents are configured in the `agents` section of your `config.yaml` and are injected into their system prompts for more reliable length control.

See [Inference Packs Guide](docs/inference-packs.md) for detailed configuration options.

### LLM Provider Setup

**Ollama (Local)**
```yaml
# config.yaml
ollama:
  host: http://localhost:11434
  model: llama3.1:8b
  timeout: 300
```

**OpenRouter (Cloud)**
```yaml
# config.yaml
openrouter:
  api_key: ${OPENROUTER_API_KEY}
  model: anthropic/claude-3.5-sonnet
  base_url: https://openrouter.ai/api/v1
  timeout: 300
  verify_ssl: true
  
  # Rate limiting (adjust to your tier)
  requests_per_minute: 16  # Free tier default
  max_retries: 3
  retry_delay: 5
```

### Database Configuration
```bash
# .env file
DB_HOST=localhost
DB_PORT=5432
DB_NAME=queenbee
DB_USER=queenbee
DB_PASSWORD=your_secure_password

# For remote PostgreSQL
# DB_HOST=your-db-host.com
# DB_SSL_MODE=require
```

### Agent Behavior Tuning
```yaml
# config.yaml
agents:
  ttl:
    idle_timeout_minutes: 10
    check_interval_seconds: 30
  
  max_concurrent_specialists: 10
  
  # Queen agent - handles both simple and complex queries
  queen:
    system_prompt_file: ./prompts/queen.md
    complexity_threshold: auto
    simple_max_tokens: 100      # Short, direct answers
    complex_max_tokens: 8000    # Full analysis with specialist input
  
  # Query classifier - determines simple vs complex
  classifier:
    system_prompt_file: ./prompts/classifier.md
    max_tokens: 10              # Just SIMPLE or COMPLEX
  
  # Discussion specialists - each contributes based on expertise
  divergent:
    system_prompt_file: ./prompts/divergent.md
    max_iterations: 25
    max_tokens: 2000            # Explores options and alternatives
  
  convergent:
    system_prompt_file: ./prompts/convergent.md
    max_iterations: 25
    max_tokens: 2000            # Synthesizes insights
  
  critical:
    system_prompt_file: ./prompts/critical.md
    max_iterations: 25
    max_tokens: 2000            # Validates and identifies risks
  
  pragmatist:
    system_prompt_file: ./prompts/pragmatist.md
    max_iterations: 25
    max_tokens: 2000            # Reality-checks feasibility
  
  user_proxy:
    system_prompt_file: ./prompts/user_proxy.md
    max_iterations: 25
    max_tokens: 2000            # Advocates for user perspective
  
  quantifier:
    system_prompt_file: ./prompts/quantifier.md
    max_iterations: 25
    max_tokens: 2000            # Demands metrics and data
  
  summarizer:
    system_prompt_file: ./prompts/summarizer.md
    max_iterations: 25
    max_tokens: 0               # No limit for comprehensive summaries
  
  web_searcher:
    system_prompt_file: ./prompts/web_searcher.md
    max_iterations: 25
    max_tokens: 0               # No limit for search results

consensus:
  discussion_rounds: 20
  specialist_timeout_seconds: 300
  summary_interval_seconds: 10  # Rolling summary update frequency
```

**Note on Token Limits**: Token limits are injected directly into agent system prompts to ensure more reliable response length control compared to API-only constraints. Each agent sees their token budget explicitly stated in their system prompt.

---

## 🏗️ Architecture

### Discussion Flow

```
                        User Query
                            ↓
                    ┌───────────────┐
                    │ Queen Agent   │ (Delegates to specialists)
                    └───────────────┘
                            ↓
                    [Task Queue] → Background Workers
                            ↓
    ╔═══════════════════════════════════════════════════════════╗
    ║         PARALLEL MULTI-ROUND DISCUSSION                   ║
    ║  (20 rounds max, async workers, streaming responses)      ║
    ╚═══════════════════════════════════════════════════════════╝
                            ↓
    ┌──────────────┬──────────────┬──────────────┬──────────────┐
    │              │              │              │              │
    │  🌟 Divergent │ 🔗 Convergent │ 🔍 Critical  │ 📋 Summarizer│
    │  (Explore)   │ (Synthesize) │  (Validate)  │  (Updates)   │
    │              │              │              │              │
    │ Round 1 ─────┼──────────────┼──────────────┼──────────────┤
    │ Response 1   │ Response 1   │ Response 1   │ Summary 1    │
    │              │              │              │ (every 10s)  │
    │ Round 2 ─────┼──────────────┼──────────────┼──────────────┤
    │ Response 2   │ Response 2   │ Response 2   │ Summary 2    │
    │ (reads all   │ (reads all   │ (reads all   │ (synthesizes │
    │  previous)   │  previous)   │  previous)   │  progress)   │
    │              │              │              │              │
    │ Round N ─────┼──────────────┼──────────────┼──────────────┤
    │ Response N   │ Response N   │ Response N   │ Summary N    │
    │              │              │              │              │
    └──────────────┴──────────────┴──────────────┴──────────────┘
                            ↓
              All agents reach consensus/timeout
                            ↓
                ┌────────────────────────┐
                │  📝 FINAL SUMMARY      │
                │  (Comprehensive        │
                │   synthesis by         │
                │   Summarizer)          │
                └────────────────────────┘
                            ↓
                    Displayed to User
                            ↓
              Persisted to PostgreSQL
```

**Key Characteristics:**
- ⚡ **Parallel Processing**: All specialists run simultaneously in background workers
- 🔄 **Multi-Round Discussion**: Up to 20 rounds, each agent builds on previous responses
- 📊 **Live Rolling Updates**: Summarizer provides progress updates every 10 seconds
- 🎯 **Context-Aware**: Each round, agents read entire discussion history
- 💾 **Persistent**: All contributions saved to PostgreSQL in real-time
- 🛑 **Smart Termination**: Discussion ends when consensus reached or timeout

### Key Components

**Agent Layer** (`src/queenbee/agents/`)
- `base.py`: Shared agent infrastructure with LLM auto-detection
- `queen.py`: Orchestration and delegation
- `divergent.py`: Creative exploration
- `convergent.py`: Solution synthesis
- `critical.py`: Validation and risk assessment
- `summarizer.py`: Rolling and final summaries

**Worker System** (`src/queenbee/workers/`)
- Async multi-process architecture
- Live discussion updates
- Task queue management
- Rolling summary generation

**Database Layer** (`src/queenbee/db/`)
- PostgreSQL persistence
- Session management
- Agent state tracking
- Chat history
- Rate limit persistence (OpenRouter)

**CLI** (`src/queenbee/cli/`)
- Rich terminal UI
- Live discussion viewer
- Command processing
- Provider-specific entry points

---

## 🧪 Development

### Running Tests
```bash
# Full test suite
pytest

# With coverage report
pytest --cov=src --cov-report=html

# Specific test file
pytest tests/test_agents.py -v

# Watch mode
pytest-watch
```

**Current Status**: ✅ 223 passed, ⚠️ 2 skipped, 📊 70% coverage

### Code Quality
```bash
# Format code
black src/ tests/

# Lint
ruff check src/ tests/ --fix

# Type checking
mypy src/
```

### Database Migrations
```bash
# Run all migrations
python scripts/migrate.py

# Check migration status
psql -h localhost -U queenbee -d queenbee -c "\dt"
```

### Project Structure
```
queenbee/
├── src/queenbee/
│   ├── agents/          # Agent implementations
│   ├── cli/             # Command-line interface  
│   ├── config/          # Configuration management
│   ├── db/              # Database layer & models
│   ├── llm/             # LLM client implementations
│   ├── session/         # Session management
│   └── workers/         # Multi-process orchestration
├── prompts/             # Agent system prompts
├── migrations/          # SQL database migrations
├── tests/               # Comprehensive test suite
├── docs/                # Detailed documentation
├── .github/
│   ├── SPECS.md         # System specification
│   └── TODO.md          # Development roadmap
├── config.yaml          # System configuration
├── .env.example         # Environment template
├── pyproject.toml       # Python package config
└── docker-compose.*.yml # Deployment configs
```

---

## 🚢 Deployment

### Local Development (All Services)
```bash
docker-compose -f docker-compose.local.yml up -d
```
Includes: PostgreSQL + Ollama + QueenBee (optional)

### Production (Remote Database)
```bash
docker-compose -f docker-compose.remote.yml up -d
```
Includes: Ollama only (connect to external PostgreSQL)

### Environment Variables
```bash
# .env file
LOG_LEVEL=INFO                    # DEBUG, INFO, WARNING, ERROR
OLLAMA_HOST=http://localhost:11434
OPENROUTER_API_KEY=sk-or-v1-...  # Optional
DB_HOST=localhost
DB_PORT=5432
DB_NAME=queenbee
DB_USER=queenbee
DB_PASSWORD=changeme
DB_SSL_MODE=prefer               # require for remote DB
```

---

## 📚 Documentation

- **[Architecture](docs/architecture_update.md)**: System design and components
- **[Inference Packs](docs/inference-packs.md)**: Advanced model configuration guide
- **[OpenRouter Integration](docs/openrouter.md)**: Cloud LLM setup and rate limiting
- **[Specialist Agents](docs/specialist-agents.md)**: Agent roles and behaviors
- **[Testing](docs/testing.md)**: Test suite and coverage
- **[Getting Started](docs/getting-started.md)**: Detailed setup guide
- **[Specification](.github/SPECS.md)**: Complete system requirements

---

## 🤝 Contributing

We welcome contributions! Here's how to get started:

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **Make** your changes with tests
4. **Run** the test suite (`pytest`)
5. **Commit** your changes (`git commit -m 'Add amazing feature'`)
6. **Push** to your branch (`git push origin feature/amazing-feature`)
7. **Open** a Pull Request

### Contribution Guidelines
- Write tests for new features
- Maintain or improve code coverage
- Follow existing code style (black, ruff)
- Update documentation as needed
- Add entries to CHANGELOG

---

## 🗺️ Roadmap

### Completed ✅
- [x] Multi-agent collaboration system
- [x] Ollama (local) LLM integration
- [x] OpenRouter (cloud) LLM integration
- [x] **Inference packs** - Per-agent model configuration
- [x] Reasoning model support (dual-field extraction)
- [x] Real-time streaming responses
- [x] Live rolling summaries
- [x] PostgreSQL persistence
- [x] Smart rate limit management
- [x] Comprehensive test suite (223 tests, 70% coverage)
- [x] Docker deployment configs

### In Progress 🚧
- [ ] Phase 3: Production polish and refinements
- [ ] Enhanced error handling and recovery
- [ ] Performance optimizations
- [ ] Advanced knowledge persistence

### Planned 🎯
- [ ] Web UI interface
- [ ] Multi-user support
- [ ] Additional LLM providers (Anthropic direct, Azure OpenAI)
- [ ] Agent personality customization
- [ ] Knowledge graph integration
- [ ] Agent learning and adaptation
- [ ] Real-time collaboration features

---

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

---

## 🆘 Support

- **Issues**: [GitHub Issues](https://github.com/jechocarlos/queenbee/issues)
- **Documentation**: See `/docs` directory
- **Discussions**: [GitHub Discussions](https://github.com/jechocarlos/queenbee/discussions)

---

## 🙏 Acknowledgments

Built with ❤️ using:
- [Python 3.14](https://www.python.org/)
- [Ollama](https://ollama.ai/) - Local LLM runtime
- [OpenRouter](https://openrouter.ai/) - Cloud LLM API
- [PostgreSQL](https://www.postgresql.org/) - Database
- [Rich](https://rich.readthedocs.io/) - Terminal UI

---

**Made with collaborative AI thinking** 🐝