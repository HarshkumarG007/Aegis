# The MAANG Engineer Journal: V2.5 Asymmetric Verifier & Set-Level Sufficiency

**Date:** 2026-09-02
**Phase:** V2.5 Scientific Validation

## The Utility Crisis

In V2.4.1, we achieved something remarkable: by interposing deterministic NLI gates (MS-MARCO and DeBERTa) around the LLM, we achieved 100% Out-Of-Domain (OOD) interception and completely eradicated the LLM's "Compulsion to Merge" conflicting facts. 

However, this pristine safety came at a terrible cost. The rigid, binary chunk-level sufficiency heuristic and the answer-level verifier rejected almost everything. Answerable query retention collapsed to 10-15%. The pipeline was safe, but virtually useless.

The mandate for V2.5 was clear: **Recover utility without giving back an inch of safety.**

## The V2.5 Architecture

We implemented two fundamental architectural shifts to soften the pipeline's rigidity:

### 1. Set-Level Sufficiency
Instead of demanding that *one single chunk* independently cross an NLI threshold, we concatenated the top-k retrieved chunks and ran the `ms-marco-MiniLM` cross-encoder over the *entire context*. This allowed facts spanning multiple chunks to cross the threshold collectively, maintaining strict mathematical boundaries while acknowledging the holistic nature of RAG contexts.

We pre-registered a calibration protocol on the Dev Set, constraining the threshold selection to the exact point where OOD leakage hit zero. The resulting optimal threshold was **5.25**.

### 2. Asymmetric Claim-Level Repair
We completely overhauled the post-generation verifier. Instead of rejecting the entire answer if a single hallucinated word slipped through, the verifier now extracts the answer into atomic claims, runs NLI against each claim independently, and returns a granular state (`SUPPORTED`, `UNSUPPORTED`, `CONTRADICTED`, `UNCERTAIN`).

We then fed this granular state back into the generator via a "Claim-Level Repair" loop, forcing the model to rewrite its answer preserving only the `SUPPORTED` claims while stripping out the `UNSUPPORTED` or `CONTRADICTED` ones.

## The Challenge Set Results

We generated a fresh, independent 30-query Challenge Set across all five benchmark vectors (OOD, Contradiction, Multi-hop, Ambiguity, Safe Infrastructure) and ran a strict 6-Arm Ablation Matrix (Arms A–F) against Mistral 7B and Llama 3 8B.

**The Safety Boundary Held**
The 5.25 Set-Level Sufficiency threshold perfectly defended the perimeter. OOD Rescue remained at **100%** on both models. Zero leakage.

**The Utility Bottleneck Remained**
Despite the elegant Claim-Level Repair loop and the sophisticated Set-Level Sufficiency evaluation, utility barely moved:
- **Mistral 7B** retained only **22%** of answerable queries.
- **Llama 3 8B** retained only **17%** of answerable queries.

The primary failure mode was **False Abstention** (rates of 72% - 78%). The pipeline is still heavily over-abstaining on genuinely answerable queries. 

## The Causal Diagnosis Mandate

The V2.5 results provided a profound scientific insight: adding more sophisticated heuristics (like claim-level repair) to the verification layer does not magically restore utility if the bottleneck lies elsewhere in the causal chain.

For V2.6, we must stop guessing. Before we write another line of heuristic code, we must construct a Gate Attribution Matrix to determine exactly *why* answerable queries are failing. Is the Retrieval layer failing to fetch the right facts? Is the Set-Level Sufficiency gate still too conservative? Or is the Generator natively self-abstaining even when given perfect, verified facts?

V2.6 will be a causal diagnosis release. We will force the pipeline to tell us where it is broken.
