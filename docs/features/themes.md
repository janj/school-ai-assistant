# Center themes (Track I)

Each center's pages carry its look: colors, font, a light background motif, and a per-center favicon.

## How it works
- `static/theme.js` exports `applyTheme(theme)`. `chat.js` (`applyTheme` is a one-line wrapper) and
  `admin.html` both call it with `session.center.theme`. `applyTheme(null)` (the picker) resets everything.
- It sets `--brand-primary`, `--brand-accent`, `--brand-bg`, `--brand-font`, `--on-primary`,
  plus `--surface-tint` and `--brand-pattern`. `base.css` has neutral defaults for all of them, so any missing
  field falls back gracefully.
- `--on-primary` is white or near-black, whichever has the higher contrast ratio against `primary`.
- Favicon: an inline SVG data URL (rounded square in `primary`, `logo_text` in `--on-primary`), plus
  `<meta name="theme-color">`. Both are removed on the picker.
- Optional seed fields in `theme`: `surface_tint` (tints bot bubbles, composer, picker cards) and
  `pattern` (`none|dots|stars|leaves`; Juniper Hill = leaves, Little Comets = stars). The motif is an SVG tile at 7%
  opacity of `primary`, applied on `body`.
- Dark mode: the center background, tint and motif are **not** applied (dark palette from `base.css` stays).
  Primary, accent and font still apply. `applyTheme` re-runs if the OS scheme changes.

## Decisions
- `.chat` background is now transparent so the body motif shows through (the body already has `--brand-bg`).
- The admin header now uses `--on-primary` instead of hard-coded white, so a light `primary` stays readable.
- Picker cards preview each center through the tinted card and its `primary` stripe (CSS only).
  A `logo_text` badge on the card needs a small change in the picker code of `chat.js` (not in this track's scope).

## Contrast check (WCAG, computed with the relative-luminance formula)
Light: text `#1d1d1f` on background 15.3 (JH) / 15.6 (LC), on the worst motif tile 13.9 / 13.7; muted text 5.5 / 5.6
(4.98 / 4.92 on the motif tile); `primary` as link color on background 5.8 / 13.5; on-primary text 6.4 / 14.6.
Dark: accent links on `#151515` 5.5 / 11.9; text on surface 13.9; muted 6.3; on-primary header text 6.4 / 14.6.
All pass 4.5:1. Non-text only: the Comets accent border on the light background is 1.4:1 (decorative; text inside the
card passes), and the Comets navy header nearly merges with the dark page (text on it still 14.6:1).
