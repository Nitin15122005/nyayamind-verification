const STYLES = {
  ENTAILED: "bg-entail/15 text-entail border-entail/40",
  CONTRADICTED: "bg-contra/15 text-contra border-contra/40",
  NOT_ENOUGH_INFORMATION: "bg-warn/15 text-warn border-warn/40",
  NO_EVIDENCE: "bg-slate-100 text-ink-secondary border-slate-200",
};

const LABELS = {
  ENTAILED: "ENTAILED",
  CONTRADICTED: "CONTRADICTED",
  NOT_ENOUGH_INFORMATION: "NOT ENOUGH INFO",
  NO_EVIDENCE: "NO EVIDENCE",
};

export default function VerdictBadge({ verdict, confidence }) {
  if (!verdict) return null;
  const cls = STYLES[verdict] || STYLES.NO_EVIDENCE;
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 font-mono text-[9px] font-semibold tracking-wide ${cls}`}
    >
      {LABELS[verdict] || verdict}
      {typeof confidence === "number" && (
        <span className="tnum opacity-80">{(confidence * 100).toFixed(1)}%</span>
      )}
    </span>
  );
}
