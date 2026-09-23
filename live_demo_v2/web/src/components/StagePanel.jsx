import VerdictBadge from "./VerdictBadge.jsx";
import SafetyChecklist from "./SafetyChecklist.jsx";
import CorrectionDiff from "./CorrectionDiff.jsx";
import ResultBanner from "./ResultBanner.jsx";

function groupBySentence(claims) {
  const order = [];
  const bySentence = new Map();
  for (const c of claims || []) {
    if (!bySentence.has(c.claim_text)) {
      bySentence.set(c.claim_text, []);
      order.push(c.claim_text);
    }
    bySentence.get(c.claim_text).push(c);
  }
  return order.map((sentence) => ({ sentence, claims: bySentence.get(sentence) }));
}

function citationLabel(citation) {
  if (!citation) return "No citation";
  const parts = [citation.provision_type, citation.provision_number];
  if (citation.subsection) parts.push(`(${citation.subsection})`);
  return parts.filter(Boolean).join(" ");
}

function EmptyClaims() {
  return (
    <p className="text-xs text-ink-secondary">
      No citation-bearing statutory claims were found in this text.
    </p>
  );
}

function ClaimsView({ data, underlying }) {
  const claims = data?.claims || [];
  if (claims.length === 0) return <EmptyClaims />;
  const groups = groupBySentence(claims);
  return (
    <div className="flex flex-col gap-1.5">
      <p className="text-sm text-ink-secondary">
        {claims.length} claim{claims.length === 1 ? "" : "s"} extracted from {groups.length} sentence
        {groups.length === 1 ? "" : "s"}.
      </p>
      {underlying && (
        <div className="glass-panel-solid rounded-lg p-3">
          <p className="mb-1.5 font-mono text-xs uppercase tracking-wider text-ink-secondary">Source text</p>
          <p className="text-xs font-medium leading-5 text-ink-primary">{data?.source_text}</p>
        </div>
      )}
      <div className="flex flex-col gap-2">
        {groups.map((g, idx) => (
          <div key={idx} className="animate-rise-in rounded-lg border border-slate-200 bg-white p-2.5 nm-claim-card" style={{ animationDelay: `${idx * 50}ms` }}>
            <p className="text-xs font-medium leading-5 text-ink-primary">{g.sentence}</p>
            <div className="mt-2 flex flex-wrap gap-1">
              {g.claims.map((c) => (
                <span
                  key={c.claim_id}
                  className="rounded-full border border-judicial/25 bg-judicial/10 px-1.5 py-0.5 font-mono text-[9px] text-judicial-soft"
                >
                  {citationLabel(c.citation_extracted)}
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function EvidenceView({ data, underlying }) {
  const claims = data?.claims || [];
  if (claims.length === 0) return <EmptyClaims />;
  return (
    <div className="flex flex-col gap-2">
      {claims.map((c, idx) => (
        <div
          key={c.claim_id}
          className={`animate-rise-in rounded-lg border border-slate-200 bg-white p-2.5 nm-claim-card`}
          style={{ animationDelay: `${idx * 50}ms` }}
        >
          <div className="flex items-center justify-between gap-2">
            <span className="font-mono text-[10px] text-judicial-soft">{citationLabel(c.citation_extracted)}</span>
            {!c.evidence_text && (
              <span className="rounded-full border border-slate-200 bg-slate-100 px-2 py-0.5 font-mono text-[10px] text-ink-secondary">
                NO EVIDENCE FOUND
              </span>
            )}
          </div>
          <p className="mt-1.5 text-xs font-medium leading-5 text-ink-primary">{c.claim_text}</p>
          {c.evidence_text ? (
            <div className="mt-2 border-l-2 border-entail/40 pl-3">
              <p className="text-xs leading-5 text-ink-secondary">{c.evidence_text}</p>
              {underlying && (
                <p className="mt-1 font-mono text-[10px] uppercase tracking-wider text-ink-muted">
                  matched via {c.evidence_match_method}
                </p>
              )}
            </div>
          ) : (
            <p className="mt-2 text-sm text-ink-secondary">
              No sufficient evidence found in the statute pool for this citation.
              {underlying && c.no_evidence_category ? ` (${c.no_evidence_category})` : ""}
            </p>
          )}
        </div>
      ))}
    </div>
  );
}


function TraceRow({ label, value, tone = "neutral" }) {
  const toneClass = {
    neutral: "border-slate-200 bg-slate-50 text-ink-secondary",
    pass: "border-entail/25 bg-entail/10 text-entail",
    warn: "border-warn/25 bg-warn/10 text-warn",
    block: "border-contra/25 bg-contra/10 text-contra",
    judicial: "border-judicial/25 bg-judicial/10 text-judicial-soft",
  }[tone] || "border-slate-200 bg-slate-50 text-ink-secondary";

  return (
    <div className={"flex flex-wrap items-center justify-between gap-1 rounded border px-1.5 py-0.5 " + toneClass}>
      <span className="font-mono text-[8px] uppercase tracking-wide opacity-80">{label}</span>
      <span className="font-mono text-[8px] font-semibold">{value}</span>
    </div>
  );
}

function claimCardClass(verdict) {
  switch (verdict) {
    case "CONTRADICTED":
      return "border-contra/25 bg-red-50/70 border-l-4 border-l-contra";
    case "ENTAILED":
      return "border-entail/25 bg-emerald-50/70 border-l-4 border-l-entail";
    case "NOT_ENOUGH_INFORMATION":
      return "border-warn/25 bg-amber-50/70 border-l-4 border-l-warn";
    case "NO_EVIDENCE":
      return "border-slate-200 bg-slate-50/80 border-l-4 border-l-slate-300";
    default:
      return "border-slate-200 bg-white";
  }
}

function VerificationTrace({ claim, underlying }) {
  const triggered = Boolean(claim.correction_trigger);
  const triggerReason = claim.correction_trigger_reason || "none";
  const subReason =
    claim.sub_reason ||
    (claim.verdict === "NO_EVIDENCE" ? "not_applicable" : "genuine_high_confidence");

  return (
    <div className="mt-2.5 rounded-lg border border-slate-200 bg-slate-50 p-2.5">
      <div className="mb-1 flex items-center justify-between gap-1.5">
        <p className="font-mono text-[10px] font-semibold uppercase tracking-wider text-ink-secondary">
          Decision trace
        </p>
        <span className={
          "rounded-full border px-2 py-0.5 font-mono text-[10px] font-semibold " +
          (triggered
            ? "border-warn/30 bg-warn/10 text-warn"
            : "border-entail/25 bg-entail/10 text-entail")
        }>
          {triggered ? "CORRECTION ELIGIBLE" : "CORRECTION NOT ELIGIBLE"}
        </span>
      </div>

      <div className="grid gap-0.5 sm:grid-cols-2">
        <TraceRow label="Verdict" value={claim.verdict || "not verified"} tone={claim.verdict === "CONTRADICTED" ? "block" : claim.verdict === "ENTAILED" ? "pass" : "neutral"} />
        <TraceRow label="Confidence" value={typeof claim.confidence === "number" ? claim.confidence.toFixed(4) : "—"} />
        <TraceRow label="Sub-reason" value={subReason} />
        <TraceRow label="Trigger reason" value={triggerReason} tone={triggered ? "warn" : "neutral"} />
      </div>

      <div className="mt-1 rounded border border-slate-200 bg-white p-1.5">
        <p className="font-mono text-[8px] uppercase tracking-wider text-ink-muted">Policy evaluation</p>
        <p className="mt-0.5 text-[10px] leading-4 text-ink-secondary">
          {triggered
            ? triggerReason === "contradicted"
              ? "CONTRADICTED is an approved automatic-correction trigger."
              : "NOT_ENOUGH_INFORMATION is eligible only because sub_reason = low_confidence."
            : claim.verdict === "NOT_ENOUGH_INFORMATION"
              ? "High-confidence NEI is treated as genuine uncertainty and does not trigger correction."
              : claim.verdict === "NO_EVIDENCE"
                ? "NO_EVIDENCE has no NLI premise and never triggers correction."
                : "This verdict does not satisfy an approved correction trigger."}
        </p>
      </div>

      {underlying && (
        <>
          <div className="mt-1.5 grid gap-0.5 sm:grid-cols-2">
            <TraceRow label="Verifier model" value={claim.verifier_model || "unknown"} />
            <TraceRow label="Evidence method" value={claim.evidence_match_method || "none"} />
            <TraceRow label="Input truncated" value={claim.input_truncated === null || claim.input_truncated === undefined ? "not recorded" : String(claim.input_truncated)} />
            <TraceRow label="Claim ID" value={claim.claim_id || "unknown"} />
          </div>

          {claim.assertion_text && claim.assertion_text !== claim.claim_text && (
            <div className="mt-2 rounded-md border border-judicial/20 bg-judicial/5 p-2">
              <p className="font-mono text-[9px] uppercase tracking-wider text-judicial-soft">Narrow assertion candidate</p>
              <p className="mt-0.5 text-xs leading-5 text-ink-secondary">{claim.assertion_text}</p>
            </div>
          )}

          {Array.isArray(claim.assertion_spans) && claim.assertion_spans.length > 0 && (
            <div className="mt-2 rounded-md border border-slate-200 bg-white p-2">
              <p className="font-mono text-[11px] uppercase tracking-wider text-ink-muted">Assertion spans</p>
              <div className="mt-1.5 flex flex-wrap gap-1.5">
                {claim.assertion_spans.map((span, i) => (
                  <span key={i} className="rounded-full border border-slate-200 bg-slate-50 px-2 py-0.5 font-mono text-[10px] text-ink-secondary">
                    {span}
                  </span>
                ))}
              </div>
            </div>
          )}

          {claim.raw_scores && (
            <div className="mt-2">
              <p className="mb-1 font-mono text-[9px] uppercase tracking-wider text-ink-muted">Raw NLI scores</p>
              <div className="grid gap-2 sm:grid-cols-3">
                {Object.entries(claim.raw_scores).map(([k, v]) => (
                  <TraceRow key={k} label={k} value={typeof v === "number" ? v.toFixed(4) : String(v)} />
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function VerificationView({ data, underlying }) {
  const claims = data?.claims || [];
  if (claims.length === 0) return <EmptyClaims />;
  return (
    <div className="flex flex-col gap-2">
      <div className="rounded-md border border-judicial/20 bg-judicial/5 p-2">
        <p className="font-mono text-[11px] uppercase tracking-wider text-judicial-soft">Correction trigger policy</p>
        <p className="mt-0.5 text-[11px] leading-4 text-ink-secondary">
          Trigger only for <span className="text-ink-primary">CONTRADICTED</span> or
          <span className="text-ink-primary"> NOT_ENOUGH_INFORMATION + low_confidence</span>.
          Genuine high-confidence NEI and NO_EVIDENCE do not trigger.
        </p>
      </div>
      {claims.map((c, idx) => (
        <div
          key={c.claim_id}
          className={`animate-rise-in rounded-md border p-2 nm-verification-card ${claimCardClass(c.verdict)}`}
          style={{ animationDelay: idx * 50 + "ms" }}
        >
          <div className="flex flex-wrap items-center justify-between gap-1.5">
            <span className="font-mono text-[9px] text-judicial-soft">{citationLabel(c.citation_extracted)}</span>
            <VerdictBadge verdict={c.verdict} confidence={c.confidence} />
          </div>
          <p className="mt-1 text-xs font-medium leading-5 text-ink-primary">{c.claim_text}</p>
          {c.evidence_text && (
            <div className="mt-1.5 border-l-2 border-entail/40 pl-2.5">
              <p className="text-[11px] leading-4 text-ink-secondary">{c.evidence_text}</p>
            </div>
          )}
          <VerificationTrace claim={c} underlying={underlying} />
        </div>
      ))}
    </div>
  );
}

function CorrectionView({ data, underlying }) {
  if (!data?.triggered) {
    return (
      <div className="rounded-lg border border-entail/20 bg-entail/5 p-4">
        <p className="font-mono text-[11px] uppercase tracking-wider text-entail">Correction decision</p>
        <p className="mt-1 text-sm text-ink-secondary">
          No correction was attempted because no claim had an approved trigger reason.
        </p>
      </div>
    );
  }
  return (
    <div className="flex flex-col gap-3">
      <div className="rounded-lg border border-warn/25 bg-warn/10 p-2.5">
        <p className="font-mono text-[11px] uppercase tracking-wider text-warn">Correction decision</p>
        <p className="mt-1 text-sm leading-6 text-ink-secondary">
          Claim <span className="font-mono text-ink-primary">{data.triggered_for_claim_id || "unknown"}</span>
          {" "}was selected because the approved trigger reason is{" "}
          <span className="font-mono font-semibold text-warn">{data.trigger_reason || "unknown"}</span>.
        </p>
      </div>
      <div className="glass-panel-solid rounded-lg p-4">
        <CorrectionDiff before={data.original_field_text} after={data.regenerated_text} />
      </div>
      {underlying && (
        <div className="grid gap-2 sm:grid-cols-2">
          <TraceRow label="Attempts" value={String(data.attempts ?? "—")} />
          <TraceRow label="Correction mode" value={data.correction_mode || "unknown"} />
          <TraceRow label="Model" value={data.corr_meta?.model || "unknown"} />
          <TraceRow label="Fragment only" value={String(Boolean(data.fragment_only))} />
        </div>
      )}
    </div>
  );
}

function SafetyView({ data }) {
  if (!data?.triggered) {
    return (
      <p className="text-xs text-ink-secondary">
        No claim met the correction trigger condition -- safety gates were not evaluated.
      </p>
    );
  }
  return (
    <div className="flex flex-col gap-3">
      <p className="text-sm text-ink-secondary">
        Validating the candidate correction from the previous stage, before it is trusted enough to re-verify.
      </p>
      <SafetyChecklist checks={data.checks} />
    </div>
  );
}

function RecheckView({ data }) {
  if (!data?.triggered) {
    return <p className="text-base text-ink-secondary">Not applicable -- no correction was attempted.</p>;
  }
  if (!data.verdict) return <p className="text-base text-ink-secondary">The corrected text could not be re-verified.</p>;
  return (
    <div className="glass-panel-solid flex flex-col gap-1.5 rounded-lg p-4">
      <div className="flex items-center gap-3">
        <VerdictBadge verdict={data.verdict} confidence={data.confidence} />
        <span className="text-sm text-ink-secondary">re-verified against its own evidence.</span>
      </div>
      <p className="text-sm font-medium leading-6 text-ink-primary">{data.claim_text}</p>
    </div>
  );
}

const STAGE_TITLES = {
  input: "Input",
  claims: "Claim Extraction",
  evidence: "Evidence Retrieval",
  verification: "NLI Verification",
  safety: "Safety Gates",
  correction: "Selective Correction",
  recheck: "Re-verification",
  result: "Final Result",
};

export default function StagePanel({ viewedStage, stageData, underlying, onToggleUnderlying, error }) {
  if (error) {
    return (
      <div className="glass-panel rounded-xl p-4">
        <p className="font-mono text-sm font-semibold uppercase tracking-wider text-contra">Run failed</p>
        <p className="mt-1.5 text-xs text-ink-secondary">{error}</p>
      </div>
    );
  }

  if (!viewedStage) {
    return (
      <div className="glass-panel flex min-h-[220px] flex-1 flex-col items-center justify-center rounded-xl p-5 text-center">
        <p className="text-sm text-ink-secondary">
          Press <span className="text-ink-primary">Run Verification</span> to execute the real pipeline.
        </p>
      </div>
    );
  }

  const data = stageData[viewedStage];
  const canToggleUnderlying = ["claims", "evidence", "verification", "correction"].includes(viewedStage);

  return (
    <div className="glass-panel flex-1 rounded-xl p-2.5 sm:p-3 nm-stage-enter">
      <div className="mb-1.5 flex flex-wrap items-center justify-between gap-1.5">
        <div>
          <p className="font-mono text-[10px] uppercase tracking-wider text-ink-secondary">Active Stage</p>
          <h3 className="font-display text-base font-semibold text-ink-primary">{STAGE_TITLES[viewedStage]}</h3>
        </div>
        {canToggleUnderlying && (
          <button
            type="button"
            onClick={onToggleUnderlying}
            className="rounded-md border border-slate-200 bg-slate-50 px-2.5 py-1.5 font-body text-[10px] font-medium text-ink-secondary transition-colors hover:border-judicial/50 hover:text-ink-primary"
          >
            {underlying ? "Hide Underlying Processing" : "Show Underlying Processing"}
          </button>
        )}
      </div>

      {!data && <p className="text-sm text-ink-secondary">Waiting for this stage to complete…</p>}

      {data && viewedStage === "claims" && <ClaimsView data={data} underlying={underlying} />}
      {data && viewedStage === "evidence" && <EvidenceView data={data} underlying={underlying} />}
      {data && viewedStage === "verification" && <VerificationView data={data} underlying={underlying} />}
      {data && viewedStage === "safety" && <SafetyView data={data} />}
      {data && viewedStage === "correction" && <CorrectionView data={data} underlying={underlying} />}
      {data && viewedStage === "recheck" && <RecheckView data={data} />}
      {data && viewedStage === "result" && <ResultBanner record={data.record} safetyChecks={data.safety_checks} />}
    </div>
  );
}
