// Data issues tab (Track K). Text is set with textContent only: issue text can quote user data.

function el(tag, cls, text) {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (text != null) n.textContent = text;
  return n;
}

async function api(url, options) {
  const res = await fetch(url, options);
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(body.detail || res.statusText);
  return body;
}

const post = (url, body) => api(url, { method: "POST", headers: { "Content-Type": "application/json" },
                                       body: JSON.stringify(body) });

function when(ts) {
  const d = new Date(ts.replace(" ", "T") + "Z"); // SQLite datetime('now') is UTC
  return isNaN(d) ? ts : d.toLocaleString([], { dateStyle: "medium", timeStyle: "short" });
}

function describeFix(r) {
  let what = r.table_name;
  try {
    const a = JSON.parse(r.after_json || "{}");
    if (r.table_name === "policies") what = `policy "${a.topic}"`;
    else if (r.table_name === "faq") what = `FAQ #${a.id}`;
  } catch (e) { /* keep the table name */ }
  return `Replaced a typed value in ${what} with its placeholder.`;
}

export async function mount(root, session) {
  if (!document.querySelector("link[data-issues-css]")) {
    const l = el("link");
    l.rel = "stylesheet";
    l.href = new URL("./issues.css", import.meta.url).href;
    l.dataset.issuesCss = "1";
    document.head.append(l);
  }
  root.innerHTML = "";
  const wrap = el("section", "issues");
  const title = el("h2", null, "Data issues");
  const ai = el("input");
  ai.type = "checkbox";
  const aiLabel = el("label");
  aiLabel.append(ai, el("span", null, "Include AI review"));
  const run = el("button", "primary", "Run check now");
  run.type = "button";
  const bar = el("div", "bar");
  const runBox = el("div", "run");
  runBox.append(aiLabel, run);
  bar.append(title, runBox);
  const note = el("p", "note");
  note.hidden = true;
  const list = el("div");
  const fixesBox = el("div");
  wrap.append(bar, note, list, fixesBox);
  root.append(wrap);

  function showNote(text) { note.textContent = text; note.hidden = false; }

  async function loadIssues() {
    list.innerHTML = "";
    try {
      const issues = await api("/api/admin/issues?status=open");
      title.textContent = `Data issues (${issues.length} open)`;
      if (!issues.length) list.append(el("p", "empty", "No open issues. Run a check to look again."));
      issues.forEach(i => list.append(card(i)));
    } catch (e) { list.append(el("p", "empty", "Could not load issues: " + e.message)); }
  }

  function card(i) {
    const c = el("article", "card");
    const body = el("div");
    const meta = el("div", "meta");
    meta.append(el("span", `badge ${i.severity}`, i.severity), el("span", "section", i.section || "general"),
                el("span", null, i.kind.replaceAll("_", " ")));
    body.append(meta, el("p", "detail", i.detail));
    if (i.suggestion) body.append(el("p", "suggestion", i.suggestion));
    const actions = el("div", "actions");
    for (const [status, label] of [["resolved", "Mark resolved"], ["dismissed", "Dismiss"]]) {
      const b = el("button", null, label);
      b.type = "button";
      b.onclick = async () => {
        b.disabled = true;
        try { await post(`/api/admin/issues/${i.id}/status`, { status }); await loadIssues(); }
        catch (e) { b.disabled = false; showNote("Could not update: " + e.message); }
      };
      actions.append(b);
    }
    c.append(body, actions);
    return c;
  }

  async function loadFixes() {
    fixesBox.innerHTML = "";
    fixesBox.append(el("h3", null, "Recent automatic fixes"));
    try {
      const rows = await api("/api/admin/issues/auto-fixes");
      if (!rows.length) {
        fixesBox.append(el("p", "empty", "None yet. The agent only fixes a typed name, phone, email or amount that maps to one data row and reads exactly the same afterwards."));
      }
      rows.forEach(r => {
        const d = el("div", "fix");
        d.append(el("div", null, describeFix(r)),
                 el("div", "meta", when(r.created_at) + " · see the History tab to review or undo"));
        fixesBox.append(d);
      });
    } catch (e) { fixesBox.append(el("p", "empty", "Could not load: " + e.message)); }
  }

  run.onclick = async () => {
    run.disabled = true;
    run.textContent = ai.checked ? "Checking (about 20s)…" : "Checking…";
    try {
      const s = await post("/api/admin/issues/run", { ai: ai.checked });
      showNote(`Check finished: ${s.auto_fixes.length} fixed automatically, ${s.issues_opened} new issue(s), `
        + `${s.issues_resolved} cleared.` + (s.ai_error ? " The AI review could not run: " + s.ai_error : ""));
    } catch (e) { showNote(e.message); }
    run.disabled = false;
    run.textContent = "Run check now";
    loadIssues();
    loadFixes();
  };
  loadIssues();
  loadFixes();
}
