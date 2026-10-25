"""Branded emails for Canvass And Analyze subscribers.

Every email shares one layout (see BRAND below) so readers always recognise
it: cream page, white card, the C+A logo, serif headings, one terracotta
button, and the same footer with an unsubscribe link.

    python3 scripts/email_templates.py preview [post-folder]   # writes HTML previews

Emails:
  confirm  - double opt-in: "Confirm your subscription"
  welcome  - sent once after confirming: where to start
  new_post - one per new post: series, cover, description, Read + Listen
Each has an HTML and a plain-text version.
"""
import html, json, os, re, sys

SITE = "https://arunkoundinya.github.io/CanvassAndAnalyze/"

# ---- Brand rules -------------------------------------------------------------
BRAND = {
    "name": "Canvass And Analyze",
    "from_name": "Arun Koundinya Parasa · Canvass And Analyze",
    "tagline": "Essays, series and stories on the mind, culture and the choices we make.",
    "logo": SITE + "images/logo-mark.png",
    # colours mirror theme.scss
    "paper": "#FAF6EF", "card": "#FFFFFF", "ink": "#2A2420", "ink_soft": "#4A403A",
    "muted": "#7A6C62", "rule": "#E3D7C6", "accent": "#B4532A", "accent_dark": "#8C3D1C",
    # web fonts are unreliable in email clients; these fall back gracefully
    "serif": "Georgia, 'Times New Roman', serif",
    "sans": "-apple-system, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
}
# Subject lines: new post = the post's own title; series posts get a prefix,
# e.g. "Thinking in Systems · Part 2: What Is Left for a Data Scientist…".
# Voice: first person, warm, short. No exclamation marks, no "Don't miss out".

SERIES_TITLE = {"novel": "Threads of One Life", "systems": "Thinking in Systems",
                "spirituality": "Extended Learnings on Indian Culture", "covid19": "COVID-19 Chronicles"}
VOICE_NAME = {"ava": "Ava", "aria": "Aria", "emma": "Emma"}


def esc(t):
    return html.escape(str(t or ""), quote=True)


def layout(preheader, body_html, unsubscribe_url=None, reason=None):
    b = BRAND
    reason = reason or f"You are receiving this because you subscribed to {b['name']}."
    unsub = (f' · <a href="{esc(unsubscribe_url)}" style="color:{b["muted"]};text-decoration:underline;">Unsubscribe</a>'
             if unsubscribe_url else "")
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light"><meta name="supported-color-schemes" content="light">
<title>{esc(b['name'])}</title></head>
<body style="margin:0;padding:0;background:{b['paper']};">
<div style="display:none;max-height:0;overflow:hidden;opacity:0;color:transparent;">{esc(preheader)}&#8199;&#65279;&#847;&#8199;&#65279;&#847;&#8199;&#65279;&#847;</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:{b['paper']};">
<tr><td align="center" style="padding:28px 14px;">
  <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" style="width:100%;max-width:600px;">
    <tr><td style="padding:0 6px 18px;">
      <a href="{SITE}" style="text-decoration:none;color:{b['ink']};">
        <img src="{b['logo']}" width="36" height="36" alt="" style="vertical-align:middle;border:0;border-radius:8px;">
        <span style="font-family:{b['serif']};font-size:19px;font-weight:bold;vertical-align:middle;margin-left:8px;">{esc(b['name'])}</span>
      </a>
    </td></tr>
    <tr><td style="background:{b['card']};border:1px solid {b['rule']};border-radius:14px;padding:34px 34px 30px;">
      {body_html}
    </td></tr>
    <tr><td style="padding:22px 10px 0;font-family:{b['sans']};font-size:12px;line-height:1.6;color:{b['muted']};text-align:center;">
      <em style="font-family:{b['serif']};font-size:13px;">{esc(b['tagline'])}</em><br>
      Written by Arun Koundinya Parasa ·
      <a href="{SITE}" style="color:{b['muted']};text-decoration:underline;">Visit the blog</a><br>
      {esc(reason)}{unsub}
    </td></tr>
  </table>
</td></tr></table>
</body></html>"""


def kicker(text):
    b = BRAND
    return (f'<p style="margin:0 0 10px;font-family:{b["sans"]};font-size:11px;font-weight:bold;'
            f'letter-spacing:1.6px;text-transform:uppercase;color:{b["accent"]};">{esc(text)}</p>')


def heading(text, size=28):
    b = BRAND
    return (f'<h1 style="margin:0 0 14px;font-family:{b["serif"]};font-size:{size}px;line-height:1.2;'
            f'font-weight:bold;color:{b["ink"]};">{esc(text)}</h1>')


def para(text, italic=False, size=16):
    b = BRAND
    style = "font-style:italic;" if italic else ""
    return (f'<p style="margin:0 0 16px;font-family:{b["serif"]};font-size:{size}px;line-height:1.65;'
            f'color:{b["ink_soft"]};{style}">{text}</p>')


def button(label, url, primary=True):
    b = BRAND
    bg, fg, border = (b["accent"], "#FFFFFF", b["accent"]) if primary else ("#FFFFFF", b["ink"], b["rule"])
    return (f'<a href="{esc(url)}" style="display:inline-block;margin:4px 8px 4px 0;padding:12px 22px;'
            f'border-radius:999px;background:{bg};border:1px solid {border};color:{fg};'
            f'font-family:{b["sans"]};font-size:14px;font-weight:bold;text-decoration:none;">{esc(label)}</a>')


def meta_line(text):
    b = BRAND
    return f'<p style="margin:14px 0 0;font-family:{b["sans"]};font-size:12px;color:{b["muted"]};">{esc(text)}</p>'


# ---- Emails --------------------------------------------------------------------
def confirm(confirm_url):
    subject = f"Confirm your subscription to {BRAND['name']}"
    pre = "One click and you're in. If this wasn't you, ignore this email."
    body = (kicker("One last step") + heading("Please confirm your subscription")
            + para("Thank you for wanting to hear from me. Click below and you'll get an email whenever I publish "
                   "something new: an essay, a chapter of my novel, or a new part of a series.")
            + f'<p style="margin:22px 0 6px;">{button("Yes, subscribe me", confirm_url)}</p>'
            + para("If you didn't ask for this, simply ignore this email and you won't hear from me again.", size=14))
    text = (f"Please confirm your subscription to {BRAND['name']}.\n\n"
            f"Confirm here: {confirm_url}\n\nIf you didn't ask for this, ignore this email.\n\n— Arun\n{SITE}")
    return subject, layout(pre, body, reason="You received this because someone entered this address on the blog."), text


def welcome(unsubscribe_url):
    subject = f"Welcome to {BRAND['name']}"
    pre = "Here's where to start, whether you like to read or to listen."
    starts = [
        ("Threads of One Life", "My novel in progress: eight lives, each carrying one emotion.", SITE + "series/novel.html"),
        ("Thinking in Systems", "AI, analytics and leadership, seen as systems.", SITE + "series/systems.html"),
        ("Extended Learnings on Indian Culture", "29 essays on Rishis, Gurus, Gunas and the three Yogas.", SITE + "series/spirituality.html"),
    ]
    b = BRAND
    items = "".join(
        f'<tr><td style="padding:12px 0;border-top:1px solid {b["rule"]};">'
        f'<a href="{esc(u)}" style="font-family:{b["serif"]};font-size:17px;font-weight:bold;color:{b["ink"]};text-decoration:none;">{esc(t)} →</a>'
        f'<div style="font-family:{b["serif"]};font-size:14px;line-height:1.5;color:{b["muted"]};margin-top:3px;">{esc(d)}</div></td></tr>'
        for t, d, u in starts)
    body = (kicker("You're subscribed") + heading("Welcome, and thank you")
            + para("I started this blog in 2017 to share my thought process where psychology, Indian culture, "
                   "analytics and management meet. You'll now get an email whenever something new is published.")
            + para("Every post can also be <strong>listened to</strong>: press ▶ at the top of any post.")
            + f'<p style="margin:18px 0 6px;font-family:{b["sans"]};font-size:12px;font-weight:bold;letter-spacing:1.4px;text-transform:uppercase;color:{b["muted"]};">Good places to start</p>'
            + f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">{items}</table>'
            + para("<br>— Arun", size=15))
    text = ("Welcome to Canvass And Analyze, and thank you.\n\nGood places to start:\n"
            + "".join(f"- {t}: {u}\n" for t, _, u in starts)
            + f"\nEvery post can also be listened to.\n\n— Arun\n\nUnsubscribe: {unsubscribe_url}")
    return subject, layout(pre, body, unsubscribe_url), text


def new_post(post, unsubscribe_url):
    """post: dict with title, description, url, image, kicker, read_min, listen_min, voice, date."""
    b = BRAND
    title = post["title"]
    subject = f"{post['series_title']} · Part {post['part']}: {title}" if post.get("series_title") else title
    w = 530 if post.get("image_ratio", 0.6) <= 0.72 else 320      # tall/square covers shouldn't fill the screen
    img = (f'<a href="{esc(post["url"])}"><img src="{esc(post["image"])}" width="{w}" alt="" '
           f'style="display:block;width:100%;max-width:{w}px;height:auto;border:0;border-radius:10px;margin:0 auto 22px;"></a>'
           if post.get("image") else "")
    listen = (button(f"▶ Listen · {post['listen_min']} min", post["url"] + "#listen", primary=False)
              if post.get("listen_min") else "")
    meta = " · ".join(x for x in [post.get("date"), f"{post['read_min']} min read" if post.get("read_min") else "",
                                    f"narrated by {post['voice']}" if post.get("voice") else ""] if x)
    body = (img + kicker(post["kicker"]) + heading(title)
            + (para(esc(post["subtitle"]), italic=True, size=17) if post.get("subtitle") else "")
            + (para(esc(post["description"])) if post.get("description") and post.get("description") != post.get("subtitle") else "")
            + f'<p style="margin:22px 0 0;">{button("Read the post", post["url"])}{listen}</p>'
            + meta_line(meta))
    text = (f"{post['kicker']}\n\n{title}\n"
            + (f"{post['subtitle']}\n" if post.get("subtitle") else "")
            + (f"\n{post['description']}\n" if post.get("description") and post.get("description") != post.get("subtitle") else "")
            + f"\nRead: {post['url']}\n"
            + (f"Listen ({post['listen_min']} min): {post['url']}#listen\n" if post.get("listen_min") else "")
            + f"\n— Arun\n\nUnsubscribe: {unsubscribe_url}")
    return subject, layout(post.get("description") or post.get("subtitle") or title, body, unsubscribe_url), text


# ---- Post data from the site sources -----------------------------------------
def front_matter(path):
    s = open(path, encoding="utf-8").read()
    m = re.match(r"---\n(.*?)\n---\n", s, re.S)
    fm = {}
    for line in (m.group(1).splitlines() if m else []):
        kv = re.match(r"^([A-Za-z-]+):\s*(.*)$", line)
        if kv:
            v = kv.group(2).strip()
            fm[kv.group(1)] = ([x.strip().strip("\"'") for x in v[1:-1].split(",") if x.strip()]
                               if v.startswith("[") and v.endswith("]") else v.strip("\"'"))
    return fm, s[m.end():] if m else s


def teaser(path, limit=260):
    """The opening of the piece, cleaned the same way the narration is."""
    sys.path.insert(0, os.path.dirname(__file__))
    from narrate import narration
    fm, text = narration(path)
    paras = text.split("\n\n")[2:-1]                  # skip the spoken title/byline and the outro
    out = ""
    for p in paras:
        if len(p) < 40 and not out:                    # skip scene headings like "5:45 P.M."
            continue
        out = (out + " " + p).strip()
        if len(out) >= 140:
            break
    if len(out) > limit:
        out = out[:limit].rsplit(" ", 1)[0].rstrip(",;:") + "…"
    return out


def display_title(title):
    """Inbox-friendly title: tidy novel episode titles, and no ALL-CAPS shouting."""
    m = re.search(r"(LOVE & TRUST|TRUST & BETRAYAL).*?Season\s*-?\s*(\d+).*?Episode\s*-?\s*(\d+)", title, re.I)
    if m:
        story = "Love & Trust" if m.group(1).upper().startswith("LOVE") else "Trust & Betrayal"
        return f"{story} · Season {m.group(2)}, Episode {m.group(3)}"
    m = re.match(r"\s*(Extended Learnings|Glossary)\s*-?\s*\d+\s*\|.*\|\s*(.+)$", title)
    if m:                                                   # the kicker already names the series and part
        return ("Glossary: " if m.group(1) == "Glossary" else "") + m.group(2).strip()
    if title.isupper():
        small = {"and", "or", "of", "the", "a", "an", "in", "on", "to", "with", "for"}
        keep = {"AI", "COVID", "US", "WHO", "IT", "CTC", "MIT", "W.I.F.M."}       # acronyms stay as they are
        out, prev = [], ""
        for i, w in enumerate(title.split()):
            core = w.strip(":,.?!()")
            if core in keep:
                out.append(w)
            elif i and not prev.endswith(":") and w.lower() in small:
                out.append(w.lower())
            else:
                out.append(w.capitalize())
            prev = w
        title = " ".join(out)
    return re.sub(r"\s+([,.?!:])", r"\1", title)


def post_info(slug):
    import datetime, glob
    fm, body = front_matter(f"posts/{slug}/index.qmd")
    url = f"{SITE}posts/{slug}/"
    info = {"slug": slug, "title": display_title(fm.get("title", slug)), "subtitle": fm.get("subtitle", ""),
            "description": fm.get("description", ""), "url": url,
            "image": url + fm["image"] if fm.get("image") and not fm["image"].startswith("http") else fm.get("image", ""),
            "read_min": max(1, round(len(body.split()) / 220))}
    local = f"posts/{slug}/{fm.get('image', '')}"
    if fm.get("image") and os.path.exists(local):
        try:
            from PIL import Image
            with Image.open(local) as im:
                info["image_ratio"] = im.height / im.width
        except Exception:
            pass
    try:
        info["date"] = datetime.date.fromisoformat(fm.get("date", "")).strftime("%B %-d, %Y")
    except ValueError:
        info["date"] = ""
    series = fm.get("series")
    if series in SERIES_TITLE:
        members = []
        for p in glob.glob("posts/*/index.qmd"):
            f2, _ = front_matter(p)
            if f2.get("series") == series:
                members.append((p.split("/")[1], f2.get("date", "")))
        key = (lambda x: [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", x[0])]) if series == "novel" else (lambda x: x[1])
        order = [m[0] for m in sorted(members, key=key)]
        info.update(series_title=SERIES_TITLE[series], part=order.index(slug) + 1,
                    kicker=f"New · {SERIES_TITLE[series]} · Part {order.index(slug) + 1} of {len(order)}")
    else:
        cats = fm.get("categories") or []
        info["kicker"] = "New post" + (f" · {cats[0]}" if cats else "")
    if info["description"].startswith(info["title"]):         # "Is Celibacy Needed? Part 105 of…" -> "Part 105 of…"
        info["description"] = info["description"][len(info["title"]):].strip()
    # the kicker numbers posts by their place in the series; drop the blog's own "Part 105" numbering
    info["description"] = re.sub(r"^Part \d+ of Extended Learnings, my series", "From my series", info["description"])
    if series == "novel":                                   # chapter descriptions are written for search engines
        info["description"] = teaser(f"posts/{slug}/index.qmd")
    manifest = json.load(open("audio/manifest.json")) if os.path.exists("audio/manifest.json") else {}
    if slug in manifest:
        info["listen_min"] = max(1, round(manifest[slug]["seconds"] / 60))
        info["voice"] = VOICE_NAME.get(manifest[slug]["voice"], "")
    return info


if __name__ == "__main__" and len(sys.argv) > 1 and sys.argv[1] == "preview":
    out = os.environ.get("PREVIEW_DIR", "email-preview")
    if os.environ.get("PREVIEW_LOGO"):                     # logo isn't published yet; show the local copy
        BRAND["logo"] = os.environ["PREVIEW_LOGO"]
    os.makedirs(out, exist_ok=True)
    unsub = SITE + "unsubscribe.html?token=EXAMPLE"
    slugs = sys.argv[2:] or ["what-is-left-for-data-scientists"]
    emails = {"1-confirm": confirm(SITE + "confirm.html?token=EXAMPLE"), "2-welcome": welcome(unsub)}
    for i, s in enumerate(slugs, 3):
        emails[f"{i}-new-post-{s}"] = new_post(post_info(s), unsub)
    for name, (subject, html_body, text) in emails.items():
        open(os.path.join(out, name + ".html"), "w", encoding="utf-8").write(html_body)
        open(os.path.join(out, name + ".txt"), "w", encoding="utf-8").write(f"Subject: {subject}\n\n{text}")
        print(f"{name}: {subject}")
