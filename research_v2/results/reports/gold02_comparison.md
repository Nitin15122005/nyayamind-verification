# GOLD02 comparison

Baseline: `MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli`; V2: `tasksource/ModernBERT-large-nli`; n=59.

| Metric | Baseline | V2 | Absolute delta |
|---|---:|---:|---:|
| Accuracy | 0.5424 | 0.4576 | -0.0847 |
| Macro-F1 | 0.2344 | 0.2093 | -0.0251 |
| Weighted F1 | 0.7033 | 0.6279 | -0.0754 |
| CONTRADICTED precision | 1.0000 | 1.0000 | +0.0000 |
| CONTRADICTED recall | 0.5424 | 0.4576 | -0.0847 |
| CONTRADICTED F1 | 0.7033 | 0.6279 | -0.0754 |
| ENTAILED recall | 0.0000 | 0.0000 | +0.0000 |
| NEI precision | 0.0000 | 0.0000 | +0.0000 |
| NEI recall | 0.0000 | 0.0000 | +0.0000 |

Exact McNemar paired-accuracy test: discordant=9, p=0.179688.
Exact paired CONTRADICTED-recall test among gold contradictions (n=59): baseline-only correct=7, V2-only correct=2, p=0.179688.

Paired bootstrap 95% CI for accuracy delta: [-0.1864406779661017, 0.016949152542372836]; contradiction-recall delta: [-0.1864406779661017, 0.016949152542372836].

Interpretation: evaluate the predeclared metric hierarchy and uncertainty together; this report does not declare V2 better by default.
