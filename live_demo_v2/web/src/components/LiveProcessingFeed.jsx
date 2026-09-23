const LABELS = {
  input: "Input",
  claims: "Claims",
  evidence: "Evidence",
  verification: "NLI",
  safety: "Safety",
  correction: "Correction",
  recheck: "Re-check",
  result: "Result",
};

const ACTIVE_DETAIL = {
  input: "Receiving request…",
  claims: "Extracting claims…",
  evidence: "Retrieving evidence…",
  verification: "Running NLI verification…",
  correction: "Generating correction candidate…",
  safety: "Validating correction candidate…",
  recheck: "Re-verifying corrected text…",
  result: "Assembling final result…",
};

function doneDetail(key, data) {
  if (!data) return "";
  switch (key) {
    case "input":
      return "Legal text accepted";
    case "claims": {
      const n = data.claims?.length || 0;
      return n === 0 ? "No citation-bearing claims found" : `${n} claim${n === 1 ? "" : "s"} identified`;
    }
    case "evidence": {
      const claims = data.claims || [];
      const matched = claims.filter((c) => c.evidence_text).length;
      return `${matched}/${claims.length} claim${claims.length === 1 ? "" : "s"} matched`;
    }
    case "verification": {
      const claims = data.claims || [];
      const counts = {};
      for (const c of claims) counts[c.verdict] = (counts[c.verdict] || 0) + 1;
      const parts = Object.entries(counts).map(([k, v]) => `${v} ${k.toLowerCase().replace(/_/g, " ")}`);
      const triggers = claims.filter((c) => c.correction_trigger);
      if (triggers.length) {
        const reasons = [...new Set(triggers.map((c) => c.correction_trigger_reason).filter(Boolean))];
        const reasonText = reasons.length ? ` (${reasons.join(", ")})` : "";
        parts.push(`${triggers.length} correction trigger${triggers.length === 1 ? "" : "s"}${reasonText}`);
      }
      return parts.join(", ") || "No claims to verify";
    }
    case "correction":
      if (!data.triggered) return "Not triggered";
      return data.trigger_reason ? `Candidate correction generated (${data.trigger_reason})` : "Candidate correction generated";
    case "safety":
      if (!data.triggered) return "Not required";
      if (data.passed === false) return "Blocked -- see detail";
      return `${(data.checks || []).filter((c) => c.result === "PASS").length}/${(data.checks || []).length} checks passed`;
    case "recheck":
      if (!data.triggered) return "Not applicable";
      return data.verdict ? `Re-verified: ${data.verdict}` : "Could not re-verify";
    case "result":
      return "Execution complete";
    default:
      return "";
  }
}

const STATUS_META = {
  ready: { label: "READY", dot: "bg-white/30" },
  running: { label: "RUNNING", dot: "bg-judicial animate-pulse-glow" },
  complete: { label: "COMPLETE", dot: "bg-entail" },
};

function Row({ stageKey, status, data, isLast, clickable, isViewed, onSelect }) {
  const isDone = status === "done";
  const isActive = status === "active";
  const isSkipped = status === "skipped";
  const isError = status === "error";
  const isPending = status === "pending";

  const detail = isDone
    ? doneDetail(stageKey, data)
    : isActive
      ? ACTIVE_DETAIL[stageKey]
      : isSkipped
        ? "Not applicable"
        : "";

  return (
    <div className="flex gap-2.5 nm-feed-row">
      <div className="flex flex-col items-center">
        <span
          className={`mt-1 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border-2 text-[10px] transition-all duration-300 ${
            isDone
              ? "border-entail bg-entail/15 text-entail"
              : isSkipped
                ? "border-slate-200 bg-slate-50 text-ink-muted"
                : isActive
                  ? "border-judicial bg-judicial/15 text-judicial-soft shadow-glow-judicial animate-pulse-glow"
                  : isError
                    ? "border-contra bg-contra/15 text-contra"
                    : "border-slate-200 bg-transparent text-ink-muted"
          }`}
        >
          {isDone && "✓"}
          {isSkipped && "–"}
          {isError && "✕"}
          {isActive && <span className="h-2 w-2 rounded-full bg-judicial" />}
        </span>
        {!isLast && (
          <span
            className={`w-px flex-1 min-h-[22px] transition-colors duration-500 ${
              isDone || isSkipped ? "bg-entail/30" : isActive ? "bg-judicial/40" : "bg-white/10"
            }`}
          />
        )}
      </div>
      <button
        type="button"
        disabled={!clickable}
        onClick={() => clickable && onSelect(stageKey)}
        className={`mb-2.5 flex-1 rounded-lg px-2 py-0.5 text-left transition-colors ${
          clickable ? "cursor-pointer hover:bg-slate-50" : "cursor-default"
        } ${isViewed ? "bg-judicial/[0.08] ring-1 ring-judicial/30" : ""} ${isPending ? "opacity-40" : "opacity-100"}`}
      >
        <p className={`text-xs font-medium ${isActive || isDone ? "text-ink-primary" : "text-ink-secondary"}`}>
          {LABELS[stageKey]}
        </p>
        {detail && <p className="mt-0.5 text-[11px] leading-4 text-ink-secondary">{detail}</p>}
      </button>
    </div>
  );
}

export default function LiveProcessingFeed({ stageOrder, stageStatus, stageData, runStatus, viewedStage, onSelect }) {
  const hasStarted = stageOrder.some((k) => stageStatus[k] !== "pending");
  const meta = STATUS_META[runStatus] || STATUS_META.ready;

  return (
    <div className="glass-panel flex flex-col rounded-xl p-3 sm:p-4">
      <div className="mb-2 flex items-center justify-between border-b border-slate-200 pb-2">
        <h3 className="font-display text-sm font-semibold uppercase tracking-wider text-ink-primary">
          Live Processing
        </h3>
        <span className="flex items-center gap-2 rounded-full border border-slate-200 bg-slate-50 px-2 py-0.5 font-mono text-[10px] font-semibold tracking-wider text-ink-secondary">
          <span className={`h-2 w-2 rounded-full ${meta.dot}`} />
          {meta.label}
        </span>
      </div>
      {!hasStarted ? (
        <div className="flex flex-1 flex-col items-center justify-center gap-1.5 py-10 text-center">
          <p className="text-xs font-medium text-ink-secondary">Ready to run</p>
          <p className="max-w-[210px] text-[11px] text-ink-secondary">
            Run the pipeline to see each stage execute, live.
          </p>
        </div>
      ) : (
        <div className="flex flex-col">
          {stageOrder.map((key, idx) => (
            <Row
              key={key}
              stageKey={key}
              status={stageStatus[key]}
              data={stageData[key]}
              isLast={idx === stageOrder.length - 1}
              clickable={stageStatus[key] !== "pending"}
              isViewed={viewedStage === key}
              onSelect={onSelect}
            />
          ))}
        </div>
      )}
    </div>
  );
}
