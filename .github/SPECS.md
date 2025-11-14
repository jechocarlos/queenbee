# QueenBee - Agent Spawning System Specification

**Version:** 2.0  
**Date:** November 10, 2025  
**Status:** Implemented - Phase 2 Complete

---

## 1. Overview

QueenBee is a meta-agent orchestration system that dynamically spawns specialized thinking agents based on task complexity. The system features a main "Queen" agent that handles simple requests directly and delegates complex, multi-step problems to specialist agents working in parallel.

### 1.1 Core Principles
- **Context Management**: Distribute cognitive load across specialized agents
- **Async Processing**: Specialists work in background without blocking main flow
- **Knowledge Ownership**: Each spawn maintains domain expertise within its thinking mode
- **Consensus-Based Completion**: Collaborative agreement determines task completion

---

## 2. System Architecture

### 2.1 Components
- **Queen Agent**: Main orchestrator and user interface
- **Specialist Agents**: Spawnable thinking-mode experts
- **PostgreSQL Database**: Agent persistence and state management
- **Ollama**: Local LLM inference
- **Agno/AgentOS**: Agent framework

### 2.2 Technology Stack
- **Language**: Python 3.14
- **Agent Framework**: Agno, AgentOS
- **LLM Provider**: Ollama (local models)
- **Database**: PostgreSQL 16+ (Dockerized)
- **Process Model**: Separate processes per agent
- **Interface**: CLI/Terminal

---

## 3. Agent Types

### 3.1 Queen Agent (Main Orchestrator)
**Role**: Entry point, complexity analyzer, task coordinator

**Responsibilities**:
- Accept user input via CLI
- Analyze request complexity
- Handle simple/single-step requests directly
- Spawn specialists for complex/multi-step work
- Mediate communication between specialists
- Aggregate and present results to user

### 3.2 Specialist Agents

#### 3.2.1 Divergent Thinker
**Thinking Mode**: Exploration, ideation, possibility expansion

**System Prompt**: Pre-configured prompt stored in `./prompts/divergent.md`

**Responsibilities**:
- Generate multiple approaches/options
- Explore edge cases and alternatives
- Challenge assumptions
- Identify unconsidered dimensions

#### 3.2.2 Convergent Thinker
**Thinking Mode**: Synthesis, solution narrowing, decision-making

**System Prompt**: Pre-configured prompt stored in `./prompts/convergent.md`

**Responsibilities**:
- Evaluate options from Divergent
- Prioritize and filter solutions
- Create coherent action plans
- Resolve contradictions

#### 3.2.3 Critical Thinker
**Thinking Mode**: Analysis, validation, risk assessment

**System Prompt**: Pre-configured prompt stored in `./prompts/critical.md`

**Responsibilities**:
- Identify flaws and risks
- Validate assumptions
- Test solution robustness
- Challenge conclusions

---

## 4. Operational Behavior

### 4.1 Decision Flow

```
User Request → Queen Agent
                    ↓
              Complexity Analysis
                    ↓
        ┌───────────┴───────────┐
        ↓                       ↓
   Simple Request          Complex Request
        ↓                       ↓
   Handle Directly         Spawn Specialists
        ↓                       ↓
   Return Result      Mediated Collaboration
                              ↓
                        Consensus Check
                              ↓
                        Aggregate Results
                              ↓
                        Return to User
```

### 4.2 Complexity Detection Criteria
**Simple Requests** (Queen handles directly):
- Single-step tasks
- Factual lookups
- Clarification questions
- Direct commands

**Complex Requests** (Spawn specialists):
- Multi-step problems requiring planning
- Open-ended questions needing exploration
- Design/architecture decisions
- Problems requiring multiple perspectives

### 4.3 Specialist Collaboration Protocol (Async Parallel Discussion)

**Current Implementation**: Agents work in parallel threads with intelligent contribution logic

1. **Spawn Phase**: Queen creates task and starts background worker with 3 specialists
2. **Async Work Phase**: 
   - Each specialist runs in independent thread (Divergent, Convergent, Critical)
   - Agents continuously monitor shared discussion state
   - Each agent decides independently when to contribute based on:
     - Discussion history analysis
     - Detection of new value they can add
     - Maximum 3 contributions per agent
     - Must not contribute twice in a row
3. **Real-time Display**:
   - Queen polls task result every 2 seconds
   - New contributions displayed immediately with color coding
   - Rolling summary updates shown every 4 seconds during discussion
4. **Stopping Logic**:
   - Monitor checks agent statuses every 1 second
   - Discussion stops when ALL agents idle for 6 consecutive seconds
   - Maximum timeout: 300 seconds (5 minutes, configurable)
5. **Summary Phase**:
   - Rolling summary thread generates brief 2-3 sentence updates during discussion
   - Final comprehensive summary generated at end (4-5 sentences)
   - Final summary builds upon rolling summary insights

**Key Features**:
- **Intelligent Contribution**: Agents analyze what's already been said before responding
- **No Forced Rounds**: Agents contribute whenever they have new value to add
- **Pass Mechanism**: Agents can respond with [PASS] if they'd just repeat existing points
- **Concise Responses**: Maximum 2-3 sentences per contribution
- **Live Context**: Rolling summary provides real-time understanding of discussion progress

### 4.4 Communication Model
- **User ↔ Queen**: Visible in terminal (shared chat history)
- **Queen → User**: Real-time display of specialist contributions with color coding
  - 🔵 Blue: Divergent contributions
  - 🟢 Green: Convergent contributions
  - 🔴 Red: Critical contributions
- **Queen → User**: Live rolling summary updates (dim gray panel, every ~4 seconds)
- **Queen → User**: Final comprehensive summary (yellow panel, at completion)
- **Queen ↔ Specialists**: Via database-backed task queue
- **Specialist ↔ Specialist**: Through shared discussion state (read-only for others' contributions)
- **Specialist → User**: Real-time as contributions are made (not aggregated)

---

## 5. Memory & Persistence

### 5.1 Memory Architecture

#### Shared Chat History
- **Scope**: Entire session, visible to user
- **Content**: User messages, Queen responses, specialist deliverables
- **Storage**: PostgreSQL `chat_history` table
- **Visibility**: User sees only this layer

#### Private Agent Memory
- **Scope**: Per-agent, per-session
- **Content**: Working thoughts, intermediate steps, reasoning traces
- **Storage**: PostgreSQL `agent_memory` table
- **Visibility**: Internal only, not shown to user

#### Agent Knowledge Base
- **Scope**: Per-agent, persistent across tasks within session
- **Content**: Learned patterns, insights, domain knowledge
- **Storage**: PostgreSQL `agent_knowledge` table
- **Purpose**: Enables specialists to accumulate expertise

### 5.2 Database Schema

#### `agents` Table
```sql
- id (UUID, PK)
- type (ENUM: 'queen', 'divergent', 'convergent', 'critical')
- status (ENUM: 'active', 'idle', 'terminated')
- created_at (TIMESTAMP)
- last_activity_at (TIMESTAMP)
- session_id (UUID, FK)
- system_prompt (TEXT)
- configuration (JSONB)
```

#### `sessions` Table
```sql
- id (UUID, PK)
- started_at (TIMESTAMP)
- ended_at (TIMESTAMP, nullable)
- status (ENUM: 'active', 'completed', 'terminated')
```

#### `chat_history` Table
```sql
- id (SERIAL, PK)
- session_id (UUID, FK)
- agent_id (UUID, FK, nullable) -- null means user message
- role (ENUM: 'user', 'queen', 'specialist')
- content (TEXT)
- timestamp (TIMESTAMP)
- metadata (JSONB)
```

#### `agent_memory` Table
```sql
- id (SERIAL, PK)
- agent_id (UUID, FK)
- session_id (UUID, FK)
- memory_type (ENUM: 'working', 'reasoning', 'observation')
- content (TEXT)
- created_at (TIMESTAMP)
```

#### `agent_knowledge` Table
```sql
- id (SERIAL, PK)
- agent_id (UUID, FK)
- knowledge_type (VARCHAR)
- content (TEXT)
- confidence_score (FLOAT)
- created_at (TIMESTAMP)
- last_accessed_at (TIMESTAMP)
```

#### `tasks` Table
```sql
- id (UUID, PK)
- session_id (UUID, FK)
- assigned_by (UUID, FK) -- agent that created task
- assigned_to (UUID, FK, array) -- agents working on it
- description (TEXT)
- status (ENUM: 'pending', 'in_progress', 'completed', 'failed')
- created_at (TIMESTAMP)
- completed_at (TIMESTAMP, nullable)
- result (TEXT, nullable)
```

---

## 6. Agent Lifecycle

### 6.1 Creation
- **Trigger**: Queen determines complexity threshold exceeded
- **Process**: 
  1. Generate unique agent ID
  2. Create database record with status='active'
  3. Load pre-configured system prompt from `./prompts/{type}.md`
  4. Spawn separate Python process with loaded prompt
  5. Link to current session

### 6.2 Activity Management
- **Active State**: Agent is processing a task
- **Idle State**: Agent awaiting new task
- **TTL Reset Conditions**:
  - Receives new task assignment
  - Writes to knowledge base (learning occurred)
  - Participates in consensus round

### 6.3 Termination
- **Idle Timeout**: 5-15 minutes of inactivity (configurable)
- **Manual Shutdown**: User ends session
- **System Restart**: All agents terminated, DB marked 'terminated'
- **Cleanup Process**:
  1. Mark agent status='terminated' in DB
  2. Flush private memory (working/reasoning only)
  3. Preserve knowledge base for analytics
  4. Kill agent process

### 6.4 Restart Behavior
- **Database State**: All agents marked 'terminated' from previous run
- **Session State**: New session created on startup
- **Historical Data**: Previous sessions readable but not reactivated
- **Clean Slate Principle**: Each system start is fresh

---

## 7. User Interface

### 7.1 CLI Interaction
```
$ queenbee

QueenBee v2.0 - Agent Orchestration System
[Queen] Ready. How can I help?

> How to design a scalable multi-agent system with knowledge graphs?

🐝 [QueenBee Collaborative Discussion Starting...]

🔵 Divergent #1
Consider using LangGraph for workflow orchestration and Neo4j for knowledge persistence. This enables both agent coordination and shared memory across the ecosystem.
────────────────────────────────────────────────────────────

🟢 Convergent #1
Building on that, prioritize LangGraph for the agent layer with a hybrid approach: simple coordination via LangGraph state management, complex knowledge via graph database when coordination isn't sufficient.
────────────────────────────────────────────────────────────

🔴 Critical #1
Be cautious of over-engineering. Start with LangGraph's built-in memory, only add Neo4j if you hit scalability limits. The integration overhead may outweigh benefits for smaller systems.
────────────────────────────────────────────────────────────

┌─ 💭 Rolling Summary ─────────────────────────────────────┐
│ The team is exploring LangGraph for agent coordination    │
│ with a cautious approach to adding knowledge graphs. Key  │
│ insight: start simple, scale complexity only when needed. │
└──────────────────────────────────────────────────────────┘

[More contributions as discussion continues...]

✨ Discussion complete!

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃              🐝 QUEEN'S SUMMARY                           ┃
┃                                                           ┃
┃  Use LangGraph as your primary framework for agent       ┃
┃  coordination and state management. Add a knowledge      ┃
┃  graph (Neo4j) only when LangGraph's built-in memory     ┃
┃  proves insufficient for complex cross-agent queries.    ┃
┃  Start simple to avoid premature optimization.           ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

Discussion complete with 8 contributions from the specialist team.

> 
```

### 7.2 Visibility Rules
**User Sees**:
- Queen's direct responses (for simple queries)
- Spawn status notification when discussion starts
- Real-time specialist contributions with color coding (🔵🟢🔴)
- Live rolling summary updates (dim panel, every ~4 seconds)
- Final comprehensive summary (yellow panel, at completion)
- Discussion completion status with contribution count
- Error messages

**User Does NOT See**:
- Individual specialist internal reasoning processes
- Agent status updates (idle/thinking/contributing - logged only)
- Database operations and task queue management
- Thread management and synchronization
- Rolling summary generation prompts

---

## 8. Configuration

### 8.1 System Configuration (`config.yaml`)
```yaml
system:
  name: queenbee
  version: 1.0.0
  environment: development

database:
  host: localhost
  port: 5432
  name: queenbee
  user: queenbee
  password: ${DB_PASSWORD}

ollama:
  host: localhost
  port: 11434
  model: llama3.1:8b
  timeout: 120

agents:
  ttl:
    idle_timeout_minutes: 10
    check_interval_seconds: 30
  
  max_concurrent_specialists: 10
  
  queen:
    system_prompt_file: ./prompts/queen.md
    complexity_threshold: auto
  
  specialists:
    divergent:
      system_prompt_file: ./prompts/divergent.md
      max_iterations: 5
    
    convergent:
      system_prompt_file: ./prompts/convergent.md
      max_iterations: 5
    
    critical:
      system_prompt_file: ./prompts/critical.md
      max_iterations: 5

consensus:
  max_rounds: 10
  agreement_threshold: "all" # all specialists must agree
  discussion_rounds: 10  # Max iterations for discussion monitor loop
  specialist_timeout_seconds: 300  # Maximum wait time (5 minutes)
```

### 8.2 Environment Variables

**Environment File**: `.env` (created from `.env.example`)

**Template** (`.env.example`):
```bash
# Common
LOG_LEVEL=INFO
OLLAMA_HOST=http://localhost:11434

# Database Configuration
# For local deployment: DB_HOST=postgres
# For remote deployment: DB_HOST=<your_remote_host>
DB_HOST=postgres
DB_PORT=5432
DB_NAME=queenbee
DB_USER=queenbee
DB_PASSWORD=changeme

# Remote DB only (uncomment if using remote PostgreSQL)
# DB_SSL_MODE=require
```

**Setup Instructions**:
1. Copy `.env.example` to `.env`
2. Modify values based on deployment type (local vs remote)
3. Never commit `.env` to version control

### 8.3 Docker Compose Configurations

#### Local Deployment (`docker-compose.local.yml`)
**Purpose**: Fully self-contained local development

**Services**:
- PostgreSQL 16 container
- Ollama container
- QueenBee application container (optional)

**Usage**:
```bash
docker-compose -f docker-compose.local.yml up -d
```

**Features**:
- PostgreSQL data persisted in named volume
- Ollama models cached locally
- All services on same Docker network
- Suitable for: development, testing, offline work

#### Remote DB Deployment (`docker-compose.remote.yml`)
**Purpose**: Connect to hosted/managed PostgreSQL

**Services**:
- Ollama container only
- QueenBee application container (optional)

**Usage**:
```bash
docker-compose -f docker-compose.remote.yml up -d
```

**Features**:
- Connects to external PostgreSQL (AWS RDS, DigitalOcean, etc.)
- SSL/TLS connection support
- Reduced local resource usage
- Suitable for: production, shared databases, cloud deployments

---

## 9. Development Phases

### Phase 1: Foundation (MVP)
**Goal**: Basic working system with single specialist type

**Deliverables**:
- PostgreSQL schema implemented
- Docker Compose setup (2 versions):
  - **Local**: PostgreSQL + Ollama containerized
  - **Remote DB**: Ollama only, connects to external PostgreSQL
- Environment configuration (`.env.example` and `.env` files based on `config.yaml`)
- Pre-configured system prompts (`./prompts/queen.md`, `./prompts/divergent.md`, `./prompts/convergent.md`, `./prompts/critical.md`)
- Queen agent with Agno integration
- Single specialist type (Divergent) spawning
- Basic CLI interface
- Simple/complex request detection

**Acceptance Criteria**:
- User can send requests via CLI
- Queen can spawn Divergent agent for complex request
- Specialist reports findings back
- Results stored in database

### Phase 2: Core Loop
**Goal**: Full specialist suite with collaboration

**Deliverables**:
- Convergent and Critical specialists implemented
- Mediated consensus protocol
- TTL and cleanup mechanism
- Parallel specialist execution
- Session management

**Acceptance Criteria**:
- All 3 specialist types spawn and collaborate
- Consensus-based completion works
- Idle agents auto-terminate
- Multiple concurrent tasks supported

### Phase 3: Polish
**Goal**: Production-ready system

**Deliverables**:
- Shared chat + private memory separation
- Knowledge persistence and retrieval
- Comprehensive logging
- Error handling and recovery
- Configuration management
- Documentation and examples

**Acceptance Criteria**:
- System handles failures gracefully
- Historical sessions browsable
- Performance metrics available
- User documentation complete

---

## 10. Success Metrics

### 10.1 Functional Metrics
- **Spawn Decision Accuracy**: % of correctly classified simple vs. complex requests
- **Consensus Efficiency**: Average rounds to reach agreement
- **Task Completion Rate**: % of spawned tasks successfully completed
- **Agent Utilization**: % of time specialists are active vs. idle

### 10.2 Performance Metrics
- **Response Time**: Time from user request to Queen response (simple)
- **Delegation Time**: Time from spawn to consensus (complex)
- **Database Latency**: Query/write times to PostgreSQL
- **Memory Footprint**: RAM usage per agent

### 10.3 Quality Metrics
- **User Satisfaction**: Subjective quality of responses
- **Knowledge Accumulation**: Growth of agent knowledge bases
- **System Stability**: Uptime and error rates

---

## 11. Constraints & Limitations

### 11.1 Technical Constraints
- **Local Inference**: Ollama performance dependent on hardware
- **Process Overhead**: Each agent is separate process (memory cost)
- **Database Bottleneck**: PostgreSQL becomes single point of contention
- **No Distributed Mode**: All components must run on same machine (v1.0)

### 11.2 Scope Limitations
- **No Web UI**: CLI only in v1.0
- **No Multi-User**: Single session at a time
- **No Agent Learning Across Restarts**: Fresh slate each run
- **No Cross-Session Knowledge**: Agents don't remember previous runs

### 11.3 Future Considerations (Out of Scope for v1.0)
- Distributed agent execution
- Multi-user session support
- Web/API interface
- Agent learning persistence across restarts
- Custom specialist type creation
- Agent-to-agent direct communication
- Integration with external tools/APIs

---

## 12. Risk Assessment

### 12.1 Technical Risks
| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Ollama model hallucination | High | Medium | Implement Critical thinker validation |
| Process spawn overhead | Medium | High | Limit concurrent specialists, aggressive TTL |
| Database connection exhaustion | High | Medium | Connection pooling, cleanup on termination |
| Consensus deadlock | High | Low | Max rounds limit, fallback to partial results |
| Agent memory leak | Medium | Medium | Explicit cleanup, monitoring |

### 12.2 Design Risks
| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Complexity detection inaccuracy | Medium | High | Tune thresholds, allow manual override |
| Specialist role overlap | Low | Medium | Clear prompt engineering per type |
| Over-spawning (resource waste) | Medium | Medium | Concurrent spawn limits, TTL |
| Under-spawning (missed parallelism) | Low | High | Acceptable for v1.0, optimize later |

---

## 13. Open Questions

1. **Complexity Threshold Tuning**: How to automatically calibrate simple vs. complex detection?
2. **Consensus Deadlock Recovery**: What if specialists never agree?
3. **Knowledge Quality Assessment**: How to validate agent learning accuracy?
4. **Specialist Personality Drift**: How to prevent prompt drift over multiple iterations?
5. **Cost Management**: How to balance thoroughness vs. Ollama inference cost (time)?

---

## Approval

- [x] System architecture approved
- [x] Database schema approved
- [x] Agent types and behaviors approved
- [x] Development phases approved
- [x] Risk mitigation strategies approved
- [x] Phase 1 (Foundation) - Complete
- [x] Phase 2 (Core Loop) - Complete
- [ ] Phase 3 (Polish) - In Progress

**Approved By**: Development Team  
**Date**: November 10, 2025

---

**Document Control**:
- **Created**: November 9, 2025
- **Last Modified**: November 14, 2025
- **Next Review**: After Phase 3 completion

**Major Changes in v2.0**:
- Implemented async parallel discussion architecture
- Added real-time live discussion viewer with terminal output
- Implemented rolling summary system (live updates every 1.5 seconds)
- Made specialist timeout configurable (default 5 minutes)
- Enhanced final summary to build upon rolling summary insights
- Replaced sequential rounds with intelligent contribution logic
- Simplified UI to direct terminal printing (removed complex Rich layouts)
- Added word wrapping and no truncation for messages
- Implemented smart agent status updates (only on change)
