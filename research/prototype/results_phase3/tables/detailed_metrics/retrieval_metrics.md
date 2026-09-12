# Retrieval fuzzy-matching method comparison (136-record evidence pool, 21 should-match + 9 should-not-match pre-registered adversarial cases)

Source: `outputs/retrieval_signal_benchmark_results.jsonl` (90 records = 3 methods x 30 cases). Full narrative and named wrong-accept examples: `outputs/retrieval_signal_benchmark_report.md`.

| method | should_match_correct | should_match_total | should_not_match_correct_reject | should_not_match_total | production_threshold | production_status |
|---|---|---|---|---|---|---|
| jaccard | 19 | 21 | 9 | 9 | 0.8 | PRODUCTION (evidence_matching.fuzzy_method default) |
| bm25 | 21 | 21 | 3 | 9 | 0.5 | EVALUATED, NOT PROMOTED |
| embedding | 21 | 21 | 2 | 9 | 0.55 | EVALUATED, NOT PROMOTED |
