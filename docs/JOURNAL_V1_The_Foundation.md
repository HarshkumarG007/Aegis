# The MAANG Engineer Journal: V1 The Foundation

## Background
The Aegis-Eval journey began with a simple but critical observation: relying on opaque "LLM-as-a-judge" patterns to evaluate RAG systems is fundamentally unscientific. When an LLM grades another LLM, the evaluation degrades into a chaotic mix of sycophancy, positional bias, and unrepeatable vibes. 

V1 was our initial attempt to build a strict, adversarial evaluation framework.

## The V1 Architecture
The V1 architecture was straightforward:
1. **Adversary Generation**: We used a smaller model to dynamically generate queries designed to attack specific failure vectors (Contradiction, Out-of-Domain, Multi-Hop, Ambiguity).
2. **Target Interaction**: The generated queries were fired at the Target RAG pipeline.
3. **Exact Match Evaluator**: We evaluated the Target's response using strict exact string inclusion. If the target was supposed to abstain, we checked for the exact presence of abstinence keywords.

## The Results
The initial results were mixed but illuminating:
- **Positive Calibration**: ~60%
- **Negative Detection**: ~80%

## The Problem
While V1 proved that generating targeted adversarial attacks was highly effective, the evaluation mechanism was a bottleneck. Exact string matching is far too brittle for abstract concepts. If the model responded with "The system does not support this" instead of our hardcoded "I don't know", the evaluator threw a false negative.

## The Takeaway
V1 proved the necessity of adversarial benchmarking, but it taught us a hard lesson: we need a semantic evaluator that is as robust as an LLM, but as deterministic and auditable as code. This realization paved the way for V2.
