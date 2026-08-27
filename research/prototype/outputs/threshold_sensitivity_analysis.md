# Confidence Calibration / Threshold Sensitivity (deterministic, no re-inference)

_No GPU, no model call — every row replays the exact `NLIVerifier.verify()` decision rule against the already-computed full softmax distribution stored in the committed 420-item controlled benchmark. Threshold NOT changed in config/prototype.yaml (still 0.70)._

## bare framing (420 items)

| threshold | accuracy | macro F1 | ENTAILED F1 | CONTRADICTED F1 | NEI F1 | low_conf downgrades |
|---:|---:|---:|---:|---:|---:|---:|
| 0.50 | 0.733 | 0.749 | 0.657 | 0.916 | 0.673 | 2 |
| 0.55 | 0.736 | 0.751 | 0.659 | 0.916 | 0.677 | 3 |
| 0.60 | 0.736 | 0.751 | 0.659 | 0.916 | 0.677 | 5 |
| 0.65 | 0.736 | 0.751 | 0.659 | 0.916 | 0.677 | 7 |
| 0.70 **(production)** | 0.733 | 0.749 | 0.662 | 0.912 | 0.673 | 14 |
| 0.75 | 0.733 | 0.749 | 0.662 | 0.912 | 0.673 | 17 |
| 0.80 | 0.731 | 0.746 | 0.662 | 0.907 | 0.671 | 22 |
| 0.85 | 0.726 | 0.742 | 0.664 | 0.897 | 0.665 | 29 |
| 0.90 | 0.729 | 0.745 | 0.664 | 0.901 | 0.669 | 40 |
| 0.95 | 0.721 | 0.738 | 0.657 | 0.896 | 0.661 | 60 |

## labeled framing (420 items)

| threshold | accuracy | macro F1 | ENTAILED F1 | CONTRADICTED F1 | NEI F1 | low_conf downgrades |
|---:|---:|---:|---:|---:|---:|---:|
| 0.50 | 0.967 | 0.965 | 0.974 | 0.948 | 0.974 | 1 |
| 0.55 | 0.967 | 0.965 | 0.974 | 0.948 | 0.974 | 2 |
| 0.60 | 0.969 | 0.967 | 0.981 | 0.948 | 0.970 | 7 |
| 0.65 | 0.971 | 0.968 | 0.987 | 0.948 | 0.970 | 11 |
| 0.70 **(production)** | 0.971 | 0.968 | 0.987 | 0.948 | 0.970 | 12 |
| 0.75 | 0.971 | 0.968 | 0.987 | 0.948 | 0.970 | 13 |
| 0.80 | 0.967 | 0.963 | 0.987 | 0.939 | 0.962 | 17 |
| 0.85 | 0.964 | 0.960 | 0.987 | 0.934 | 0.958 | 26 |
| 0.90 | 0.955 | 0.948 | 0.989 | 0.915 | 0.939 | 34 |
| 0.95 | 0.948 | 0.942 | 0.981 | 0.923 | 0.921 | 56 |

