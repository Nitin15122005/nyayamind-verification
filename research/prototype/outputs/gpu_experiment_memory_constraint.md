# Large-batch GPU experiment: blocked by a verified host memory constraint

_2026-09-11_

## What was attempted

`scripts/run_narrow_primary_hypothesis_gpu_ablation.py` (real Qwen2.5-7B-Instruct
generation + real DeBERTa verification + real selective correction, through
the actual production `pipeline.py`, Mode C), targeting the task's requested
n=100 fresh natural-data cases isolating the `narrow_primary_hypothesis`
lever, with a documented fallback to "the largest defensible sample between
50 and 100" if 100 could not be completed.

## What happened

Three consecutive attempts, at decreasing batch size, ALL failed during
**model loading** (before processing a single case, i.e. independent of
batch size):

| Attempt | n | Outcome | Failure point |
|---|---|---|---|
| 1 | 100 | Killed by host OS (low memory) | During checkpoint-shard loading |
| 2 | 50 | Killed by host OS (low memory) | During checkpoint-shard loading (shard 3/4) |
| 3 | 30 | Killed by host OS (low memory) | Before the first checkpoint shard finished |

System memory, checked directly before and after each attempt
(`Get-CimInstance Win32_OperatingSystem`): **15.7 GB total, consistently
~5.3-5.5 GB free** throughout, essentially unchanged across attempts —
this machine's other running applications (browser windows, IDE instances,
Windows Defender, etc. — a normal desktop workload, not something induced
by this session) leave headroom that is evidently insufficient to load
Qwen2.5-7B-Instruct in 4-bit quantization (which needs several GB for
weights alone, plus transient overhead during the quantization/loading
process itself, plus the DeBERTa verifier, plus PyTorch/CUDA driver
overhead).

## Why this was not "fixed" by changing code

`src/generator.py`'s `AutoModelForCausalLM.from_pretrained()` call already
uses a `device_map`, which causes `transformers` (pinned 4.40.2) to default
`low_cpu_mem_usage=True` automatically — the standard, documented mitigation
for exactly this class of problem is already active. There is no evident
code-level inefficiency to fix; this is a genuine hardware/environment
resource ceiling, not a bug. Per this task's own explicit instruction
("do not change runtime semantics merely to make the build pass" — stated
about Docker, but the same principle applies here), no speculative change
was made to generation code to try to route around this.

## Why retries were not continued indefinitely

All three failures occurred at the same point (model loading) regardless of
requested batch size, and free memory was stable (~5.3-5.5 GB) across all
three attempts with no trend toward recovery. A fourth attempt at an even
smaller n would not address the actual constraint (loading the model at
all), so further retries would have been guessing, not diagnosing. This is
reported as a confirmed, reproducible blocker rather than continuing to
consume the user's GPU/CPU time on attempts with no new information to
justify expecting a different outcome.

## What this means for the project's results

- The **n=15 fresh batch from the prior session**
  (`outputs/narrow_primary_hypothesis_gpu_ablation_{OLD,CURRENT,metrics,report}.*`)
  remains the actual, real, already-committed fresh end-to-end GPU result
  for the `narrow_primary_hypothesis` lever. It is NOT superseded or
  invalidated by this session's blocked attempts.
- Correction-shipping impact of `narrow_primary_hypothesis` at a
  statistically meaningful scale (n>=50) **remains genuinely unmeasured**,
  exactly as documented before this session began. This session did not
  change that fact, and does not claim to.
- Docker image validation for today's code is **also blocked** by the same
  constraint (Docker Desktop's WSL2 VM was found not running when checked
  after the third failed GPU attempt, and starting it under the same
  memory pressure that just killed three Python processes would not be a
  responsible use of the user's machine) — see the final freeze report's
  Docker section for the precise state.

## Recommended follow-up (not done this session)

Re-attempt `scripts/run_narrow_primary_hypothesis_gpu_ablation.py --n-cases 50`
(or 100) at a time when the host has more free memory available (e.g. fewer
concurrent desktop applications), or on a machine/VM with more RAM headroom
dedicated to this workload. No code change is needed to attempt this — the
script and its `--n-cases`/`--out-prefix` arguments already support it.

## RESOLVED (2026-09-12, one session later) — the model-loading blocker specifically

A follow-up session's memory architecture audit
(`outputs/16gb_memory_architecture_audit.md`) found the root cause of the
**model-loading** failures documented above: loading a single ~3.9GB
safetensors shard into CPU RAM as a transient staging step, on a system
with only 5.1-5.5GB free, left almost no headroom. Two small,
legitimate, model-identity-preserving fixes to `src/generator.py`
(`low_cpu_mem_usage=True` explicit, `gc.collect()`/`torch.cuda.empty_cache()`
immediately before `from_pretrained()`) resolved this specific failure mode
— model loading now succeeds reliably in ~13 seconds, confirmed across 4
separate process launches. The experiment script was also rewritten to be
checkpointed/resumable (writes each case immediately, detects and skips
already-completed cases on restart, includes a pre-case memory guard).

Using this, a real n=62 fresh dataset was collected (see
`outputs/16gb_final_execution_report.md` for the full results) — exceeding
the n=50 minimum-useful target this document originally could not reach.
**Not fully resolved**: a second, different failure (an OS kill during
active *generation*, not loading, on a push toward n=100) confirms the
underlying resource ceiling is real and not eliminated, only pushed back —
the per-case memory guard checks only *before* each case starts, and
cannot catch every possible transient spike *during* one. Checkpointing
correctly preserved all data through that second interruption; it was not
retried a third time at that scale, per explicit instruction not to
repeatedly rerun a demonstrated OOM.

Docker remains blocked, unchanged by this resolution (it is a separate
constraint — see `FINAL_RESEARCH_FREEZE_REPORT.md` for its current status).
