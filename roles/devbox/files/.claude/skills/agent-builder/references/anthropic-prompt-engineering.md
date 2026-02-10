# Anthropic Prompt Engineering Reference

Cached reference from official Anthropic documentation (February 2026).
Sources:
- https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/overview
- https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/use-xml-tags
- https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/chain-of-thought
- https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/system-prompts

## Technique Impact Order (Most to Least)

1. **Be clear and direct** — explicit instructions like you would to a new employee
2. **Use examples (multishot)** — 3-5 diverse examples dramatically improve accuracy
3. **Let Claude think (CoT)** — for complex tasks requiring reasoning
4. **Use XML tags** — separate different parts of prompts for clarity
5. **Give Claude a role (system prompts)** — domain expert persona
6. **Chain complex prompts** — break down multi-step workflows
7. **Long context tips** — optimise for large context windows

## XML Tags

### Why Use XML Tags

- **Clarity**: Separate different parts of prompt
- **Accuracy**: Reduce errors from misinterpretation
- **Flexibility**: Easily modify parts without rewriting
- **Parseability**: Extract specific parts of response

### Best Practices

1. **Be consistent**: Use same tag names throughout; refer to them when discussing content
2. **Nest tags**: Use hierarchical structure for complex content

### Common Tag Patterns

```xml
<instructions>Step-by-step guidance</instructions>
<example>Sample input/output</example>
<document>
  <document_content>Full document text</document_content>
  <source>Document metadata</source>
</document>
<thinking>Claude's reasoning process</thinking>
<answer>Final response</answer>
```

**Key insight from Anthropic**: There are NO canonical "best" XML tags Claude has been trained with. Tag names should make sense with the information they surround.

### Power Pattern: XML + Multishot + CoT

```xml
<examples>
  <example>
    <input>...</input>
    <thinking>Step-by-step reasoning</thinking>
    <output>...</output>
  </example>
</examples>
```

## Chain of Thought (CoT)

### Three Complexity Levels

| Level | Approach | Structure |
|-------|----------|-----------|
| Basic | "Think step-by-step" | No guidance on HOW to think |
| Guided | Outline specific steps | Steps but no separation |
| Structured | XML tags (`<thinking>`, `<answer>`) | Easy parsing, separation |

### When to Use

- Complex math, logic, or analysis
- Multi-step reasoning
- Decisions with many factors
- Tasks where a human would need to think through

### When NOT to Use

- Simple tasks (adds latency)
- Not all tasks require in-depth thinking

**Critical rule**: Always have Claude OUTPUT its thinking. Without outputting, no thinking occurs.

## Clear and Direct Prompting

### Golden Rule

Show your prompt to a colleague with minimal context. If they're confused, Claude will be too.

### How to Be Clear

1. **Give contextual information**:
   - What the task results will be used for
   - What audience the output is meant for
   - What workflow the task belongs to
   - What success looks like

2. **Be specific about what you want**:
   - If you want only code, say so
   - Specify format, length, tone, style

3. **Provide instructions as sequential steps**:
   - Use numbered lists or bullet points
   - Ensures exact task execution

### Mental Model

Think of Claude as a brilliant but very new employee (with amnesia) who:
- Needs explicit instructions
- Has no context on norms, styles, or preferences
- Cannot infer unstated requirements

## Multishot Prompting (Examples)

### Effective Examples Must Be

- **Relevant**: Mirror actual use case
- **Diverse**: Cover edge cases; vary enough to avoid unintended patterns
- **Clear**: Wrapped in `<example>` tags (multiple in `<examples>`)

### Meta-tip

Ask Claude to evaluate your examples for relevance, diversity, or clarity. Or generate more examples from your initial set.

## System Prompts and Roles

### Benefits

- **Enhanced accuracy**: Significant boost in complex scenarios
- **Tailored tone**: Adjust communication style
- **Improved focus**: Stay within task-specific requirements

### Pro Tip

Experiment with roles. A "data scientist" sees different insights than a "marketing strategist". Specificity matters: "data scientist specialising in customer insight analysis for Fortune 500 companies" outperforms "data scientist".

## Implications for Agent Definitions

Agent markdown bodies ARE system prompts. Apply these principles:

1. **Role first**: Core identity paragraph establishes the persona
2. **XML tags for structure**: Use tags to separate workflow phases, validation steps, output formats
3. **Examples where ambiguous**: If a pattern is easy to get wrong, show the right way
4. **Be explicit about workflow**: Numbered steps, not vague "do good work"
5. **Context over rules**: Explain WHY, not just WHAT — Claude follows reasoning better than commands
6. **Calibrate strength**: Reserve CRITICAL/FORBIDDEN for genuine zero-tolerance items
