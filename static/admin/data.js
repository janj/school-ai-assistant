// Admin data editor (mountData) and change history (mountHistory). Plain DOM, no framework.

if (!document.querySelector('link[data-dx-css]')) {
  const link = document.createElement("link");
  link.rel = "stylesheet";
  link.href = "/static/admin/data.css";
  link.dataset.dxCss = "1";
  document.head.append(link);
}

// h("div.cls", {onclick}, child, ...): tiny element builder. Strings become text nodes (never HTML).
function h(tag, attrs, ...kids) {
  const [name, ...classes] = tag.split(".");
  const el = document.createElement(name);
  if (classes.length) el.className = classes.join(" ");
  for (const [k, v] of Object.entries(attrs || {})) {
    if (k.startsWith("on")) el[k] = v;
    else if (v === true) el.setAttribute(k, "");
    else if (v !== false && v != null) el.setAttribute(k, v);
  }
  for (const kid of kids.flat(Infinity)) if (kid != null && kid !== false) el.append(kid);
  return el;
}

async function api(method, path, body) {
  const res = await fetch("/api/admin" + path, {
    method,
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const d = data.detail;
    throw new Error(typeof d === "string" ? d : Array.isArray(d) ? "Invalid request." : `Request failed (${res.status}).`);
  }
  return data;
}

const dollars = (cents) => (cents == null ? "" : (cents / 100).toLocaleString("en-US", { style: "currency", currency: "USD" }));

function display(col, value) {
  if (value == null || value === "") return "";
  return col.type === "money_cents" ? dollars(value) : String(value);
}

// Minimal markdown for the preview toggle: headings, bold/italic, bullet lists, paragraphs.
function renderMarkdown(src) {
  const root = h("div");
  const inline = (text) => {
    const frag = document.createDocumentFragment();
    text.split(/(\*\*[^*]+\*\*|\*[^*]+\*)/).forEach((part) => {
      if (part.startsWith("**") && part.length > 4) frag.append(h("strong", null, part.slice(2, -2)));
      else if (part.startsWith("*") && part.length > 2) frag.append(h("em", null, part.slice(1, -1)));
      else frag.append(part);
    });
    return frag;
  };
  let list = null, para = [];
  const flushPara = () => { if (para.length) root.append(h("p", null, inline(para.join(" ")))); para = []; };
  for (const line of src.split("\n")) {
    const heading = line.match(/^(#{1,3})\s+(.*)/);
    const bullet = line.match(/^\s*[-*]\s+(.*)/);
    if (bullet) { flushPara(); if (!list) { list = h("ul"); root.append(list); } list.append(h("li", null, inline(bullet[1]))); continue; }
    list = null;
    if (heading) { flushPara(); root.append(h("h" + heading[1].length, null, inline(heading[2]))); }
    else if (!line.trim()) flushPara();
    else para.push(line.trim());
  }
  flushPara();
  return root;
}

// ---------- Data tab ----------

export async function mountData(el, session) {
  el.replaceChildren(h("p.dx-muted", null, "Loading…"));
  let registry;
  try { registry = await api("GET", "/registry"); }
  catch (e) { el.replaceChildren(h("p.dx-error", null, e.message)); return; }

  const names = Object.keys(registry);
  let current = names[0];
  const root = h("div.dx");
  const select = h("select", { "aria-label": "Table", onchange: () => open(select.value) },
    names.map((n) => h("option", { value: n }, registry[n].label)));
  const side = h("nav.dx-side", { "aria-label": "Tables" });
  const main = h("div.dx-main");
  root.append(
    h("div.dx-layout", null, h("div.dx-picker", null, select), side, main),
    resetPanel(session, () => open(current)),
  );
  el.replaceChildren(root);

  function open(name) {
    current = name;
    select.value = name;
    side.replaceChildren(...names.map((n) =>
      h("button", { type: "button", "aria-current": String(n === name), onclick: () => open(n) }, registry[n].label)));
    showList(name);
  }

  async function showList(name, notice) {
    const meta = registry[name];
    main.replaceChildren(h("p.dx-muted", null, "Loading…"));
    let rows;
    try { rows = await api("GET", "/data/" + name); }
    catch (e) { main.replaceChildren(h("p.dx-error", null, e.message)); return; }

    const add = meta.single_row ? null
      : h("button.dx-btn.primary", { type: "button", onclick: () => showForm(name, null) }, "+ Add");
    const msg = h("div");
    if (notice) msg.append(h("p.dx-ok", null, notice));
    const cols = meta.columns;

    const table = h("table.dx-table", null,
      h("thead", null, h("tr", null, cols.map((c) => h("th", null, c.label)), h("th", null, ""))),
      h("tbody", null, rows.map((r) => h("tr", null,
        cols.map((c) => h("td", null, h("div.dx-cell-long", null, display(c, r[c.name])))),
        h("td.act", null, rowActions(name, meta, r, msg))))));
    const cards = h("div.dx-cards", null, rows.map((r) => h("div.dx-card", null,
      h("dl", null, cols.map((c) => [h("dt", null, c.label), h("dd", null, display(c, r[c.name]) || "–")])),
      rowActions(name, meta, r, msg))));

    main.replaceChildren(
      h("div.dx-head", null, h("h2", null, meta.label), add),
      msg,
      // A single record (Center info) reads better as label/value cards at every width.
      !rows.length ? h("p.dx-muted", null, "Nothing here yet.")
        : meta.single_row ? h("div.dx-single", null, cards) : h("div", null, table, cards),
    );
  }

  function rowActions(name, meta, row, msg) {
    const box = h("div.act");
    const edit = h("button.dx-btn", { type: "button", onclick: () => showForm(name, row) }, "Edit");
    box.append(edit);
    if (!meta.single_row) {
      const del = h("button.dx-btn.danger", { type: "button" }, "Delete");
      del.onclick = () => {
        if (box.querySelector(".dx-confirm")) return;
        const err = h("span.dx-error");
        const yes = h("button.dx-btn.danger.solid", { type: "button" }, "Yes, delete");
        const no = h("button.dx-btn", { type: "button" }, "Cancel");
        const confirm = h("div.dx-confirm", null, h("span", null, "Delete this row?"), yes, no, err);
        no.onclick = () => confirm.remove();
        yes.onclick = async () => {
          yes.disabled = true;
          try { await api("DELETE", `/data/${name}/${row.id}`); showList(name, "Deleted."); }
          catch (e) { err.textContent = e.message; yes.disabled = false; }
        };
        box.append(confirm);
        box.style.flexWrap = "wrap";
      };
      box.append(del);
    }
    return box;
  }

  function showForm(name, row) {
    const meta = registry[name];
    const inputs = {};
    const fields = meta.columns.map((c) => {
      const value = row ? row[c.name] : null;
      let input, extra = null;
      if (c.type === "longtext" || c.type === "markdown") {
        input = h("textarea", { name: c.name, rows: c.type === "markdown" ? 10 : 4 });
        input.value = value ?? "";
        if (c.type === "markdown") extra = markdownToggle(input);
      } else if (c.type === "time" || c.type === "date") {
        input = h("input", { name: c.name, type: c.type, value: value ?? "" });
      } else if (c.type === "money_cents") {
        input = h("input", { name: c.name, type: "number", step: "0.01", min: "0", inputmode: "decimal",
                             value: value == null ? "" : (value / 100).toFixed(2) });
      } else if (c.type === "int") {
        input = h("input", { name: c.name, type: "number", step: "1", inputmode: "numeric", value: value ?? "" });
      } else {
        input = h("input", { name: c.name, type: "text", value: value ?? "", maxlength: 500 });
      }
      if (c.required) input.required = true;
      inputs[c.name] = input;
      return h("label", null, h("span", { class: c.required ? "req" : "" }, c.label), input, extra);
    });

    const err = h("div.dx-error", { role: "alert" });
    const save = h("button.dx-btn.primary", { type: "submit" }, row ? "Save changes" : "Add");
    const cancel = h("button.dx-btn", { type: "button", onclick: () => showList(name) }, "Cancel");
    const form = h("form.dx-form", { novalidate: true }, fields, err, h("div.actions", null, save, cancel));
    form.onsubmit = async (ev) => {
      ev.preventDefault();
      err.textContent = "";
      const body = {};
      for (const c of meta.columns) {
        const raw = inputs[c.name].value;
        if (c.type === "money_cents") {
          if (raw.trim() === "") body[c.name] = null;
          else {
            const n = Number(raw);
            if (!Number.isFinite(n) || n < 0) { err.textContent = `${c.label} must be a dollar amount.`; return; }
            body[c.name] = Math.round(n * 100);
          }
        } else if (c.type === "int") {
          body[c.name] = raw.trim() === "" ? null : Number(raw);
        } else body[c.name] = raw;
      }
      save.disabled = true;
      try {
        if (row) await api("PUT", `/data/${name}/${encodeURIComponent(row.id)}`, body);
        else await api("POST", `/data/${name}`, body);
        showList(name, row ? "Saved." : "Added.");
      } catch (e) { err.textContent = e.message; save.disabled = false; }
    };
    main.replaceChildren(h("div.dx-head", null, h("h2", null, `${row ? "Edit" : "Add"}: ${meta.label}`)), form);
    form.querySelector("input, textarea")?.focus();
  }

  function markdownToggle(textarea) {
    const edit = h("button", { type: "button", "aria-pressed": "true" }, "Edit");
    const prev = h("button", { type: "button", "aria-pressed": "false" }, "Preview");
    const preview = h("div.dx-preview");
    preview.hidden = true;
    const set = (on) => {
      textarea.hidden = on; preview.hidden = !on;
      edit.setAttribute("aria-pressed", String(!on)); prev.setAttribute("aria-pressed", String(on));
      if (on) preview.replaceChildren(renderMarkdown(textarea.value));
    };
    edit.onclick = () => set(false);
    prev.onclick = () => set(true);
    return h("div", null, h("div.dx-md-tabs", null, edit, prev), preview);
  }

  open(current);
}

function resetPanel(session, onDone) {
  const err = h("div.dx-error", { role: "alert" });
  const input = h("input", { type: "text", placeholder: "Type RESET", "aria-label": "Type RESET to confirm", autocomplete: "off" });
  const go = h("button.dx-btn.danger.solid", { type: "button", disabled: true }, "Reset now");
  const cancel = h("button.dx-btn", { type: "button" }, "Cancel");
  const confirmBox = h("div", { hidden: true },
    h("p", null, "Type RESET to confirm."), input, " ", go, " ", cancel, err);
  const start = h("button.dx-btn.danger", { type: "button" }, "Reset center to original data");
  start.onclick = () => { confirmBox.hidden = false; start.hidden = true; input.focus(); };
  cancel.onclick = () => { confirmBox.hidden = true; start.hidden = false; input.value = ""; go.disabled = true; err.textContent = ""; };
  input.oninput = () => { go.disabled = input.value !== "RESET"; };
  go.onclick = async () => {
    go.disabled = true;
    try {
      await api("POST", "/reset", { confirm: "RESET" });
      cancel.onclick();
      onDone();
    } catch (e) { err.textContent = e.message; go.disabled = false; }
  };
  return h("section.dx-danger-zone", null,
    h("h3", null, "Reset"),
    h("p", null, `This replaces all of ${session.center.name}'s data (directory, hours, closures, schedule, fees, lunch menu, policies and admin answers) with the original sample data, and restores the center info. Your edits are lost. The change history and chat logs are kept, and the reset itself is recorded.`),
    start, confirmBox);
}

// ---------- History tab ----------

const PAGE = 50;

function parse(json) {
  if (!json) return null;
  try { return JSON.parse(json); } catch { return null; }
}

function when(utc) {
  const d = new Date(utc.replace(" ", "T") + "Z");
  return isNaN(d) ? utc : d.toLocaleString([], { dateStyle: "medium", timeStyle: "short" });
}

export async function mountHistory(el, session) {
  const root = h("div.dx");
  const list = h("div.dx-hist");
  const more = h("button.dx-btn", { type: "button" }, "Load more");
  const err = h("p.dx-error");
  root.append(h("div.dx-head", null, h("h2", null, "Change history")), list, err, more);
  el.replaceChildren(root);

  let registry = {};
  try { registry = await api("GET", "/registry"); } catch { /* labels fall back to raw names */ }
  let offset = 0;

  async function load() {
    more.disabled = true;
    err.textContent = "";
    try {
      const rows = await api("GET", `/history?limit=${PAGE}&offset=${offset}`);
      offset += rows.length;
      rows.forEach((r) => list.append(entry(r)));
      more.hidden = rows.length < PAGE;
      if (!offset) list.append(h("p.dx-muted", null, "No changes yet."));
    } catch (e) { err.textContent = e.message; }
    more.disabled = false;
  }

  function entry(r) {
    const meta = registry[r.table_name];
    const before = parse(r.before_json), after = parse(r.after_json);
    const target = r.table_name === "*" ? "whole center" :
      `${meta ? meta.label : r.table_name}${r.row_id != null ? " #" + r.row_id : ""}`;
    const body = h("div.dx-diff");
    if (r.action === "reset") body.append(h("p.dx-muted", null, "All center data was reset to the original sample data."));
    else {
      const keys = [...new Set([...Object.keys(before || {}), ...Object.keys(after || {})])]
        .filter((k) => k !== "id" && JSON.stringify(before?.[k]) !== JSON.stringify(after?.[k]));
      const label = (k) => meta?.columns.find((c) => c.name === k)?.label || k;
      const show = (k, v) => {
        const col = meta?.columns.find((c) => c.name === k);
        return v == null || v === "" ? "(empty)" : col ? display(col, v) : String(v);
      };
      for (const k of keys) {
        body.append(h("div", null,
          h("div.field", null, label(k)),
          before ? h("div.before", null, show(k, before[k])) : null,
          after ? h("div.after", null, show(k, after[k])) : null));
      }
      if (!keys.length) body.append(h("p.dx-muted", null, "No field changes."));
    }
    return h("details", null,
      h("summary", null,
        h("span.dx-badge." + r.action, null, r.action),
        h("strong", null, target),
        h("span.dx-muted", null, `${r.admin_name} · ${when(r.created_at)}`)),
      body);
  }

  more.onclick = load;
  load();
}
