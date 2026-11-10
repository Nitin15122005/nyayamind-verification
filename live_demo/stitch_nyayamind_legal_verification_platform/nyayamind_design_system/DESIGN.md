---
name: NyayaMind Design System
colors:
  surface: '#0f131c'
  surface-dim: '#0f131c'
  surface-bright: '#353943'
  surface-container-lowest: '#0a0e17'
  surface-container-low: '#181b25'
  surface-container: '#1c1f29'
  surface-container-high: '#262a34'
  surface-container-highest: '#31353f'
  on-surface: '#dfe2ef'
  on-surface-variant: '#c2c6d6'
  inverse-surface: '#dfe2ef'
  inverse-on-surface: '#2c303a'
  outline: '#8c909f'
  outline-variant: '#424754'
  surface-tint: '#adc6ff'
  primary: '#adc6ff'
  on-primary: '#002e6a'
  primary-container: '#4d8eff'
  on-primary-container: '#00285d'
  inverse-primary: '#005ac2'
  secondary: '#4edea3'
  on-secondary: '#003824'
  secondary-container: '#00a572'
  on-secondary-container: '#00311f'
  tertiary: '#d0bcff'
  on-tertiary: '#3c0091'
  tertiary-container: '#a078ff'
  on-tertiary-container: '#340080'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#d8e2ff'
  primary-fixed-dim: '#adc6ff'
  on-primary-fixed: '#001a42'
  on-primary-fixed-variant: '#004395'
  secondary-fixed: '#6ffbbe'
  secondary-fixed-dim: '#4edea3'
  on-secondary-fixed: '#002113'
  on-secondary-fixed-variant: '#005236'
  tertiary-fixed: '#e9ddff'
  tertiary-fixed-dim: '#d0bcff'
  on-tertiary-fixed: '#23005c'
  on-tertiary-fixed-variant: '#5516be'
  background: '#0f131c'
  on-background: '#dfe2ef'
  surface-variant: '#31353f'
typography:
  headline-xl:
    fontFamily: Plus Jakarta Sans
    fontSize: 40px
    fontWeight: '700'
    lineHeight: 48px
    letterSpacing: -0.025em
  headline-xl-mobile:
    fontFamily: Plus Jakarta Sans
    fontSize: 30px
    fontWeight: '700'
    lineHeight: 38px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 28px
    fontWeight: '600'
    lineHeight: 36px
    letterSpacing: -0.02em
  headline-lg-mobile:
    fontFamily: Plus Jakarta Sans
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.015em
  headline-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
    letterSpacing: -0.015em
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 26px
    letterSpacing: -0.011em
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 22px
    letterSpacing: -0.006em
  body-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 18px
    letterSpacing: 0em
  label-md:
    fontFamily: JetBrains Mono
    fontSize: 13px
    fontWeight: '500'
    lineHeight: 18px
    letterSpacing: 0.02em
  label-sm:
    fontFamily: JetBrains Mono
    fontSize: 11px
    fontWeight: '500'
    lineHeight: 14px
    letterSpacing: 0.04em
  statute-citation:
    fontFamily: JetBrains Mono
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.03em
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  gutter: 1.5rem
  margin: 2rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 1rem
  space-lg: 1.5rem
  space-xl: 2.5rem
---

## Brand & Style

This design system establishes an environment of unwavering legal authority fused with cutting-edge computational verification. Engineered for legal analysts, compliance officers, and judicial examiners, the interface balances deep cognitive focus with surgical, audit-ready precision.

The aesthetic fuses **Modern Technical Minimalism** with **Refined Dark-Mode Glassmorphism**:
- **Atmosphere**: Deep slate and obsidian substrates eliminate eye fatigue during dense document verification, framing live AI reasoning graphs like an advanced mission control console.
- **Tone & Demeanor**: Rigorous, uncompromising, analytical, and authoritative.
- **Visual Mechanics**: Razor-thin structural borders, translucent layered acrylic plates, directional backlights, and telemetry-grade status indicators that instantly communicate semantic entailment, logical contradiction, and mitigation pipeline states.

## Colors

The color architecture is calibrated for zero-ambiguity verification in low-light, high-density environments. Every chromatic accent serves an explicit semantic function:

- **Substrates & Surfaces**:
  - `canvas-default`: `#090D16` (Deep Obsidian Base)
  - `canvas-subtle`: `#0D1527` (Deep Navy Slate)
  - `surface-elevated`: `rgba(15, 23, 42, 0.72)` (Translucent Dark Slate)
  - `surface-border`: `rgba(255, 255, 255, 0.08)` (Neutral Glass Boundary)
  - `surface-border-active`: `rgba(59, 130, 246, 0.35)` (Focused State)

- **Semantic Telemetry**:
  - **Judicial Electric Blue (`#3B82F6`)**: Primary actionable items, pipeline stages, selection targets, and active focus.
  - **Entailment Emerald (`#10B981`)**: Verified claims, statutory entailment, validated premises, and consensus certainty.
  - **Contradiction Amber & Coral (`#F59E0B` / `#EF4444`)**: Unsubstantiated claims, logical fallacies, policy breaches, and safety blocks.
  - **Synthetic Flow (`#8B5CF6` to `#06B6D4`)**: Reserved for live inference loops, multi-agent debates, and token generation stream visualizations.

- **Content & Text**:
  - `text-primary`: `#F8FAFC` (100% legibility on dark layers)
  - `text-secondary`: `#94A3B8` (Structural metadata, unselected facets)
  - `text-muted`: `#64748B` (Line numbers, disabled states, inactive timestamps)

## Typography

Typography establishes an evidentiary hierarchy:

1. **Plus Jakarta Sans (Headings)**: Provides contemporary structural clarity with subtly rounded terminals that balance cold algorithmic data with humanistic judicial dignity.
2. **Inter (Body & Analysis)**: Clean, neutral, high-density legibility with optical metrics engineered for scanning complex legal argumentation and dense factual briefs without visual fatigue.
3. **JetBrains Mono (Statutory Code, Metadata, Metrics)**: Renders case citations, statutory references (e.g., `42 U.S.C. § 1983`), verification scores, model confidence intervals, and token differential diffs.

All numeric values in tabular comparisons must use tabular figures (`tnum`) to ensure aligned comparisons across verification matrices.

## Layout & Spacing

The layout is built upon a balanced 12-column dynamic grid designed to facilitate synchronized multi-pane workflows:
- **Left Panel (3 columns)**: Document source inputs, claim decomposition hierarchy, and extracted premise list.
- **Center Canvas (6 columns)**: Live claim verification board, token-level delta editor, and active reasoning engine.
- **Right Panel (3 columns)**: Statutory citation lookup, confidence heatmaps, and audit logs.

### Responsive Breakpoints
- **Desktop (`>= 1440px`)**: Full 3-pane orchestration with 24px gutters and 32px canvas margins.
- **Laptop / Tablet Landscape (`1024px – 1439px`)**: Collapsible drawer for right-side audit logs; main editor and claim stream share the primary space.
- **Tablet Portrait & Mobile (`< 1024px`)**: Stacked single-column card view with persistent bottom drawer for claim verification status.

Margins scale down to `1rem` on mobile, while gutters compress to `0.75rem` to maximize screen real estate for technical audits.

## Elevation & Depth

This system avoids heavy drop shadows in favor of **Layered Glassmorphic Plates** with calibrated luminescence:

- **Level 0 (Canvas Base)**: Solid `#090D16` matte finish.
- **Level 1 (Structural Rail / Panes)**: `#0D1527` with 1px border (`rgba(255, 255, 255, 0.05)`).
- **Level 2 (Analysis & Claim Cards)**: `rgba(15, 23, 42, 0.65)` backdrop with `backdrop-filter: blur(16px)` and a subtle top-lit inner highlight (`inset 0 1px 0 0 rgba(255, 255, 255, 0.1)`).
- **Level 3 (Modal Verifiers & Inspection Drawers)**: `rgba(15, 23, 42, 0.88)` with `backdrop-filter: blur(24px)`, framed by an ambient glow:
  - Verified Focus: `0 8px 32px -4px rgba(16, 185, 129, 0.18)`
  - Contradiction Alert: `0 8px 32px -4px rgba(239, 68, 68, 0.22)`
  - Active Inference: `0 8px 32px -4px rgba(59, 130, 246, 0.22)`

Outlines remain fine (1px) and strictly structural, retaining architectural definition across overlapping panels.

## Shapes

The interface utilizes a disciplined **Soft (Scale 1)** border-radius philosophy:
- **Base Components (Inputs, Buttons, Badges)**: `4px` (`0.25rem`) to maintain an engineered, instrument-like feel.
- **Card Containers & Panels**: `8px` (`0.5rem`) for crisp compartmentalization.
- **Floating Flyouts & Dialogue Windows**: `12px` (`0.75rem`).

Pill shapes are strictly restricted to state chips and confidence score counters to separate interactive controls from analytical metadata.

## Components

### 1. Buttons
- **Primary Action (Verify / Commit Safe Edit)**:
  - Gradient background: `linear-gradient(135deg, #3B82F6 0%, #2563EB 100%)`.
  - Border: `1px solid rgba(255, 255, 255, 0.2)`.
  - Typography: `Inter`, 14px, semi-bold (`text-white`).
  - Micro-glow on hover: `0 0 16px rgba(59, 130, 246, 0.45)`.
- **Secondary / Ghost (Inspect Citation)**:
  - Background: `rgba(255, 255, 255, 0.03)`.
  - Border: `1px solid rgba(255, 255, 255, 0.1)`.
  - Hover: Background rises to `rgba(255, 255, 255, 0.07)` with border color shifting to `#3B82F6`.

### 2. Claim Verification Cards
- Multi-layer glass container showing raw claim, verified claim, source citation, and validation pipeline.
- Status bar on the card's left boundary (3px solid):
  - Emerald (`#10B981`) = Verified / Entailed.
  - Coral (`#EF4444`) = Factual Contradiction.
  - Amber (`#F59E0B`) = Unverifiable / Ambiguous.
- Interactive token diff inline: inserted legal conditions highlighted in subtle translucent emerald tags (`rgba(16, 185, 129, 0.15)`), strikethrough contradictions highlighted in translucent coral tags.

### 3. Statutory Badges & Status Chips
- Height: 22px.
- Typography: `JetBrains Mono`, 11px, medium.
- Visuals: Border `1px solid` matching state hue, inner fill at 12% opacity. Formatted as `[STATUTE: 18 U.S.C. § 1001]` or `[ENTAILMENT: 99.4%]`.

### 4. Selective Correction Diff Viewers
- Side-by-side or inline view with line numbers (`text-muted`, mono font).
- Replaced arguments feature an audit trail flyout that surfaces exact reasoning steps and precedent links on hover.

### 5. Input Fields & Prompt Consoles
- Dark background (`#0D1527`), inset border `1px solid rgba(255, 255, 255, 0.08)`.
- Focused state: Border transforms to `#3B82F6` with subtle outer blur `0 0 0 3px rgba(59, 130, 246, 0.15)`.
- Integrated mono suffix indicators displaying remaining context tokens and current compliance mode.