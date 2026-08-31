# Aegis-Eval: Adversarial RAG Evaluation Harness

Aegis-Eval is an evaluation framework designed to test Retrieval-Augmented Generation (RAG) pipelines against deterministic, type-matched checks. Instead of relying on self-grading LLM judges, Aegis-Eval pairs generation-time adversarial query classification with non-LLM gating mechanisms (NLI cross-encoders, groundedness bounds, and multi-chunk coverage checks).

## Architecture

```text
Adversary (Local GGUF) ──> Target RAG ──> Evaluator Dispatcher
│
┌──────────────────────────────┼──────────────────────────────┐
▼                              ▼                              ▼
[Contradiction: NLI]            [Out-of-Domain: Cosine]        [Multi-Hop: Source Spread]
```

- **Adversary Model**: Local `qwen2.5-1.5b-instruct` / `Qwen3-1.7B` running via GGUF.
- **Evaluator Dispatcher**: Routes queries to deterministic gating checks by attack category.
- **Informational Metrics**: BERTScore and ROUGE-L are collected for diagnostic logging but are strictly prohibited from gating pass/fail decisions.

---

## Empirical Benchmark Results

All metrics below are drawn directly from committed validation runs (`reports/reference_validation.json` and `reports/independent_validation.json`).

| Attack Type | Evaluator Mechanism | Phase 6 Catch Rate (Reference Target) | Phase 7 Catch Rate (LlamaIndex Target) | Primary Failure Mode Observed |
| :--- | :--- | :--- | :--- | :--- |
| **Contradiction** | DeBERTa-v3-small NLI | **90.0%** (0.90) | **100.0%** (1.00) | Single-chunk retrieval bias; model accepted outdated source facts without cross-referencing. |
| **Out-of-Domain** | Claim Groundedness (Cosine Sim) | **50.0%** (0.50) | **60.0%** (0.60) | Parametric hallucination; target answered confidently from pre-training weights instead of abstaining. |
| **Multi-Hop** | Source Spread / Chunk Synthesis | **50.0%** (0.50) | **100.0%** (1.00) | Single-source isolation; target failed to synthesize across multiple retrieved nodes. |
| **Ambiguous** | Ambiguity / Hedging Marker Match | **50.0%** (0.50) | **0.0%** (0.00)* | *Evaluator Heuristic Failure: GGML daemon crash returned `Error`, which tripped substring token matches (`or`). |

---

## Key Findings & Generalization Gap

1. **The Single-Chunk Retrieval Fallacy**: The independent LlamaIndex target suffered a 100% catch rate on multi-hop queries. Standard similarity-based top-k retrieval frequently surfaced the dominant chunk while failing to force multi-node synthesis during answer generation.
2. **Parametric Leakage Over Abstention**: Out-of-domain queries triggered confident, hallucinated answers 60% of the time, demonstrating that default RAG system prompts fail to enforce groundedness constraints when documents do not contain the answer.
3. **The Danger of Surface Heuristics**: The Ambiguous check anomaly (0.0% catch rate) demonstrates why heuristic pattern matching requires strict tokenization/word boundaries. An unhandled `GGML_ASSERT` crash emitted `Error`, satisfying a loose `"or"` substring filter.

---

## Integration Contract

Every target under test must expose retrieved chunk IDs to enable deterministic verification:

```python
def validate_target_contract(response: dict) -> None:
    if not response.get("retrieved_chunk_ids"):
        raise IntegrationError(
            "Target RAG did not return retrieved_chunk_ids. "
            "Aegis-Eval cannot evaluate a black-box system with no retrieval evidence."
        )
```

---

## Quickstart

### 1. Environment Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Or .\.venv\Scripts\Activate.ps1 on Windows
pip install -e ".[dev]"
```

### 2. Run Database Migrations

```bash
set DATABASE_URL="postgresql://postgres:password@localhost:5433/postgres"
python scripts/init_db.py
```

### 3. Execute Reference Suite

```bash
python scripts/run_evaluation.py --target reference --report reports/reference_validation.json
```
