import CorrectionDiff from "./CorrectionDiff.jsx";
import VerdictBadge from "./VerdictBadge.jsx";

const WITHHELD_STATUSES = new Set([
  "correction_scope_violation",
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
    return (
      <div className="flex flex-col gap-4">
        <div className="flex items-center gap-2.5 rounded-lg border border-warn/30 bg-warn/10 px-5 py-3">
          <span className="h-2.5 w-2.5 rounded-full bg-warn" />
          <span className="font-mono text-sm font-semibold tracking-wider text-warn">CORRECTION WITHHELD</span>
        </div>
        <p className="text-lg leading-[1.65] text-ink-primary">{reason}</p>
        <div>
          <p className="mb-1.5 font-mono text-xs uppercase tracking-wider text-ink-secondary">
            Attempted correction (not shipped)
          </p>
          <div className="glass-panel-solid rounded-lg p-6 opacity-70">
            <CorrectionDiff before={correction.original_field_text} after={correction.regenerated_text} />
          </div>
        </div>
        <p className="text-sm text-ink-secondary">
          The original text is kept unchanged in the final result -- an unsafe edit is never shipped.
        </p>
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
