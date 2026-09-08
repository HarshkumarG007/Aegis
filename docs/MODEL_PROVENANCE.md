# Model Provenance & Supply-Chain Integrity

In order to maintain strict deterministic security bounds across Aegis-Eval, the exact cryptographic provenance of generator and evaluator models must be preserved.

## Supported Open-Weights Models

The Aegis offline generation and evaluation infrastructure relies on the following fixed models. The SHA-256 hashes must be verified before the models are executed in a zero-trust environment.

### 1. Evaluators (DeBERTa-v3)
The V4 architecture relies on the decoupled NLI pipeline.
- **Model**: `MoritzLaurer/deberta-v3-large-zeroshot-v2.0`
- **Origin**: HuggingFace Model Hub
- **Immutable Verification**: The framework enforces caching and hashing of the `pytorch_model.bin` or `model.safetensors` associated with this exact repository commit.

### 2. Primary Offline Generators (Llama 3 8B)
During the V2.3 to V3.4 executions, `Meta-Llama-3-8B-Instruct` was executed offline via `llama-cpp-python`.
- **Format**: GGUF
- **Required Quants**: Q4_K_M or Q8_0
- **Provenance Validation**: 
  All evaluations must record the specific SHA-256 hash of the `.gguf` file utilized during the execution of `scripts/aegis_cli.py generate`. This hash is embedded into the immutable generation artifact.

## Why Provenance Matters
If an attacker can silently substitute the evaluator model with a weakened variant, they can induce false `PASS_SUBSTANTIVE` authorizations. The Aegis framework considers the physical model weights as part of the Trusted Computing Base (TCB).

## Validating Weights
Prior to initializing the pipeline, deployers should explicitly lock their HuggingFace downloads or `.gguf` archives. We recommend integrating tools like `sha256sum` directly into the deployment pipeline.
