# The MAANG Engineer Journal: V2.2 The Deterministic Leap

## Background
With the V2.1 benchmark infrastructure frozen and capable of byte-for-byte offline replay, we turned our attention back to the fatal flaw of V1: the brittle exact-match evaluator. We needed an evaluator that understood semantics but didn't hallucinate like an "LLM-as-a-judge".

V2.2 represents the "Deterministic Leap"—our successful integration of NLI (Natural Language Inference) Cross-Encoders as the core semantic engine.

## The V2.2 Architecture
Instead of exact string matching, we decoupled the evaluation into discrete mechanisms:
1. **Contradiction Evaluator (NLI + Exact Fallback)**
2. **Out-of-Domain Evaluator (Cosine Similarity / Entailment)**
3. **Multi-Hop Evaluator (Source Spread Tracking)**

We used the `DeBERTa-v3-small` NLI cross-encoder to evaluate the semantic relationship between the retrieved evidence and the LLM's claims. 

## The Breakthrough
During V2.2 testing, we discovered that while NLI was brilliant at semantics, it occasionally produced false positives on highly adversarial, identically-phrased contradictory claims. 

To solve this, we patched the DeBERTa NLI cross-encoder with strict `normalize_text` exact substring fallbacks. This hybrid approach—using NLI for semantic breadth and exact-matching as a strict boundary constraint—completely solved the semantic bottleneck.

## The Results
The V2.2 Release Candidate (evaluated against a Qwen 1.5B target) yielded unprecedented evaluator calibration:
- **Positive Calibration**: **98.3%**
- **Negative Detection**: **0.0%** (zero capitulation)

## The Takeaway
V2.2 proved that "LLM-as-a-judge" is entirely unnecessary for rigorous RAG evaluation. By chaining small, deterministic NLI cross-encoders with strict normalization fallbacks, we achieved near-perfect calibration and mathematically sound evaluation bounds. The evaluator was officially hardened.
