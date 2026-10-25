// Canvass And Analyze: email subscriptions.
//
//   POST /subscribe              {email, turnstile}  -> saves as pending, emails a confirm link
//   POST /confirm {token}        -> marks active, sends the welcome email (called by the blog's confirm page)
//   GET  /confirm?token=...      -> forwards to the blog's confirm page (links in older emails)
//   POST /unsubscribe?token=...  -> marks unsubscribed (also the one-click List-Unsubscribe target)
//   GET  /admin/subscribers      -> active subscribers for scripts/notify.py (Bearer ADMIN_TOKEN)
//
// Mail goes out through Gmail SMTP (app password) over a TLS socket.
import { connect } from "cloudflare:sockets";
import { confirmEmail, welcomeEmail } from "./templates.js";

const ALLOWED_ORIGINS = ["https://arunkoundinya.github.io", "http://localhost:4322"];
const RESEND_AFTER_MS = 10 * 60 * 1000; // don't re-send a confirm email more often than this

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const origin = request.headers.get("Origin") || "";
    const cors = ALLOWED_ORIGINS.includes(origin)
      ? { "Access-Control-Allow-Origin": origin, "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
          "Access-Control-Allow-Headers": "Content-Type", Vary: "Origin" }
      : {};
    if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: cors });

    try {
      if (url.pathname === "/subscribe" && request.method === "POST") return await subscribe(request, env, cors);
      if (url.pathname === "/confirm" && request.method === "GET")
        return Response.redirect(`${env.SITE_URL}confirm.html?token=${encodeURIComponent(url.searchParams.get("token") || "")}`, 302);
      if (url.pathname === "/confirm" && request.method === "POST") return await confirm(url, request, env, cors);
      if (url.pathname === "/unsubscribe" && request.method === "POST") return await unsubscribe(url, request, env, cors);
      if (url.pathname === "/admin/subscribers" && request.method === "GET") return await listSubscribers(request, env);
      return new Response("Not found", { status: 404 });
    } catch (err) {
      console.error(err);
      return json({ ok: false, error: "Something went wrong. Please try again later." }, 500, cors);
    }
  },
};

// ---- handlers -----------------------------------------------------------------
async function subscribe(request, env, cors) {
  const body = await request.json().catch(() => ({}));
  const email = String(body.email || "").trim().toLowerCase();
  if (!/^[^\s@<>()",;]+@[^\s@<>()",;]+\.[a-z]{2,}$/i.test(email) || email.length > 254) {
    return json({ ok: false, error: "Please enter a valid email address." }, 400, cors);
  }
  if (!(await turnstileOk(body.turnstile, request, env))) {
    return json({ ok: false, error: "Please complete the check and try again." }, 400, cors);
  }

  const now = new Date().toISOString();
  const row = await env.DB.prepare("SELECT status, token, confirm_sent_at FROM subscribers WHERE email = ?")
    .bind(email).first();
  // The reply is the same whatever the address's state, so the form can't be used to find out who subscribes.
  const reply = json({ ok: true, message: "Almost there. Check your inbox for a confirmation email." }, 200, cors);

  if (row && row.status === "active") return reply;
  if (row && row.confirm_sent_at && Date.now() - Date.parse(row.confirm_sent_at) < RESEND_AFTER_MS) return reply;

  const token = row ? row.token : randomToken();
  if (row) {
    await env.DB.prepare("UPDATE subscribers SET status = 'pending', confirm_sent_at = ?, unsubscribed_at = NULL WHERE email = ?")
      .bind(now, email).run();
  } else {
    await env.DB.prepare("INSERT INTO subscribers (email, status, token, created_at, confirm_sent_at) VALUES (?, 'pending', ?, ?, ?)")
      .bind(email, token, now, now).run();
  }
  const mail = confirmEmail(`${env.SITE_URL}confirm.html?token=${token}`);  // link to the blog, not workers.dev
  await sendMail(env, { to: email, ...mail });
  return reply;
}

async function confirm(url, request, env, cors) {
  const body = await request.json().catch(() => ({}));
  const token = String(body.token || "");
  const row = await env.DB.prepare("SELECT email, status FROM subscribers WHERE token = ?").bind(token).first();
  if (!row || row.status === "unsubscribed") {
    return json({ ok: false, message: "This link is not valid. Please subscribe again from any page of the blog." }, 404, cors);
  }
  if (row.status !== "active") {
    await env.DB.prepare("UPDATE subscribers SET status = 'active', confirmed_at = ? WHERE token = ?")
      .bind(new Date().toISOString(), token).run();
    const unsub = `${env.SITE_URL}unsubscribe.html?token=${token}`;
    await sendMail(env, { to: row.email, ...welcomeEmail(unsub), unsubscribeUrl: unsub, oneClick: `${url.origin}/unsubscribe?token=${token}` })
      .catch((e) => console.error("welcome email failed", e)); // confirming must still succeed
  }
  return json({ ok: true }, 200, cors);
}

async function unsubscribe(url, request, env, cors) {
  let token = url.searchParams.get("token") || "";
  if (!token) {
    const body = await request.json().catch(() => ({}));
    token = String(body.token || "");
  }
  const result = await env.DB.prepare(
    "UPDATE subscribers SET status = 'unsubscribed', unsubscribed_at = ? WHERE token = ? AND status != 'unsubscribed'")
    .bind(new Date().toISOString(), token).run();
  const known = result.meta.changes > 0 ||
    !!(await env.DB.prepare("SELECT 1 FROM subscribers WHERE token = ?").bind(token).first());
  return json({ ok: known, message: known ? "You have been unsubscribed." : "This link is not valid." }, known ? 200 : 404, cors);
}

async function listSubscribers(request, env) {
  if (!env.ADMIN_TOKEN || request.headers.get("Authorization") !== `Bearer ${env.ADMIN_TOKEN}`) {
    return new Response("Unauthorized", { status: 401 });
  }
  const { results } = await env.DB.prepare(
    "SELECT email, token FROM subscribers WHERE status = 'active' ORDER BY confirmed_at").all();
  return json({ subscribers: results });
}

// ---- helpers ------------------------------------------------------------------
function json(data, status = 200, headers = {}) {
  return new Response(JSON.stringify(data), { status, headers: { "Content-Type": "application/json", ...headers } });
}

function randomToken() {
  const bytes = crypto.getRandomValues(new Uint8Array(24));
  return [...bytes].map((b) => b.toString(16).padStart(2, "0")).join("");
}

async function turnstileOk(token, request, env) {
  if (!token) return false;
  const form = new FormData();
  form.append("secret", env.TURNSTILE_SECRET);
  form.append("response", token);
  const ip = request.headers.get("CF-Connecting-IP");
  if (ip) form.append("remoteip", ip);
  const res = await fetch("https://challenges.cloudflare.com/turnstile/v0/siteverify", { method: "POST", body: form });
  const data = await res.json();
  return data.success === true;
}

// ---- Gmail SMTP over implicit TLS (port 465) ---------------------------------------
const enc = new TextEncoder();
const dec = new TextDecoder();

function b64(str) {
  const bytes = enc.encode(str);
  let bin = "";
  for (let i = 0; i < bytes.length; i += 0x8000) bin += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
  return btoa(bin);
}

function wrap76(s) {
  return s.replace(/.{1,76}/g, "$&\r\n");
}

function encodedWord(s) {
  return /^[\x20-\x7e]*$/.test(s) ? s : `=?UTF-8?B?${b64(s)}?=`;
}

export function buildMessage({ fromName, from, to, subject, html, text, unsubscribeUrl, oneClick }) {
  const boundary = "=_ca_" + randomToken();
  const headers = [
    `From: ${encodedWord(fromName)} <${from}>`,
    `To: <${to}>`,
    `Subject: ${encodedWord(subject)}`,
    `Date: ${new Date().toUTCString()}`,
    "MIME-Version: 1.0",
    `Content-Type: multipart/alternative; boundary="${boundary}"`,
  ];
  if (unsubscribeUrl) {
    headers.push(`List-Unsubscribe: <${oneClick || unsubscribeUrl}>`);
    if (oneClick) headers.push("List-Unsubscribe-Post: List-Unsubscribe=One-Click");
  }
  return [
    ...headers, "",
    `--${boundary}`, "Content-Type: text/plain; charset=UTF-8", "Content-Transfer-Encoding: base64", "",
    wrap76(b64(text)),
    `--${boundary}`, "Content-Type: text/html; charset=UTF-8", "Content-Transfer-Encoding: base64", "",
    wrap76(b64(html)),
    `--${boundary}--`, "",
  ].join("\r\n");
}

async function sendMail(env, { to, subject, html, text, unsubscribeUrl, oneClick }) {
  const message = buildMessage({ fromName: env.FROM_NAME, from: env.FROM_EMAIL, to, subject, html, text, unsubscribeUrl, oneClick });
  const socket = connect({ hostname: "smtp.gmail.com", port: 465 }, { secureTransport: "on" });
  const writer = socket.writable.getWriter();
  const reader = socket.readable.getReader();
  let buffer = "";

  async function reply(expect) {
    for (;;) {
      const lines = buffer.split("\r\n");
      const done = lines.findIndex((l) => /^\d{3} /.test(l));
      if (done >= 0) {
        const code = parseInt(lines[done].slice(0, 3), 10);
        buffer = lines.slice(done + 1).join("\r\n");
        if (code !== expect) throw new Error(`SMTP expected ${expect}, got: ${lines.slice(0, done + 1).join(" | ")}`);
        return;
      }
      const { value, done: closed } = await reader.read();
      if (closed) throw new Error("SMTP connection closed");
      buffer += dec.decode(value, { stream: true });
    }
  }
  const send = (line) => writer.write(enc.encode(line + "\r\n"));

  try {
    await reply(220);
    await send("EHLO canvassandanalyze"); await reply(250);
    await send("AUTH PLAIN " + b64(`\0${env.FROM_EMAIL}\0${env.GMAIL_APP_PASSWORD}`)); await reply(235);
    await send(`MAIL FROM:<${env.FROM_EMAIL}>`); await reply(250);
    await send(`RCPT TO:<${to}>`); await reply(250);
    await send("DATA"); await reply(354);
    await writer.write(enc.encode(message.replace(/^\./gm, "..") + "\r\n.\r\n")); await reply(250);
    await send("QUIT");
  } finally {
    try { await writer.close(); } catch (e) { /* already closed */ }
    try { await socket.close(); } catch (e) { /* already closed */ }
  }
}
