# Verifier Confusion Matrix

This matrix compares the DeBERTa NLI predictions against the strict human labeling of the 43 rejected claims.

| DeBERTa Verifier | Human Adjudication | Count | Description |
| :--- | :--- | :--- | :--- |
| CONTRADICTED | UNCERTAIN | 3 | False rejection (Utility collapse) |
| UNSUPPORTED | UNSUPPORTED | 24 | Accurate rejection |
| UNSUPPORTED | UNCERTAIN | 8 | False rejection (Utility collapse) |
| UNSUPPORTED | SUPPORTED | 6 | False rejection (Utility collapse) |
| CONTRADICTED | UNSUPPORTED | 1 | Misclassified hallucination |
| UNSUPPORTED | CONTRADICTED | 1 | False rejection (Utility collapse) |
