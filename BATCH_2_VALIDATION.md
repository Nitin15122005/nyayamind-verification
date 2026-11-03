# Batch 2 — Reliability and verification safeguards

**Base:** `checkpoint/batch-1-complete-2026-11-03`  
**Working branch:** `fix/batch-2-reliability`

Batch 2 is intentionally layered on the immutable Batch 1 checkpoint. It does not change the canonical evidence corpus, production configuration, model weights, historical outputs, or baseline submodule.

## Changes in this branch

### Streaming API and frontend lifecycle
- NDJSON parsing is strict: malformed JSON, invalid event shapes, events after a terminal event, and streams without a successful `run/complete` event now fail visibly.
- Backend run errors use an explicit `error/failed` event instead of looking like a normal completed stage.
- The frontend distinguishes successful, failed, cancelled, and incomplete runs; it no longer infers success merely because a stage started.
- The frontend aborts its active request when unmounted and exposes a Cancel Run action.
- When a socket write observes that the streaming client disconnected, the backend stops at that event boundary. Detection depends on the operating system reporting the closed connection; an already-running synchronous model inference cannot be interrupted mid-kernel. Once detected, later pipeline stages are prevented from starting.

### Final safety decision
- The server publishes an authoritative safety result after the correction pipeline returns. This supersedes provisional structural-gate events, so a later splice failure or sibling regression cannot leave the UI displaying an all-PASS safety result.
- Unknown safety gate identifiers fail closed as `correction_failed`.

### NLI input length
- The DeBERTa verifier refuses premise/hypothesis pairs longer than its configured maximum sequence length.
- It no longer silently truncates a canonical statute premise before scoring. This avoids issuing a verdict after a trailing statutory exception or proviso has been removed.
- Overlength input raises an explicit error; the live API reports the run as failed rather than inventing an NLI verdict.

## Validation commands

Run from the repository root on the project environment:

```powershell
research/.venv/Scripts/python.exe -m unittest discover -s live_demo_v2/server/tests -v
research/.venv/Scripts/python.exe -m pytest research/prototype/tests/ -q
```

Run the frontend checks:

```powershell
cd live_demo_v2/web
npm test
npm run build
```

The research test suite includes a real-verifier integration test that requires the configured CUDA environment. If CUDA is unavailable, report that test as environment-blocked; do not count it as passed.

## Required manual smoke checks

1. Start the backend and frontend using the documented project commands.
2. Confirm `/api/health` reaches `ready`.
3. Run one curated correction-applied example and one correction-withheld example.
4. Confirm the final safety panel reflects the final correction status, including a withheld legacy splice case.
5. Start a custom run and press Cancel Run; confirm the UI shows CANCELLED rather than COMPLETE. After the server observes the disconnect on a stream write, it should stop before starting subsequent stages. An inference already in progress may finish first.
6. Force a backend error or malformed stream in a test fixture and confirm the UI shows FAILED, never COMPLETE.
7. Confirm Batch 1 API security tests still pass.

## Validation status

Code and regression tests have been added on the Batch 2 branch. They are **not marked as passing until executed** in the target Windows/Python/CUDA/Node environment. The Batch 1 checkpoint remains unchanged and is the rollback target.
