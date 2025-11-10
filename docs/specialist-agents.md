# Specialist Agent System

## Overview

QueenBee now features a full **multi-agent collaboration system** where the Queen agent can spawn specialized thinking agents (Divergent, Convergent, Critical) to handle complex requests collaboratively.

## Architecture

### Agent Types

**1. Queen Agent** (`src/queenbee/agents/queen.py`)
- Main orchestrator
- Analyzes request complexity
- Delegates to specialists for complex questions
- Synthesizes and presents final results
- Manages conversation flow

**2. Divergent Agent** (`src/queenbee/agents/divergent.py`)
- **Role**: Explore multiple perspectives
- **Temperature**: 0.9 (high creativity)
- **Output**: List of 3-5 diverse perspectives
- **Thinking mode**: Brainstorming, lateral thinking, challenging assumptions

**3. Convergent Agent** (`src/queenbee/agents/convergent.py`)
- **Role**: Synthesize and evaluate options
- **Temperature**: 0.5 (balanced)
- **Output**: Ranked recommendations with reasoning
- **Thinking mode**: Analysis, comparison, prioritization

**4. Critical Agent** (`src/queenbee/agents/critical.py`)
- **Role**: Validate and identify issues
- **Temperature**: 0.3 (low for consistency)
- **Output**: Risk assessment, concerns, improvements
- **Thinking mode**: Skeptical analysis, edge case identification

## How It Works

### 1. Complexity Detection

Queen analyzes user input for:
- Complex keywords (analyze, compare, evaluate, design)
- Multiple questions (more than one `?`)
- Long input (>50 words)
- Decision-making phrases ("should I", "which is better")

### 2. Task Creation

If complex, Queen creates a task in the database:
```python
task_data = {
    "type": "full_analysis",
    "input": user_input,
    "context": recent_conversation
}
```

Task stored in `tasks` table with:
- `session_id`: Current session
- `assigned_by`: Queen's agent ID
- `assigned_to`: Array of specialist agent IDs
- `description`: JSON task data
- `status`: pending → in_progress → completed

### 3. Worker Process

Background worker process (`src/queenbee/workers/manager.py`):
- Polls `tasks` table for pending tasks
- Spawns specialists in sequence:
  1. **Divergent**: Generates 3-5 perspectives
  2. **Convergent**: Synthesizes perspectives into recommendations
  3. **Critical**: Validates and identifies risks
- Stores results as JSON in `tasks.result`
- Updates status to `completed`

### 4. Result Synthesis

Queen waits for task completion (max 2 minutes), then:
- Retrieves results from database
- Formats collaborative response
- Displays with color-coded sections:
  - 🔵 Divergent Perspectives
  - 🟢 Convergent Synthesis
  - 🔴 Critical Validation

## Usage

### Enable/Disable Specialists

By default, specialists are **enabled**. Toggle with CLI commands:

```
You: specialists off
⚠ Specialist spawning disabled

You: specialists on
✓ Specialist spawning enabled
```

### Example Complex Question

```
You: Should I use microservices or monolithic architecture for my startup?

Queen is thinking...
```

Behind the scenes:
1. Queen detects complexity (keywords: "should I", comparison question)
2. Creates task for specialists
3. Worker spawns:
   - Divergent explores: scalability vs simplicity, team size implications, cost factors
   - Convergent synthesizes: startup phase recommendations, hybrid approach
   - Critical validates: risks of premature optimization, deployment complexity

```
🐝 [QueenBee Collaborative Analysis]
I've consulted with my specialist team to analyze: 'Should I use microservices...'

🔵 Divergent Perspectives:
1. Microservices offer independent scaling but require DevOps expertise
2. Monolithic architecture enables faster initial development
3. Hybrid approach: start monolithic, extract services as needed
4. Consider team size and experience with distributed systems
5. Cost implications of infrastructure complexity

🟢 Convergent Synthesis:
For a startup, I recommend starting with a well-structured monolith...
[detailed synthesis]

🔴 Critical Validation:
Key risks to consider:
- Premature microservices can slow development
- Monolith requires disciplined modular design
- Migration path should be planned from day one
[detailed validation]

✨ This analysis represents a collaborative effort from multiple thinking modes.
```

## Database Schema

### Tasks Table

```sql
CREATE TABLE tasks (
    id UUID PRIMARY KEY,
    session_id UUID REFERENCES sessions(id),
    assigned_by UUID REFERENCES agents(id),  -- Queen's ID
    assigned_to UUID[],  -- Specialist IDs
    description TEXT,  -- JSON task data
    status task_status,  -- pending/in_progress/completed/failed
    created_at TIMESTAMP,
    completed_at TIMESTAMP,
    result TEXT  -- JSON results from specialists
);
```

### Task Flow

1. Queen creates task → status: `pending`
2. Worker picks up task → status: `in_progress`
3. Worker completes → status: `completed`, stores `result`
4. Queen reads result → formats response

## Worker Process Management

### WorkerManager Class

```python
from queenbee.workers import WorkerManager

# Create manager
worker_mgr = WorkerManager(config)

# Start worker for session
worker_mgr.start_worker(session_id)

# Worker runs in separate process, polls for tasks

# Stop worker when done
worker_mgr.stop_worker(session_id)
```

### Worker Lifecycle

- **Started**: When CLI session begins
- **Runs**: Daemon process, polls every 2 seconds
- **Processes**: Tasks sequentially for the session
- **Stopped**: When user exits CLI (automatic cleanup)

## Configuration

No additional configuration needed. Uses existing settings:

```yaml
agents:
  divergent:
    system_prompt_file: ./prompts/divergent.md
    max_iterations: 5
  convergent:
    system_prompt_file: ./prompts/convergent.md
    max_iterations: 5
  critical:
    system_prompt_file: ./prompts/critical.md
    max_iterations: 5
```

## Performance Considerations

### Timeouts

- **Task wait**: 120 seconds (2 minutes)
- **Fallback**: If timeout, Queen provides direct answer
- **Worker poll**: Every 2 seconds

### Resource Usage

- **One worker per session**: Lightweight process
- **Sequential execution**: Specialists run one after another
- **Database-based**: No complex IPC, simple and reliable

### Optimization Opportunities

1. **Parallel specialist execution**: Run Divergent agents in parallel
2. **Streaming results**: Stream specialist outputs as they complete
3. **Caching**: Cache perspectives for similar questions
4. **Worker pool**: Reuse workers across sessions

## Specialist Methods

### Divergent Agent

```python
perspectives = divergent.explore(task, context)
# Returns: ["perspective 1", "perspective 2", ...]
```

### Convergent Agent

```python
synthesis = convergent.synthesize(task, perspectives, context)
# Returns: {"synthesis": "...", "perspectives_evaluated": 5}

trade_offs = convergent.evaluate_trade_offs(options, criteria)
# Returns: {"trade_off_analysis": "...", ...}
```

### Critical Agent

```python
validation = critical.validate(task, synthesis, context)
# Returns: {"validation": "...", "concerns_identified": True}

risks = critical.identify_risks(proposal, domain)
# Returns: {"risk_analysis": "...", "domain": "security"}

consistency = critical.verify_consistency(statements)
# Returns: {"consistency_check": "...", ...}
```

## Troubleshooting

### Specialists not responding

**Check worker process:**
```bash
ps aux | grep "worker_process"
```

**Check tasks table:**
```sql
SELECT * FROM tasks WHERE session_id = '<your_session_id>' ORDER BY created_at DESC;
```

**Check logs:**
```
[Worker] Task <task_id> completed successfully
```

### Timeout issues

- Increase `max_wait` in `queen.py` (default: 120 seconds)
- Check Ollama performance (`ollama ps`)
- Try smaller model for faster responses

### Task stuck in pending

- Worker process may have crashed
- Restart CLI (worker auto-starts)
- Check database connectivity

## Future Enhancements

1. **Iterative refinement**: Specialists can review each other's work
2. **Consensus voting**: Require agreement threshold
3. **Specialized domains**: Financial, technical, creative specialists
4. **Memory sharing**: Specialists access shared knowledge base
5. **Parallel processing**: Multiple Divergent agents for broader exploration
6. **Real-time updates**: Stream specialist progress to CLI

## Testing

### Test specialist spawning:

```bash
queenbee
```

```
You: specialists on
You: Compare the trade-offs between REST and GraphQL APIs

# Should trigger full specialist workflow
```

### Verify task creation:

```sql
SELECT 
    t.id, 
    t.status, 
    t.description,
    jsonb_pretty(t.result::jsonb) as formatted_result
FROM tasks t
ORDER BY t.created_at DESC
LIMIT 1;
```

### Check agent creation:

```sql
SELECT agent_type, status, created_at 
FROM agents 
WHERE session_id = '<your_session_id>'
ORDER BY created_at DESC;
```
