import { useEffect, useState } from "react";

const STEPS = [
  { label: "Input", detail: "Legal text to verify" },
  { label: "Claims", detail: "Citation-bearing sentences extracted" },
  { label: "Evidence", detail: "Matched against real statute text" },
  { label: "Verify", detail: "NLI checks claim vs. evidence" },
  { label: "Safety", detail: "Every unflagged claim must survive" },
  { label: "Correct", detail: "Only the flagged span is rewritten" },
  { label: "Re-check", detail: "Corrected text re-verified" },
  { label: "Result", detail: "Final, evidence-grounded text" },
];

/** Decorative, auto-cycling visual for the Home hero -- illustrates the
 * pipeline shape. Not wired to a live backend run (there is none on this
 * page); the Live Demo's own pipeline rail is the real, event-driven one. */
export default function PipelineShowcase() {
  const [active, setActive] = useState(0);

  useEffect(() => {
    const id = setInterval(() => setActive((v) => (v + 1) % STEPS.length), 1400);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="glass-panel relative flex flex-col gap-1 rounded-2xl p-8">
      {STEPS.map((step, idx) => {
        const isActive = idx === active;
        const isPast = idx < active;
        return (
          <div key={step.label} className="flex items-start gap-5 py-3">
            <div className="flex flex-col items-center">
              <span
                className={`flex h-4 w-4 shrink-0 rounded-full border-2 transition-all duration-500 ${
                  isActive
                    ? "border-judicial bg-judicial shadow-glow-judicial"
                    : isPast
                      ? "border-entail/60 bg-entail/60"
                      : "border-white/15 bg-transparent"
                }`}
              />
              {idx < STEPS.length - 1 && (
                <span
                  className={`my-1 h-9 w-px transition-colors duration-500 ${
                    isPast ? "bg-entail/40" : "bg-white/10"
                  }`}
                />
              )}
            </div>
            <div className={`transition-opacity duration-500 ${isActive ? "opacity-100" : "opacity-50"}`}>
              <p className="font-body text-lg font-semibold tracking-wide text-ink-primary">{step.label}</p>
              <p className="text-sm text-ink-secondary">{step.detail}</p>
            </div>
          </div>
        );
      })}
    </div>
  );
}
