# The MAANG Engineer Journal: V2.1 Benchmark Infrastructure

## Background
After the brittleness of V1's exact-match evaluator became apparent, we realized that before we could build a better semantic evaluator, we needed bulletproof infrastructure. V2.1 marks the transition of Aegis-Eval from a simple deterministic evaluation script into a rigorous, reproducible, target-agnostic adversarial RAG benchmark harness.

## The Engineering Leap
We established a completely isolated execution and reporting pipeline to ensure that the evaluation instrument itself was scientifically sound.

### 1. Immutable Run Artifacts
Every executed run is now stored as an immutable structure linking the evaluation manifest, the adversarial queries, the target's raw responses, and the exact evaluation verdicts into a single JSON artifact bundle. 

### 2. Byte-for-Byte Offline Replay
We built a completely isolated replay mechanism that recalculates the local metrics directly from the raw data artifacts without ever hitting the target API again. Replays are 100% byte-for-byte deterministic. This was a massive engineering win, allowing us to rapidly iterate on the evaluator logic without spending hours regenerating LLM responses.

### 3. Infrastructure vs. Semantic Separation
Previously, if a target timed out or crashed, it polluted the semantic evaluation metrics. In V2.1, infrastructure failures (HTTP errors, timeouts, malformed JSON) instantly yield a verifiable target failure at the infrastructure layer, protecting the purity of the semantic evaluator.

## The Takeaway
V2.1 froze the benchmark infrastructure. With strict SQLite persistence, strict preflight checks, and immutable offline artifacts, Aegis was finally ready to host a true, hardened semantic evaluator.
