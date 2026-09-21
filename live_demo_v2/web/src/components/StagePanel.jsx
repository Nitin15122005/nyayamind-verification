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
    <p className="text-base text-ink-secondary">
      No citation-bearing statutory claims were found in this text.
    </p>
  );
}

function ClaimsView({ data, underlying }) {
  const claims = data?.claims || [];
  if (claims.length === 0) return <EmptyClaims />;
  const groups = groupBySentence(claims);
  return (
    <div className="flex flex-col gap-4">
      <p className="text-sm text-ink-secondary">
        {claims.length} claim{claims.length === 1 ? "" : "s"} extracted from {groups.length} sentence
        {groups.length === 1 ? "" : "s"}.
      </p>
      {underlying && (
        <div className="glass-panel-solid rounded-lg p-6">
          <p className="mb-1.5 font-mono text-xs uppercase tracking-wider text-ink-secondary">Source text</p>
          <p className="text-lg font-medium leading-[1.65] text-ink-primary">{data?.source_text}</p>
        </div>
      )}
      <div className="flex flex-col gap-3">
        {groups.map((g, idx) => (
          <div key={idx} className="animate-rise-in rounded-lg border border-white/8 bg-white/[0.02] p-5" style={{ animationDelay: `${idx * 50}ms` }}>
            <p className="text-lg font-medium leading-[1.65] text-ink-primary">{g.sentence}</p>
            <div className="mt-3 flex flex-wrap gap-1.5">
              {g.claims.map((c) => (
                <span
                  key={c.claim_id}
                  className="rounded-full border border-judicial/25 bg-judicial/10 px-2.5 py-1 font-mono text-xs text-judicial-soft"
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
    <div className="flex flex-col gap-3">
      {claims.map((c, idx) => (
        <div
          key={c.claim_id}
          className="animate-rise-in rounded-lg border border-white/8 bg-white/[0.02] p-5"
          style={{ animationDelay: `${idx * 50}ms` }}
        >
          <div className="flex items-center justify-between gap-2">
            <span className="font-mono text-xs text-judicial-soft">{citationLabel(c.citation_extracted)}</span>
            {!c.evidence_text && (
              <span className="rounded-full border border-white/15 bg-white/5 px-2 py-0.5 font-mono text-xs text-ink-secondary">
                NO EVIDENCE FOUND
              </span>
            )}
          </div>
          <p className="mt-2.5 text-lg font-medium leading-[1.65] text-ink-primary">{c.claim_text}</p>
          {c.evidence_text ? (
            <div className="mt-3 border-l-2 border-entail/40 pl-4">
              <p className="text-lg leading-[1.65] text-ink-secondary">{c.evidence_text}</p>
              {underlying && (
                <p className="mt-1.5 font-mono text-xs uppercase tracking-wider text-ink-muted">
                  matched via {c.evidence_match_method}
                </p>
              )}
            </div>
          ) : (
            <p className="mt-3 text-base text-ink-secondary">
              No sufficient evidence found in the statute pool for this citation.
              {underlying && c.no_evidence_category ? ` (${c.no_evidence_category})` : ""}
            </p>
          )}
        </div>
      ))}
    </div>
  );
}

function VerificationView({ data, underlying }) {
  const claims = data?.claims || [];
  if (claims.length === 0) return <EmptyClaims />;
  return (
    <div className="flex flex-col gap-3">
      {claims.map((c, idx) => (
        <div
          key={c.claim_id}
          className="animate-rise-in rounded-lg border border-white/8 bg-white/[0.02] p-5"
          style={{ animationDelay: `${idx * 50}ms` }}
        >
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="font-mono text-xs text-judicial-soft">{citationLabel(c.citation_extracted)}</span>
            <VerdictBadge verdict={c.verdict} confidence={c.confidence} />
          </div>
          <p className="mt-2.5 text-lg font-medium leading-[1.65] text-ink-primary">{c.claim_text}</p>
          {c.evidence_text && <p className="mt-2 text-lg leading-[1.65] text-ink-secondary">{c.evidence_text}</p>}
          {underlying && c.raw_scores && (
            <div className="mt-3 flex gap-3 font-mono text-xs text-ink-secondary">
              {Object.entries(c.raw_scores).map(([k, v]) => (
                <span key={k}>
                  {k}: {typeof v === "number" ? v.toFixed(4) : String(v)}
                </span>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

function CorrectionView({ data, underlying }) {
  if (!data?.triggered) {
    return <p className="text-base text-ink-secondary">No correction was attempted for this run.</p>;
  }
  return (
    <div className="flex flex-col gap-3">
      <p className="text-sm text-ink-secondary">
        A candidate correction was generated for the flagged claim. It has not yet been validated or shipped --
        see Safety and Re-check.
      </p>
      <div className="glass-panel-solid rounded-lg p-6">
        <CorrectionDiff before={data.original_field_text} after={data.regenerated_text} />
      </div>
      {underlying && (
        <p className="font-mono text-xs text-ink-secondary">model: {data.corr_meta?.model}</p>
      )}
    </div>
  );
}

function SafetyView({ data }) {
  if (!data?.triggered) {
    return (
      <p className="text-base text-ink-secondary">
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
    <div className="glass-panel-solid flex flex-col gap-2 rounded-lg p-6">
      <div className="flex items-center gap-3">
        <VerdictBadge verdict={data.verdict} confidence={data.confidence} />
        <span className="text-sm text-ink-secondary">re-verified against its own evidence.</span>
      </div>
      <p className="text-lg font-medium leading-[1.65] text-ink-primary">{data.claim_text}</p>
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
      <div className="glass-panel rounded-2xl p-7">
        <p className="font-mono text-sm font-semibold uppercase tracking-wider text-contra">Run failed</p>
        <p className="mt-2.5 text-lg text-ink-secondary">{error}</p>
      </div>
    );
  }

  if (!viewedStage) {
    return (
      <div className="glass-panel flex min-h-[320px] flex-1 flex-col items-center justify-center rounded-2xl p-8 text-center">
        <p className="text-lg text-ink-secondary">
          Press <span className="text-ink-primary">Run Verification</span> to execute the real pipeline.
        </p>
      </div>
    );
  }

  const data = stageData[viewedStage];
  const canToggleUnderlying = ["claims", "evidence", "verification", "correction"].includes(viewedStage);

  return (
    <div className="glass-panel flex-1 rounded-2xl p-6 sm:p-8">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="font-mono text-xs uppercase tracking-wider text-ink-secondary">Active Stage</p>
          <h3 className="font-display text-2xl font-semibold text-ink-primary">{STAGE_TITLES[viewedStage]}</h3>
        </div>
        {canToggleUnderlying && (
          <button
            type="button"
            onClick={onToggleUnderlying}
            className="rounded-md border border-white/10 bg-white/[0.03] px-4 py-2.5 font-body text-sm font-medium text-ink-secondary transition-colors hover:border-judicial/50 hover:text-ink-primary"
          >
            {underlying ? "Hide Underlying Processing" : "Show Underlying Processing"}
          </button>
        )}
      </div>

      {!data && <p className="text-lg text-ink-secondary">Waiting for this stage to complete…</p>}

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
