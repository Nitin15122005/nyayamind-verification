import { Link, useLocation } from "react-router-dom";

export default function NavBar() {
  const { pathname } = useLocation();
  const isHome = pathname === "/";
  const isDemo = pathname === "/demo";

  return (
    <header className="sticky top-0 z-40 border-b border-white/5 bg-canvas/85 backdrop-blur-panel">
      <div className="mx-auto flex w-[96vw] max-w-[2200px] items-center justify-between py-5 sm:py-6">
        <Link to="/" className="flex items-center gap-3">
          <img
            src="/logo.png"
            alt="NyayaMind"
            className="h-9 w-9 shrink-0 object-contain sm:h-10 sm:w-10"
          />
          <span className="font-display text-[22px] font-extrabold tracking-wide text-ink-primary sm:text-2xl">
            NYAYAMIND
          </span>
        </Link>
        <nav className="flex items-center gap-2 font-body text-sm font-medium uppercase tracking-wider sm:text-base">
          <Link
            to="/"
            className={`rounded-lg px-4 py-2.5 transition-colors ${
              isHome ? "bg-white/[0.07] text-ink-primary" : "text-ink-secondary hover:text-ink-primary"
            }`}
          >
            Home
          </Link>
          <Link
            to="/demo"
            className={`rounded-lg px-4 py-2.5 transition-colors ${
              isDemo ? "bg-judicial/15 text-judicial-soft" : "text-ink-secondary hover:text-ink-primary"
            }`}
          >
            Live Demo
          </Link>
        </nav>
      </div>
    </header>
  );
}
