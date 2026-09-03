# V3.2 Factorial Capability Recovery

*Evaluating the G2 Semantic Contract vs. the V1 Deterministic Verifier.*

## The Problem
After implementing the deterministic safety boundary (V1 Verifier) in V3.1, our safety bounds seemed robust. However, this left the system's "answerable capability" in question. We needed to know: could we instruct the generator to safely recover capability without it aggressively hallucinating structural extensions under pressure?

We designed the **G2 Structured Synthesis Contract**, a set of instructions strictly telling the LLM:
- Answer if unconditional.
- State condition splits if mutually exclusive.
- Abstain if insufficient.
- **Never invent conditions or relationships.**

## The 2x2 Factorial Experiment
We executed a 2x2 factorial run using `Mistral-7B-Instruct-v0.2`:
- **Axes**: Instruction Set (G1 Baseline vs. G2 Contract) x Sufficiency Threshold (5.25 Strict vs. 4.25 Relaxed)
- **Pressure**: A newly introduced adversarial suite explicitly designed to bait the generator into making unsupported derived claims.

## The Results
The findings were illuminating and fundamentally validated a core architectural philosophy: **Generator obedience is not part of the safety argument.**

### 1. G2 Provided Zero Marginal Utility
At both strict and relaxed sufficiency thresholds, the `G2` instruction provided **no** statistical improvement in Answerable Success over the baseline `G1` instruction. 
- Thresh 5.25: Both G1 and G2 recovered 6/18.
- Thresh 4.25: Both G1 and G2 recovered 7/18.
The capability limit lies in the base model and the evidence threshold, not the instruction semantics.

### 2. The Generator Cannot Be Trusted
When subjected to the adversarial pressure suite, the 7B generator attempted to invent ungrounded dependencies exactly **3 out of 6 times** under *both* G1 and G2 instructions. It completely ignored the "Never invent conditions" mandate. 

### 3. V1 Intercepted All Observed Violations
Within this test suite, the `V1` verifier correctly intercepted and rejected 100% of these attempts (all 6/6 observed unsupported-derived-claim attempts across both arms). The architecture properly brackets the generator as a proposer, while V1 acts as a strict derivability engine.

## Note on Sample Size
We observed 0 failures in 12 safety-critical cases (6 OOD + 6 Contradiction). This does not establish a low population failure probability; it merely yields an upper bound of ~39%. To prove the boundary remains frozen, we must run a Frozen Safety Replay (V3.3-A) against our established suites (e.g., the 160 contradiction cases from V2.9).

## The Verdict
We definitively reject the hypothesis that a 7B generator can be constrained by semantics alone in a safety-critical environment. The overarching Aegis philosophy holds true: **"Generator capability may increase. Generator authority may not increase."** 
