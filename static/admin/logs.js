// Logs tab (Track E). Rendering uses textContent only: logged text is never injected as HTML.
const PAGE = 50;

function el(tag, cls, text) {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (text != null) n.textContent = text;
  return n;
}

async function getJSON(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || res.statusText);
  return res.json();
}

function when(ts) {
  // SQLite datetime('now') is UTC without a zone marker
  const d = new Date(ts.replace(" ", "T") + "Z");
  return isNaN(d) ? ts : d.toLocaleString([], { dateStyle: "medium", timeStyle: "short" });
}

function card(r) {
  const c = el("article", "card");
  const meta = el("div", "meta");
  meta.append(el("span", null, when(r.created_at)), el("span", null, r.role || ""));
  if (!r.found) meta.append(el("span", "badge", "not found"));
  c.append(meta, el("div", "q", r.question));

  const a = el("p", "a", r.answer);
  const more = el("button", "more", "Show more");
  more.type = "button";
  more.hidden = true;
  more.onclick = () => {
    a.classList.toggle("open");
    more.textContent = a.classList.contains("open") ? "Show less" : "Show more";
  };
  c.append(a, more);
  // The 3-line clamp only needs a toggle if the text overflows; check after layout.
  requestAnimationFrame(() => { more.hidden = a.scrollHeight <= a.clientHeight + 1; });

  if (r.sources.length) {
    const chips = el("div", "chips");
    r.sources.forEach(s => chips.append(el("span", "chip", s)));
    c.append(chips);
  }
  const parts = [`in ${r.input_tokens ?? 0}`, `out ${r.output_tokens ?? 0}`, `cache read ${r.cache_read_tokens ?? 0}`];
  if (r.latency_ms != null) parts.push(`${r.latency_ms} ms`);
  c.append(el("div", "usage", parts.join(" · ")));

  if (!r.found) {
    // HOOK(faq): "Answer this" action mounts here
    c.append(el("div", "faq-hook"));
  }
  return c;
}

export async function mount(root, session) {
  if (!document.querySelector("link[data-logs-css]")) {
    const l = el("link");
    l.rel = "stylesheet";
    l.href = new URL("./logs.css", import.meta.url).href;
    l.dataset.logsCss = "1";
    document.head.append(l);
  }
  root.innerHTML = "";
  const wrap = el("section", "logs");
  const stats = el("div", "stats");
  const filters = el("div", "filters");
  const list = el("div");
  const load = el("button", "load", "Load more");
  load.type = "button";
  load.hidden = true;
  wrap.append(stats, filters, list, load);
  root.append(wrap);

  let filter = "all", offset = 0;
  const choices = [["all", "All"], ["false", "Unanswered"], ["true", "Answered"]];
  const buttons = choices.map(([value, label]) => {
    const b = el("button", null, label);
    b.type = "button";
    b.onclick = () => { filter = value; refresh(); };
    filters.append(b);
    return [value, b];
  });

  async function loadStats() {
    try {
      const s = await getJSON("/api/admin/logs/stats");
      const t = s.tokens, denom = t.input + t.cache_read;
      const share = denom ? Math.round(100 * t.cache_read / denom) + "%" : "–";
      stats.innerHTML = "";
      [[s.total, "questions"], [s.unanswered, "unanswered"], [s.last_7_days, "last 7 days"], [share, "cache-read share"]]
        .forEach(([v, l]) => {
          const d = el("div", "stat");
          d.append(el("b", null, String(v)), el("span", null, l));
          stats.append(d);
        });
    } catch (e) { stats.textContent = "Could not load stats: " + e.message; }
  }

  async function loadPage() {
    load.disabled = true;
    try {
      const rows = await getJSON(`/api/admin/logs?found=${filter}&limit=${PAGE}&offset=${offset}`);
      rows.forEach(r => list.append(card(r)));
      offset += rows.length;
      load.hidden = rows.length < PAGE;
      if (!offset) list.append(el("p", "empty", "No questions logged yet."));
    } catch (e) {
      list.append(el("p", "empty", "Could not load logs: " + e.message));
    }
    load.disabled = false;
  }

  function refresh() {
    buttons.forEach(([v, b]) => b.setAttribute("aria-pressed", String(v === filter)));
    list.innerHTML = "";
    offset = 0;
    loadStats();
    loadPage();
  }
  load.onclick = loadPage;
  refresh();
}
