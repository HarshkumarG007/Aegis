# v1.0.0 — Architecture Audit & Deviations

A direct audit against `AegisEval_Architecture.md` and `AegisEval_Agent_Implementation_Spec.md` confirms that the finalized Aegis-Eval implementation satisfies the project's core mandates: deterministic non-LLM evaluation mechanisms, local-only execution within the 8 GB hardware constraint, type-aware evaluator dispatch, and the two-stage reference/independent validation methodology.

Several implementation decisions evolved from the original design during validation. These are documented below for transparency.

## 1. Adversary Model Pin

**Original design:** The architecture considered moving from the original Qwen2.5-1.5B model to a newer small Qwen variant, subject to local hardware constraints.

**Final implementation:** Aegis-Eval uses `qwen2.5-1.5b-instruct-q4_k_m.gguf`.

The model fit comfortably within the local hardware budget and successfully generated the required adversarial query suite. No newer model was required to satisfy the Phase 2 generation objectives, so the tested Qwen2.5 model was retained as the reproducible release pin.

This is a documented model-selection deviation, not an evaluator dependency: the adversary generates test inputs but does not determine evaluation verdicts.

## 2. Deterministic Node IDs and the Integration Contract

**Original design:** The multi-hop evaluator relied on target-provided `retrieved_chunk_ids` to establish evidence spread across multiple source chunks.

**Implementation evolution:** LlamaIndex's ordinary document ingestion can assign generated identifiers that are unsuitable for a deterministic cross-system evaluation contract. The independent target therefore constructs explicit `TextNode` objects and assigns stable identifiers corresponding to the Phase 1 corpus (`chunk-001` through `chunk-007`).

This preserves the target integration contract:

```text
query
  → retrieval
  → source_nodes
  → stable retrieved_chunk_ids
  → deterministic evaluator
```

The identifiers are not used to manufacture evaluator outcomes; they provide stable provenance metadata so that the evaluator can determine which corpus chunks were actually returned.

## 3. Orchestration and API Topology

**Original design:** The architecture proposed a central FastAPI orchestration layer exposing run-management endpoints.

**Final implementation:** Evaluation orchestration is performed by `scripts/run_evaluation.py`. The independent RAG target remains an isolated FastAPI service, while the evaluator runner communicates with that service, persists results to PostgreSQL, and writes validation reports.

This is an architectural simplification intended to improve reproducibility and CI/CD operation. It does not alter the evaluator mechanisms or their thresholds.

The resulting topology is:

```text
                    ┌─────────────────────┐
                    │  Adversary / Query  │
                    │      Generator      │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │  Evaluation Runner  │
                    │ run_evaluation.py   │
                    └──────────┬──────────┘
                               │ HTTP
                               ▼
                    ┌─────────────────────┐
                    │ Independent RAG     │
                    │ FastAPI / LlamaIndex│
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Deterministic       │
                    │ Evaluator Dispatcher│
                    └──────────┬──────────┘
                               │
                 ┌─────────────┼─────────────┐
                 ▼             ▼             ▼
              NLI /         Groundedness   Coverage /
           Contradiction                   Ambiguity
                               │
                               ▼
                    ┌─────────────────────┐
                    │ PostgreSQL + JSON   │
                    │ Validation Reports  │
                    └─────────────────────┘
```

## 4. Strict Infrastructure Error Boundary

The original integration contract primarily protected against malformed target responses and missing `retrieved_chunk_ids`.

During Phase 7, an additional failure mode was discovered: an infrastructure failure could return error text to a semantic evaluator. A lexical ambiguity check could then incorrectly interpret that text as a legitimate semantic response.

The final implementation therefore introduces an explicit target-response status boundary:

```text
SUCCESS
TIMEOUT
HTTP_ERROR
DAEMON_CRASH
MALFORMED
```

Only `SUCCESS` responses enter the semantic evaluation path.

Infrastructure failures are recorded as operational failures and are never converted into semantic pass/fail verdicts.

This change is considered an integrity improvement rather than merely a cosmetic architectural deviation.

## 5. Reference Calibration vs. Independent Validation

The Phase 6 `ReferenceTarget` was deliberately constructed to exercise the evaluator mechanisms and establish a controlled baseline. Its resulting distribution is therefore a **calibration result**, not evidence that the evaluator has universal accuracy.

Phase 7 uses an independently implemented LlamaIndex/FastAPI target with the same semantic corpus and frozen adversarial suite. Its results are consequently treated as the independent generalization measurement.

The two stages serve different purposes:

```text
Phase 6
Reference target
     ↓
Mechanism calibration / controlled validation

Phase 7
Independent target
     ↓
Generalization / external-behavior validation
```

The independent target is not expected to reproduce the Phase 6 percentages.

## 6. Core Methodological Constraint

Aegis-Eval intentionally does not use an LLM-as-a-judge mechanism for gating.

LLMs may participate in:

* adversarial query generation;
* target-side answer generation.

They do **not** determine whether a target answer passes evaluation.

The final gating path is deterministic and consists of the configured evaluator mechanisms:

* NLI contradiction detection;
* groundedness/similarity analysis;
* multi-chunk coverage;
* deterministic ambiguity analysis.

This separation is the central methodological property of Aegis-Eval.

## Release Assessment

The finalized implementation should therefore be understood as a **documented evolution of the original architecture**, rather than a byte-for-byte implementation of every initial proposal.

The important invariants remain intact:

* local execution;
* 8 GB hardware constraint;
* deterministic semantic gating;
* explicit attack-type dispatch;
* stable target integration contract;
* infrastructure/semantic error separation;
* frozen thresholds during independent validation;
* reference calibration separated from independent validation;
* no LLM-as-a-judge gating.

These properties form the basis for the `v1.0.0` release.
