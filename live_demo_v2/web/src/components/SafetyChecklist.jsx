export default function SafetyChecklist({ checks }) {
  if (!checks || checks.length === 0) {
    return <p className="text-base text-ink-secondary">No safety checks were run.</p>;
  }
  return (
    <ul className="flex flex-col gap-2.5">
      {checks.map((c, idx) => {
        const pass = c.result === "PASS";
        return (
          <li
            key={idx}
            className={`animate-rise-in rounded-lg border px-5 py-4 ${
              pass ? "border-entail/25 bg-entail/[0.06]" : "border-contra/25 bg-contra/[0.06]"
            }`}
            style={{ animationDelay: `${idx * 60}ms` }}
          >
            <div className="flex items-center justify-between gap-3">
              <span className="text-base font-semibold text-ink-primary">{c.name}</span>
              <span
                className={`shrink-0 rounded-full px-3 py-1 font-mono text-xs font-semibold tracking-wider ${
                  pass ? "bg-entail/15 text-entail" : "bg-contra/15 text-contra"
                }`}
              >
                {c.result}
              </span>
            </div>
            <p className="mt-1.5 text-sm leading-[1.5] text-ink-secondary">{c.detail}</p>
          </li>
        );
      })}
    </ul>
  );
}
