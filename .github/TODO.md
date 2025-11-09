# QueenBee - Development TODO

**Last Updated**: November 9, 2025  
**Current Phase**: Phase 1 - Foundation (MVP)

---

## Phase 1: Foundation (MVP)

### 1. Project Setup ✅
- [x] Initialize Python 3.14 project structure
- [x] Create `pyproject.toml` with dependencies (Agno, AgentOS, psycopg2, etc.)
- [x] Set up `.gitignore` (include `.env`, `__pycache__`, etc.)
- [x] Create `README.md` with project overview and setup instructions

### 2. Configuration Management ✅
- [x] Create `config.yaml` with system configuration
- [x] Create `.env.example` template
- [x] Implement configuration loader (`src/config/loader.py`)
- [x] Add environment variable validation

### 3. Docker Infrastructure ✅
- [x] Create `docker-compose.local.yml` (PostgreSQL + Ollama)
- [x] Create `docker-compose.remote.yml` (Ollama only)
- [x] Write `Dockerfile` for QueenBee application (optional for Phase 1)
- [x] Test local Docker setup
- [x] Document Docker setup in `/docs/docker-setup.md`

### 4. Database Setup ✅
- [x] Create SQL migration files (`migrations/001_initial_schema.sql`)
  - [x] Create ENUM types (`agent_type`, `agent_status`, `session_status`, etc.)
  - [x] Create `sessions` table
  - [x] Create `agents` table
  - [x] Create `chat_history` table
  - [x] Create `agent_memory` table
  - [x] Create `agent_knowledge` table
  - [x] Create `tasks` table
  - [x] Add indexes for performance
- [x] Implement database connection manager (`src/db/connection.py`)
- [x] Create database models/ORM layer (`src/db/models.py`)
- [ ] Write migration runner script (`scripts/migrate.py`)
- [ ] Test database schema creation

### 5. System Prompts ✅
- [x] Create `prompts/queen.md` - Main orchestrator prompt
- [x] Create `prompts/divergent.md` - Divergent thinker prompt
- [x] Create `prompts/convergent.md` - Convergent thinker prompt (for Phase 2, stub for now)
- [x] Create `prompts/critical.md` - Critical thinker prompt (for Phase 2, stub for now)
- [ ] Validate prompts with Ollama

### 6. Core Agent Framework
- [ ] Implement base agent class (`src/agents/base.py`)
  - [ ] Agent initialization with config
  - [ ] Prompt loading from markdown files
  - [ ] Connection to Ollama
  - [ ] Database interaction methods
  - [ ] Activity tracking (last_activity_at updates)
- [ ] Implement Queen agent (`src/agents/queen.py`)
  - [ ] CLI input handling
  - [ ] Complexity analysis logic
  - [ ] Simple request direct handling
  - [ ] Spawn specialist capability (process creation)
  - [ ] Result aggregation
- [ ] Implement Divergent agent (`src/agents/divergent.py`)
  - [ ] Task receiving from Queen
  - [ ] Private memory management
  - [ ] Report generation back to Queen
  - [ ] Knowledge base writing

### 7. Inter-Process Communication
- [ ] Design IPC mechanism (message queue, pipes, or database polling)
- [ ] Implement Queen → Specialist task delegation
- [ ] Implement Specialist → Queen result reporting
- [ ] Test process spawning and communication

### 8. Session Management
- [ ] Implement session creation on startup (`src/session/manager.py`)
- [ ] Link agents to active session
- [ ] Terminate old sessions on restart
- [ ] Session cleanup on shutdown

### 9. CLI Interface
- [ ] Create main CLI entry point (`src/cli/main.py`)
- [ ] Implement input loop
- [ ] Display Queen responses
- [ ] Show specialist spawn notifications
- [ ] Handle graceful shutdown (Ctrl+C)
- [ ] Basic error display

### 10. Testing & Validation
- [ ] Write unit tests for configuration loader
- [ ] Write unit tests for database models
- [ ] Write integration test: Queen handles simple request
- [ ] Write integration test: Queen spawns Divergent for complex request
- [ ] Write integration test: End-to-end with database persistence
- [ ] Manual testing with Ollama

### 11. Documentation
- [ ] Create `/docs/architecture.md` - System architecture overview
- [ ] Create `/docs/database.md` - Database schema documentation
- [ ] Create `/docs/getting-started.md` - Quick start guide
- [ ] Create `/docs/configuration.md` - Config and environment setup
- [x] Update `README.md` with installation and usage

---

## Phase 2: Core Loop (Not Started)

### 1. Additional Specialists
- [ ] Implement Convergent agent (`src/agents/convergent.py`)
- [ ] Implement Critical agent (`src/agents/critical.py`)
- [ ] Test all three specialist types

### 2. Consensus Protocol
- [ ] Implement mediated communication protocol
- [ ] Implement consensus checking logic
- [ ] Handle multi-round Work/Report cycles
- [ ] Implement max rounds limit and fallback
- [ ] Test consensus with all three specialists

### 3. TTL & Cleanup
- [ ] Implement idle timeout checker (background thread/process)
- [ ] Agent activity tracking
- [ ] Automatic termination on timeout
- [ ] Process cleanup
- [ ] Database cleanup (mark terminated, flush memory)

### 4. Parallel Execution
- [ ] Refactor to support multiple concurrent specialist spawns
- [ ] Implement concurrent spawn limits
- [ ] Test parallel specialist execution

### 5. Enhanced Session Management
- [ ] Session status tracking
- [ ] Session history viewing
- [ ] Session resume capability (stretch goal)

---

## Phase 3: Polish (Not Started)

### 1. Memory Architecture Refinement
- [ ] Clearly separate shared chat history from private memory
- [ ] Implement memory visibility controls
- [ ] Knowledge persistence and retrieval optimization

### 2. Logging & Monitoring
- [ ] Structured logging (JSON format)
- [ ] Log levels per component
- [ ] Performance metrics collection
- [ ] Agent activity dashboard (CLI or simple UI)

### 3. Error Handling & Recovery
- [ ] Graceful handling of Ollama connection failures
- [ ] Database connection retry logic
- [ ] Agent process crash recovery
- [ ] Partial result handling when consensus fails

### 4. Configuration Management
- [ ] Runtime config validation
- [ ] Config hot-reload capability (stretch)
- [ ] Multiple environment support (dev/staging/prod)

### 5. Documentation & Examples
- [ ] Create example use cases
- [ ] Video/GIF demos
- [ ] Troubleshooting guide
- [ ] Performance tuning guide
- [ ] API reference documentation

---

## Future Considerations (Post v1.0)

- [ ] Web UI interface
- [ ] API endpoints for programmatic access
- [ ] Multi-user session support
- [ ] Agent learning persistence across restarts
- [ ] Custom specialist type creation
- [ ] Agent-to-agent direct communication
- [ ] Distributed agent execution
- [ ] Integration with external tools/APIs
- [ ] Agent performance analytics dashboard
- [ ] Cost/token usage tracking

---

## Current Sprint (Week 1)

**Focus**: Get basic infrastructure running

**Priority Tasks**:
1. Project setup and dependencies
2. Docker infrastructure (local mode)
3. Database schema and migrations
4. Basic Queen agent with Ollama integration
5. Simple CLI interface

**Success Criteria**:
- Can run `queenbee` CLI
- Queen responds to simple requests via Ollama
- Responses stored in PostgreSQL

---

## Blockers & Issues

_None currently_

---

## Notes

- Using Python 3.14 (ensure compatibility)
- Ollama must be running on localhost:11434
- PostgreSQL 16+ required
- Agno/AgentOS integration details TBD (research needed)

---

## Completed Tasks

### Phase 1 - Foundation (Completed)
- [x] **Project Setup**: Python 3.14 structure, pyproject.toml, src/ directories, .gitignore
- [x] **Configuration Management**: config.yaml, .env.example, configuration loader with Pydantic validation and env var substitution
- [x] **Docker Infrastructure**: docker-compose.local.yml (PostgreSQL + Ollama), docker-compose.remote.yml (Ollama only)
- [x] **Database Schema**: Complete 001_initial_schema.sql with all 6 tables, ENUMs, indexes, triggers, and utility functions
- [x] **Database Layer**: Connection manager with context managers, repository pattern for sessions/agents/chat
- [x] **System Prompts**: All four agent prompts (queen.md, divergent.md, convergent.md, critical.md) with detailed thinking frameworks
- [x] **Documentation**: Comprehensive README.md with architecture, quick start, configuration guide

### Summary of What's Built
**Infrastructure** (100%):
- Complete project scaffolding
- Configuration management system
- Docker deployment (local + remote)
- Database schema with full migration
- Database access layer

**Documentation** (70%):
- README with full setup guide
- System prompts for all agents
- In-code documentation
- Still needed: `/docs` detailed guides

**Core Framework** (30%):
- Database models and enums
- Repository pattern established
- Configuration loader
- Still needed: Agent implementations, CLI, Ollama integration
