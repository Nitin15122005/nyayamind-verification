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
    <div className="flex min-h-screen flex-col">
      <NavBar />

      <main className="mx-auto flex w-[96vw] max-w-[2200px] flex-1 flex-col gap-7 px-1 py-8 sm:py-10">
        <div className="grid flex-1 grid-cols-1 gap-7 lg:grid-cols-[65fr_35fr]">
          {/* LEFT: Verification workspace */}
          <div className="flex flex-col gap-7">
            <section className="glass-panel rounded-2xl p-6 sm:p-8">
              <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
                <label className="font-mono text-sm uppercase tracking-wider text-ink-secondary">Legal Input</label>
                <div className="flex items-center gap-2.5">
                  <SampleMenu examples={examples} onPick={handlePickSample} disabled={running} />
                  {(inputText || hasStarted) && (
                    <button
                      type="button"
                      onClick={handleReset}
                      disabled={running}
                      className="rounded-md border border-white/10 bg-white/[0.03] px-4 py-2 font-body text-sm font-medium text-ink-secondary transition-colors hover:border-white/25 hover:text-ink-primary disabled:opacity-40"
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
                className="h-52 w-full resize-none rounded-xl border border-white/10 bg-canvas-subtle px-5 py-4 font-body text-lg font-medium leading-[1.65] text-ink-primary placeholder:font-normal placeholder:text-ink-muted focus:border-judicial focus:outline-none focus:ring-3 focus:ring-judicial/15"
              />
              <div className="mt-4 flex flex-col gap-3.5 sm:flex-row sm:items-center sm:justify-between">
                <input
                  value={citation}
                  onChange={(e) => setCitation(e.target.value)}
                  disabled={running}
                  placeholder="Citation / authority (optional)"
                  className="w-full max-w-xs rounded-md border border-white/10 bg-canvas-subtle px-3.5 py-2.5 font-body text-sm text-ink-primary placeholder:text-ink-muted focus:border-judicial focus:outline-none sm:w-72"
                />
                <button
                  type="button"
                  onClick={handleRun}
                  disabled={running || !inputText.trim()}
                  className="rounded-lg bg-gradient-to-br from-judicial to-judicial-dim px-7 py-3.5 font-body text-base font-semibold text-white shadow-glow-judicial transition-transform hover:scale-[1.02] disabled:cursor-not-allowed disabled:opacity-40 disabled:shadow-none"
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
          <div className="lg:sticky lg:top-28 lg:self-start">
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
