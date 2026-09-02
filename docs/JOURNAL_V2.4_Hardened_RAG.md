# Aegis Engineering Journal: V2.4 Hardened RAG (Externalizing Grounding Policy)

*Authored by the Aegis Architecture Team*

## The Problem: The "Compulsion to Merge and Stitch"

In V2.3, we made a shocking discovery when benchmarking Llama 3 8B and Mistral 7B against Qwen 1.5B. While the larger models possessed far superior reasoning and generative capabilities (improving contradiction resolution by +25%), they suffered a severe **-25% regression on Out-Of-Domain (OOD) safety**.

Why? We coined two new failure modes:
1. **The Compulsion to Stitch (OOD Failures):** A highly capable model hates saying "I don't know". It will extract irrelevant fragments from completely unrelated text (e.g. stitching together database terminology to invent a fake API answer) just to fulfill the user's prompt.
2. **The Compulsion to Merge (Contradiction Failures):** When presented with two conflicting pieces of evidence, the generator will attempt to peacefully "merge" them (e.g., claiming a password rotation policy is 30 *and* 90 days), rather than identifying the conflict and abstaining.

We realized our core research question had shifted. It was no longer: *"Do larger models hallucinate more?"*
It became: *"Can model capability be separated from grounding policy?"*

## The Solution: Aegis-Hardened RAG V2.4

We hypothesized that we could externalize the model's grounding policy. If we could move the "Can I answer this safely?" decision out of the LLM and into discrete, observable gates, we could stop treating hallucinations as unpredictable black-box failures and start treating them as tunable engineering parameters.

We built two discrete, deterministic safety gates using specialized small models (Cross-Encoders) running on the CPU:

### 1. The Evidence Gate (Pre-Generation)
Before the LLM even sees the prompt, we pass the query and the retrieved chunks through an **MS-MARCO** cross-encoder (for sufficiency) and a **DeBERTa-v3** NLI cross-encoder (for conflict detection). 
- If MS-MARCO decides the text is irrelevant -> **INSUFFICIENT (Abstain)**
- If DeBERTa detects pairwise contradiction in the chunks -> **CONFLICT (Constrained Prompt)**
- Else -> **SUFFICIENT (Generate)**

### 2. The Verification Gate (Post-Generation)
After the LLM generates an answer, we parse every single sentence into declarative claims and pass them through DeBERTa against the retrieved chunks.
- If *any* claim is ungrounded -> **REJECT (Abstain)**

## The 5-Way Ablation Experiment

To scientifically prove these gates worked, we couldn't just run the full pipeline. We ran a strict 5-way paired ablation across 60 adversarial queries on Mistral 7B (0.2), locking down identical models, temperature, retrieval ranks, and manifests to guarantee a perfectly clean signal.

The results were eye-opening.

### Successes (What Worked Beautifully)
* **OOD Fabrications Plummeted**: The Evidence Gate successfully caught unanswerable queries. OOD score rocketed from **41.7% to 83.3%**. We successfully intercepted the Compulsion to Stitch!
* **Silent Failures Exposed**: Out of 38 failures in the baseline, the V2.4 pipeline successfully intervened on 21 of them, shifting them from silent fabrications into explicit, logged system abstentions/rejections. We even rescued 7 entirely, turning them into passes.
* **We separated capability from policy**: Grounding is no longer an LLM mystery. It is a measurable system state.

### Failures (The Engineering Reality)
* **Detection ≠ Intervention (The Conflict Problem)**: The Evidence Gate successfully detected 23% of contradictions. But simply passing a constrained prompt ("Do not reconcile conflicting claims") to Mistral 7B did *nothing*. The generator's internal alignment overrode our prompt, and Contradiction scores stayed flat at 33.3%.
* **The "False Abstention" Tax**: MS-MARCO isn't perfectly calibrated. It triggered a 26.7% false-abstention rate, erroneously blocking valid multi-hop queries because it deemed them "insufficient."
* **The "Binary Guillotine" Verifier**: The post-generation verifier rejected 86.7% of all generated text, completely destroying the overall pass rate (10%). It was far too rigid.

## Outcomes and V2.4.1 Decisions

V2.4 is a massive architectural transition. It did exactly what a good experimental design should do: it turned vague generative hallucinations into specific, measurable engineering failures. 

We now have the roadmap for **V2.4.1 (Calibration and Deterministic Controllers)**:

1. **Stop asking the generator to resolve conflicts.** If the Evidence Gate detects a conflict, the system will now deterministically output an explicit "conflicting evidence" response. The generator cannot be trusted with conflicting data.
2. **Calibrate the gates.** We will sweep the MS-MARCO sufficiency thresholds on our Development Set to find the perfect tradeoff between OOD recall and False Abstentions.
3. **Build a Claim-Level Repair Loop.** Instead of tossing out an entire answer because of one bad claim, V2.4.1 will execute a repair loop: isolating the unsupported claim, shrinking the context to only the valid evidence, and forcing a constrained regeneration. 

We are moving away from prompting our way out of hallucinations, and into hard software engineering.
