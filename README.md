# QueenBee 🐝

**Meta-Agent Orchestration System with Specialized Thinking Agents**

![Tests](https://img.shields.io/badge/tests-87%20passed%2C%202%20skipped-brightgreen)
![Coverage](https://img.shields.io/badge/coverage-42%25-yellow)
![Python](https://img.shields.io/badge/python-3.14-blue)
![License](https://img.shields.io/badge/license-MIT-blue)

QueenBee is an intelligent agent orchestration system that dynamically spawns specialized thinking agents to tackle complex problems through divergent exploration, convergent synthesis, and critical analysis.

## ✨ Key Features

- **🎯 Intelligent Orchestration**: Queen agent analyzes complexity and delegates to specialists
- **🧠 Multi-Agent Collaboration**: Three specialist agents work together on complex problems
  - **Divergent Agent**: Explores multiple perspectives and creative approaches
  - **Convergent Agent**: Synthesizes insights and ranks recommendations
  - **Critical Agent**: Validates solutions and identifies risks
- **⚡ Real-time Streaming**: LLM responses stream token-by-token for immediate feedback
- **💬 Live Chat History**: View entire conversation with `history` command
- **🔄 Async Worker Processes**: Specialists run in background for true parallelism
- **🗄️ Persistent Memory**: PostgreSQL-backed agent state, tasks, and knowledge
- **🏠 Local LLM**: Powered by Ollama for privacy and control
- **⏰ Activity-Based TTL**: Agents expire after inactivity, keeping system lean

## Architecture

```
User Input
    ↓
Queen Agent (Orchestrator)
    ├─→ Simple Request → Direct Response
    └─→ Complex Request → Task Queue
                              ↓
                     Worker Process Manager
                              ↓
                    ┌─────────┼─────────┐
                    ↓         ↓         ↓
                Divergent Convergent Critical
                (Explore)  (Synthesize) (Validate)
                    ↓         ↓         ↓
                    └─────────┼─────────┘
                              ↓
                        Task Results
                              ↓
                    Queen Synthesizes
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
```bash
queenbee
```

## Usage

### Simple Request (Queen handles directly)
```
> What's the capital of France?
[Queen] Paris.
```

### Complex Request (Spawns specialists)
```
> Should I use microservices or a monolith for my startup?

[Queen] This is a complex multi-perspective question. Spawning specialists...
[Queen] ✓ Divergent spawned
[Queen] ✓ Convergent spawned
[Queen] ✓ Critical spawned
[Queen] Coordinating analysis...

[Working in background...]

[Queen] Analysis complete. Here's what the team found:
[Synthesized findings from all three specialists]
```

## Configuration

### Environment Variables (`.env`)

```bash
# Common
LOG_LEVEL=INFO
OLLAMA_HOST=http://localhost:11434

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
- Ollama model selection
- Specialist behavior tuning

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
pytest
```

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