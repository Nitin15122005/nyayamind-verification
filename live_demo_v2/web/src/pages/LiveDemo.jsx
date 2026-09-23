import { useEffect, useRef, useState } from "react";
import NavBar from "../components/NavBar.jsx";
import StagePanel from "../components/StagePanel.jsx";
import SampleMenu from "../components/SampleMenu.jsx";
import LiveProcessingFeed from "../components/LiveProcessingFeed.jsx";
import { fetchExamples, runVerification } from "../lib/api.js";

// Matches the REAL pipeline's true execution order (src/pipeline.py's
// apply_selective_correction): the corrector runs first and its candidate
// is safety-validated afterward -- "generate, then verify the output" is
// this project's own design convention, not the reverse.
const STAGE_ORDER = ["input", "claims", "evidence", "verification", "correction", "safety", "recheck", "result"];

function initialStatus() {
  return Object.fromEntries(STAGE_ORDER.map((k) => [k, "pending"]));
}

export default function LiveDemo() {
  const [examples, setExamples] = useState([]);
  const [inputText, setInputText] = useState("");
  const [citation, setCitation] = useState("");
  const [filledPreview, setFilledPreview] = useState(null);
  const [selectedExampleId, setSelectedExampleId] = useState(null);

  const [running, setRunning] = useState(false);
  const [stageStatus, setStageStatus] = useState(initialStatus);
  const [stageData, setStageData] = useState({});
  const [viewedStage, setViewedStage] = useState(null);
  const [underlying, setUnderlying] = useState(false);
  const [error, setError] = useState(null);

  const abortRef = useRef(null);

  useEffect(() => {
    fetchExamples()
      .then(setExamples)
      .catch(() => setExamples([]));
  }, []);

  function handlePickSample(example) {
    setInputText(example.input_preview);
    setFilledPreview(example.input_preview);
    setSelectedExampleId(example.id);
    setCitation("");
    setStageData({});
    setStageStatus(initialStatus());
    setViewedStage(null);
    setError(null);
  }

  function handleTextChange(e) {
    setInputText(e.target.value);
  }

  function handleReset() {
    setInputText("");
    setCitation("");
    setFilledPreview(null);
    setSelectedExampleId(null);
    setStageData({});
    setStageStatus(initialStatus());
    setViewedStage(null);
    setUnderlying(false);
    setError(null);
  }

  // Every transition below is driven by a real event the backend emitted at
  // the moment the corresponding real operation actually started/finished
  // (server/app.py's run_streaming) -- never a timer, never inferred ahead
  // of the data it describes.
  function handleEvent(event) {
    const { stage, status, data } = event;
    if (stage === "run") return; // overall lifecycle marker; `running` already tracks this via the fetch itself
    if (stage === "error") {
      setError(data?.message || "This run could not be completed.");
      return;
    }
    if (status === "started") {
      setStageStatus((prev) => ({ ...prev, [stage]: "active" }));
      setViewedStage(stage);
      return;
    }
    setStageData((prev) => ({ ...prev, [stage]: data }));
    setStageStatus((prev) => ({ ...prev, [stage]: status === "skipped" ? "skipped" : "done" }));
    setViewedStage(stage);
  }

  async function handleRun() {
    if (!inputText.trim() || running) return;
    setRunning(true);
    setError(null);
    setStageData({});
    setUnderlying(false);
    setStageStatus(initialStatus());
    setViewedStage(null);

    const usingExample = Boolean(selectedExampleId) && inputText === filledPreview;
    const body = usingExample
      ? { mode: "example", id: selectedExampleId }
      : { mode: "custom", text: citation.trim() ? `${citation.trim()}. ${inputText}` : inputText };

    const controller = new AbortController();
    abortRef.current = controller;
    try {
      await runVerification(body, handleEvent, { signal: controller.signal });
    } catch (e) {
      if (e.name !== "AbortError") setError(e.message || "The run could not be completed.");
    } finally {
      setRunning(false);
    }
  }

  const hasStarted = Object.values(stageStatus).some((s) => s !== "pending");
  const runStatus = running ? "running" : hasStarted ? "complete" : "ready";

  return (
    <div className="min-h-screen">
      <NavBar />

      <main className="mx-auto flex w-[94vw] max-w-[1440px] flex-1 flex-col gap-3 px-1 py-4 sm:py-5">
        <div className="mb-0.5">
          <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-judicial">Live verification workspace</p>
          <h1 className="mt-1 font-display text-xl font-semibold tracking-tight text-ink-primary sm:text-2xl">Verify a legal claim</h1>
          <p className="mt-1 max-w-2xl text-xs leading-5 text-ink-secondary">
            Paste a legal passage or choose a prepared evaluation scenario. Follow the real pipeline as it extracts claims, retrieves evidence, verifies them, and applies safety-gated correction.
          </p>
        </div>
        <div className="grid flex-1 grid-cols-1 gap-3 lg:grid-cols-[minmax(0,1.55fr)_minmax(320px,0.85fr)]">
          {/* LEFT: Verification workspace */}
          <div className="flex flex-col gap-3">
            <section className="glass-panel rounded-xl p-3 sm:p-4">
              <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                <label className="text-xs font-semibold uppercase tracking-[0.14em] text-judicial">Legal Input</label>
                <div className="flex items-center gap-2.5">
                  <SampleMenu examples={examples} onPick={handlePickSample} disabled={running} />
                  {(inputText || hasStarted) && (
                    <button
                      type="button"
                      onClick={handleReset}
                      disabled={running}
                      className="rounded-xl border border-slate-200 bg-white px-3 py-1.5 font-body text-xs font-semibold text-ink-secondary transition-colors hover:border-white/25 hover:text-ink-primary disabled:opacity-40"
                    >
                      Reset
                    </button>
                  )}
                </div>
              </div>
              <textarea
                value={inputText}
                onChange={handleTextChange}
                disabled={running}
                placeholder="Paste a legal statement or generated legal passage…"
                className="h-44 w-full resize-none rounded-lg border border-slate-200 bg-slate-50 px-3 py-2.5 font-body text-xs leading-5 text-ink-primary placeholder:font-normal placeholder:text-ink-muted focus:border-judicial focus:bg-white focus:outline-none focus:ring-4 focus:ring-judicial/10"
              />
              <div className="mt-2 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                <input
                  value={citation}
                  onChange={(e) => setCitation(e.target.value)}
                  disabled={running}
                  placeholder="Citation / authority (optional)"
                  className="w-full max-w-xs rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 font-body text-xs text-ink-primary placeholder:text-ink-muted focus:border-judicial focus:outline-none sm:w-72"
                />
                <button
                  type="button"
                  onClick={handleRun}
                  disabled={running || !inputText.trim()}
                  className="rounded-lg bg-primary-container px-4 py-2 font-body text-xs font-semibold text-white shadow-md transition-all hover:-translate-y-0.5 hover:shadow-lg disabled:cursor-not-allowed disabled:opacity-40 disabled:shadow-none"
                >
                  {running ? "Running…" : "Run Verification →"}
                </button>
              </div>
            </section>

            <StagePanel
              viewedStage={viewedStage}
              stageData={stageData}
              underlying={underlying}
              onToggleUnderlying={() => setUnderlying((v) => !v)}
              error={error}
            />
          </div>

          {/* RIGHT: canonical live execution pipeline */}
          <div className="lg:sticky lg:top-20 lg:self-start">
            <LiveProcessingFeed
              stageOrder={STAGE_ORDER}
              stageStatus={stageStatus}
              stageData={stageData}
              runStatus={runStatus}
              viewedStage={viewedStage}
              onSelect={setViewedStage}
            />
          </div>
        </div>
      </main>
    </div>
  );
}
