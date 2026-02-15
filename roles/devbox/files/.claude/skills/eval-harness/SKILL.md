---
name: eval-harness
description: >
  Eval-Driven Development (EDD) framework for AI features. Triggers on: evals, evaluation, test harness, llm testing, capability testing.
---

# Eval-Driven Development

## Philosophy

Define evals before coding, like TDD but for AI features.

**Workflow**:
1. Write eval (expected input → output behaviour)
2. Implement feature
3. Run eval → iterate until passing
4. Regression suite for future changes

## Eval Types

### Capability Evals

"Can Claude do X?" — test new abilities.

**Example**: Can Claude extract structured data from unstructured text?

```python
{
    "input": "John Doe, 35, lives in London",
    "expected_output": {
        "name": "John Doe",
        "age": 35,
        "city": "London"
    }
}
```

**Use cases**:
- New feature development
- Prompt engineering experiments
- Model comparison (Sonnet vs Opus)

### Regression Evals

"Does change break Y?" — prevent regressions.

**Example**: After prompt change, ensure existing cases still work.

```python
{
    "id": "regression_email_extraction",
    "input": "Contact support@example.com for help",
    "expected_output": "support@example.com"
}
```

**Use cases**:
- CI pipeline (block PRs that break evals)
- Model upgrade validation
- Prompt change validation

## Grader Types

### Code-Based (Deterministic)

Fast, reliable, no API calls.

**Exact match**:
```python
def grade_exact_match(output: str, expected: str) -> bool:
    return output.strip() == expected.strip()
```

**Regex**:
```python
def grade_email_extraction(output: str) -> bool:
    return re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', output) is not None
```

**JSON schema validation**:
```python
def grade_json_schema(output: str, schema: dict) -> bool:
    try:
        data = json.loads(output)
        jsonschema.validate(data, schema)
        return True
    except (json.JSONDecodeError, jsonschema.ValidationError):
        return False
```

**When to use**:
- Structured output (JSON, CSV, specific format)
- Factual extraction (email, phone, URL)
- Classification tasks with known labels

### Model-Based (LLM Judge)

Use LLM to grade LLM output.

**Rubric scoring**:
```python
grading_prompt = """
Score the assistant's response on a scale of 1-5:

1 - Completely wrong or irrelevant
2 - Partially correct but missing key information
3 - Correct but lacking detail
4 - Correct and detailed
5 - Excellent, comprehensive, and insightful

User question: {input}
Assistant response: {output}

Score (1-5):
"""
```

**Pairwise comparison**:
```python
comparison_prompt = """
Which response is better?

Question: {input}

Response A: {output_a}
Response B: {output_b}

Answer with "A" or "B":
"""
```

**When to use**:
- Subjective quality (helpfulness, tone, clarity)
- Open-ended generation (essays, summaries, creative writing)
- Multi-dimensional scoring (accuracy + completeness + readability)

**Anti-patterns**:
- Using expensive model (Opus) for simple grading (use Haiku)
- No ground truth examples (LLM judges need context)
- Single-shot grading (use multiple samples for reliability)

### Human

Manual review for subjective quality.

**Process**:
1. Generate output on eval set
2. Randomise order (blind reviewer to A/B test)
3. Review with rubric
4. Aggregate scores

**When to use**:
- Safety and alignment (harmful content detection)
- Creative quality (story writing, humour)
- Final validation before launch

## Metrics

### pass@k

At least 1 of k attempts passes.

```python
def pass_at_k(outputs: list[str], grader: callable, k: int) -> bool:
    """Returns True if at least 1 of the first k outputs passes."""
    passing = sum(1 for output in outputs[:k] if grader(output))
    return passing >= 1
```

**Use case**: Tasks where multiple attempts are allowed (code generation, creative writing).

**Example**: pass@3 = 80% means 80% of eval cases had at least 1 passing output in 3 attempts.

### pass^k

All k attempts pass.

```python
def pass_all_k(outputs: list[str], grader: callable, k: int) -> bool:
    """Returns True if all k outputs pass."""
    passing = sum(1 for output in outputs[:k] if grader(output))
    return passing == k
```

**Use case**: Tasks requiring consistency (deterministic output, production reliability).

**Example**: pass^3 = 95% means 95% of eval cases had all 3 outputs passing.

### Accuracy

Standard classification metric.

```python
def accuracy(predictions: list, labels: list) -> float:
    correct = sum(1 for pred, label in zip(predictions, labels) if pred == label)
    return correct / len(labels)
```

## Eval Structure

```python
{
    "id": "unique_eval_id",
    "input": "The prompt or input to the model",
    "expected_output": "Expected response (optional, for exact match)",
    "metadata": {
        "category": "extraction",
        "difficulty": "easy",
        "tags": ["email", "regex"]
    },
    "grader": {
        "type": "code",  # or "model" or "human"
        "function": "grade_email_extraction"  # or grading_prompt
    }
}
```

## Decision Tree: Which Grader?

```
Is the output structured (JSON, CSV, specific format)?
  YES → Code-based (JSON schema, regex, exact match)
  NO ↓

Is there a single correct answer (factual extraction)?
  YES → Code-based (exact match, contains check)
  NO ↓

Is the task objective (classification, entity extraction)?
  YES → Code-based (label matching, F1 score)
  NO ↓

Is the output quality subjective (helpfulness, tone)?
  YES ↓

    Is ground truth available (gold standard responses)?
      YES → Model-based (rubric scoring with examples)
      NO ↓

    Is safety/alignment critical?
      YES → Human review
      NO → Model-based (pairwise comparison)
```

## Running Evals

### Baseline

Establish baseline performance before changes.

```bash
# Run evals on current prompt/model
python run_evals.py --model claude-sonnet-4-5 --output baseline.json

# Results: 85/100 passing (85% accuracy)
```

### Change

Make prompt/model/code change.

```bash
# Run evals on new version
python run_evals.py --model claude-opus-4-6 --output experiment.json

# Results: 92/100 passing (92% accuracy)
```

### Compare

```bash
# Compare results
python compare_evals.py baseline.json experiment.json

# Output:
# Overall: +7% improvement (85% → 92%)
# By category:
#   extraction: +5% (80% → 85%)
#   reasoning: +10% (90% → 100%)
# Regressions: 3 cases worse (see details)
```

## CI Integration

```yaml
# .github/workflows/evals.yml
name: Run Evals
on: [pull_request]

jobs:
  evals:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run evals
        run: python run_evals.py --threshold 0.95
      - name: Upload results
        uses: actions/upload-artifact@v3
        with:
          name: eval-results
          path: results.json
```

**Threshold policy**:
- Block PR if accuracy drops below 95%
- Allow minor regressions if overall improvement
- Flag new failures for manual review

## Best Practises

1. **Start small**: 10-20 evals before scaling to 100s
2. **Diverse cases**: edge cases, common cases, adversarial inputs
3. **Version control**: evals in git, track changes over time
4. **Fast feedback**: run subset locally, full suite in CI
5. **Monitor drift**: rerun evals after model updates (Claude 3.5 → 3.7)
6. **Document failures**: add failing cases to regression suite
