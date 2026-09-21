// Layers 3/5 of the site-wide background atmosphere (see src/styles/index.css
// for layers 1/2/4 -- base, ambient orbs, grid). Rendered once at the app
// root so it never remounts on navigation between Home/Live Demo.
//
// Deliberately CSS-only motion (transform + opacity), no JavaScript
// animation loop, no canvas/WebGL -- a couple dozen tiny absolutely
// positioned nodes animated purely by the browser's compositor, which is
// negligible next to the real Python/GPU work the live demo already does.
// Fixed, pointer-events: none, and z-index below every card, so it can
// never intercept a click or push layout.

const PARTICLE_COUNT = 22;
const HUES = ["rgba(173,198,255,", "rgba(6,200,235,", "rgba(217,160,65,", "rgba(255,255,255,"];

// Deterministic pseudo-random spread (no Math.random -- keeps the layout
// identical between server/client renders and across reloads) using two
// coprime-ish multipliers so positions don't visibly line up in a grid.
const PARTICLES = Array.from({ length: PARTICLE_COUNT }, (_, i) => {
  const left = (i * 37 + (i % 5) * 11 + 4) % 100;
  const top = (i * 53 + (i % 7) * 13 + 6) % 100;
  const size = 1 + (i % 3); // 1-3px
  const opacity = 0.15 + ((i * 7) % 5) * 0.035; // ~0.15-0.30
  const duration = 20 + (i % 6) * 3; // 20-35s
  const delay = -((i * 2.3) % duration); // negative delay staggers start mid-cycle
  const hue = HUES[i % HUES.length];
  return { left, top, size, opacity, duration, delay, hue, key: i };
});

export default function AmbientBackground() {
  return (
    <div className="pointer-events-none fixed inset-0 z-[-1] overflow-hidden" aria-hidden="true">
      <div className="ambient-sweep absolute -inset-1/4 opacity-[0.035]" style={{ animation: "lightSweep 32s ease-in-out infinite alternate" }}>
        <div
          className="h-full w-full"
          style={{
            background: "linear-gradient(100deg, transparent 40%, rgba(148, 197, 255, 0.5) 50%, transparent 60%)",
            filter: "blur(60px)",
          }}
        />
      </div>
      {PARTICLES.map((p) => (
        <span
          key={p.key}
          className="ambient-particle absolute rounded-full"
          style={{
            left: `${p.left}%`,
            top: `${p.top}%`,
            width: p.size,
            height: p.size,
            backgroundColor: `${p.hue}${p.opacity})`,
            boxShadow: `0 0 ${p.size * 3}px ${p.hue}${p.opacity * 0.6})`,
            "--p-op": p.opacity,
            opacity: p.opacity,
            animation: `particleDrift ${p.duration}s ease-in-out infinite`,
            animationDelay: `${p.delay}s`,
          }}
        />
      ))}
    </div>
  );
}
