import { useState } from "react";
import { Link } from "react-router-dom";
import NavBar from "../components/NavBar.jsx";
import PipelineShowcase from "../components/PipelineShowcase.jsx";
import Lightbox from "../components/Lightbox.jsx";

const FIGURES = [
  {
    src: "/figures/verification_accuracy.png",
    title: "Verifier accuracy",
    caption: "Verifier accuracy on a controlled, labeled benchmark.",
  },
  {
    src: "/figures/correction_outcomes.png",
    title: "Correction outcomes",
    caption: "Correction outcomes across every evaluated candidate.",
  },
  {
    src: "/figures/evidence_coverage.png",
    title: "Evidence coverage",
    caption: "Evidence coverage across the statute pool.",
  },
];

const CAPABILITIES = [
  {
    title: "Deterministic claim extraction",
    body: "Every citation-bearing sentence becomes its own atomic, independently-checkable claim.",
  },
  {
    title: "Evidence-grounded verification",
    body: "Claims are checked against real statute text with an NLI model -- never a guess.",
  },
  {
    title: "Programmatic safety gates",
    body: "A correction ships only if every unflagged claim survives untouched and re-verification passes.",
  },
  {
    title: "Selective, surgical correction",
    body: "Only the flagged span is rewritten -- the rest of the paragraph is provably unchanged.",
  },
];

export default function Home() {
  const [openFigure, setOpenFigure] = useState(null);

  return (
    <div className="min-h-screen">
      <NavBar />

      <main className="mx-auto flex w-[96vw] max-w-[2200px] flex-col gap-28 pb-32 pt-16 sm:pt-24">
        <section className="grid items-center gap-16 lg:grid-cols-2">
          <div className="flex flex-col items-start">
            <h1 className="font-display text-6xl font-extrabold leading-[1.03] tracking-tight text-ink-primary sm:text-7xl lg:text-8xl">
              NYAYAMIND
            </h1>
            <p className="mt-6 font-display text-2xl font-medium text-ink-secondary sm:text-3xl">
              Evidence-Grounded Legal Claim Verification &amp; Safe Selective Correction
            </p>
            <p className="mt-6 max-w-2xl text-lg leading-relaxed text-ink-secondary">
              NyayaMind checks legal claims against retrieved evidence, verifies their relationship, and
              applies correction only when safety conditions are satisfied.
            </p>
            <Link
              to="/demo"
              className="mt-10 rounded-xl bg-gradient-to-br from-judicial to-judicial-dim px-9 py-4 font-body text-lg font-semibold text-white shadow-glow-judicial transition-transform hover:scale-[1.03]"
            >
              RUN LIVE DEMO →
            </Link>
          </div>
          <PipelineShowcase />
        </section>

        <section className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {CAPABILITIES.map((c) => (
            <div key={c.title} className="glass-panel rounded-2xl p-7">
              <h3 className="font-display text-lg font-semibold text-ink-primary">{c.title}</h3>
              <p className="mt-3 text-base leading-relaxed text-ink-secondary">{c.body}</p>
            </div>
          ))}
        </section>

        <section>
          <h2 className="mb-9 text-center font-display text-3xl font-semibold text-ink-primary">
            Measured on real evaluation data
          </h2>
          <div className="grid gap-7 sm:grid-cols-3">
            {FIGURES.map((f) => (
              <button
                key={f.src}
                type="button"
                onClick={() => setOpenFigure(f)}
                className="glass-panel group overflow-hidden rounded-2xl text-left transition-transform hover:scale-[1.015] hover:shadow-glow-judicial"
              >
                <div className="overflow-hidden bg-white/5">
                  <img
                    src={f.src}
                    alt={f.caption}
                    className="w-full object-contain transition-transform duration-300 group-hover:scale-105"
                  />
                </div>
                <div className="px-5 py-5">
                  <p className="text-lg font-medium text-ink-primary">{f.title}</p>
                  <p className="mt-1 text-sm text-ink-secondary">{f.caption}</p>
                </div>
              </button>
            ))}
          </div>
        </section>

        <section className="flex flex-col items-center gap-5 rounded-2xl border border-judicial/20 bg-judicial/[0.06] px-10 py-16 text-center">
          <h2 className="font-display text-4xl font-semibold text-ink-primary">See it verify a real claim.</h2>
          <p className="max-w-lg text-lg text-ink-secondary">
            Paste your own legal text, or run one of the prepared scenarios -- the real pipeline executes live.
          </p>
          <Link
            to="/demo"
            className="mt-3 rounded-xl bg-gradient-to-br from-judicial to-judicial-dim px-9 py-4 font-body text-lg font-semibold text-white shadow-glow-judicial transition-transform hover:scale-[1.03]"
          >
            RUN LIVE DEMO →
          </Link>
        </section>
      </main>

      <Lightbox figure={openFigure} onClose={() => setOpenFigure(null)} />
    </div>
  );
}
