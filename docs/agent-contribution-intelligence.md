# Agent Contribution Intelligence System

## Overview

The QueenBee multi-agent system now uses intelligent decision-making to determine when agents should contribute to discussions. This prevents redundant contributions, reduces noise, and ensures agents only speak when they can add genuine value.

## Key Improvements

### 1. Relevance-Based Participation

Agents now assess whether their expertise is actually relevant before contributing:

- **Keyword Matching**: Each agent has domain-specific keywords that indicate when their expertise applies
- **Question Analysis**: Agents check if the original question relates to their domain
- **Discussion Context**: Agents monitor if recent discussion touches on their expertise area

**Example**: UserProxy won't jump into a purely technical architecture debate unless user impact is being discussed.

### 2. Strategic Timing

Agents contribute at the right stage of discussion:

- **Early Discussion (< 6 contributions)**: Core agents (Divergent, Convergent, Critical) establish foundation
- **Mid Discussion (6-12 contributions)**: Support agents (Pragmatist, UserProxy, Quantifier) add specialized perspectives when needed
- **Late Discussion (12+ contributions)**: Very selective - discussion should converge, not expand

### 3. Anti-Spam Protections

Multiple safeguards prevent agent domination:

- **No Consecutive Contributions**: Agents can't contribute twice in a row
- **No Recent Domination**: Agents can't appear in 2 of last 3 contributions
- **Contribution Limits**: Max 3 contributions per agent per discussion
- **Late-Stage Cutoff**: After 12 contributions, new contributions are rare

### 4. Quality Over Quantity

Agents explicitly check if they can add NEW value:

```python
# From agent prompts:
"Respond with [PASS] if:
- You would just be repeating what others already said
- Your perspective is already well-covered
- No new insights come to mind"
```

## Agent Roles & Contribution Triggers

### Core Agents (Always Participate Early)

**Divergent** - Contributes when:
- Options or alternatives are missing
- Assumptions need challenging
- Edge cases haven't been explored
- Fresh perspectives are absent

**Convergent** - Contributes when:
- Multiple options need evaluation
- Scattered ideas need synthesis
- Execution plan is missing
- Trade-offs need explicit acknowledgment

**Critical** - Contributes when:
- Critical risks are overlooked
- Significant flaws exist in reasoning
- Dangerous assumptions are unchallenged
- Safety/validation is missing

### Support Agents (Contribute When Expertise Needed)

**Pragmatist** - Contributes when:
- Feasibility hasn't been assessed
- Resource constraints are ignored
- Discussion is too theoretical
- Implementation reality-check needed

**UserProxy** - Contributes when:
- User impact is missing from discussion
- Technical complexity doesn't serve users
- UX/accessibility concerns overlooked
- Need to ground in user reality

**Quantifier** - Contributes when:
- Vague claims need quantification
- Decisions lack data/metrics
- Comparisons need concrete numbers
- Cost/benefit analysis would help

## Technical Implementation

### Manager-Level Logic

```python
def _should_agent_contribute(agent_name, discussion, user_input, contribution_count):
    # First check: relevance
    if not _is_agent_expertise_relevant(agent_name, user_input, discussion):
        return False
    
    # Second check: timing and anti-spam
    if _would_dominate_discussion(agent_name, discussion):
        return False
    
    # Third check: discussion stage
    if len(discussion) >= 12:  # Late stage
        return False
    
    return True
```

### Prompt-Level Guidance

Each agent prompt now includes explicit "When to Contribute" and "Stay SILENT" sections:

```markdown
## When to Contribute

**ONLY contribute when:**
- [Specific conditions where expertise adds value]

**Stay SILENT (respond with [PASS]) if:**
- [Conditions where contribution would be redundant]
```

## Benefits

### Before Improvements

- All agents tried to contribute regardless of relevance
- Discussions became verbose with repetitive insights
- Hard to identify signal from noise
- Late-stage discussions expanded instead of converging

### After Improvements

- **Focused Discussions**: Only relevant agents participate
- **Better Signal/Noise**: Each contribution adds genuine value
- **Natural Convergence**: Discussions naturally conclude when synthesis is reached
- **Faster Resolution**: Fewer redundant contributions = quicker answers
- **Resource Efficiency**: Less token usage, lower API costs

## Example: Before vs After

### Before (All Agents Always Contribute)

```
Question: "What's the best way to cache API responses?"

Divergent: Here are 5 caching options... [relevant]
Convergent: I recommend Redis because... [relevant]
Critical: Watch out for cache invalidation... [relevant]
Pragmatist: Redis is feasible with our stack... [somewhat relevant]
UserProxy: Users want fast responses... [generic, not adding value]
Quantifier: Redis handles 100K ops/sec... [relevant]
Divergent: Also consider CDN caching... [some new value]
Convergent: Updated recommendation... [clarifying]
UserProxy: Users won't notice 50ms difference... [repetitive]
Pragmatist: Implementation will take 2 days... [minor detail]
```

Result: 10 contributions, some redundant

### After (Intelligent Contribution)

```
Question: "What's the best way to cache API responses?"

Divergent: Here are 5 caching options... [first, relevant]
Convergent: I recommend Redis because... [synthesis needed]
Critical: Watch out for cache invalidation... [risk identified]
Quantifier: Redis handles 100K ops/sec vs Memcached 50K... [data clarifies choice]
Pragmatist: [PASS] - Redis is already feasible
UserProxy: [PASS] - no user-specific concerns here
Divergent: [PASS] - options well-covered
Convergent: Final recommendation with cache invalidation strategy... [incorporating feedback]
```

Result: 5 contributions, all valuable

## Configuration

Contribution intelligence is configured in `config.yaml`:

```yaml
consensus:
  discussion_rounds: 3  # Max rounds before forcing conclusion
  specialist_timeout_seconds: 300  # Max time for discussion
```

Hard-coded limits in `manager.py`:
- Max contributions per agent: 3
- Late-stage cutoff: 12 total contributions
- Anti-domination window: last 3 contributions

## Testing

Test coverage includes:

- `test_should_agent_contribute_first_time`: First contribution behavior
- `test_should_agent_contribute_prevents_consecutive`: Anti-spam logic
- `test_should_agent_contribute_max_contributions`: Contribution limits
- `test_is_agent_expertise_relevant`: Keyword-based relevance
- `test_is_contribution_needed`: Stage-based participation

## Future Enhancements

Potential improvements:

1. **LLM-Based Relevance**: Use lightweight LLM to assess relevance vs keyword matching
2. **Dynamic Limits**: Adjust contribution limits based on discussion complexity
3. **Agent Voting**: Agents vote on whether discussion needs more input
4. **Confidence Scoring**: Agents indicate confidence level, affecting participation threshold
5. **Learning from History**: Track which agent contributions were most valuable, adjust participation accordingly

## Monitoring

Track contribution patterns:

```python
# Log contribution decisions
logger.info(f"{agent_name} contribution decision: {should_contribute}")
logger.debug(f"Relevance: {is_relevant}, Count: {contribution_count}, Stage: {len(discussion)}")
```

Metrics to monitor:
- Average contributions per discussion
- Agent utilization (% of discussions where agent contributes)
- [PASS] rate per agent
- Discussion length distribution

## Conclusion

The intelligent contribution system transforms QueenBee from a "everyone always speaks" model to a "speak when you have value to add" model. This results in:

- **More focused discussions**
- **Better user experience** (faster, clearer answers)
- **Lower costs** (fewer LLM calls)
- **Higher quality** (every contribution matters)

The system balances thorough multi-perspective analysis with efficient, signal-focused communication.
