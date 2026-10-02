# Track I: Center themes

**Branch:** `track/i-themes` · **Port:** 8113 · **Owns:** `static/theme.js` (new), `static/base.css`, `static/chat.css`, the theme parts of `static/admin.html`, the `applyTheme` function in `static/chat.js` (only that function), `seed/*/center.json` `theme` objects, `docs/features/themes.md`

## Goal
Each center's pages look like that center, so a parent can tell at a glance whose assistant
this is. It's a nice-to-have, so keep it tasteful and lightweight.

## Scope
- **`static/theme.js`:** `export function applyTheme(theme)` sets the `--brand-*` tokens,
  `--on-primary` contrast, the font, and a **per-center favicon**. The favicon is an inline SVG
  data URL: a rounded square in `primary`, with `logo_text` in `on-primary`. It also sets
  `<meta name="theme-color">`.
  - Move the existing logic from `chat.js` `applyTheme` here (luminance check, dark-mode
    handling), and make the `chat.js` function a one-line call to it.
  - Replace the inline theme lines in `admin.html` with an import of it.
- **Theme fields** (CONTRACTS §2 `Center.theme`): `primary`, `accent`, `background`, `font`,
  `logo_text`. You may add **optional** fields to the seed `center.json` files:
  - `surface_tint` (a subtle card tint);
  - `pattern` (one of `none|dots|stars|leaves`): a very light CSS background motif. Leaves for
    Juniper Hill, stars for Little Comets. Pure CSS/SVG data URLs, no images or CDNs.

  Missing fields must fall back gracefully. Don't change `app/` code: `theme_json` already
  passes through as is.
- **Picker:** the center cards on the picker screen preview each center's colors and badge.
- **Accessibility:** text on `primary` and on `background` must meet WCAG AA contrast (4.5:1
  for body text). Check both seed themes in light and dark mode, and say how you checked.
- **Dark mode:** keep the existing behavior (center background not applied in dark mode). The
  motif must be subtle or off in dark mode.

## Check
Picker, chat and admin pages for both centers, at 360px and 1280px wide, in light and dark
mode, with screenshots described in your summary. Confirm the favicon changes after Start over
and picking the other center.
