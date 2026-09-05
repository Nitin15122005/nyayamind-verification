# Reports — Planned

No reports exist here yet. This step only defines the plan and sequencing.

## Planned reports

1. **Executive summary** — audience: someone with 5 minutes, unfamiliar with the project.
2. **Input/output walkthrough** — one real case traced through all 8 pipeline stages,
   showing exactly what each stage received and produced (built on
   `final_demo_pack/live_demo/run_demo.py`'s pattern and `final_demo_pack/examples/`'s
   8 worked cases).
3. **Component evaluation** — per-stage findings from `component_tests/`.
4. **End-to-end evaluation** — findings from `integration_tests/` and `evaluation/`.
5. **Original vs. current comparison** — built from `comparisons/`, with the two
   evidentiary tiers (gold-backed vs. metric-based) kept visibly distinct throughout, and
   the correction-shipping-rate significance caveat and no-combined-joint-run caveat
   stated as first-class findings, not footnotes.
6. **Ablation study** — findings from `ablation/`, including the unreconciled
   scope-check-mode discrepancy (1/11 vs. 4/6 unblocked across two different batches).
7. **Safety/correction analysis** — sibling-regression and scope-violation outcomes
   across every triggered correction in the project's history (0 unsafe shipments to
   date), framed as a safety-net track record, not an accuracy claim.
8. **Reproducibility report** — must include, prominently, the environment gap found
   during this step: `research/.venv/` does not exist in this checkout (only system
   Python 3.14 is present, incompatible with the pinned Python 3.11.9/torch 2.2.2+cu121
   stack) — every documented reproduction command in this repository currently assumes a
   venv that must be created first. This is a real, unresolved gap discovered during
   Step 1, not a pre-existing documented caveat.
9. **Final evaluation report** — the consolidated document tying 1-8 together, written
   last, once every input above is complete and citation-checked.

## Sequencing

These are written **last**, in roughly the order above, only once `inputs/`,
`expected_outputs/`, `component_tests/`, `evaluation/`, `ablation/`, and `figures/` have
real content to cite — a report written before its evidence exists would be aspirational,
not evaluative. See the top-level `../README.md` and this project's overall STEP 2
recommendation for exact sequencing.
