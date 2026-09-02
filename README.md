# Aegis-Eval: The Evolution of Adversarial RAG Evaluation 🛡️

Aegis-Eval is a rigorous, open-source evaluation framework designed to test Retrieval-Augmented Generation (RAG) pipelines against deterministic, type-matched adversarial attacks. 

We are pushing the boundaries of scientific benchmarking. Instead of relying on unreliable self-grading "LLM-as-a-judge" patterns, Aegis-Eval pairs generation-time adversarial query classification with decoupled, non-LLM gating mechanisms (NLI cross-encoders, groundedness bounds, and exact-match safety checks).

---

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

---

## 📂 Repository Git Tree

```text
Aegis/
├── docs/
│   ├── JOURNAL_V2.3_Llama3_Pilot.md    # The story of escaping 8GB VRAM limits
│   ├── JOURNAL_V2.4_Hardened_RAG.md    # The discovery of the "Compulsion to Merge/Stitch"
│   └── JOURNAL_V2.4.1_Calibration.md   # The pristine Holdout results & tradeoff discovery
├── experiments/
│   └── v2.3/llama3-8b/
│       └── experiment.json             # Immutable hashes and runtime config
├── reports/
│   ├── benchmark-v2.2.0/               # V2.2 adversarial query manifests
│   └── run-<uuid>/                     # Evaluated run artifacts and SQLite metrics
├── scripts/
│   └── aegis_cli.py                    # Unified CLI (generate, evaluate, leaderboard)
└── src/
    └── aegis_eval/
        ├── data/                       # Manifest structures and DB schemas
        ├── evaluator/                  # NLI Cross-encoders, Aggregators, Metrics
        ├── hardened_rag/               # V2.4 Evidence & Verification Gates
        └── targets/                    # Multi-Model target integration contracts
```

---

## 📚 Essential Reading (The Aegis Lore)

- [📖 **The MAANG Engineer Journal: V2.4.1 Calibration & Control**](docs/JOURNAL_V2.4.1_Calibration.md)
  *The pristine Holdout execution. How deterministic abstention eradicated hallucinations entirely, but collapsed utility.*
- [📖 **The MAANG Engineer Journal: V2.4 Hardened RAG & Externalizing Policy**](docs/JOURNAL_V2.4_Hardened_RAG.md)
  *How we conquered the Compulsion to Merge and Stitch by ripping grounding out of the LLM and putting it into discrete NLI gates!*
- [📖 **The MAANG Engineer Journal: V2.3 Llama 3 Pilot**](docs/JOURNAL_V2.3_Llama3_Pilot.md) 
  *Discover the technical battle against GPU OOMs and the fascinating scientific differential between 1.5B and 8B models!*
- [🚀 **Release Notes**](RELEASE_NOTES.md)
  *The formal, meticulous changelog of our relentless march toward benchmarking perfection.*
- [📈 **Progress & Roadmap**](PROGRESS.md)
  *Where we've been, what we've conquered, and the grand vision of where we're going next.*

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
