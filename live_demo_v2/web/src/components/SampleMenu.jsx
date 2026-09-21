import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

/** Maps the 5 requested categories onto real, already-curated example ids
 * (server/app.py EXAMPLE_SPECS) -- never invents a new example. */
const CATEGORY_TO_EXAMPLE_ID = {
  "Supported Claim": "entailed_34_2003_760",
  "Contradicted Claim": "contradicted_148_1997_1306",
  "Insufficient Evidence": "mixed_2011_625",
  "Selective Correction": "correction_scripted_ship_1994_495",
  "Assertion-Aware Correction": "assertion_aware_1955_32",
};

const MENU_WIDTH = 320; // 280-360px range
const VIEWPORT_MARGIN = 12;

export default function SampleMenu({ examples, onPick, disabled }) {
  const [open, setOpen] = useState(false);
  const [pos, setPos] = useState(null); // {top, left, openUpward}
  const buttonRef = useRef(null);
  const menuRef = useRef(null);

  // Every left column and the right column ("Live Processing") each sit
  // inside a `.glass-panel` element, which uses backdrop-filter -- per the
  // CSS spec, backdrop-filter creates a new stacking context on the box it's
  // applied to. That means a z-index set on this dropdown while it is still
  // a DOM descendant of the input card's own .glass-panel can never paint
  // above a *sibling* .glass-panel panel (Live Processing, the result
  // card) that appears later in source order, no matter how high the
  // z-index value is -- the ancestor's own stacking context traps it.
  // Portaling straight onto document.body removes the dropdown from that
  // ancestor's stacking context entirely, so its own z-index governs
  // directly against the whole page.
  function computePosition() {
    const btn = buttonRef.current;
    if (!btn) return;
    const rect = btn.getBoundingClientRect();
    const menuHeight = menuRef.current?.offsetHeight ?? 340;
    const spaceBelow = window.innerHeight - rect.bottom;
    const openUpward = spaceBelow < menuHeight + VIEWPORT_MARGIN && rect.top > menuHeight + VIEWPORT_MARGIN;

    // Right-align to the button's right edge, clamped inside the viewport.
    let left = rect.right - MENU_WIDTH;
    left = Math.max(VIEWPORT_MARGIN, Math.min(left, window.innerWidth - MENU_WIDTH - VIEWPORT_MARGIN));

    const top = openUpward ? rect.top - menuHeight - 8 : rect.bottom + 8;
    setPos({ top, left, openUpward });
  }

  useLayoutEffect(() => {
    if (!open) return;
    computePosition();
    // Recompute once more after the menu has actually rendered (its real
    // height may differ from the fallback estimate above).
    const id = requestAnimationFrame(computePosition);
    return () => cancelAnimationFrame(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  useEffect(() => {
    if (!open) return undefined;
    function onDocClick(e) {
      if (
        buttonRef.current && !buttonRef.current.contains(e.target) &&
        menuRef.current && !menuRef.current.contains(e.target)
      ) {
        setOpen(false);
      }
    }
    function onKey(e) {
      if (e.key === "Escape") setOpen(false);
    }
    // A dropdown anchored by measured coordinates can't track scroll/resize
    // continuously without extra complexity -- closing on either is the
    // simplest correct behavior (standard for viewport-anchored menus) and
    // guarantees it never ends up stale/misplaced.
    function onScrollOrResize() {
      setOpen(false);
    }
    document.addEventListener("mousedown", onDocClick);
    document.addEventListener("keydown", onKey);
    window.addEventListener("scroll", onScrollOrResize, true);
    window.addEventListener("resize", onScrollOrResize);
    return () => {
      document.removeEventListener("mousedown", onDocClick);
      document.removeEventListener("keydown", onKey);
      window.removeEventListener("scroll", onScrollOrResize, true);
      window.removeEventListener("resize", onScrollOrResize);
    };
  }, [open]);

  const byId = Object.fromEntries((examples || []).map((e) => [e.id, e]));

  return (
    <>
      <button
        ref={buttonRef}
        type="button"
        disabled={disabled}
        onClick={() => setOpen((v) => !v)}
        className="rounded-md border border-white/10 bg-white/[0.03] px-4 py-2.5 font-body text-sm font-medium text-ink-secondary transition-colors hover:border-judicial/50 hover:bg-white/[0.07] hover:text-ink-primary disabled:opacity-40"
      >
        Fill Sample ▾
      </button>
      {open &&
        createPortal(
          <div
            ref={menuRef}
            style={{
              position: "fixed",
              top: pos?.top ?? -9999,
              left: pos?.left ?? -9999,
              width: MENU_WIDTH,
              visibility: pos ? "visible" : "hidden",
            }}
            className="z-50 animate-rise-in rounded-lg border border-white/10 bg-canvas-subtle p-2 shadow-2xl ring-1 ring-black/40"
          >
            {Object.entries(CATEGORY_TO_EXAMPLE_ID).map(([label, id]) => {
              const ex = byId[id];
              return (
                <button
                  key={id}
                  type="button"
                  disabled={!ex}
                  onClick={() => {
                    if (!ex) return;
                    onPick(ex);
                    setOpen(false);
                  }}
                  className="flex w-full flex-col gap-1 rounded-md px-3.5 py-3 text-left transition-colors hover:bg-white/[0.06] disabled:opacity-40"
                >
                  <span className="text-base font-medium text-ink-primary">{label}</span>
                  <span className="text-sm text-ink-muted">
                    {ex?.headline ? ex.headline.slice(0, 70) + (ex.headline.length > 70 ? "…" : "") : "Loading…"}
                  </span>
                </button>
              );
            })}
          </div>,
          document.body,
        )}
    </>
  );
}
