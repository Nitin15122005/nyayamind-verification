import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { AlertTriangle, CheckCircle2, FileCheck2, GitCompareArrows, ShieldAlert, ShieldCheck } from "lucide-react";

const SAMPLES = [
  { id: "entailed_34_2003_760", label: "Supported Claim", eyebrow: "Verified / ENTAILED", description: "A citation whose claimed content genuinely matches the statute text.", icon: CheckCircle2, tone: "green" },
  { id: "contradicted_148_1997_1306", label: "Contradicted Claim", eyebrow: "Citation mismatch", description: "The claim conflicts with what its cited statutory provision actually says.", icon: AlertTriangle, tone: "red" },
  { id: "mixed_2011_625", label: "Insufficient Evidence", eyebrow: "Uncertain / NO EVIDENCE", description: "Shows a genuine neutral result alongside a claim outside the evidence corpus.", icon: FileCheck2, tone: "amber" },
  { id: "correction_scripted_ship_1994_495", label: "Selective Correction", eyebrow: "Safe edit / SHIPS", description: "The flagged Section 302 claim is corrected while the untouched sentence remains unchanged.", icon: GitCompareArrows, tone: "blue" },
  { id: "correction_scripted_block_1994_495", label: "Unsafe Correction", eyebrow: "Scope violation / BLOCKED", description: "The correction also changes unrelated text, so the safety gate withholds the edit.", icon: ShieldAlert, tone: "red" },
  { id: "assertion_aware_1955_32", label: "Assertion-Aware Correction", eyebrow: "Targeted fix / BLOCKED", description: "The target fragment re-verifies, but an untouched sibling claim causes the safety gate to block it.", icon: ShieldCheck, tone: "purple" },
];

const MENU_WIDTH = 360;
const VIEWPORT_MARGIN = 10;
const toneClasses = {
  green: "bg-emerald-50 text-emerald-700 border-emerald-200",
  red: "bg-red-50 text-red-700 border-red-200",
  amber: "bg-amber-50 text-amber-700 border-amber-200",
  blue: "bg-blue-50 text-blue-700 border-blue-200",
  purple: "bg-violet-50 text-violet-700 border-violet-200",
};

export default function SampleMenu({ examples, onPick, disabled }) {
  const [open, setOpen] = useState(false);
  const [pos, setPos] = useState(null);
  const buttonRef = useRef(null);
  const menuRef = useRef(null);

  function computePosition() {
    const btn = buttonRef.current;
    if (!btn) return;
    const rect = btn.getBoundingClientRect();
    const menuHeight = menuRef.current?.offsetHeight ?? 360;
    const spaceBelow = Math.max(120, window.innerHeight - rect.bottom - VIEWPORT_MARGIN - 8);
    const spaceAbove = Math.max(120, rect.top - VIEWPORT_MARGIN - 8);
    const openUpward = spaceBelow < 300 && spaceAbove > spaceBelow;
    const availableHeight = Math.max(180, openUpward ? spaceAbove : spaceBelow);
    let left = rect.right - MENU_WIDTH;
    left = Math.max(VIEWPORT_MARGIN, Math.min(left, window.innerWidth - MENU_WIDTH - VIEWPORT_MARGIN));
    const top = openUpward
      ? Math.max(VIEWPORT_MARGIN, rect.top - Math.min(menuHeight, availableHeight) - 8)
      : rect.bottom + 8;
    setPos({ top, left, maxHeight: availableHeight });
  }

  useLayoutEffect(() => {
    if (!open) return;
    computePosition();
    const id = requestAnimationFrame(computePosition);
    return () => cancelAnimationFrame(id);
  }, [open]);

  useEffect(() => {
    if (!open) return undefined;
    function closeOnOutside(e) {
      if (!buttonRef.current?.contains(e.target) && !menuRef.current?.contains(e.target)) setOpen(false);
    }
    function closeOnKey(e) { if (e.key === "Escape") setOpen(false); }
    function handleViewportScroll() { computePosition(); }
    function handleResize() { setOpen(false); }
    document.addEventListener("mousedown", closeOnOutside);
    document.addEventListener("keydown", closeOnKey);
    window.addEventListener("scroll", handleViewportScroll, true);
    window.addEventListener("resize", handleResize);
    return () => {
      document.removeEventListener("mousedown", closeOnOutside);
      document.removeEventListener("keydown", closeOnKey);
      window.removeEventListener("scroll", handleViewportScroll, true);
      window.removeEventListener("resize", handleResize);
    };
  }, [open]);

  const byId = Object.fromEntries((examples || []).map((e) => [e.id, e]));
  function pick(id) {
    const example = byId[id];
    if (!example) return;
    onPick(example);
    setOpen(false);
  }

  return (
    <>
      <button
        ref={buttonRef}
        type="button"
        disabled={disabled}
        onClick={() => setOpen((v) => !v)}
        className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-xs font-semibold text-ink-primary shadow-sm transition-all hover:border-judicial/30 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40"
      >
        <FileCheck2 className="h-3.5 w-3.5 text-judicial" />
        Fill Sample
        <span className="text-slate-400">⌄</span>
      </button>

      {open && createPortal(
        <div
          ref={menuRef}
          style={{
            position: "fixed",
            top: pos?.top ?? -9999,
            left: pos?.left ?? -9999,
            width: "min(360px, calc(100vw - 20px))",
            maxHeight: pos?.maxHeight ? `${pos.maxHeight}px` : "360px",
            overflowY: "auto",
            visibility: pos ? "visible" : "hidden",
          }}
          className="z-50 animate-rise-in rounded-lg border border-slate-200 bg-white p-1 shadow-xl"
        >
          <div className="px-2 pb-1.5 pt-1">
            <p className="text-[9px] font-semibold uppercase tracking-[0.12em] text-judicial">Guided test cases</p>
            <h3 className="mt-0.5 font-display text-xs font-semibold text-ink-primary">Choose what you want to demonstrate</h3>
            <p className="mt-0.5 text-[10px] leading-3.5 text-ink-secondary">
              Each sample maps to a real evaluation scenario already supported by the live pipeline.
            </p>
          </div>

          <div className="grid gap-0.5">
            {SAMPLES.map((sample) => {
              const Icon = sample.icon;
              const available = Boolean(byId[sample.id]);
              return (
                <button
                  key={sample.id}
                  type="button"
                  disabled={!available}
                  onClick={() => pick(sample.id)}
                  className="group flex w-full items-start gap-2 rounded-md border border-transparent p-1.5 text-left transition-all hover:border-slate-200 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40"
                >
                  <span className={`mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-lg border ${toneClasses[sample.tone]}`}>
                    <Icon className="h-3.5 w-3.5" />
                  </span>
                  <span className="min-w-0">
                    <span className="block text-xs font-semibold text-ink-primary">{sample.label}</span>
                    <span className="mt-0.5 block text-[9px] font-semibold uppercase tracking-wider text-ink-muted">{sample.eyebrow}</span>
                    <span className="mt-0.5 block text-[10px] leading-3.5 text-ink-secondary">{sample.description}</span>
                  </span>
                  <span className="ml-auto pt-1 text-slate-300 transition-colors group-hover:text-judicial">→</span>
                </button>
              );
            })}
          </div>
        </div>,
        document.body,
      )}
    </>
  );
}
