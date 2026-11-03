import CorrectionDiff from "./CorrectionDiff.jsx";
import VerdictBadge from "./VerdictBadge.jsx";

const WITHHELD_STATUSES = new Set([
  "correction_scope_violation",
  "correction_output_invalid",
  "correction_sentence_splice_unavailable",
  "correction_sibling_regression",
  "correction_ordinal_ambiguous",
  "correction_unauthorized_addition",
  "correction_failed",
  "correction_splice_unavailable",
  "correction_span_invalid",
  "correction_structural_span_lost",
]);

export default function ResultBanner({ record, safetyChecks }) {
  const correction = record?.correction || {};
  const status = correction.status;
  const counts = record?.verification?.counts || {};

  if (status === "corrected") {
    const reverif = correction.reverification;
    return (
      <div className="flex flex-col gap-4">
        <div className="flex items-center gap-2.5 rounded-lg border border-entail/30 bg-entail/10 px-5 py-3">
          <span className="h-2.5 w-2.5 rounded-full bg-entail" />
          <span className="font-mono text-sm font-semibold tracking-wider text-entail">CORRECTION APPLIED</span>
        </div>
        <div className="flex flex-col gap-3">
          <div>
            <p className="mb-1.5 font-mono text-xs uppercase tracking-wider text-ink-secondary">Original → Corrected</p>
            <div className="glass-panel-solid rounded-lg p-6">
              <CorrectionDiff before={correction.original_field_text} after={correction.regenerated_text} />
            </div>
          </div>
          {reverif && (
            <div>
              <p className="mb-1.5 font-mono text-xs uppercase tracking-wider text-ink-secondary">Re-verified</p>
              <div className="glass-panel-solid flex items-center gap-3 rounded-lg p-6">
                <VerdictBadge verdict={reverif.verdict} confidence={reverif.confidence} />
                <span className="text-sm text-ink-secondary">against its own evidence.</span>
              </div>
            </div>
          )}
        </div>
      </div>
    );
  }

  if (status && WITHHELD_STATUSES.has(status)) {
    const blockedCheck = (safetyChecks || []).find((c) => c.result === "BLOCK");
    const reason = blockedCheck?.detail || "Safety conditions were not satisfied.";
    const notAttempted = status === "correction_span_invalid";
    const rawOutputRejected = status === "correction_output_invalid" || status === "correction_splice_unavailable";
    const correctedParagraph = correction.corrected_paragraph;
    return (
      <div className="flex flex-col gap-4">
        <div className="flex items-center gap-2.5 rounded-lg border border-warn/30 bg-warn/10 px-5 py-3">
          <span className="h-2.5 w-2.5 rounded-full bg-warn" />
          <span className="font-mono text-sm font-semibold tracking-wider text-warn">
            {notAttempted ? "CORRECTION NOT ATTEMPTED" : "CORRECTION WITHHELD"}
          </span>
        </div>
        <p className="text-lg leading-[1.65] text-ink-primary">{reason}</p>
        {Array.isArray(correction.sibling_regressions) && correction.sibling_regressions.length > 0 && (
          <div className="rounded-lg border border-warn/25 bg-warn/5 p-3">
            <p className="font-mono text-xs font-semibold uppercase tracking-wider text-warn">
              Sibling claims requiring attention
            </p>
            <div className="mt-2 flex flex-col gap-2">
              {correction.sibling_regressions.map((item, index) => (
                <div key={item.claim_id || index} className="rounded-md border border-slate-200 bg-white p-2.5">
                  <p className="text-sm leading-5 text-ink-primary">{item.claim_text || "Claim could not be matched after correction."}</p>
                  <p className="mt-1 font-mono text-[10px] text-ink-secondary">
                    {item.baseline_verdict || "Original verdict"} → {item.verdict || "UNVERIFIABLE"}
                    {item.reason ? ` · ${item.reason.replace(/_/g, " ")}` : ""}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}
        {!notAttempted && correctedParagraph && (
          <div>
            <p className="mb-1.5 font-mono text-xs uppercase tracking-wider text-ink-secondary">
              Candidate paragraph (not shipped)
            </p>
            <div className="glass-panel-solid rounded-lg p-6 opacity-70">
              <CorrectionDiff before={correction.original_field_text} after={correctedParagraph} />
            </div>
          </div>
        )}
        {!notAttempted && rawOutputRejected && correction.regenerated_text && (
          <div>
            <p className="mb-1.5 font-mono text-xs uppercase tracking-wider text-ink-secondary">
              Rejected model output
            </p>
            <div className="glass-panel-solid rounded-lg p-4 opacity-70">
              <p className="whitespace-pre-wrap text-sm leading-6 text-ink-primary">{correction.regenerated_text}</p>
            </div>
          </div>
        )}
        <p className="text-sm text-ink-secondary">
          The original text is kept unchanged in the final result. An unvalidated correction is never shipped.
        </p>
        <div>
          <p className="mb-1.5 font-mono text-xs uppercase tracking-wider text-ink-secondary">
            Final text (original retained)
          </p>
          <div className="glass-panel-solid rounded-lg p-5">
            <p className="text-base leading-7 text-ink-primary">{record?.final_field?.text}</p>
          </div>
        </div>
      </div>
    );
  }

  // Verification-only outcome (mode B, or mode C where no claim triggered correction).
  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center gap-2.5 rounded-lg border border-judicial/30 bg-judicial/10 px-5 py-3">
        <span className="h-2.5 w-2.5 rounded-full bg-judicial" />
        <span className="font-mono text-sm font-semibold tracking-wider text-judicial-soft">
          VERIFICATION COMPLETE
        </span>
      </div>
      <div className="flex flex-wrap gap-2">
        {counts.ENTAILED > 0 && (
          <span className="rounded-full border border-entail/30 bg-entail/10 px-3.5 py-1.5 text-sm font-medium text-entail">
            {counts.ENTAILED} entailed
          </span>
        )}
        {counts.CONTRADICTED > 0 && (
          <span className="rounded-full border border-contra/30 bg-contra/10 px-3.5 py-1.5 text-sm font-medium text-contra">
            {counts.CONTRADICTED} contradicted
          </span>
        )}
        {counts.NOT_ENOUGH_INFORMATION > 0 && (
          <span className="rounded-full border border-warn/30 bg-warn/10 px-3.5 py-1.5 text-sm font-medium text-warn">
            {counts.NOT_ENOUGH_INFORMATION} not enough info
          </span>
        )}
        {counts.NO_EVIDENCE > 0 && (
          <span className="rounded-full border border-slate-200 bg-slate-100 px-3.5 py-1.5 text-sm font-medium text-ink-secondary">
            {counts.NO_EVIDENCE} no evidence found
          </span>
        )}
        {Object.values(counts).every((v) => !v) && (
          <span className="rounded-full border border-slate-200 bg-slate-100 px-3.5 py-1.5 text-sm font-medium text-ink-secondary">
            No citation-bearing statutory claims were found in this text.
          </span>
        )}
      </div>
      <div>
        <p className="mb-1.5 font-mono text-xs uppercase tracking-wider text-ink-secondary">Final text</p>
        <div className="glass-panel-solid rounded-lg p-6">
          <p className="text-lg font-medium leading-[1.65] text-ink-primary">{record?.final_field?.text}</p>
        </div>
      </div>
    </div>
  );
}
