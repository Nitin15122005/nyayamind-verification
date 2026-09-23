/** Tailwind theme extended with nyayamind_design_system/DESIGN.md's own
 * tokens (colors, type scale) -- referenced as a visual starting point,
 * not copied markup. */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        canvas: "#F8F9F7",
        "canvas-subtle": "#FFFFFF",
        surface: "#FFFFFF",
        "primary-fixed": "#DCE8F7",
        "primary-container": "#0F172A",
        "surface-elevated": "#FFFFFF",
        "surface-container": "#F1F3F1",
        "surface-container-high": "#E8EBE8",
        border: {
          DEFAULT: "#DDE2E0",
          active: "rgba(0, 88, 190, 0.25)",
        },
        ink: {
          primary: "#0F172A",
          secondary: "#475569",
          muted: "#64748B",
        },
        judicial: {
          DEFAULT: "#0058BE",
          dim: "#00479A",
          soft: "#0058BE",
        },
        entail: {
          DEFAULT: "#059669",
          soft: "rgba(16, 185, 129, 0.15)",
        },
        contra: {
          DEFAULT: "#DC2626",
          soft: "rgba(239, 68, 68, 0.15)",
        },
        warn: {
          DEFAULT: "#D97706",
          soft: "rgba(245, 158, 11, 0.15)",
        },
        tertiary: "#B45309",
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
        "glow-judicial": "0 8px 24px -8px rgba(0, 88, 190, 0.24)",
        "glow-entail": "0 8px 24px -8px rgba(5, 150, 105, 0.16)",
        "glow-contra": "0 8px 24px -8px rgba(220, 38, 38, 0.16)",
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
