# Frontend Design Contract

## UI/UX Pro Max Evidence

### Commands executed (local)
```bash
python3 .codex/skills/ui-ux-pro-max/scripts/search.py "SaaS B2B dashboard" --domain product -n 3
python3 .codex/skills/ui-ux-pro-max/scripts/search.py "modern minimal professional" --domain style -n 3
python3 .codex/skills/ui-ux-pro-max/scripts/search.py "system font professional" --domain typography -n 3
python3 .codex/skills/ui-ux-pro-max/scripts/search.py "saas" --domain color -n 3
python3 .codex/skills/ui-ux-pro-max/scripts/search.py "accessibility form error empty state" --domain ux -n 3
python3 .codex/skills/ui-ux-pro-max/scripts/search.py "app router layout" --stack nextjs -n 3
python3 .codex/skills/ui-ux-pro-max/scripts/search.py "component architecture" --stack react -n 3
```

### Verified search evidence (local)
```text
$ python3 .codex/skills/ui-ux-pro-max/scripts/search.py "SaaS analytics dashboard" --domain product -n 3
## UI Pro Max Search Results
**Domain:** product | **Query:** SaaS analytics dashboard
**Source:** products.csv | **Found:** 3 results

### Result 1
- **Product Type:** Analytics Dashboard
- **Primary Style Recommendation:** Data-Dense + Heat Map & Heatmap
- **Dashboard Style (if applicable):** Drill-Down Analytics + Comparative
```

```text
$ python3 .codex/skills/ui-ux-pro-max/scripts/search.py "bento grid minimal" --domain style -n 3
## UI Pro Max Search Results
**Domain:** style | **Query:** bento grid minimal
**Source:** styles.csv | **Found:** 3 results

### Result 1
- **Style Category:** Bento Box Grid
- **Keywords:** Modular cards, asymmetric grid, varied sizes, Apple-style, dashboard tiles, negative space, clean hierarchy, cards
- **Primary Colors:** Neutral base + brand accent, #FFFFFF, #F5F5F5, brand primary
- **Best For:** Dashboards, product pages, portfolios, Apple-style marketing, feature showcases, SaaS
```

```text
$ python3 .codex/skills/ui-ux-pro-max/scripts/search.py "professional system" --domain typography -n 3
## UI Pro Max Search Results
**Domain:** typography | **Query:** professional system
**Source:** typography.csv | **Found:** 3 results

### Result 1
- **Font Pairing Name:** Spatial Clear
- **Heading Font:** Inter
- **Body Font:** Inter
- **Notes:** Optimized for readability on dynamic backgrounds.
```

### Top 3 summary and mapping

#### Product (SaaS B2B dashboard)
1. SaaS (General): glass/flat hybrid, data-dense dashboards, trust blue + accent contrast.
2. Micro SaaS: flat + vibrant blocks, minimal messaging, executive dashboards.
3. B2B Service: trust & authority, feature-rich, professional blue + neutral grey.
Mapping: Primary + neutral palette drives `--color-primary`, `--color-bg`, `--color-border`; data-dense/exec cues map to Card + grid layouts and structured AppShell spacing.

#### Style (modern minimal professional)
1. Soft UI Evolution: subtle depth, improved contrast, accessible shadows.
2. Swiss Modernism 2.0: modular grid, strict hierarchy, minimal accents.
3. Minimal & Direct: whitespace heavy, subtle hover, single accent CTA.
Mapping: shadows use `--shadow-xs/sm`, grids use layout tokens, CTAs use `--color-cta` with restrained hover.

#### Typography (system font professional)
1. Spatial Clear (Inter/Inter): clean, legible, system-like tone.
2. Modern Professional (Poppins/Open Sans): geometric heading + readable body.
3. Legal Professional (EB Garamond/Lato): traditional authority.
Mapping: external font hosts are disallowed, so system sans stack + weight scale replaces Google Fonts, with clear hierarchy via `--font-size-*` and `--font-weight-*`.

#### Color (saas)
1. Primary #2563EB, Secondary #3B82F6, CTA #F97316, Background #F8FAFC, Text #1E293B, Border #E2E8F0.
2. Micro SaaS repeats the same palette emphasis.
Mapping: direct hex values become core tokens; CTA is isolated to buttons/badges only.

#### UX (accessibility + error + empty state)
1. Error messages must be announced (`role="alert"`).
2. Inputs require labels (no placeholder-only fields).
3. Empty states must provide message + action.
Mapping: Input component renders labels and errors; pages include empty/error states with actionable buttons/links.

#### Stack (nextjs)
1. App Router structure with app/ directory.
2. File-based routing and layouts.
3. Fonts applied in root layout.
Mapping: use app route groups for login vs app shell; layout applies system font class only.

#### Stack (react)
1. Small, focused components.
2. Destructure props for clarity.
3. Error boundaries for runtime safety (not required for static skeleton).
Mapping: UI components are small, reusable, and props-destructured.

---

## Design Tokens (Implemented)

### Color Palette
- --color-primary: #2563EB
- --color-primary-strong: #1D4ED8
- --color-secondary: #3B82F6
- --color-cta: #F97316
- --color-on-primary: #FFFFFF
- --color-on-cta: #FFFFFF
- --color-bg: #F8FAFC
- --color-surface: #FFFFFF
- --color-surface-alt: #F1F5F9
- --color-text: #1E293B
- --color-text-muted: #475569
- --color-border: #E2E8F0
- Tints: --color-primary-soft, --color-cta-soft, --color-danger-soft, --color-success-soft
- Semantic: --color-success #16A34A, --color-warning #F59E0B, --color-danger #DC2626, --color-info #0EA5E9

### Typography
- System sans stack via `--font-sans`
- Size scale: 12/14/16/18/22/28/36 (xs to 3xl)
- Weights: 400/500/600/700
- Line height: 1.2/1.5/1.7

### Spacing
- Scale (px): 4, 8, 12, 16, 20, 24, 32, 40, 48, 64

### Radius
- --radius-sm: 8px
- --radius-md: 12px
- --radius-lg: 16px
- --radius-pill: 999px

### Shadows
- --shadow-xs: soft outline
- --shadow-sm: card elevation
- --shadow-md: hero elevation

### Borders
- --border-width: 1px

### Motion
- --transition-fast: 150ms
- --transition-medium: 240ms
- --easing-standard: cubic-bezier(0.2, 0.8, 0.2, 1)

### Focus
- --focus-ring: 0 0 0 3px rgba(37, 99, 235, 0.24)

### Layout
- --sidebar-width: 260px
- --topbar-height: 64px
- --layout-max: 1200px
- --content-narrow: 520px
- --size-search: 240px
- --size-panel-sm: 220px
- --size-panel-lg: 240px
- --size-card-min: 280px
- --size-report-min: 240px

---

## Component Rules (Implemented)

### Button
- Variants: primary (default), secondary, ghost.
- Primary uses `--color-primary` with `--color-on-primary`; hover uses `--color-primary-strong`.
- Focus uses `--focus-ring`, no layout shift.

### Input
- Always paired with `<label>`.
- Error state uses `--color-danger` border and `role="alert"` message.
- Focus ring uses `--focus-ring` and `--color-primary`.

### Card
- Surface uses `--color-surface`, border `--color-border`, shadow `--shadow-sm`.
- Soft variant uses `--color-surface-alt`.
- Alert variant uses `--color-danger-soft` + `--color-danger` border.

### Badge
- Default muted badge; semantic variants map to success/warning/danger/info tokens.

### Separator
- 1px divider using `--color-border`.

### Skeleton
- Gradient between `--color-surface-alt` and `--color-surface`.
- Animation disabled when `prefers-reduced-motion: reduce`.

### AppShell
- Sidebar and topbar use surface/background tokens.
- Active nav uses `--color-surface-alt` + inset border.
- Content area centers to `--layout-max` with consistent padding tokens.

---

## Page Contracts

### /login
- Form labels are visible; error block uses `role="alert"` and provides action.
- Uses Card + Button + Input tokens only.

### /projects
- Empty state includes message + CTA + alternate action.
- No hard-coded spacing or colors; all via tokens/classes.

### /projects/[projectId]/chat
- Three-column workspace layout.
- Message composer has label (sr-only allowed) and visible focus state.

### /projects/[projectId]/report
- Error state includes Retry + Return actions.
- Report cards show placeholders using Skeleton.

---

## Usage Rules
- Do not introduce new colors or spacing values outside `tokens.css`.
- All UI components must use token-backed classes (no inline hex/radius/spacing).
- No external font hosts; system font only.
