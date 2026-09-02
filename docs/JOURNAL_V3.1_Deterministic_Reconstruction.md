# The MAANG Engineer Journal: V3.1 Deterministic Reconstruction

## 1. The Observation: NLI as a Weak Trigger

In V3.0, we discovered that the raw-NLI trigger (`T0`) was a systemic point of failure. It operated under a dangerous assumption: that NLI models would safely flag contradictions even across differently-scoped conditional boundaries.

This proved false. Raw NLI answered "not contradictory" when two conditionally scoped propositions should have been rigorously examined, allowing contradictions to bypass the structural safety gate entirely. 

## 2. The Architectural Shift: Unconditional Structure First (`T1`)

To fix this, we eliminated the raw-NLI trigger. The new architecture (`T1`) requires unconditional structural parsing via `E0` for all retrieved chunks. 

Current Logic:
1. **Unconditional Parsing:** Parse all top-K retrieved chunks using `E0`.
2. **Deterministic Trigger:** If extracted condition graphs intersect on any condition variable, we trigger the rigorous conflict gate.
3. **Controlled Fallback:** Only if the conditions do not intersect do we allow a baseline semantic compatibility check.

## 3. Post-Generation Verifier: Eliminating the LLM (`V1`)

The generator may formulate language; it may not introduce relationships that cannot be reconstructed from the verified evidence graph.

In V3.0, our verification step relied on either an LLM-based structured reasoning prompt or a synthesized NLI meta-hypothesis (e.g. `nli.predict([ "The timeout depends on API version", claim ])`). Both approaches introduced probabilistic failure points into what should be a deterministic safety envelope.

We replaced this with a **Deterministic Derivability Check (`V1`)**:
- We use strict string matching heuristics and structural graph lookup.
- If a generated claim makes a meta-statement (e.g., "The timeout depends on API version"), the verifier checks if the extracted condition keys exactly match the `differentiators` identified by the conflict gate.
- It strictly rejects any unauthorized causal extensions (e.g., "because production traffic is higher").
- It falls back to full-context NLI *only* for non-meta logical comparisons (e.g., "Version 2 is longer").

## 4. The Results

**V3.1-A Trigger Ablation (`T0` vs `T1`)**
The `T1` unconditional parse perfectly intercepts the false-compatible merges that slipped through the `T0` raw NLI trigger. 

**V3.1-B Verifier Diagnostics (`V1`)**
The `V1` deterministic verifier perfectly passed all safety test cases, correctly labeling logical derivations as `SUPPORTED` and strictly rejecting causal hallucinations as `REJECT`.

## 5. Next Steps

With the safety gate and verification pipeline completely deterministic and mathematically bounded, we have successfully insulated the pipeline from the generator's stochasticity. The next release will focus on end-to-end generator capability recovery within this hardened safety envelope.
