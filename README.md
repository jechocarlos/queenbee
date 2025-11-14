# QueenBee 🐝

**Meta-Agent Orchestration System with Specialized Thinking Agents**

![Tests](https://img.shields.io/badge/tests-223%20passed%2C%202%20skipped-brightgreen)
![Coverage](https://img.shields.io/badge/coverage-70%25-yellow)
![Python](https://img.shields.io/badge/python-3.14-blue)
![License](https://img.shields.io/badge/license-MIT-blue)

QueenBee is an intelligent agent orchestration system that dynamically spawns specialized thinking agents to tackle complex problems through divergent exploration, convergent synthesis, and critical analysis.

## ✨ Key Features

- **🎯 Pure Orchestration**: Queen agent delegates all requests to specialist team
- **🧠 Multi-Agent Collaboration**: Four specialist agents work together on every query
  - **Divergent Agent**: Explores multiple perspectives and creative approaches
  - **Convergent Agent**: Synthesizes insights and ranks recommendations
  - **Critical Agent**: Validates solutions and identifies risks
  - **Summarizer Agent**: Generates rolling summaries and final synthesis
- **📊 Live Progress Updates**: Real-time rolling summaries show emerging insights
- **⚡ Real-time Streaming**: LLM responses stream token-by-token for immediate feedback
- **💬 Live Chat History**: View entire conversation with `history` command
- **🔄 Async Worker Processes**: Specialists run in background for true parallelism
- **🗄️ Persistent Memory**: PostgreSQL-backed agent state, tasks, and knowledge
  - Robust connection management with automatic reconnection
  - Transaction safety with commit/rollback
  - Context manager support for clean resource handling
- **🤖 Flexible LLM Backend**: Choose your AI provider
  - **Ollama**: Local LLM for privacy and control
  - **OpenRouter**: Access to Claude, GPT-4, and other premium models
- **⏰ Activity-Based TTL**: Agents expire after inactivity, keeping system lean

## Architecture

```
User Input
    ↓
Queen Agent (Pure Orchestrator)
    ↓
Task Queue → Specialist Discussion
                ↓
     ┌──────────┼──────────┐
     ↓          ↓          ↓
 Divergent  Convergent  Critical
 (Explore)  (Synthesize) (Validate)
     ↓          ↓          ↓
     └──────────┼──────────┘
                ↓
        Summarizer Agent
     (Rolling + Final Synthesis)
                ↓
      Queen's Final Response
                ↓
                    Collaborative Response
```

## Quick Start

### Prerequisites

- Python 3.14+
- Docker & Docker Compose
- Ollama (or use containerized version)

### Installation

1. **Clone the repository**:
```bash
git clone https://github.com/jechocarlos/queenbee.git
cd queenbee
```

2. **Set up environment**:
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. **Start infrastructure** (local mode):
```bash
docker-compose -f docker-compose.local.yml up -d
```

4. **Pull Ollama model**:
```bash
docker exec -it queenbee-ollama ollama pull llama3.1:8b
```

5. **Install Python dependencies**:
```bash
pip install -e .
```

6. **Run migrations**:
```bash
python scripts/migrate.py
```

7. **Start QueenBee**:

**With Ollama (local):**
```bash
queenbee
```

**With OpenRouter (cloud):**
```bash
# Add your OpenRouter API key to .env
echo "OPENROUTER_API_KEY=your_key_here" >> .env

# Run with OpenRouter
queenbee-openrouter
```

## Usage

### Every Request Gets Full Team Analysis
```
> What's the capital of France?

[Queen] Delegating to my specialist team for collaborative analysis...

🔵 Divergent #1
France's capital is Paris, known for the Eiffel Tower, Louvre Museum, and as a cultural hub...

🟢 Convergent #1
Paris is definitively the capital of France, both politically and culturally...

🔴 Critical #1
Confirmed: Paris has been France's capital since 987 CE...

📋 FINAL SYNTHESIS
Paris is the capital of France, serving as the political, cultural, and economic center.

🐝 QUEEN'S RESPONSE
Paris is the capital of France.
```

### Complex Analysis Example
```
> Should I use microservices or a monolith for my startup?

[Queen] Delegating to my specialist team for collaborative analysis...

🔵 Divergent #1
Let's explore multiple architectural approaches: microservices for scalability...

🟢 Convergent #1
Synthesizing the perspectives: start with a modular monolith...

🔴 Critical #1
Key concerns: operational complexity vs development speed...

💭 Rolling Summary
The team is analyzing trade-offs between microservices (scalability, complexity) 
and monoliths (simplicity, faster initial development)...

[Discussion continues...]

📋 FINAL SYNTHESIS
For a startup, begin with a modular monolith to validate product-market fit quickly. 
Extract microservices only when specific scaling bottlenecks emerge. Key trade-off: 
operational complexity vs development velocity.

🐝 QUEEN'S RESPONSE
I recommend starting with a modular monolith architecture for your startup...
```

[Queen] Analysis complete. Here's what the team found:
[Synthesized findings from all three specialists]
```

## Configuration

### Environment Variables (`.env`)

```bash
# Common
LOG_LEVEL=INFO

# Ollama (local LLM)
OLLAMA_HOST=http://localhost:11434

# OpenRouter (cloud LLM - optional)
OPENROUTER_API_KEY=your_api_key_here

# Database (local deployment)
DB_HOST=postgres
DB_PORT=5432
DB_NAME=queenbee
DB_USER=queenbee
DB_PASSWORD=your_password

# Database (remote deployment)
# DB_HOST=your-remote-host.com
# DB_SSL_MODE=require
```

### System Configuration (`config.yaml`)

See `config.yaml` for full configuration options including:
- Agent TTL settings
- Consensus parameters
- **Ollama**: Local model selection (llama3.1:8b by default)
- **OpenRouter**: Cloud model selection (anthropic/claude-3.5-sonnet by default)
- Specialist behavior tuning

### LLM Provider Selection

**Use Ollama (local, private, free):**
```bash
queenbee
```

**Use OpenRouter (cloud, premium models):**
```bash
queenbee-openrouter
```

Both commands use the same configuration and database - only the LLM provider changes. You can switch between providers anytime without losing conversation history.

### Rate Limiting (OpenRouter)

OpenRouter integration includes intelligent rate limiting:

```yaml
# config.yaml
openrouter:
  requests_per_minute: 16  # Free tier limit
  max_retries: 3           # Retry on rate limit
  retry_delay: 5           # Seconds between retries
```

**How it works:**
- **Token Bucket Algorithm**: Automatically throttles requests to respect provider limits
- **Proactive Limiting**: Prevents hitting rate limits by tracking usage locally
- **Automatic Retries**: Handles 429 errors with exponential backoff
- **Thread-Safe**: Works correctly with multiple specialist agents running concurrently

**Rate Limit Tiers:**
- **Free**: 16 requests/minute (default)
- **Paid Plans**: Update `requests_per_minute` in config to match your tier

## Deployment Modes

### Local Development
All services containerized:
```bash
docker-compose -f docker-compose.local.yml up -d
```

### Remote Database
Ollama only, connect to external PostgreSQL:
```bash
docker-compose -f docker-compose.remote.yml up -d
```

## Project Structure

```
queenbee/
├── .github/
│   ├── SPECS.md          # System specification
│   └── TODO.md           # Development tasks
├── src/queenbee/
│   ├── agents/           # Agent implementations
│   ├── cli/              # Command-line interface
│   ├── config/           # Configuration management
│   ├── db/               # Database layer
│   └── session/          # Session management
├── prompts/              # Agent system prompts
├── migrations/           # Database migrations
├── tests/                # Test suite
├── config.yaml           # System configuration
├── .env.example          # Environment template
└── pyproject.toml        # Python package config
```

## Development

### Running Tests
```bash
pytest                              # Run all tests
pytest -v                          # Verbose output
pytest --cov                       # With coverage report
pytest tests/test_agents.py        # Specific test file
```

**Latest Test Results:**
- ✅ 223 tests passed
- ⚠️ 2 tests skipped (environment-dependent)
- 📊 70% code coverage
- ⏱️ Completed in 173 seconds (2m 53s)

### Code Quality
```bash
black src/ tests/
ruff check src/ tests/
mypy src/
```

### Database Migrations
```bash
python scripts/migrate.py
```

## Specialist Thinking Modes

### Queen Agent (Pure Orchestrator)
- Receives all user requests
- Delegates to specialist team for analysis
- Receives synthesis from SummarizerAgent
- Presents final response to user
- No direct analysis or complexity checking

### Divergent Thinker
- Explores possibilities
- Generates multiple approaches
- Challenges assumptions
- Identifies edge cases

### Convergent Thinker
- Evaluates options
- Creates action plans
- Prioritizes solutions
- Resolves contradictions

### Critical Thinker
- Identifies flaws
- Assesses risks
- Validates assumptions
- Tests robustness

### Summarizer Agent
- Generates rolling summaries during discussion
- Synthesizes insights from all perspectives
- Creates final comprehensive synthesis
- Focuses on substance over process

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

MIT License - see LICENSE file for details

## Roadmap

- [x] Phase 1: MVP with single specialist
- [ ] Phase 2: Full consensus protocol
- [ ] Phase 3: Production polish
- [ ] Web UI interface
- [ ] Multi-user support
- [ ] Agent learning persistence

## Support

- Issues: https://github.com/jechocarlos/queenbee/issues
- Documentation: See `/docs` directory
- Specification: See `.github/SPECS.md`

---

Built with ❤️ using Python, PostgreSQL, and Ollama