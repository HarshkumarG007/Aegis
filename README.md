# Aegis-Eval: The Evolution of Adversarial RAG Evaluation 🛡️

Aegis-Eval is a rigorous, open-source evaluation framework designed to test Retrieval-Augmented Generation (RAG) pipelines against deterministic, type-matched adversarial attacks.

We are pushing the boundaries of scientific benchmarking. Instead of relying on unreliable self-grading "LLM-as-a-judge" patterns, Aegis-Eval pairs generation-time adversarial query classification with decoupled, non-LLM gating mechanisms (NLI cross-encoders, groundedness bounds, and exact-match safety checks).

## 🚀 The Aegis Journey (Evolution & Architectures)

### V1: The Foundation
*The beginning of adversarial generation and basic matching.*
```text
Adversary Model ──> Target RAG ──> Exact Match Evaluator
(Generates query)                      (String inclusion)
```
- **Metrics**: Positive Calibration: ~60%. Negative Detection: ~80%.
- **The Problem**: Exact string matching is far too brittle for abstract concepts, leading to false negatives.

### V2.2: The Deterministic Leap
*Decoupling target interactions and hardening the NLI semantic evaluator.*
```text
Adversary Model ──> Target RAG ──> Immutable JSON Bundle ──> Evaluator Dispatcher
(Qwen 1.5B)                                                        │
┌───────────────────────────────┬──────────────────────────────────┴──┐
▼                               ▼                                     ▼
[Contradiction: NLI / Exact]    [Out-of-Domain: Cosine/Entail]        [Multi-Hop: Source Spread]
```
- **Metrics**: Positive Calibration: **98.3%**. Negative Detection: **0.0%** (zero capitulation). 
- **The Breakthrough**: Patched the DeBERTa NLI cross-encoder with strict `normalize_text` exact substring fallbacks. This solved the semantic bottleneck, driving positive calibration to near 100% and providing mathematically sound evaluation bounds.

### V2.3: The Offline Multi-Model Scientific Pilot
*Busting the memory wall. Decoupling generation from evaluation for mathematically provable provenance.*
```text
Llama 3 8B (GPU) ──> Raw Responses ──> Immutable JSON (SHA-256)
                           │
                           ▼ (Offline & Independent)
DeBERTa-v3 (CPU) <── Evaluator Dispatcher <── Manifest Hash
```
- **The Breakthrough**: Bypassed Uvicorn/FastAPI threading instabilities and 8GB VRAM contention constraints via a completely offline architecture.
- **The Discovery**: Llama 3 8B handles Contradictions **+25.0%** better than Qwen 1.5B, but suffers a **-25.0%** regression in Out-of-Domain robustness due to "confident hallucination" and parametric leakage.

### V2.4: Hardened RAG Pipeline (Externalized Grounding Policy)
*Separating model capability from grounding policy. Turning opaque hallucinations into explicit, tunable gate states.*
```text
                         Query + Evidence
                                │
                                ▼
                        ┌───────────────┐
                        │ Evidence Gate │ (MS-MARCO + NLI)
                        └───────┬───────┘
                                │
                    ┌───────────┼───────────┐
                    ▼           ▼           ▼
               INSUFFICIENT  CONFLICT   SUFFICIENT
                    │           │           │
                 ABSTAIN    constrained   grounded
                            generation    generation
                                │           │
                                └─────┬─────┘
                                      ▼
                              ┌────────────┐
                              │  Verifier  │ (DeBERTa-v3)
                              └─────┬──────┘
                                    │
                               PASS/REJECT
```
- **The Breakthrough**: By intercepting queries with NLI Cross-Encoders *before* and *after* the LLM, we successfully reduced OOD fabrications significantly, shifting silent generation failures into measurable, observable gate decisions.
- **The Discovery**: The ablation revealed that detecting a conflict (23%) doesn't mean a 7B LLM can safely resolve it (0% improvement in contradiction). The generator's "Compulsion to Merge" is stronger than prompting constraints.
- **The Focus**: Next up is V2.4.1 (Calibration), where we redesign the conflict state to be deterministic and introduce a claim-level repair loop.

### V2.4.1: Calibration & Control
*The pristine Holdout execution. Eradicating hallucinations through deterministic abstention.*
- **The Breakthrough**: By replacing generative conflict resolution with a rigid deterministic policy, we neutralized the "Compulsion to Stitch" and hit 100% OOD safety with 0% Contradiction merging.
- **The Tradeoff**: Answerable preservation collapsed to 10-15%. The rigid Verifier became the new boundary, forcing us to explore asymmetric repair.

### V2.5: Asymmetric Verifier & Set-Level Sufficiency
*Recovering utility without compromising the pristine safety boundary.*
```text
Generator ──> Claim Extraction ──> Asymmetric Repair Loop
                                     ├─ SUPPORTED
                                     ├─ PARTIAL ──> Retry
                                     └─ CONTRADICTED ──> Drop
```
- **The Breakthrough**: Replaced binary chunk-level sufficiency with holistic Set-Level evaluation and introduced claim-level repair. 
- **The Discovery**: While 100% safety was maintained, utility recovery was minimal. We discovered a massive "False Abstention" bottleneck where the LLM refused to answer despite sufficient evidence.

### V2.6: Causal Diagnosis & Gate Attribution
*An Oracle ablation study that isolated the False Abstention bottleneck.*
- **The Discovery**: Bypassing the Sufficiency Gate recovered 85% of blocked answerable queries, proving it was severely over-conservative. Furthermore, the Conflict Gate was misinterpreting conditional ambiguity as flat contradiction.

### V2.7: Controlled Gate Calibration
*A controlled factorial experiment that yielded a causal null result.*
- **The Discovery**: We attempted to use NLI (DeBERTa-v3) to zero-shot conditional compatibility (e.g., version mismatches). The causal delta was exactly +0. NLI models act as random-number generators for complex enterprise conditional logic.
- **The Focus**: This null result forced a hard pivot away from zero-shot NLI toward deterministic structural extraction.

### V2.8: Structured Conditional Evidence
*Rescuing utility from the NLI bottleneck via structural extraction.*
```text
Evidence A & B ──> Syntactic Extractor (E0) ──> Deterministic Policy
                          │                           │
                   [Condition: v1]             [Mutually Exclusive]
                   [Condition: v2] ──────────> CONDITIONAL_COMPATIBILITY
```
- **The Breakthrough**: Explicitly extracting version/time/role conditions and matching them deterministically recovered utility (up to 33.3%) while perfectly maintaining 0% OOD leakage. We proved rules are safer and more capable than NLI for conditionality.

### V2.9: Adversarial Safety Generalization
*Stress-testing the conditional logic against 220 false-conditionality traps.*
```text
Syntactic Span Stripping ──> Proposition Binding ──> NLI Verification
(Extracts "For legacy")      (Isolates claim)        (Checks core conflict)
```
- **The Breakthrough**: Re-architected the extractor into a "Proposition-Bound" architecture. By safely isolating clauses and verifying core propositions via NLI before comparing conditions, we completely solved the ambiguity crisis.
- **The Tradeoff**: Reduced uncertain fallbacks from 81 to 25 while explicitly maintaining a perfect 0-tolerance boundary for false-compatible merges (0/160 breaches).

---

## 📂 Repository Git Tree

```text
Aegis/
├── docs/
│   ├── JOURNAL_V1_The_Foundation.md          # The brittle exact-match evaluator
│   ├── JOURNAL_V2.1_Benchmark_Infrastructure.md # Immutable artifacts & offline replay
│   ├── JOURNAL_V2.2_Deterministic_Leap.md    # Hardened NLI & 98.3% positive calibration
│   ├── JOURNAL_V2.3_Llama3_Pilot.md          # The story of escaping 8GB VRAM limits
│   ├── JOURNAL_V2.4_Hardened_RAG.md          # The discovery of the "Compulsion to Merge/Stitch"
│   ├── JOURNAL_V2.4.1_Calibration.md         # The pristine Holdout results & tradeoff discovery
│   ├── JOURNAL_V2.5_Scientific_Validation.md # Asymmetric verifier & the false abstention crisis
│   ├── JOURNAL_V2.6_Causal_Diagnosis.md      # Oracle ablation & gate attribution
│   ├── JOURNAL_V2.7_Conflict_Classifier.md   # The NLI conditional reasoning null result
│   ├── JOURNAL_V2.8_Structured_Conflict.md   # Syntactic extraction rescuing utility
│   └── JOURNAL_V2.9_Adversarial_Safety.md    # Proposition-bound extraction crushing ambiguity
├── experiments/
│   └── v2.3/llama3-8b/
│       └── experiment.json                   # Immutable hashes and runtime config
├── reports/
│   ├── benchmark-v2.2.0/                     # V2.2 adversarial query manifests
│   └── run-<uuid>/                           # Evaluated run artifacts and SQLite metrics
├── scripts/
│   └── aegis_cli.py                          # Unified CLI (generate, evaluate, leaderboard)
└── src/
    └── aegis_eval/
        ├── data/                             # Manifest structures and DB schemas
        ├── evaluator/                        # NLI Cross-encoders, Aggregators, Metrics
        ├── hardened_rag/                     # Evidence Gates & Verification mechanisms
        └── targets/                          # Multi-Model target integration contracts
```

---

## 📚 Essential Reading (The Aegis Lore)

- [📖 **The MAANG Engineer Journal: V2.9 Adversarial Safety Generalization**](docs/JOURNAL_V2.9_Adversarial_Safety.md)
  *Stress-testing the new conditional logic against 220 false-conditionality traps. We introduce 'Proposition-Bound' architecture (E+E0) to crush ambiguity and perfectly maintain our 0-tolerance safety boundary.*
- [📖 **The MAANG Engineer Journal: V2.8 Structured Conditional Evidence**](docs/JOURNAL_V2.8_Structured_Conflict.md)
  *How explicitly structuring conditional overlap rescued utility from the NLI bottleneck. We prove mathematically that deterministic extraction is safer and more capable than zero-shot NLI for conditional compatibility.*
- [📖 **The MAANG Engineer Journal: V2.7 Controlled Gate Calibration**](docs/JOURNAL_V2.7_Conflict_Classifier.md)
  *A controlled factorial experiment that yielded a causal null result. Proving that NLI cannot zero-shot complex conditional compatibility, forcing our pivot to structural extraction.*
- [📖 **The MAANG Engineer Journal: V2.6 Causal Diagnosis**](docs/JOURNAL_V2.6_Causal_Diagnosis.md)
  *An Oracle ablation study that isolated the False Abstention bottleneck, proving the Sufficiency Gate was over-conservative and the Conflict Gate was misinterpreting ambiguity.*
- [📖 **The MAANG Engineer Journal: V2.5 Asymmetric Verifier & Set-Level Sufficiency**](docs/JOURNAL_V2.5_Scientific_Validation.md)
  *How we introduced claim-level repair and set-level sufficiency to recover utility, and the surprising discovery of the False Abstention bottleneck.*
- [📖 **The MAANG Engineer Journal: V2.4.1 Calibration & Control**](docs/JOURNAL_V2.4.1_Calibration.md)
  *The pristine Holdout execution. How deterministic abstention eradicated hallucinations entirely, but collapsed utility.*
- [📖 **The MAANG Engineer Journal: V2.4 Hardened RAG & Externalizing Policy**](docs/JOURNAL_V2.4_Hardened_RAG.md)
  *How we conquered the Compulsion to Merge and Stitch by ripping grounding out of the LLM and putting it into discrete NLI gates!*
- [📖 **The MAANG Engineer Journal: V2.3 Llama 3 Pilot**](docs/JOURNAL_V2.3_Llama3_Pilot.md) 
  *Discover the technical battle against GPU OOMs and the fascinating scientific differential between 1.5B and 8B models!*
- [📖 **The MAANG Engineer Journal: V2.2 The Deterministic Leap**](docs/JOURNAL_V2.2_Deterministic_Leap.md)
  *Hardening the NLI semantic evaluator with exact-substring fallbacks to achieve 98.3% positive calibration and 0.0% capitulation.*
- [📖 **The MAANG Engineer Journal: V2.1 Benchmark Infrastructure**](docs/JOURNAL_V2.1_Benchmark_Infrastructure.md)
  *The transition to reproducible, immutable JSON artifacts and byte-for-byte offline deterministic replay.*
- [📖 **The MAANG Engineer Journal: V1 The Foundation**](docs/JOURNAL_V1_The_Foundation.md)
  *Our initial attempt at adversarial benchmarking and the discovery of the severe brittleness of exact-match evaluators.*
- [🚀 **Release Notes**](RELEASE_NOTES.md)
  *The formal, meticulous changelog of our relentless march toward benchmarking perfection.*
- [📈 **Progress & Roadmap**](PROGRESS.md)
  *With V2.9 completing our gate safety optimizations, Aegis is now ready for V3.0: End-to-end bottleneck optimization!*

---

## 🛠️ Getting Started (V2.3 CLI)

Aegis-Eval now operates via a unified CLI (`scripts/aegis_cli.py`) leveraging local SQLite for self-contained persistence.

### 1. Environment Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

### 2. Run an Offline Multi-Model Evaluation

Generate the raw responses from a target (serializing them to an immutable artifact):
```powershell
python scripts/aegis_cli.py generate --target http://127.0.0.1:8000/query --output runs/my-model-generation.json
```

Evaluate the responses offline (using the decoupled NLI pipeline):
```powershell
$env:DATABASE_URL="sqlite:///aegis_eval.db"
python scripts/aegis_cli.py evaluate --responses runs/my-model-generation.json --queries reports/benchmark-v2.2.0/adversarial-v2.2.0.json
```

View the scientific Leaderboard (with exact provenance and differentials):
```powershell
python scripts/aegis_cli.py leaderboard --details
```
