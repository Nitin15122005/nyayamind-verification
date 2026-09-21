import { useEffect } from "react";
import { createPortal } from "react-dom";

/** Premium full-screen figure viewer. Never shows a filename or path --
 * only the caption already given to it. Closes on Escape or backdrop click.
 * Portaled directly onto document.body so it is never nested inside a
 * scrolled page section (a fixed-position element deep in a tall page can
 * otherwise get dragged into an unwanted scroll-into-view by the browser). */
export default function Lightbox({ figure, onClose }) {
  useEffect(() => {
    if (!figure) return undefined;
    function onKey(e) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("keydown", onKey);
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = prevOverflow;
    };
  }, [figure, onClose]);

  if (!figure) return null;

  return createPortal(
    <div
      className="fixed inset-0 z-50 flex animate-rise-in items-center justify-center bg-canvas/80 p-6 backdrop-blur-modal"
      onClick={onClose}
    >
      <div
        className="relative flex max-h-[85vh] w-full max-w-4xl flex-col overflow-hidden rounded-2xl border border-white/10 bg-canvas-subtle shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <button
          type="button"
          onClick={onClose}
          aria-label="Close"
          className="absolute right-4 top-4 z-10 flex h-9 w-9 items-center justify-center rounded-full border border-white/15 bg-canvas/80 text-ink-secondary transition-colors hover:border-white/30 hover:text-ink-primary"
        >
          ✕
        </button>
        <div className="flex items-center justify-center overflow-hidden bg-white/[0.03] p-6">
          <img src={figure.src} alt={figure.caption} className="max-h-[55vh] w-auto object-contain" />
        </div>
        <div className="border-t border-white/8 px-6 py-4">
          <h3 className="font-display text-base font-semibold text-ink-primary">{figure.title}</h3>
          <p className="mt-1 text-sm text-ink-secondary">{figure.caption}</p>
        </div>
      </div>
    </div>,
    document.body,
  );
}
