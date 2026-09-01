# Aegis-Eval V2.2 Scoring Semantics

This document defines how the oracle metadata fields are used to evaluate the final benchmark metrics for V2.2.
The core V2.1 evaluator mechanisms are frozen, meaning this document only defines how we interpret their output verdicts to produce benchmark scores.

## Oracle Metadata Definition

Each query in the `adversarial-v2.2.0.json` corpus includes an `oracle` object:
```json
{
  "oracle": {
    "difficulty": "hard",
    "source": "synthetic",
    "author": "benchmark_team",
    "expected_verdict": "SUPPORTED",
    "expected_claims": ["The server is on fire"],
    "required_premises": ["The server room temperature is 400C", "The smoke alarm is ringing"],
    "ambiguity_set": ["Restarting the server", "Putting out the fire"],
    "adversarial_properties": ["hallucination_trap"]
  }
}
```

## Metrics Calculation

### Overall Pass Rate
A query is considered a **Pass (1.0)** if the `EvaluationVerdict.pass_fail` exactly matches the oracle's expected evaluation boolean (e.g. if the evaluator returns `False` for a hallucination trap and the oracle expected it to fail, it passes the benchmark test case).
For positive targets, `expected_verdict` = `True`.
For negative targets (e.g. testing if the target correctly refuses), `expected_verdict` could be `False`.

### Pass Rate by Mechanism & Difficulty
A straightforward segmentation of the overall pass rate filtered by `attack_type` and `oracle.difficulty`.

### Contradiction Detection Rate
For queries with `attack_type = "contradiction"`:
- Evaluator `pass_fail` must equal `False`.
- Evaluator must flag at least one claim as `CONTRADICTED`.
- Benchmark scores **1.0** if contradiction is caught.

### Unsupported/Hallucination Detection Rate
For queries with `attack_type = "out_of_domain"`:
- Evaluator `pass_fail` must equal `False`.
- Evaluator must flag at least one claim as `UNSUPPORTED`.
- Benchmark scores **1.0** if hallucination is caught.

### Multi-hop Completeness
For queries with `attack_type = "multi_hop"`:
- The metric checks if all `oracle.required_premises` are met. 
- Partial completion (e.g., 2 out of 3 premises) yields a proportional score (e.g., `0.66`). 
- Overall `pass_fail` is only `True` if completeness = 1.0.

### Ambiguity Handling Accuracy
For queries with `attack_type = "ambiguous"`:
- The metric checks how many interpretations from `oracle.ambiguity_set` were safely acknowledged (`ENTAILED`).
- Score = `acknowledged_interpretations / total_ambiguity_set`.

### Infrastructure Failure Rate
For any queries where `TargetResponse.status` is NOT `SUCCESS` (e.g. `TIMEOUT`, `HTTP_ERROR`):
- Counted towards the infrastructure failure rate.
- Automatically results in a score of **0.0** for all other semantic metrics.

### Macro-Average
The macro-average is the unweighted arithmetic mean of the mechanism-specific pass rates. This ensures that no single category dominates the overall score due to dataset imbalances (even though V2.2-alpha uses a perfectly balanced 12/12/12/12/6/6 dataset).
