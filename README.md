# Aegis-Eval: Adversarial RAG Evaluation Harness

Aegis-Eval is an evaluation framework designed to test Retrieval-Augmented Generation (RAG) pipelines against deterministic, type-matched checks. Instead of relying on self-grading LLM judges, Aegis-Eval pairs generation-time adversarial query classification with non-LLM gating mechanisms (NLI cross-encoders, groundedness bounds, and multi-chunk coverage checks).

## V2.2 Architecture & Engineering

```text
Adversary Model ──> Target RAG ──> Immutable JSON Bundle ──> Evaluator Dispatcher
(Qwen 1.5B)                                                        │
┌───────────────────────────────┬──────────────────────────────────┴──┐
▼                               ▼                                     ▼
[Contradiction: NLI / Exact]    [Out-of-Domain: Cosine/Entail]        [Multi-Hop: Source Spread]
```

Aegis-Eval V2.2 completely separates target interaction from semantic evaluation, providing a mathematically rigorous and offline-replayable benchmark suite.

### Key Engineering Decisions & Problem Solving

1. **Deterministic Byte-for-Byte Replay:** By separating the target generation phase from the evaluation phase and introducing composite `(run_id, query_id)` primary keys, we can perfectly replay and re-evaluate identical answers offline without hitting the target again.
2. **Hardening Contradiction against NLI Hallucination:** During V2.2 calibration, we found that the 1.5B DeBERTa NLI cross-encoder was producing false-positive entailments when the target's output had high lexical overlap with the adversarial claim, capping our Positive Calibration gate at 88.3%. 
   * **Solution:** We patched the evaluator to perform a strict `normalize_text` exact substring match against the `expected_truth` and `expected_claims` before falling back to NLI. This solved the semantic limitation, reliably bypassing the NLI bottleneck and driving Positive Calibration to 98.3% without weakening negative detection (which remained at 0.0%).
3. **Infrastructure / Semantic Separation:** Queries that time out or trigger infrastructure failures (like HTTP 500s) are intercepted by the orchestrator and immediately scored as `TIMEOUT` or `ERROR`. They bypass semantic evaluation entirely, ensuring semantic catch rates remain mathematically pure.
4. **Preserving "Mixed" Intent:** Mixed queries deterministically reconstruct exactly as `mixed` during replay, preserving the original adversarial intent rather than silently falling back to `out_of_domain`.

---

## V2.2.0-beta.1 Final Sign-off Metrics

Before independent evaluation can occur, the evaluator is gated against known-positive (perfect behavior) and known-negative (adversarial capitulation) fixtures to prove its mathematical boundaries. 

### Calibration Verification (Evaluator Soundness)
| Configuration         | Pass Rate | Required Bound | Status |
| --------------------- | --------: | -------------: | :----: |
| Positive Target       | **98.3%** | >95%           |   ✅    |
| Negative Target       |  **0.0%** | <20%           |   ✅    |
| Mixed Target          | **48.3%** | between bounds |   ✅    |

*(Note: Pre-fix calibration pass rates were Positive 88.3%, Mixed 43.3% before the exact-match semantic hardening)*

### Independent Baseline Results (Qwen 1.5B Target)
Once calibration was locked, the final 60-query benchmark was executed against `independent_target.py`:

| Metric | Result | Analysis |
| :--- | :--- | :--- |
| **Overall Pass Rate** | **46.7%** | The baseline capability of the 1.5B model against the V2.2 adversarial corpus. |
| **Multi-Hop** | 91.7% | Strongest mechanism. The target successfully synthesized multiple chunk parameters. |
| **Out of Domain** | 66.7% | The target occasionally hallucinated parametric knowledge instead of safely abstaining. |
| **Ambiguous** | 33.3% | The target often collapsed multiple valid interpretations into a single answer. |
| **Contradiction** | 16.7% | Weakest mechanism. The target consistently capitulated to adversarial constraints. |

---

## Documentation & Proof of Work
- **Release Notes:** [RELEASE_NOTES.md](RELEASE_NOTES.md)
- **Progress Log:** [PROGRESS.md](PROGRESS.md)
- **Detailed V2.2 Report:** [v2.2_benchmark_report.md](v2.2_benchmark_report.md) (Stored in Artifacts / CI)

---

## Integration Contract

Every target under test must expose retrieved chunk IDs to enable deterministic verification. Infrastructure timeouts will be caught cleanly and bypassed by the evaluator.

```python
def validate_target_contract(response: dict) -> None:
    if not response.get("retrieved_chunk_ids"):
        raise IntegrationError("Target RAG did not return retrieved_chunk_ids.")
```

---

## CLI Usage (V2.2)

Aegis-Eval now operates via a unified CLI (`scripts/aegis_cli.py`) leveraging local SQLite for self-contained persistence.

### 1. Environment Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

### 2. Run Benchmark against a Target

```powershell
# Set database to local SQLite
$env:DATABASE_URL="sqlite:///aegis_eval.db"

# Evaluate the local target
python scripts/aegis_cli.py run --target http://127.0.0.1:8000/query --queries reports/benchmark-v2.2.0/adversarial-v2.2.0.json
```

### 3. Generate Reports

```powershell
python scripts/aegis_cli.py report <run_id>
```
