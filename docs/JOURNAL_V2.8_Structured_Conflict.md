# The MAANG Engineer Journal: V2.8 Structured Conditional Evidence

## Background

In V2.7, we discovered that while separating contradiction detection from compatibility inference was architecturally safe, the NLI model (DeBERTa-v3) lacked the zero-shot reasoning required to recognize conditionally compatible claims. Its failure to approve compatible evidence (0/45 recall) forced the deterministic conflict policy to overwhelmingly reject valid, conditionally qualified information.

V2.8 tests whether explicitly extracting underlying conditions from the evidence—and structuring the deterministic policy around those extracted conditions—can recover utility without sacrificing safety.

## Methodology

We introduced a three-stage conflict resolution pipeline:
1. **Contradiction Trigger**: Standard NLI assesses raw contradiction. If high, we proceed to conflict analysis.
2. **Condition Extraction**: We tested two extraction strategies:
   - **E0**: Deterministic, Regex/Rules-based (extracting version, dates, lifecycle, roles).
   - **E1**: LLM Information Extraction (Mistral-7B guided by JSON schema).
3. **Deterministic Compatibility Policy**: If conditions exist and are explicitly mutually exclusive (e.g., `version="v1"` vs `version="v2"`), they are declared `CONDITIONAL_COMPATIBILITY`. If conditions are missing or cannot be differentiated, they fall back to `UNCERTAIN` or `CONTRADICTION`.

## Classifier Ablation

We evaluated the classifiers on the V2.8 Diagnostic Set (60 pairs):

| Classifier             | Contra Merge Rate | Compat Recall (Correct) | Compat Uncertain |
|------------------------|-------------------|-------------------------|------------------|
| A (Current)            | 0/15              | 0/45                    | 0/45             |
| B (V2.7 NLI)           | 0/15              | 0/45                    | 11/45            |
| C+E0 (Rules Only)      | 0/15              | 10/45                   | 1/45             |
| D+E0 (Rules + NLI)     | 0/15              | 0/45                    | 11/45            |

**Extractor Performance (E0 vs E1)**
Mistral-7B (E1) frequently failed to adhere to the rigid JSON extraction schema zero-shot, resulting in high parsing errors and falling back to E0. E0, meanwhile, achieved 83% accuracy and a **0% hallucinated condition rate**.

**Conclusion**: Classifier C + Extractor E0 is the clear winner. It achieved perfect safety (0 false merges) while successfully recalling 10/45 conditionally compatible pairs. Furthermore, adding NLI on top of explicit rule checking (Classifier D) *destroyed* the recall, confirming the NLI model as the bottleneck for compatibility logic.

## Safety Validation

Before scaling up, we validated the new `4.25` individual sufficiency threshold on a 10-query adversarial out-of-domain challenge set.
- **OOD Leakage at 4.25**: 0 observed leakage (0/10 queries successfully blocked by the gate). Note that this does not establish a universal 0% leakage guarantee, but is consistent with the safety boundary.

## Factorial Experiment Results

We executed a 2x2 Factorial Experiment on the independent challenge set using Mistral-7B:
- **Arm A**: 5.25 Sufficiency / Current Classifier A
- **Arm B**: 4.25 Sufficiency / Current Classifier A
- **Arm C**: 5.25 Sufficiency / Structured Classifier C+E0
- **Arm D**: 4.25 Sufficiency / Structured Classifier C+E0

### Attribution Matrix

| Metric                | Arm A (5.25 + Old Gate) | Arm B (4.25 + Old Gate) | Arm C (5.25 + New Gate) | Arm D (4.25 + New Gate) |
|-----------------------|-------------------------|-------------------------|-------------------------|-------------------------|
| Answerable Retained   | 5/24 (20.8%)            | 5/24 (20.8%)            | 7/24 (29.2%)            | 8/24 (33.3%)            |
| OOD Leakage           | 0/6 (0.0%)              | 0/6 (0.0%)              | 0/6 (0.0%)              | 0/6 (0.0%)              |
| Gate Rejections       | 20                      | 19                      | 17                      | 14                      |
| Gen Abstentions       | 5                       | 6                       | 6                       | 8                       |

## Takeaways

1. **The Interaction Effect**: Arm B proved that lowering the sufficiency threshold *alone* (from 5.25 to 4.25) did not improve utility (20.8% -> 20.8%) because the Old Conflict Gate continued to erroneously reject the newly retrieved chunks.
2. **The Rescue**: Arm C proved that swapping to the New Structured Gate at the same strict threshold (5.25) recovered utility (20.8% -> 29.2%).
3. **The Synergistic Frontier**: When we combined the relaxed threshold with the new gate (Arm D), utility jumped to 33.3%, unlocking chunks that were previously blocked by *both* the sufficiency threshold and the naive contradiction detector!
4. **Observed Safety Boundary**: No true contradiction was merged in the evaluated diagnostic (0/15) or challenge examples (0/6 OOD leakage). This establishes 0 observed false-compatible merges in our frozen sets, though it does not guarantee a universal 0% error rate.

V2.8 successfully recovers utility by shifting the bottleneck from the black-box NLI model to explicit, deterministic evidence structures.
