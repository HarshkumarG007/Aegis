# The MAANG Engineer Journal: V2.7 Controlled Gate Calibration

## Background
Following the revelations of V2.6—that the conflict gate was erroneously flagging conditional evidence as contradictions—we executed V2.7 to attempt to recover utility. We restructured the Conflict Gate to first extract explicit conditional qualifiers (version, time, scope) using an NLI compatibility pass, theoretically allowing the LLM to process and synthesize conditional evidence without being prematurely blocked by the gate. We paired this with a threshold sweep to relax the Sufficiency Gate (lowering from 5.25 to 4.25).

## Factorial Experiment Results

We executed a 2x2 Factorial Experiment to causally isolate the effect of the Sufficiency sweep (A -> B) vs the Conflict Classifier redesign (A -> C) on Mistral-7B:

| Arm | Description | Answerable PASS | True Contradiction Merge (95% CI) |
|---|---|---|---|
| A | Sufficiency 5.25 / Conflict Current | 28% (5/18) | 50% [19%, 81%] |
| B | Sufficiency 4.25 / Conflict Current | 33% (6/18) | 50% [19%, 81%] |
| C | Sufficiency 5.25 / Conflict Conditional | 28% (5/18) | 50% [19%, 81%] |
| D | Sufficiency 4.25 / Conflict Conditional | 33% (6/18) | 50% [19%, 81%] |

### Causal Deltas
| Contrast | What it estimates | Answerable Queries Recovered |
|---|---|---|
| B − A | Sufficiency intervention | +1 |
| C − A | Conditional-conflict intervention | +0 |
| D − B | Incremental conflict effect after sufficiency calibration | +0 |
| D − A | Combined V2.7 effect | +1 |

## Conclusion: A Causal Null Result
V2.7 provided a stark negative result. Lowering the sufficiency threshold only yielded 1 additional PASS. More importantly, our architectural intervention for the Conflict Classifier (C-A and D-B) yielded exactly +0 recoveries. 

The underlying problem was discovered in the logs: the zero-shot NLI compatibility tester (DeBERTa-v3) essentially acts as a random number generator when asked to infer compatibility of complex enterprise-specific conditions. Its failure to correctly verify conditional compatibility acts as a hard bottleneck.

The takeaway for V2.8 is clear: we cannot rely on NLI models to zero-shot conditional compatibility. We must shift to deterministic, structural condition extraction (E0/E1) and construct explicit logic to handle conditional intersections.
