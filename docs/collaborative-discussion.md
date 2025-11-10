# Iterative Collaborative Discussion System

## Overview

The specialist agents now engage in **true collaborative discussion** where they can respond to each other's points iteratively, building on the conversation rather than working in a linear pipeline.

## How It Works

### Old System (Linear Pipeline)
```
Divergent → generates perspectives
    ↓
Convergent → synthesizes perspectives  
    ↓
Critical → validates synthesis
    ↓
Done (single pass, no interaction)
```

### New System (Iterative Discussion)
```
Round 1:
  Divergent → shares initial perspectives
  Convergent → provides initial synthesis
  Critical → identifies initial concerns

Round 2:
  Divergent → adds new angles based on what Convergent/Critical said
  Convergent → refines synthesis based on new perspectives
  Critical → addresses gaps or validates improvements

Round 3:
  [Agents can choose to PASS if nothing new to add]
  Or continue contributing new insights
  
Discussion ends when:
- Max rounds reached (configurable, default: 3)
- All agents pass (nothing more to contribute)
```

## Key Features

### 1. Agents Can See Each Other's Responses

Each agent receives the **full discussion history** when it's their turn:

```
Previous discussion:

[Round 1] Divergent: We could approach this from a microservices angle...
[Round 1] Convergent: Based on those perspectives, I recommend...
[Round 1] Critical: I see a potential issue with scalability...

[Round 2] Divergent: Building on Critical's point about scalability...
```

### 2. Agents Can Choose to Pass

If an agent feels everything has been covered, they can pass:

- Agent responds with `[PASS]` or `[NO RESPONSE]`
- Or says "I have nothing to add"
- Worker recognizes this and skips that agent for the round

### 3. Intelligent Prompting

Each agent gets role-specific instructions:

**Divergent (Explorer):**
- First round: Brainstorm 2-3 perspectives
- Later rounds: Add NEW angles, challenge assumptions
- Pass if: All perspectives explored

**Convergent (Synthesizer):**
- First round: Synthesize perspectives
- Later rounds: Refine based on new info, prioritize options
- Pass if: Nothing new to synthesize

**Critical (Validator):**
- First round: Identify risks and concerns
- Later rounds: Point out NEW issues, validate solutions
- Pass if: All concerns addressed

## Configuration

### In `config.yaml`:

```yaml
consensus:
  max_rounds: 10  # Not used for discussion
  agreement_threshold: "all"
  discussion_rounds: 3  # Number of discussion rounds
```

**discussion_rounds**: Maximum number of rounds before discussion ends
- Default: 3
- Recommended: 2-4 (balance thoroughness vs cost)
- Higher = more thorough but slower and more token usage

## Example Discussion Flow

### User Question:
> "Should I use microservices or monolithic architecture for my startup?"

### Round 1:

**🔵 Divergent:**
> Let me explore different perspectives:
> 1. **Speed perspective**: Monolithic allows faster initial development
> 2. **Scalability perspective**: Microservices enable independent scaling
> 3. **Team perspective**: Your team size and DevOps expertise matter significantly

**🟢 Convergent:**
> Synthesizing these perspectives: For an early-stage startup, I recommend starting with a well-structured monolith. The speed advantage is crucial when you need to validate your product quickly. You can plan a migration path to microservices as you scale.

**🔴 Critical:**
> Key concern: A monolith requires strong architectural discipline from day one. Without clear module boundaries, you'll face a "big ball of mud" that's hard to refactor. Also, the team needs to understand the eventual migration path before writing the first line of code.

### Round 2:

**🔵 Divergent:**
> Building on Critical's concern about architecture: Consider a "modular monolith" approach - single deployment but with clear bounded contexts. This gives you monolith benefits while maintaining microservices-ready boundaries. Also, containerization from day one makes future splitting easier.

**🟢 Convergent:**
> Excellent point from Divergent. My refined recommendation: 
> 1. Start with modular monolith in containers
> 2. Define bounded contexts using Domain-Driven Design
> 3. Extract to microservices only when specific modules need independent scaling
> This addresses Critical's concern while maintaining startup speed.

**🔴 Critical:**
> I validate this refined approach. However, add these safeguards:
> - Document module APIs as if they were services (OpenAPI specs)
> - Enforce no cross-module database access
> - Set up monitoring early to identify scaling bottlenecks
> The modular monolith works ONLY if discipline is maintained.

### Round 3:

**🔵 Divergent:** [PASS]
> (All major perspectives covered)

**🟢 Convergent:**
> [PASS] - The recommendation is clear and validated.

**🔴 Critical:**
> One final safeguard: Schedule architectural reviews every 3 months to reassess if extraction is needed. Otherwise, [PASS].

**Discussion ends** (all key points addressed)

## Response Format

The Queen formats the discussion as a transcript:

```
🐝 [QueenBee Collaborative Discussion]

My specialist team had a 3-round discussion about:
'Should I use microservices or monolithic architecture...'

============================================================
Round 1: 3 contribution(s)
============================================================

🔵 Divergent:
[Their contribution]

🟢 Convergent:
[Their contribution]

🔴 Critical:
[Their contribution]

============================================================
Round 2: 3 contribution(s)
============================================================
[...continues...]

============================================================
✨ Discussion complete with 7 total contributions
This represents a truly collaborative multi-perspective analysis.
============================================================
```

## Benefits

### 1. More Natural Collaboration
- Agents build on each other's ideas
- Challenges and refinements happen organically
- More realistic team discussion

### 2. Higher Quality Outputs
- Issues caught and addressed within discussion
- Recommendations refined iteratively
- More nuanced final answers

### 3. Transparent Process
- User sees the thinking process
- Can understand how conclusion was reached
- More trustworthy than black-box output

### 4. Efficient
- Agents can pass when done
- No wasted rounds on redundant info
- Early termination if consensus reached

## Performance Considerations

### Token Usage
- **Per round**: ~3 agent responses @ ~200 tokens each = 600 tokens
- **3 rounds**: ~1,800 tokens for responses
- **Plus prompts**: ~500 tokens/agent/round with discussion history
- **Total**: ~3,000-4,000 tokens for typical discussion

### Time
- **Per agent response**: 2-5 seconds (depending on model)
- **Per round**: 6-15 seconds (3 agents)
- **3 rounds**: 18-45 seconds total

### Optimization Tips
1. **Reduce rounds**: 2 rounds often sufficient for simple questions
2. **Smaller model**: Use faster models for specialists (7B vs 70B)
3. **Parallel execution**: Future enhancement - agents respond simultaneously
4. **Smart termination**: Detect early consensus automatically

## Configuration Tuning

### For Quick Responses:
```yaml
consensus:
  discussion_rounds: 2  # Fewer rounds
```

### For Thorough Analysis:
```yaml
consensus:
  discussion_rounds: 5  # More rounds, deeper exploration
```

### For Cost Optimization:
```yaml
consensus:
  discussion_rounds: 1  # Single round (essentially old behavior)
```

## Troubleshooting

### Discussion takes too long
- Reduce `discussion_rounds` in config
- Use smaller/faster model
- Check Ollama performance

### Agents repeating themselves
- Prompts emphasize "NEW" contributions
- Agents should pass when nothing new
- May indicate prompt tuning needed

### Not enough depth
- Increase `discussion_rounds`
- Check agent prompts encourage elaboration
- Ensure agents aren't passing too early

## Future Enhancements

1. **Parallel rounds**: All agents respond simultaneously per round
2. **Smart termination**: Auto-detect when discussion is complete
3. **Voting system**: Agents vote on consensus
4. **Specialized roles**: Domain-specific agents join discussion
5. **Real-time streaming**: User sees contributions as they happen
6. **Agent interruption**: Agents can interject out of turn
7. **Sub-discussions**: Agents can have side conversations

## Testing

### Test the collaborative discussion:

```bash
queenbee
```

```
You: specialists on
You: What are the trade-offs between REST and GraphQL?

# Watch the multi-round discussion unfold
```

### Verify in database:

```sql
SELECT 
    id, 
    status,
    jsonb_pretty(result::jsonb) as discussion
FROM tasks 
WHERE session_id = '<your_session_id>'
ORDER BY created_at DESC 
LIMIT 1;
```

Look for:
- `rounds` array with multiple rounds
- `full_discussion` with all contributions
- Each contribution has `agent`, `round`, `content`

### Check logs:

```
[Worker] Round 1/3
[Worker] Divergent contributed in round 1
[Worker] Convergent contributed in round 1
[Worker] Critical contributed in round 1
[Worker] Round 2/3
[Worker] Divergent contributed in round 2
...
[Worker] Task <id> completed successfully after 3 rounds
```

## Comparison: Before vs After

### Before (Linear Pipeline)
```
User: "Compare X vs Y"
→ Divergent generates 5 perspectives (blind to others)
→ Convergent synthesizes (only sees perspectives)
→ Critical validates (only sees synthesis)
→ Done (no refinement possible)
```

**Issues:**
- No interaction between agents
- Can't address each other's points
- Missed opportunities for refinement
- Less natural collaboration

### After (Iterative Discussion)
```
User: "Compare X vs Y"
→ Round 1: All agents share initial thoughts
→ Round 2: Agents respond to each other
  - Divergent adds angle Critical mentioned
  - Convergent refines based on new info
  - Critical validates improved solution
→ Round 3: Final refinements or passes
→ Done (collaborative consensus)
```

**Benefits:**
- Natural back-and-forth
- Ideas build on each other
- Issues addressed in discussion
- Higher quality output

## Code Changes

### Files Modified:
1. `src/queenbee/workers/manager.py`:
   - Replaced `process_task()` with iterative logic
   - Added `_run_collaborative_discussion()`
   - Added `_get_agent_response()`
   - Added prompt builders for each agent type

2. `src/queenbee/agents/queen.py`:
   - Added `_format_discussion_results()`
   - Updated `_format_specialist_results()` to detect format
   - Updated task creation to include `max_rounds`

3. `config.yaml`:
   - Added `consensus.discussion_rounds`

### New Methods:
- `_run_collaborative_discussion()` - Main discussion loop
- `_get_agent_response()` - Get response from specific agent
- `_format_discussion()` - Format history for agents
- `_build_divergent_prompt()` - Build Divergent-specific prompt
- `_build_convergent_prompt()` - Build Convergent-specific prompt
- `_build_critical_prompt()` - Build Critical-specific prompt
- `_format_discussion_results()` - Format discussion for user

## Summary

The iterative collaborative discussion system transforms QueenBee from a pipeline of isolated agents into a **true collaborative team** where specialists:

✅ Respond to each other's points
✅ Build on shared insights
✅ Challenge and refine ideas
✅ Reach consensus through discussion
✅ Produce higher quality, more nuanced answers

This makes QueenBee's multi-agent collaboration feel more natural and produce more thoughtful results! 🐝✨
