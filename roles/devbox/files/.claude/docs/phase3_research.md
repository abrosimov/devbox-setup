# Phase 3: Research on Agent Architectures

## Metadata
| Field | Value |
|-------|-------|
| Created | 2025-12-05 |
| Status | Complete |
| Purpose | Research industry patterns and alternatives to inform improvements |

---

## Executive Summary

Research reveals your current architecture aligns with industry best practices in agent specialization, but has friction points that established patterns can solve. The key insight: **Claude Agent SDK already supports subagent orchestration natively** - you may be manually doing what the system can automate.

---

## 1. Industry Orchestration Patterns

### Pattern Comparison

| Pattern | Description | Pros | Cons | Your Current State |
|---------|-------------|------|------|-------------------|
| **Linear/Sequential** | Agents run in fixed order | Predictable, simple | Inflexible | ✓ This is you |
| **Graph-Based (LangGraph)** | Nodes + edges, conditional routing | Flexible, observable | Complex setup | Not used |
| **Role-Based (CrewAI)** | Agents as "team members" | Intuitive metaphor | Can be rigid | ✓ Conceptually similar |
| **Conversational (AutoGen)** | Agents as chat participants | Dynamic | Unpredictable | Not used |
| **Conductor/Orchestrator** | Meta-agent routes to specialists | Smart delegation | Single point of failure | Not used |

### Key Insight from LangChain
> "Orchestrating via code makes tasks more deterministic and predictable in terms of speed, cost, and performance."

Your approach of specialized agents is sound. The issue is **manual orchestration overhead**, not the architecture itself.

---

## 2. Claude Agent SDK Native Capabilities

### Subagent Support (Already Available!)

From [Anthropic's documentation](https://www.anthropic.com/engineering/building-agents-with-the-claude-agent-sdk):

> "Subagents are useful for two main reasons: First, they enable parallelization. Second, they help manage context: subagents use their own isolated context windows, and only send relevant information back to the orchestrator."

### Production Pattern Recommendation

From [Claude Agent SDK best practices](https://skywork.ai/blog/claude-agent-sdk-best-practices-ai-agents-2025/):

> "Give each subagent one job, and let an orchestrator coordinate. Chain subagents in pipelines for deterministic workflows (analyst → architect → implementer → tester → security audit)."

**This is exactly your workflow!** The SDK already supports:
- Subagent chaining
- Isolated context per agent
- Orchestrator coordination

### Your Agents as Subagents

Your current agents map directly to the recommended pattern:

```
Orchestrator (could be main Claude session or slash command)
    ├── TPM subagent (analyst)
    ├── Planner subagent (architect)
    ├── SE subagent (implementer)
    ├── Tests subagent (tester)
    └── Reviewer subagent (security audit equivalent)
```

---

## 3. Single-Agent vs Multi-Agent Tradeoffs

### When Single-Agent is Better

From [DigitalOcean research](https://www.digitalocean.com/resources/articles/single-agent-vs-multi-agent):

> "While the agent can delegate specific tasks by using tools, orchestration and conversation control stay with a single agent. This design removes communication and coordination overhead."

From [Cognition's contrarian view](https://cognition.ai/blog/dont-build-multi-agents):

> "Ensure your agent's every action is informed by the context of all relevant decisions made by other parts of the system."

**Implication for you**: Context loss between your agents is a known anti-pattern.

### When Multi-Agent is Better

From [WillowTree analysis](https://www.willowtreeapps.com/craft/multi-agent-ai-systems-when-to-expand):

> "Over time, as tasks become more complex and the number of tools grow larger, single-agent approaches become challenging. The agent gets confused on which tools to use."

**Implication for you**: Your complex tasks (TPM → Planner → SE → Tests → Reviewer) justify multi-agent. Your simple tasks (chat mode) correctly use single-agent.

### The Real Tradeoff

| Approach | Latency | Cost | Context | Debugging |
|----------|---------|------|---------|-----------|
| Single agent | Low | Low | Full | Easy |
| Multi-agent (sequential) | High (N calls) | High (N calls) | Lost between | Hard |
| Multi-agent (parallel) | Medium | High | Isolated | Harder |

**Your situation**: Sequential multi-agent with context loss. Worst of both worlds for medium tasks.

---

## 4. Known Failure Modes

### Relevant to Your Agents

| Failure Mode | Description | Risk in Your System |
|--------------|-------------|---------------------|
| **Instruction following degradation** | Long prompts cause instruction skipping | High (Reviewer is 700 lines) |
| **Context compression** | Important details lost in long contexts | Medium (agents don't share) |
| **Hallucination** | Confident incorrect output | Medium (code review helps) |
| **Looping** | Agents pass similar prompts repeatedly | Low (linear pipeline) |

### Mitigation Strategies Found

1. **Shorter, focused prompts** - Your Reviewer might benefit from simplification
2. **Layered defenses** - Your SE → Tests → Reviewer is good (multiple checks)
3. **Self-consistency** - Multiple agents reviewing same work catches errors

---

## 5. Alternative Architectures Considered

### Option A: Status Quo (Manual Orchestration)
```
User manually calls: SE → Tests → Reviewer
```
- **Pros**: Full control, works now
- **Cons**: Friction, context loss, user burden
- **Verdict**: Current pain point

### Option B: Slash Commands (Workflow Triggers)
```
/implement → runs SE
/test → runs Tests
/review → runs Reviewer
/full-cycle → runs SE → Tests → Reviewer automatically
```
- **Pros**: Easy invocation, memorable, can bundle
- **Cons**: Setup required, less flexible
- **Verdict**: ✓ Recommended for friction reduction

### Option C: Composite Agent (Merged Roles)
```
"implementer" = SE + Tests (one agent does both)
```
- **Pros**: Fewer transitions, preserved context
- **Cons**: Larger prompt, less specialization, harder to debug
- **Verdict**: Consider for medium tasks only

### Option D: Conductor Agent
```
User describes task → Conductor decides which agents to call
```
- **Pros**: Smart routing, handles complexity detection
- **Cons**: Added abstraction, conductor can make wrong choices
- **Verdict**: Overkill for your use case

### Option E: Enhanced Handoffs (Fix Current System)
```
Each agent explicitly reads previous output and suggests next step
```
- **Pros**: Minimal change, preserves specialization
- **Cons**: Still manual invocation (though guided)
- **Verdict**: ✓ Recommended as foundation

---

## 6. Research-Backed Recommendations

### Immediate (No Structural Changes)

1. **Add plan reading to SE** - Critical gap, easy fix
2. **Add "next step" prompts** - Reduces cognitive load on user
3. **Structured feedback format** - Enables feedback loop

### Short-Term (Slash Commands)

From Claude Code docs, custom slash commands can bundle workflows:

```markdown
# /commands/implement.md
Run the software-engineer-{lang} agent to implement the current task.
After implementation, suggest running /test.

# /commands/full-cycle.md
1. Run software-engineer-{lang}
2. Run unit-test-writer-{lang}
3. Run code-reviewer-{lang}
4. Report summary
```

### Medium-Term (Subagent Orchestration)

Leverage Claude Agent SDK's native subagent support:
- Main session acts as orchestrator
- Agents invoked as subagents with isolated context
- Results flow back to orchestrator

---

## 7. Key Insights for Your System

### What Research Validates

1. ✓ **Specialization is correct** - One job per agent is best practice
2. ✓ **Linear pipeline is valid** - For deterministic workflows
3. ✓ **Code review as final step** - Matches "security audit" pattern
4. ✓ **Separate test writing** - Enables bug-hunting mindset

### What Research Challenges

1. ❌ **Context loss** - Agents should read previous outputs
2. ❌ **Manual orchestration** - SDK supports automation
3. ❌ **No orchestrator** - Missing coordination layer
4. ⚠️ **Prompt length** - Reviewer may be too complex

### Paradigm Shift Suggestion

> **From**: 5 independent agents that user manually chains
> **To**: 5 subagents coordinated by orchestrator (slash command or main session)

This preserves your specialization while eliminating friction.

---

## Sources

### Multi-Agent Orchestration
- [LLM Orchestration Best Practices - orq.ai](https://orq.ai/blog/llm-orchestration)
- [Multi-agent LLMs in 2025 - SuperAnnotate](https://www.superannotate.com/blog/multi-agent-llms)
- [Agent Orchestration Patterns - Dynamiq](https://www.getdynamiq.ai/post/agent-orchestration-patterns-in-multi-agent-systems-linear-and-adaptive-approaches-with-dynamiq)
- [How and when to build multi-agent systems - LangChain](https://blog.langchain.com/how-and-when-to-build-multi-agent-systems/)

### Framework Comparisons
- [CrewAI vs LangGraph vs AutoGen - DataCamp](https://www.datacamp.com/tutorial/crewai-vs-langgraph-vs-autogen)
- [Technical Comparison of Frameworks - AI Plain English](https://ai.plainenglish.io/technical-comparison-of-autogen-crewai-langgraph-and-openai-swarm-1e4e9571d725)
- [Don't Build Multi-Agents - Cognition](https://cognition.ai/blog/dont-build-multi-agents)

### Claude Agent SDK
- [Building agents with Claude Agent SDK - Anthropic](https://www.anthropic.com/engineering/building-agents-with-the-claude-agent-sdk)
- [Subagents - Claude Code Docs](https://code.claude.com/docs/en/sub-agents)
- [Claude Agent SDK Best Practices - Skywork](https://skywork.ai/blog/claude-agent-sdk-best-practices-ai-agents-2025/)

### Single vs Multi-Agent
- [Single-Agent vs Multi-Agent Systems - DigitalOcean](https://www.digitalocean.com/resources/articles/single-agent-vs-multi-agent)
- [When to Expand From Single Agent - WillowTree](https://www.willowtreeapps.com/craft/multi-agent-ai-systems-when-to-expand)
- [Multi-Agent vs Single Agent - Kye Gomez](https://medium.com/@kyeg/multi-agent-vs-single-agent-a72713812b68)

### Failure Modes
- [LLM Hallucination Examples - Evidently AI](https://www.evidentlyai.com/blog/llm-hallucination-examples)
- [Field Guide to LLM Failure Modes - Adnan Masood](https://medium.com/@adnanmasood/a-field-guide-to-llm-failure-modes-5ffaeeb08e80)
- [LLMs Will Always Hallucinate - arXiv](https://arxiv.org/html/2409.05746v1)
