import { useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, BookOpenCheck, ShieldCheck, Sparkles } from "lucide-react";
import NavBar from "../components/NavBar.jsx";
import PipelineShowcase from "../components/PipelineShowcase.jsx";
import Lightbox from "../components/Lightbox.jsx";

const FIGURES = [
  { src: "/figures/verification_accuracy.png", title: "Verifier accuracy", caption: "Verifier accuracy on a controlled, labeled benchmark." },
  { src: "/figures/correction_outcomes.png", title: "Correction outcomes", caption: "Correction outcomes across evaluated candidates." },
  { src: "/figures/evidence_coverage.png", title: "Evidence coverage", caption: "Evidence coverage across the statute pool." },
];

const CAPABILITIES = [
  ["Deterministic claim extraction", "Citation-bearing sentences are decomposed into independently checkable claims."],
  ["Evidence-grounded verification", "Each claim is checked against retrieved statutory text using NLI verification."],
  ["Programmatic safety gates", "A correction ships only when the required safety conditions pass."],
  ["Selective correction", "Only the flagged sentence is rewritten; untouched claims are checked again."],
];

export default function Home() {
  const [openFigure, setOpenFigure] = useState(null);

  return (
    <div className="min-h-screen">
      <NavBar />
      <main className="mx-auto flex w-[94vw] max-w-[1440px] flex-col gap-9 pb-12">
        <section className="flex flex-col items-center px-4 pt-7 text-center sm:pt-9 lg:pt-10">
          <div className="mb-3 inline-flex items-center gap-2 rounded-full bg-slate-100 px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.14em] text-judicial">
            <span className="h-2 w-2 rounded-full bg-judicial" />
            Evidence-grounded legal verification
          </div>

          <h1 className="max-w-4xl font-display text-2xl font-bold leading-[1.1] tracking-[-0.03em] text-ink-primary sm:text-2xl lg:text-[40px]">
            Verify legal claims.
            <br />
            <span className="text-judicial">Correct only when it is safe.</span>
          </h1>

          <p className="mt-3 max-w-2xl text-xs leading-5 text-ink-secondary sm:text-base">
            NyayaMind decomposes legal text into atomic claims, grounds them against statutory
            evidence, verifies each relationship, and applies selective correction only when its
            safety gates pass.
          </p>

          <div className="mt-4 flex flex-wrap items-center justify-center gap-2.5">
            <Link
              to="/demo"
              className="inline-flex items-center gap-2 rounded-xl bg-primary-container px-4 py-2.5 text-xs font-semibold text-white shadow-md transition-all hover:-translate-y-0.5 hover:shadow-lg"
            >
              Run Live Verification <ArrowRight className="h-4 w-4" />
            </Link>
            <a
              href="#architecture"
              className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-xs font-semibold text-ink-primary shadow-sm transition-colors hover:bg-slate-50"
            >
              Explore the pipeline
            </a>
          </div>
        </section>

        <section id="architecture" className="px-2 sm:px-4">
          <div className="mb-4 flex flex-col gap-1">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-judicial">How it works</p>
            <h2 className="font-display text-lg font-semibold tracking-tight text-ink-primary sm:text-xl">
              One legal passage. Multiple verification layers.
            </h2>
            <p className="max-w-2xl text-xs leading-5 text-ink-secondary">
              A transparent pipeline from input to evidence, NLI verification, safety validation and final result.
            </p>
          </div>
          <PipelineShowcase />
        </section>

        <section className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
          {CAPABILITIES.map(([title, body], i) => (
            <div key={title} className="glass-panel rounded-xl p-3">
              <div className="mb-3 flex h-8 w-8 items-center justify-center rounded-xl bg-primary-fixed text-judicial">
                {i === 0 ? <BookOpenCheck className="h-4 w-4" /> : i === 1 ? <Sparkles className="h-5 w-5" /> : <ShieldCheck className="h-5 w-5" />}
              </div>
              <h3 className="font-display text-xs font-semibold text-ink-primary">{title}</h3>
              <p className="mt-1.5 text-[11px] leading-4 text-ink-secondary">{body}</p>
            </div>
          ))}
        </section>

        <section>
          <div className="mb-4 flex items-end justify-between gap-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-judicial">Evaluation</p>
              <h2 className="mt-2 font-display text-xl font-semibold tracking-tight text-ink-primary">
                Measured on real evaluation data
              </h2>
            </div>
          </div>
          <div className="grid gap-2 sm:grid-cols-3">
            {FIGURES.map((f) => (
              <button
                key={f.src}
                type="button"
                onClick={() => setOpenFigure(f)}
                className="glass-panel group overflow-hidden rounded-xl text-left transition-all hover:-translate-y-0.5 hover:shadow-lg"
              >
                <div className="overflow-hidden bg-slate-50">
                  <img src={f.src} alt={f.caption} className="w-full object-contain transition-transform duration-300 group-hover:scale-[1.02]" />
                </div>
                <div className="border-t border-slate-200 px-3 py-3">
                  <p className="text-sm font-semibold text-ink-primary">{f.title}</p>
                  <p className="mt-1 text-[11px] leading-4 text-ink-secondary">{f.caption}</p>
                </div>
              </button>
            ))}
          </div>
        </section>

        <section className="glass-panel flex flex-col items-center rounded-2xl px-5 py-7 text-center sm:px-10">
          <span className="mb-3 rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold uppercase tracking-wider text-judicial">
            Live research pipeline
          </span>
          <h2 className="font-display text-xl font-semibold tracking-tight text-ink-primary sm:text-2xl">
            See a real claim move through the pipeline.
          </h2>
          <p className="mt-1.5 max-w-xl text-xs leading-5 text-ink-secondary">
            Use a prepared scenario or paste your own legal passage and inspect every verification stage.
          </p>
          <Link
            to="/demo"
            className="mt-4 inline-flex items-center gap-2 rounded-xl bg-primary-container px-5 py-3 text-sm font-semibold text-white shadow-md hover:shadow-lg"
          >
            Open Live Demo <ArrowRight className="h-4 w-4" />
          </Link>
        </section>
      </main>
      <Lightbox figure={openFigure} onClose={() => setOpenFigure(null)} />
    </div>
  );
}
