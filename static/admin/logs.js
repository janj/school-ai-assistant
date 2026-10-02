// Logs tab (Track E). Rendering uses textContent only: logged text is never injected as HTML.
const PAGE = 50;

function el(tag, cls, text) {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (text != null) n.textContent = text;
  return n;
}

async function getJSON(url, body) {
  const res = await fetch(url, body === undefined ? {} : {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || res.statusText);
  return res.json();
}

// Placeholder picker (insert at the cursor) + a preview resolved by the server.
function placeholderTools(textarea) {
  const picker = el("select");
  picker.setAttribute("aria-label", "Insert placeholder");
  picker.append(new Option("Insert placeholder…", ""));
  getJSON("/api/admin/placeholders").then(items => {
    const groups = {};
    for (const it of items) (groups[it.group] ||= []).push(it);
    for (const [group, list] of Object.entries(groups)) {
      const g = el("optgroup");
      g.label = group;
      list.forEach(it => g.append(new Option(`${it.token}  →  ${it.value || "(empty)"}`, it.token)));
      picker.append(g);
    }
  }).catch(() => picker.append(new Option("Couldn't load placeholders", "")));
  picker.onchange = () => {
    if (!picker.value) return;
    textarea.setRangeText(picker.value, textarea.selectionStart, textarea.selectionEnd, "end");
    textarea.focus();
    picker.value = "";
  };

  const prev = el("button", "ghost", "Preview");
  prev.type = "button";
  const out = el("div", "preview");
  out.hidden = true;
  prev.onclick = async () => {
    out.hidden = false;
    out.textContent = "Loading preview…";
    try {
      const { rendered, invalid } = await getJSON("/api/admin/preview", { text: textarea.value });
      out.textContent = rendered;
      if (invalid.length) out.append(el("div", "error", `Unknown placeholder(s): ${invalid.join(", ")}. Saving will fail until they're fixed.`));
    } catch (e) { out.textContent = e.message; }
  };
  const bar = el("div", "tools");
  bar.append(picker, prev);
  const box = el("div");
  box.append(bar, out);
  return box;
}

function answerForm(r, onSaved, onCancel) {
  const form = el("form", "faq-form");
  const qLabel = el("label", null, "Question (as a parent would ask it)");
  const q = el("input");
  q.type = "text";
  q.value = r.question;
  q.maxLength = 500;
  q.required = true;
  qLabel.append(q);
  const aLabel = el("label", null, "Answer");
  aLabel.append(el("small", null, "Insert placeholders for fees, contacts and times; don't type values that live in another table."));
  const a = el("textarea");
  a.rows = 5;
  a.required = true;
  aLabel.append(a, placeholderTools(a));
  const err = el("div", "error");
  err.setAttribute("role", "alert");
  const save = el("button", "primary", "Save to FAQ");
  save.type = "submit";
  const cancel = el("button", "ghost", "Cancel");
  cancel.type = "button";
  const actions = el("div", "actions");
  actions.append(save, cancel);
  form.append(qLabel, aLabel, err, actions);
  cancel.onclick = () => { form.remove(); onCancel(); };
  form.onsubmit = async ev => {
    ev.preventDefault();
    err.textContent = "";
    save.disabled = true;
    try {
      const faq = await getJSON(`/api/admin/logs/${r.id}/answer`, { question: q.value, answer: a.value });
      onSaved(faq);
    } catch (e) { err.textContent = e.message; save.disabled = false; }
  };
  return form;
}

function when(ts) {
  // SQLite datetime('now') is UTC without a zone marker
  const d = new Date(ts.replace(" ", "T") + "Z");
  return isNaN(d) ? ts : d.toLocaleString([], { dateStyle: "medium", timeStyle: "short" });
}

function card(r, onChange) {
  const c = el("article", "card");
  const meta = el("div", "meta");
  meta.append(el("span", null, when(r.created_at)), el("span", null, r.role || ""));
  if (!r.found) meta.append(el("span", "badge", "not found"));
  if (r.resolved_faq_id != null) meta.append(el("span", "badge ok", `Answered in FAQ #${r.resolved_faq_id}`));
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

  if (!r.found && r.resolved_faq_id == null) {
    const hook = el("div", "faq-hook");
    const btn = el("button", "primary", "Answer this");
    btn.type = "button";
    btn.onclick = () => {
      btn.hidden = true;
      const form = answerForm(r, onChange, () => { btn.hidden = false; });
      hook.append(form);
      form.querySelector("textarea").focus();
    };
    hook.append(btn);
    c.append(hook);
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
  const choices = [["open", "Open"], ["all", "All"], ["false", "Unanswered"], ["true", "Answered"]];
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
      [[s.total, "questions"], [s.open_unanswered, "open unanswered"], [s.unanswered, "unanswered"], [s.last_7_days, "last 7 days"], [share, "cache-read share"]]
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
      const q = filter === "open" ? "status=open" : `found=${filter}`;
      const rows = await getJSON(`/api/admin/logs?${q}&limit=${PAGE}&offset=${offset}`);
      rows.forEach(r => list.append(card(r, refresh)));
      offset += rows.length;
      load.hidden = rows.length < PAGE;
      if (!offset) list.append(el("p", "empty", filter === "open" ? "Nothing waiting for an answer." : "No questions logged yet."));
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
  // Default to the Open filter when something is waiting for an answer.
  getJSON("/api/admin/logs/stats").then(s => { if (s.open_unanswered) filter = "open"; }).catch(() => {}).then(refresh);
}
