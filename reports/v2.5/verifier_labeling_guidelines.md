# Verifier Error-Analysis Labeling Guidelines

This document outlines the protocol for manually adjudicating rejected claims in the V2.5 diagnostic dataset (`verifier_diagnostics.json`).

## Blinding Protocol
To ensure human labels are not biased by the strict threshold logic:
1. Extract the `claim` and `supporting_chunk_text` pairs.
2. Hide the `nli_entailment`, `nli_contradiction`, and `similarity_score` outputs during the manual review phase.
3. Hide the `verifier_decision`.

## Definitions

Assign exactly one of the following labels to each claim based strictly on the retrieved context:

- **SUPPORTED:** The evidence logically entails the claim, including reasonable semantic paraphrases. The claim does not introduce outside world knowledge or hallucinations.
- **CONTRADICTED:** The evidence explicitly conflicts with the claim. If the chunk states "Timeout is 60s" and the claim states "Timeout is 30s", it is CONTRADICTED.
- **UNSUPPORTED:** The claim requires information completely absent from the retrieved evidence (i.e., hallucination). Also applies if the claim is nonsensical (e.g., extracting a dictionary definition of "60 seconds").
- **UNCERTAIN:** The evidence is highly relevant and plausible, but does not definitively establish entailment or contradiction. (e.g., The claim is a slight over-extrapolation, or relies on multi-hop synthesis that cannot be confirmed from a single isolated chunk).

## Ambiguous Cases

For cases where the context is genuinely ambiguous or contradictory within itself:
- Do not force an arbitrary label.
- Leave `human_label` blank.
- Populate a new `adjudication_notes` field with the raw evidence and the reasoning for the ambiguity.

## Inter-Annotator Agreement (IAA)

A 20% subset of the diagnostic dataset must be independently labeled by a second annotator. Calculate Cohen's Kappa ($\kappa$) on this subset. 

This ensures that the metric "verifier false rejection" reflects an objective truth, rather than simply "human disagreed with the verifier."
