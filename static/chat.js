// Picker + chat UI. No framework: small render functions that rebuild #app.
const app = document.getElementById("app");
const MAX_CHARS = 1000;
const COUNTER_FROM = 800;

// Track G: history/thread state keyed by this id. A new one is minted on Start over.
let conversationId = crypto.randomUUID();
let session = null;
let busy = false;

const SOURCE_LABELS = {
  center: "Center info", contacts: "Contacts", hours: "Hours", closures: "Closures",
  schedule: "Daily schedule", fees: "Fees", lunch_menu: "Lunch menu",
};
const SUGGESTIONS = [
  "What are your hours?", "What happens if I pick up late?",
  "When should I keep my child home sick?", "What's for lunch this week?",
];

function el(tag, props = {}, ...kids) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(props)) {
    if (k === "class") node.className = v;
    else if (k === "text") node.textContent = v;
    else if (k.startsWith("on")) node.addEventListener(k.slice(2), v);
    else if (v === true) node.setAttribute(k, "");
    else if (v !== false && v != null) node.setAttribute(k, v);
  }
  node.append(...kids.flat().filter(Boolean));
  return node;
}

function sourceLabel(id) {
  if (SOURCE_LABELS[id]) return SOURCE_LABELS[id];
  const [kind, rest] = id.split(":");
  if (kind === "policy" && rest) {
    const t = rest.replace(/_/g, " ");
    return t.charAt(0).toUpperCase() + t.slice(1) + " policy";
  }
  if (kind === "faq") return "FAQ";
  return id;
}

// Escape first, then allow only **bold**, "- " lists and line breaks.
function escapeHtml(s) {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}
function renderMarkdown(text) {
  const inline = (s) => escapeHtml(s).replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  const out = [];
  let list = false;
  let para = [];
  const flushPara = () => { if (para.length) out.push("<p>" + para.join("<br>") + "</p>"); para = []; };
  for (const line of text.split("\n")) {
    const m = line.match(/^\s*[-*] (.*)$/);
    if (m) {
      flushPara();
      if (!list) { out.push("<ul>"); list = true; }
      out.push("<li>" + inline(m[1]) + "</li>");
    } else {
      if (list) { out.push("</ul>"); list = false; }
      if (line.trim() === "") flushPara(); else para.push(inline(line));
    }
  }
  if (list) out.push("</ul>");
  flushPara();
  return out.join("");
}

// ---- Theme ----
function luminance(hex) {
  const m = /^#?([0-9a-f]{6})$/i.exec(hex || "");
  if (!m) return null;
  const c = [0, 2, 4].map((i) => {
    const v = parseInt(m[1].slice(i, i + 2), 16) / 255;
    return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
}
function applyTheme(theme) {
  const root = document.documentElement.style;
  if (!theme) {
    ["--brand-primary", "--brand-accent", "--brand-bg", "--on-primary"].forEach((p) => root.removeProperty(p));
    return;
  }
  if (theme.primary) {
    root.setProperty("--brand-primary", theme.primary);
    const l = luminance(theme.primary);
    root.setProperty("--on-primary", l !== null && l > 0.4 ? "#111" : "#fff");
  }
  if (theme.accent) root.setProperty("--brand-accent", theme.accent);
  // Keep the dark-mode background from base.css; a light center background would break contrast.
  const dark = window.matchMedia("(prefers-color-scheme: dark)").matches;
  if (theme.background && !dark) root.setProperty("--brand-bg", theme.background);
}

// ---- API ----
async function api(path, opts = {}) {
  const res = await fetch(path, {
    ...opts,
    headers: opts.body ? { "Content-Type": "application/json" } : undefined,
  });
  let data = null;
  try { data = await res.json(); } catch { /* non-JSON error body */ }
  return { res, data };
}

// ---- Picker ----
async function showPicker(notice) {
  applyTheme(null);
  session = null;
  app.replaceChildren(el("p", { class: "loading", text: "Loading…" }));
  let centers = [];
  try {
    const { res, data } = await api("/api/centers");
    if (!res.ok) throw new Error();
    centers = data;
  } catch {
    app.replaceChildren(el("div", { class: "picker" },
      el("h1", { text: "School Assistant" }),
      el("p", { class: "form-error", role: "alert", text: "Temporarily unavailable. Please try again." }),
      el("button", { class: "btn primary", onclick: () => showPicker(), text: "Retry" })));
    return;
  }

  let center = null;
  let role = "parent";
  const errorBox = el("p", { class: "form-error", role: "alert" });
  if (notice) errorBox.textContent = notice;
  const nameInput = el("input", { id: "display-name", maxlength: "60", autocomplete: "name" });
  const nameField = el("label", { class: "field", hidden: true },
    "Your name (required)", nameInput,
    el("span", { class: "muted", text: "Admin mode can edit this center's information. Your name is recorded in the change history." }));
  const go = el("button", { class: "btn primary", type: "button", disabled: true, text: "Continue" });

  const centerCards = centers.map((c) => {
    const card = el("button", {
      class: "card-opt", role: "radio", "aria-checked": "false", type: "button",
      style: `--tint:${c.theme?.primary || "var(--brand-primary)"}`,
      onclick: () => { center = c; centerCards.forEach((x) => x.setAttribute("aria-checked", x === card)); sync(); },
    }, el("strong", { text: c.name }), el("span", { class: "muted", text: c.tagline || "" }));
    return card;
  });
  const roleCards = [["parent", "Parent", "Ask questions about the center"], ["admin", "Admin", "Ask questions and edit center information"]]
    .map(([value, label, hint]) => {
      const b = el("button", {
        class: "card-opt", role: "radio", type: "button", "aria-checked": String(value === role),
        onclick: () => { role = value; roleCards.forEach((x) => x.setAttribute("aria-checked", x.dataset.role === role)); sync(); },
        "data-role": value,
      }, el("strong", { text: label }), el("span", { class: "muted", text: hint }));
      return b;
    });

  function sync() {
    nameField.hidden = role !== "admin";
    go.disabled = !center || (role === "admin" && !nameInput.value.trim());
  }
  nameInput.addEventListener("input", sync);

  async function submit() {
    errorBox.textContent = "";
    go.disabled = true;
    try {
      const body = { role, center_slug: center.slug };
      if (role === "admin") body.display_name = nameInput.value.trim();
      const { res, data } = await api("/api/session", { method: "POST", body: JSON.stringify(body) });
      if (!res.ok) {
        errorBox.textContent = data?.detail || "Could not start the session.";
        sync();
        return;
      }
      conversationId = crypto.randomUUID();
      showChat(data);
    } catch {
      errorBox.textContent = "Temporarily unavailable. Please try again.";
      sync();
    }
  }
  go.addEventListener("click", submit);

  app.replaceChildren(el("form", { class: "picker", onsubmit: (e) => { e.preventDefault(); if (!go.disabled) submit(); } },
    el("h1", { text: "School Assistant" }),
    el("p", { class: "muted", text: "Ask questions about a childcare center and get answers from its own information." }),
    el("h2", { text: "1. Choose a center" }),
    el("div", { class: "cards", role: "radiogroup", "aria-label": "Center" }, centerCards),
    el("h2", { text: "2. Choose your role" }),
    el("div", { class: "roles", role: "radiogroup", "aria-label": "Role" }, roleCards),
    nameField, errorBox, go,
    el("p", { class: "demo-note", text: "This is a demo: there are no accounts, and you can change your choice any time with \"Start over\"." })));
  sync();
}

async function startOver() {
  try { await api("/api/session", { method: "DELETE" }); } catch { /* picker works regardless */ }
  conversationId = crypto.randomUUID();
  showPicker();
}

// ---- Chat ----
function showChat(s) {
  session = s;
  applyTheme(s.center.theme);
  busy = false;
  let lastQuestion = null;

  const messages = el("div", { class: "messages", "aria-live": "polite", "aria-label": "Conversation", role: "log" });
  const input = el("textarea", { id: "q", rows: "1", maxlength: String(MAX_CHARS), placeholder: "Ask a question…", "aria-label": "Your question" });
  const counter = el("div", { class: "counter", "aria-live": "off" });
  const send = el("button", { class: "btn primary send", type: "button", text: "Send" });

  const header = el("header", { class: "chat-header" },
    s.center.theme?.logo_text ? el("span", { class: "logo", text: s.center.theme.logo_text }) : null,
    el("span", { class: "name", text: s.center.name }),
    el("span", { class: "pill", text: s.role === "admin" ? `Admin: ${s.display_name || ""}` : "Parent" }),
    s.role === "admin" ? el("a", { href: "/admin", text: "Admin" }) : null,
    el("button", { type: "button", onclick: startOver, text: "Start over" }));

  const empty = el("div", { class: "empty" },
    el("h2", { text: `Welcome to ${s.center.name}` }),
    el("p", { class: "muted", text: "Ask me anything about the center. Try one of these:" }),
    el("div", { class: "chips" }, SUGGESTIONS.map((q) => el("button", { class: "chip-q", type: "button", text: q, onclick: () => ask(q) }))));
  messages.append(empty);

  const composer = el("div", { class: "composer" },
    el("div", { class: "composer-row" },
      input,
      ((slot) => (import("/static/voice.js").then((m) => m.mountVoice(slot, { input, send: ask, getLang: () => navigator.language })).catch(() => {}), slot))(el("div", { class: "voice-slot" })),
      send),
    counter);
  app.replaceChildren(el("div", { class: "chat" }, header, messages, composer));

  function scroll() { messages.scrollTop = messages.scrollHeight; }
  function add(node) { empty.remove(); messages.append(node); scroll(); return node; }
  function setBusy(v) {
    busy = v;
    input.disabled = v;
    send.disabled = v;
    if (!v) input.focus();
  }
  function autosize() {
    input.style.height = "auto";
    input.style.height = Math.min(input.scrollHeight, parseFloat(getComputedStyle(input).maxHeight)) + "px";
    const n = input.value.length;
    counter.textContent = n >= COUNTER_FROM ? `${n} / ${MAX_CHARS}` : "";
    counter.classList.toggle("warn", n >= MAX_CHARS - 50);
  }

  function botMessage(data) {
    const node = el("div", { class: "msg bot" });
    node.innerHTML = renderMarkdown(data.answer || "");
    if (data.sources?.length) {
      node.append(el("div", { class: "sources", "aria-label": "Sources" },
        data.sources.map((id) => el("span", { class: "src", text: sourceLabel(id) }))));
    }
    if (data.found === false && data.contact) {
      const { phone, email } = data.contact;
      node.append(el("div", { class: "contact-card" },
        el("strong", { text: "Contact the center" }),
        phone ? el("a", { href: "tel:" + phone.replace(/[^\d+]/g, ""), text: phone }) : null,
        email ? el("a", { href: "mailto:" + email, text: email }) : null));
    }
    return node;
  }
  function errorMessage(text, retry) {
    const node = el("div", { class: "msg error", role: "alert" }, el("div", { text }));
    if (retry) node.append(el("button", { class: "btn", type: "button", text: "Retry", onclick: () => { node.remove(); ask(lastQuestion, true); } }));
    return node;
  }

  async function ask(text, isRetry = false) {
    text = text.trim();
    if (busy || !text) return;
    lastQuestion = text;
    if (!isRetry) add(el("div", { class: "msg user", text }));
    input.value = "";
    autosize();
    setBusy(true);
    const typing = add(el("div", { class: "msg bot typing", role: "status", "aria-label": "Assistant is typing" },
      el("span"), el("span"), el("span")));
    try {
      const { res, data } = await api("/api/chat", {
        method: "POST", body: JSON.stringify({ message: text, conversation_id: conversationId }),
      });
      typing.remove();
      if (res.ok) {
        add(botMessage(data));
      } else if (res.status === 401) {
        showPicker("Your session ended. Please choose a center again.");
        return;
      } else if (res.status === 429) {
        const lead = data?.kind === "budget" ? "Daily usage limit reached. " : "You're sending questions too quickly. ";
        add(errorMessage(lead + (data?.detail || "")));
      } else if (res.status === 400) {
        add(errorMessage(data?.detail || "That message couldn't be sent."));
      } else {
        add(errorMessage("The assistant is temporarily unavailable.", true));
      }
    } catch {
      typing.remove();
      add(errorMessage("The assistant is temporarily unavailable.", true));
    }
    setBusy(false);
  }

  send.addEventListener("click", () => ask(input.value));
  input.addEventListener("input", autosize);
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey && !e.isComposing) { e.preventDefault(); ask(input.value); }
  });
  input.focus();
}

// ---- Boot ----
try {
  const { res, data } = await api("/api/session");
  if (res.ok) showChat(data); else showPicker();
} catch {
  showPicker();
}
