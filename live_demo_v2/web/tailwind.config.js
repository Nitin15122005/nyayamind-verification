/** Tailwind theme extended with nyayamind_design_system/DESIGN.md's own
 * tokens (colors, type scale) -- referenced as a visual starting point,
 * not copied markup. */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        canvas: "#090D16",
        "canvas-subtle": "#0D1527",
        surface: "#0f131c",
        "surface-elevated": "rgba(15, 23, 42, 0.72)",
        "surface-container": "#1c1f29",
        "surface-container-high": "#262a34",
        border: {
          DEFAULT: "rgba(255, 255, 255, 0.08)",
          active: "rgba(59, 130, 246, 0.35)",
        },
        ink: {
          primary: "#F8FAFC",
          secondary: "#94A3B8",
          muted: "#64748B",
        },
        judicial: {
          DEFAULT: "#3B82F6",
          dim: "#2563EB",
          soft: "#adc6ff",
        },
        entail: {
          DEFAULT: "#10B981",
          soft: "rgba(16, 185, 129, 0.15)",
        },
        contra: {
          DEFAULT: "#EF4444",
          soft: "rgba(239, 68, 68, 0.15)",
        },
        warn: {
          DEFAULT: "#F59E0B",
          soft: "rgba(245, 158, 11, 0.15)",
        },
        tertiary: "#d0bcff",
      },
      fontFamily: {
        display: ["Plus Jakarta Sans", "Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        body: [
          "Inter",
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "sans-serif",
        ],
        sans: [
          "Inter",
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "sans-serif",
        ],
        mono: ["JetBrains Mono", "ui-monospace", "monospace"],
      },
      backdropBlur: {
        panel: "16px",
        modal: "24px",
      },
      boxShadow: {
        "glow-judicial": "0 8px 32px -4px rgba(59, 130, 246, 0.22)",
        "glow-entail": "0 8px 32px -4px rgba(16, 185, 129, 0.18)",
        "glow-contra": "0 8px 32px -4px rgba(239, 68, 68, 0.22)",
      },
      keyframes: {
        pulseGlow: {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.55" },
        },
        flowLine: {
          "0%": { backgroundPosition: "0% 0%" },
          "100%": { backgroundPosition: "200% 0%" },
        },
        riseIn: {
          "0%": { opacity: "0", transform: "translateY(8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        "pulse-glow": "pulseGlow 1.4s ease-in-out infinite",
        "flow-line": "flowLine 1.6s linear infinite",
        "rise-in": "riseIn 0.35s ease-out",
      },
    },
  },
  plugins: [],
};
