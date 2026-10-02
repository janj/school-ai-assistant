// Per-center theming: --brand-* tokens, contrast color, font, motif, favicon, theme-color.
// Every field is optional; missing ones fall back to the defaults in base.css.

const PROPS = ["--brand-primary", "--brand-accent", "--brand-bg", "--brand-font", "--on-primary", "--surface-tint", "--brand-pattern"];
const dark = window.matchMedia("(prefers-color-scheme: dark)");
let current = null;

function channel(hex) {
  const m = /^#?([0-9a-f]{6})$/i.exec(hex || "");
  if (!m) return null;
  return [0, 2, 4].map((i) => {
    const v = parseInt(m[1].slice(i, i + 2), 16) / 255;
    return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;
  });
}
export function luminance(hex) {
  const c = channel(hex);
  return c && 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
}
export function contrast(a, b) {
  const [x, y] = [luminance(a), luminance(b)];
  if (x === null || y === null) return null;
  return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05);
}
// Whichever of white / near-black reads better on the given color.
function onColor(hex) {
  return contrast(hex, "#ffffff") >= contrast(hex, "#111111") ? "#fff" : "#111";
}

const svgUrl = (svg) => `data:image/svg+xml,${encodeURIComponent(svg)}`;

// Very light 56px tiles; the low opacity keeps text contrast unaffected.
function patternUrl(kind, color) {
  const f = `fill="${color}" fill-opacity="0.07"`;
  const star = (x, y, r) => {
    const pts = [];
    for (let i = 0; i < 10; i++) {
      const rad = i % 2 ? r * 0.45 : r, a = (Math.PI / 5) * i - Math.PI / 2;
      pts.push(`${(x + rad * Math.cos(a)).toFixed(1)},${(y + rad * Math.sin(a)).toFixed(1)}`);
    }
    return `<polygon points="${pts.join(" ")}" ${f}/>`;
  };
  const shapes = {
    dots: `<circle cx="14" cy="14" r="2.5" ${f}/><circle cx="42" cy="42" r="2.5" ${f}/>`,
    stars: star(14, 14, 7) + star(42, 42, 5),
    leaves: `<path d="M12 22C12 12 20 6 28 6c0 10-8 16-16 16z" ${f}/><path d="M36 52c0-8 6-13 12-13 0 8-6 13-12 13z" ${f}/>`,
  };
  if (!shapes[kind]) return null;
  return `url("${svgUrl(`<svg xmlns="http://www.w3.org/2000/svg" width="56" height="56" viewBox="0 0 56 56">${shapes[kind]}</svg>`)}")`;
}

function faviconHref(primary, text, onPrimary) {
  const t = String(text).slice(0, 3).replace(/[<>&"']/g, "");
  const size = t.length > 2 ? 26 : t.length === 2 ? 32 : 40;
  return svgUrl(
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="14" fill="${primary}"/>` +
    `<text x="32" y="32" dy=".35em" text-anchor="middle" font-family="system-ui,sans-serif" font-weight="700" font-size="${size}" fill="${onPrimary}">${t}</text></svg>`);
}

function setIcon(href) {
  let link = document.head.querySelector("link[data-theme-icon]");
  if (!href) { link?.remove(); return; }
  if (!link) {
    link = document.createElement("link");
    link.rel = "icon";
    link.type = "image/svg+xml";
    link.dataset.themeIcon = "";
    document.head.append(link);
  }
  link.href = href;
}

function setThemeColor(color) {
  let meta = document.head.querySelector('meta[name="theme-color"]');
  if (!color) { meta?.remove(); return; }
  if (!meta) {
    meta = document.createElement("meta");
    meta.name = "theme-color";
    document.head.append(meta);
  }
  meta.content = color;
}

export function applyTheme(theme) {
  current = theme || null;
  const root = document.documentElement.style;
  PROPS.forEach((p) => root.removeProperty(p));
  let icon = null, color = null;

  if (theme) {
    if (theme.primary && channel(theme.primary)) {
      const on = onColor(theme.primary);
      root.setProperty("--brand-primary", theme.primary);
      root.setProperty("--on-primary", on);
      color = theme.primary;
      icon = faviconHref(theme.primary, theme.logo_text || "", on);
    }
    if (theme.accent) root.setProperty("--brand-accent", theme.accent);
    if (theme.font) root.setProperty("--brand-font", theme.font);
    // Light mode only: a light center background/tint/motif would break contrast on the dark palette.
    if (!dark.matches) {
      if (theme.background) root.setProperty("--brand-bg", theme.background);
      if (theme.surface_tint) root.setProperty("--surface-tint", theme.surface_tint);
      const p = theme.pattern && theme.primary ? patternUrl(theme.pattern, theme.primary) : null;
      if (p) root.setProperty("--brand-pattern", p);
    }
  }
  setIcon(icon);
  setThemeColor(color);
}

// Follow OS light/dark changes while a theme is active.
dark.addEventListener("change", () => applyTheme(current));
