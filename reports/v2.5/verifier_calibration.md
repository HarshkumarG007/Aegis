# Verifier Calibration Report

## 1. NLI Stitching Failure (Multi-hop)
DeBERTa fails to verify synthesized claims because it scores against isolated chunks. A claim combining chunk-002 and chunk-003 is scored against chunk-003 alone, resulting in a false `UNSUPPORTED` rejection.

## 2. Extractor Hallucinations
The LLM generates correct short answers (e.g. '60 seconds'), but the `ClaimExtractor` hallucinates dictionary definitions ('60 seconds is a unit of time'). The verifier rightly rejects these, but it causes the entire valid answer to be discarded.

## 3. Retrieval Misalignment
A claim derived from chunk-004 ('60 seconds') is incorrectly paired with chunk-005 ('30 seconds') by the semantic similarity model, causing the NLI to falsely label it as `CONTRADICTED`.

## Recommendation for V2.5
The binary answer-level reject policy is the sole cause of the utility collapse. The verifier accurately identifies unsupported text, but because of extractor bugs and NLI multi-hop limitations, it throws away perfectly valid answers. The proposed Claim-Level Repair and Asymmetric Policy will fix this.
