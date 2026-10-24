"""Quarto post-render step: series navigation on posts, and live series counts.

Any post with `series: <name>` in its front matter (matching series/<name>.qmd)
gets a "Part N of M · Series" line above its title and previous/next cards
at the end. Order is by date, except the novel, which follows its folders
(Love & Trust S1, S2, then Trust & Betrayal).

It also fills in counts anywhere a page has an element marked
data-count="<series>" (or "<series>:<folder prefix>", or "series" for the
number of series), replacing {n}, {first}, {last} and {seasons} in its text.
So "{n} essays · {first} – {last}" always matches the posts that exist.
"""
import glob, html, os, re

OUT = "_site"
MARK = "<!-- series_nav -->"


def fm(path):
    s = open(path, encoding="utf-8").read()
    m = re.match(r"---\n(.*?)\n---", s, re.S)
    out = {}
    for line in (m.group(1).splitlines() if m else []):
        kv = re.match(r"^([A-Za-z-]+):\s*(.*)$", line)
        if kv:
            out[kv.group(1)] = kv.group(2).strip().strip("\"'")
    return out


def natural(s):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", s)]


series = {}
for page in glob.glob("series/*.qmd"):
    key = os.path.splitext(os.path.basename(page))[0]
    series[key] = {"title": fm(page).get("title", key), "page": f"series/{key}.html", "posts": []}

for src in glob.glob("posts/*/index.qmd"):
    meta = fm(src)
    if meta.get("series") in series:
        folder = src.split("/")[1]
        series[meta["series"]]["posts"].append({"folder": folder, "title": meta.get("title", folder),
                                                 "date": meta.get("date", "")})

for key, s in series.items():
    s["posts"].sort(key=(lambda p: natural(p["folder"])) if key == "novel" else (lambda p: p["date"]))

lookup = {p["folder"]: (key, i) for key, s in series.items() for i, p in enumerate(s["posts"])}


def card(p, label, cls):
    return (f'<a class="series-nav-card {cls}" href="../{p["folder"]}/">'
            f'<span class="kicker">{label}</span><span class="t">{html.escape(p["title"])}</span></a>')


done = 0
for folder, (key, i) in lookup.items():
    path = os.path.join(OUT, "posts", folder, "index.html")
    if not os.path.exists(path):
        continue
    page = open(path, encoding="utf-8").read()
    if MARK in page:
        continue
    s, posts = series[key], series[key]["posts"]
    top = (f'{MARK}<p class="series-crumb"><a href="../../{s["page"]}">'
           f'Part {i + 1} of {len(posts)} · {html.escape(s["title"])}</a></p>')
    prev_ = card(posts[i - 1], "← Previous", "prev") if i > 0 else '<span></span>'
    next_ = card(posts[i + 1], "Next →", "next") if i + 1 < len(posts) else \
        f'<a class="series-nav-card next" href="../../{s["page"]}"><span class="kicker">You\'re up to date</span><span class="t">Back to {html.escape(s["title"])}</span></a>'
    bottom = (f'{MARK}<nav class="series-nav" aria-label="Series navigation">'
              f'<p class="series-nav-head"><a href="../../{s["page"]}">{html.escape(s["title"])}</a> · Part {i + 1} of {len(posts)}</p>'
              f'<div class="series-nav-grid">{prev_}{next_}</div></nav>')

    page = re.sub(r'(<header id="title-block-header"[^>]*>)', r"\1" + top.replace("\\", "\\\\"), page, count=1)
    anchor = '<script src="https://giscus.app' if '<script src="https://giscus.app' in page else "</main>"
    page = page.replace(anchor, bottom + "\n" + anchor, 1)
    open(path, "w", encoding="utf-8").write(page)
    done += 1
print(f"series_nav.py: added navigation to {done} posts")


def fill_text(key, text):
    if key == "series":
        n, years, seasons = len(series), [], []
    else:
        name, _, prefix = key.partition(":")
        posts = [p for p in series.get(name, {}).get("posts", []) if p["folder"].startswith(prefix)]
        n = len(posts)
        years = sorted(p["date"][:4] for p in posts if p["date"][:4].isdigit())
        seasons = sorted({int(m) for p in posts for m in re.findall(r"Season(\d+)", p["folder"])})
    span = "" if not seasons else (str(seasons[0]) if len(seasons) == 1 else f"{seasons[0]}–{seasons[-1]}")
    return (text.replace("{n}", str(n)).replace("{first}", years[0] if years else "")
                .replace("{last}", years[-1] if years else "").replace("{seasons}", span))


def fill(match):
    text = fill_text(match.group(1), match.group(3))
    return match.group(0)[: match.start(3) - match.start(0)] + text + "<"


filled = 0
for path in glob.glob(os.path.join(OUT, "**", "*.html"), recursive=True):
    page = open(path, encoding="utf-8").read()
    if 'data-count="' not in page:
        continue
    new = re.sub(r'data-count="([^"]+)"([^>]*)>([^<]*)<', fill, page)
    if new != page:
        open(path, "w", encoding="utf-8").write(new)
        filled += 1

# The site search index holds the raw page text too, so fill the series pages' entries there.
import json
idx_path = os.path.join(OUT, "search.json")
if os.path.exists(idx_path):
    idx = json.load(open(idx_path, encoding="utf-8"))
    for entry in idx:
        m = re.match(r"series/([\w-]+)\.html", entry.get("href", ""))
        if m and "{n}" in entry.get("text", ""):
            entry["text"] = fill_text(m.group(1), entry["text"])
    json.dump(idx, open(idx_path, "w", encoding="utf-8"), ensure_ascii=False)
print(f"series_nav.py: filled series counts on {filled} pages")
