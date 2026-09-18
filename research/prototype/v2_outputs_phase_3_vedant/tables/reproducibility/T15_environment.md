# T15_environment

The two software stacks side by side. The skew is the reason some experiments could be rerun and others could not.

| component | historical (pinned venv) | this V2 session | impact |
|---|---|---|---|
| Python | 3.11.9 | 3.13.1 | MAJOR SKEW |
| torch | 2.2.2+cu121 | 2.13.0+cpu | MAJOR SKEW - no CUDA |
| transformers | 4.40.2 | 5.15.1 | MAJOR SKEW |
| numpy | 1.26.4 | 2.2.6 | MAJOR SKEW |
| pandas | 2.2.2 | 3.0.2 | MAJOR SKEW |
| CUDA available | True (RTX 4050, 6 GB) | False | NO GPU |
| research/.venv | present | DOES NOT EXIST | gone |
| accelerate / bitsandbytes | 0.29.3 / 0.43.1 | NOT INSTALLED | blocks 4-bit Qwen |
| rank_bm25 | installed | NOT INSTALLED | blocks BM25 arm; skips 12 tests |
| sentence_transformers | installed | NOT INSTALLED | blocks embedding arm |
| MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli | cached | CACHED - verified working on CPU | OK |
| Qwen/Qwen2.5-7B-Instruct | cached, GPU | NOT CACHED, no GPU | RERUN_INFEASIBLE |
| sentence-transformers/all-MiniLM-L6-v2 | cached | NOT CACHED | RERUN_INFEASIBLE |

## Notes

- No package was installed and no dependency added to produce this package.
- Installing rank_bm25 (small, pure-Python) would unblock the BM25 arm; that was deliberately not done, as changing the environment was outside the brief.
