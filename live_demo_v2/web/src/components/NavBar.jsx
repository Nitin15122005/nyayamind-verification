import { Link, useLocation } from "react-router-dom";

export default function NavBar() {
  const { pathname } = useLocation();
  const isHome = pathname === "/";
  const isDemo = pathname === "/demo";

  return (
    <header className="sticky top-0 z-40 border-b border-slate-200 bg-canvas/85 backdrop-blur-panel">
      <div className="mx-auto flex w-[96vw] max-w-[2200px] items-center justify-between py-1.5 sm:py-2">
        <Link to="/" className="flex items-center gap-2.5">
          <img
            src="/logo.png"
            alt="NyayaMind"
            className="h-6.5 w-6.5 shrink-0 object-contain sm:h-7 sm:w-7"
          />
          <span className="font-display text-[14px] font-bold tracking-tight text-ink-primary sm:text-sm">
            NYAYAMIND
          </span>
        </Link>
        <nav className="flex items-center gap-1.5 font-body text-xs font-medium sm:text-sm">
          <Link
            to="/"
            className={`rounded-lg px-2.5 py-1 transition-colors ${
              isHome ? "bg-slate-100 text-ink-primary" : "text-ink-secondary hover:bg-slate-50 hover:text-ink-primary"
            }`}
          >
            Home
          </Link>
          <Link
            to="/demo"
            className={`rounded-lg px-2.5 py-1.5 transition-colors ${
              isDemo ? "bg-judicial text-white shadow-sm" : "text-ink-secondary hover:text-ink-primary"
            }`}
          >
            Live Demo
          </Link>
        </nav>
      </div>
    </header>
  );
}
