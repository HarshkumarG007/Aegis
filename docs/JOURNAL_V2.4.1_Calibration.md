# Aegis Engineering Journal: V2.4.1 Calibration & Control

*Authored by the Aegis Architecture Team*

## The Problem: Detection is Not Intervention

In V2.4, we successfully intercepted hallucination mechanisms by placing NLI and MS-MARCO gates around the generator. However, we discovered a fatal flaw: **Detection ≠ Intervention**.

When the Evidence Gate detected conflicting claims, we simply passed a constrained prompt to the generator ("Do not reconcile conflicting claims"). The result? The generator ignored us. The "Compulsion to Merge" alignment was so deep that Contradiction failures remained stubbornly flat.

Furthermore, our post-generation verifier was acting as a "binary guillotine." If a generator produced a beautiful 4-sentence answer, but one sentence hallucinated a minor detail, the entire answer was rejected.

## The Solution: V2.4.1 (Calibration and Deterministic Controllers)

We introduced three strictly deterministic protocols to the pipeline:

1. **Deterministic Abstention for Conflict:** No heuristics. No version inference. If DeBERTa detects a conflict in the retrieved evidence, the generator is completely bypassed, and the system issues a hard abstention.
2. **Claim-Level Verification & Repair:** We shifted the Verifier to score at the *claim* level. If a generation fails, the system executes exactly *one* repair regeneration. It strictly maps passing claims to their supporting evidence chunks, drops all other context, and forces a regeneration. 
3. **Multi-Objective Calibration:** We swept the MS-MARCO sufficiency threshold on a Dev Set to find the exact threshold (`1.0`) that maximized OOD rescue without inflicting unacceptable false-abstention collateral damage.

## The Pristine Holdout Evaluation

We froze the configuration and executed it against the untouched `adversarial-holdout.json` queries on both Mistral 7B and Llama 3 8B.

### The Successes: Total Safety
The architecture was a phenomenal success for safety:
* **OOD Silent Hallucinations: 0%** (Down from ~58% in V2.3). 100% of these were caught *immediately* by the MS-MARCO gate before a single token was generated, dropping median latency to 0.08 seconds.
* **Silent Contradiction Merging: 0%**. The deterministic conflict gate intervened in 80% of contradiction queries, safely stopping the generator from merging dangerous instructions.

### The Engineering Reality: Collapse of Utility
Safety came at an extreme cost. Answerable preservation collapsed.
* **False Abstention Rate:** 85% - 90%.
* **Repair Failure:** Mistral 7B failed 100% of its repairs. Llama 3 8B failed 87.5% of them. Even when constrained to only verified chunks, the generators still produced at least one claim that the rigid DeBERTa verifier rejected.

## Outcomes and V2.5 Decisions

V2.4.1 definitively proved that we can architecturally control hallucination mechanisms without needing a "smarter" LLM. The two generative failure mechanisms (Stitching and Merging) have been neutralized.

As we move toward **V2.5**, our roadmap is perfectly clear. The problem is no longer the generator. We must tune the verifier's rigidity (to stop rejecting valid repairs) and calibrate the retrieval sufficiency representations.
