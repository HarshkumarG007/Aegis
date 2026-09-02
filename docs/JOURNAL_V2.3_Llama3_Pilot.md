# Aegis-Eval V2.3: The Multi-Model Pilot (MAANG Elite Engineer Journal)

## The Vision & The Goal

As Aegis-Eval scales from a single-model validation tool into a rigorous scientific benchmark for adversarial RAG, the architecture needed a fundamental upgrade. V2.3 was born out of the necessity to answer a core scientific question: **Does increasing model capability actually solve adversarial RAG failure modes?**

To answer this, we needed a robust architecture that could decouple LLM generation from evaluation, allowing us to test frontier models (like Llama 3 8B) under identical benchmark conditions to our Qwen 1.5B baseline. The goal was to establish mathematical provenance (SHA-256 hashes of models, manifests, and artifacts) so that every leaderboard entry is a reproducible, immutable scientific observation.

## The Hard Problem (Failures & Roadblocks)

Engineering in a constrained environment (an 8GB VRAM RTX 4060 laptop) pushed us into hard architectural walls almost immediately:

1. **The Memory Wall**: Initially, the `aegis run` command attempted to host the target LLM in `uvicorn` while concurrently instantiating the semantic evaluator (DeBERTa-v3). This concurrent execution exceeded the 8GB VRAM + System RAM constraints, causing silent OS-level `WinError 10054` (Connection Reset) kills.
2. **The Thread-Safety Trap**: To bypass the VRAM limit, we attempted canonical CPU execution. However, `llama-cpp-python` exhibited severe instability when embedded inside a threaded `FastAPI` endpoint. The target successfully returned a `200 OK` response for the first query, but immediately crashed/segfaulted during garbage collection or subsequent requests. 

The traditional "live target" architecture (where the benchmark actively pings a standing model) proved fragile for large, local quantized models running on consumer hardware.

## The Elite Engineering Solution (Success)

We abandoned the brittle concurrent architecture in favor of a robust **Offline Evaluation Pipeline**.

1. **Decoupling Generation**: We implemented an `aegis generate` command that bypasses the HTTP layer entirely for local execution. It runs a single-threaded, highly stable inference loop that offloads all 33 layers (`n_gpu_layers=-1`) of Llama 3 8B to the RTX 4060. 
2. **Immutable Artifacts**: The generation loop serializes the raw, un-scored responses into an immutable JSON artifact.
3. **Decoupled Evaluation**: The `aegis evaluate` command loads the JSON artifact, hashes it for strict provenance (`3df41cc57...`), and pipes it through the NLI evaluator. Since the LLM is no longer in memory, the DeBERTa evaluator runs freely without contention.

This guarantees that we can audit the raw 8B responses exactly as they were generated, decoupling execution from measurement.

## Scientific Discovery & Analysis

With the architecture stabilized, we ran the full 60-query adversarial manifest. The comparison between our baseline (Qwen 1.5B) and the pilot (Llama 3 8B) yielded fascinating differentials:

| Failure mode | Qwen 1.5B | Llama 3 8B | Δ |
| :--- | :--- | :--- | :--- |
| **Overall** | 46.7% | 51.7% | +5.0% |
| **Contradiction** | 16.7% | 41.7% | **+25.0%** |
| **Out-of-Domain (OOD)** | 66.7% | 41.7% | **-25.0%** |
| **Ambiguous** | 33.3% | 58.3% | **+25.0%** |
| **Multi-hop** | 91.7% | 83.3% | -8.4% |

### 1. Empirical Results

*   **Overall Accuracy**: Qwen (46.7%, 28/60) outperformed Llama 3 8B (51.7%, 31/60) and Mistral 7B (36.7%, 22/60). Capability does not strictly correlate with Aegis score.
*   **Contradiction Resilience**: Replicated improvement across both larger models. Qwen 16.7% (2/12) → Llama 41.7% (5/12) and Mistral 41.7% (5/12). (+25 percentage points / +3 queries).
*   **Out-of-Domain (OOD) Grounding**: Both larger models are below Qwen. Qwen 66.7% (8/12) → Llama 41.7% (5/12) and Mistral 50.0% (6/12).
*   **Ambiguity Resolution**: Not a general capability improvement. Llama 3 achieved 58.3% (7/12), but Mistral dropped to 0.0% (0/12).

### 2. Failure Taxonomy Analysis

The raw evidence reveals that the OOD degradation is primarily driven by:
*   **Unsupported Fabrication**: The model attempts to stitch together unrelated retrieved facts (e.g., assuming "billing system password" is the same as "database password") rather than refusing to answer.
*   **Evaluator Disagreement**: The strict evaluator penalizes correct synthesis.
*   The models consistently fail to recognize retrieval insufficiency, preferentially producing a plausible answer instead of a grounded refusal.

For contradictions, the models consistently attempt to **merge incompatible claims** by hallucinating reconciliations (e.g., treating conflicting facts as version history or injecting external context like "OpenAPI Petstore").

## Limitations

Each adversarial category currently contains 12 queries, meaning individual query outcomes can produce large changes in category-level percentages (approx. 8.3 percentage points per query). Additionally, this comparison involves different model families (Qwen vs Llama) rather than a controlled, intra-family parameter-scaling experiment. These results therefore establish an empirical model comparison under the Aegis protocol, rather than a causal estimate of parameter scaling.

## Run Provenance

This experiment was executed under the following strict conditions, documented in `experiments/v2.3/llama3-8b/experiment.json`:

* **Hardware**: RTX 4060 Laptop (8GB VRAM)
* **Model**: `Meta-Llama-3-8B-Instruct-Q4_K_M.gguf`
* **Model SHA-256**: `ab9e4eec7e80892fd78f74d9a15d0299f1e22121cea44efd68a7a02a3fe9a1da`
* **Manifest SHA-256**: `dd5b23101a6a61603c064491a179fc741b9310af4e3a1b5afae7097068cf985d`
* **Runtime**: `n_gpu_layers=-1`, `temperature=0.0`, Offline Generation Architecture
