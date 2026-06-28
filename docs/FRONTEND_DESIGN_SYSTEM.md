# Frontend Design System

## Fonts (System Stack by Default)
- Current: use the system font stack via `--font-sans`; we do not ship a brand font file yet.
- Entry point: `frontend/app/globals.css` applies `font-family: var(--font-sans)` and tokens define the stack.
- Future release: add the local font asset + license record, then set `REQUIRE_BRAND_FONT=1` to enforce the gate (local woff2 + `next/font/local`).
- External font hosts/CDNs are not allowed (e.g., Google Fonts domains or third-party font CDNs).

## Theme Tokens
- Tokens live in `frontend/styles/tokens.css`.
- Light defaults are defined on `:root`.
- Dark overrides are defined on `:root.dark` and `:root[data-theme="dark"]`.
- Tokens include: `--bg`, `--fg`, `--card`, `--border`, `--muted`, `--muted-fg`, `--primary`, `--cta`.

## Global Styles
- `frontend/app/globals.css` imports `../styles/tokens.css`.
- Single entrypoint: `layout.tsx` -> `app/globals.css` -> `styles/tokens.css` (removed `frontend/styles/globals.css` floating entry).
- Baseline UI (background, text, borders, font) derives from tokens.
- Avoid duplicating competing global styles; prefer updating `tokens.css`.

## Guard Test
- `npm run test` runs `frontend/scripts/asset-guard.mjs`.
- It blocks banned external font/CDN references, verifies dark token rules exist, enforces the tokens import, and only requires the local font when `REQUIRE_BRAND_FONT=1`.
