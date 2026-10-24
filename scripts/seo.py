"""Quarto post-render step: adds the SEO tags Quarto doesn't emit on its own.

For every rendered page it adds a canonical URL, and for posts it adds
author/date meta tags plus schema.org JSON-LD (BlogPosting), which Google,
Bing and the engines that use Bing's index (DuckDuckGo, Yahoo, Ecosia) read
to understand the page. Runs automatically after `quarto render`.
"""
import json, os, re

SITE = ""
cfg = open("_quarto.yml", encoding="utf-8").read()
m = re.search(r"^\s*site-url:\s*(\S+)", cfg, re.M)
SITE = (m.group(1) if m else "").rstrip("/") + "/"
OUT = "_site"
AUTHOR = {"@type": "Person", "name": "Arun Koundinya Parasa", "url": SITE + "about.html",
          "sameAs": ["https://www.linkedin.com/in/arunkoundinya0710/", "https://github.com/ArunKoundinya"]}
MARK = "<!-- seo.py -->"


def front_matter(src):
    try:
        s = open(src, encoding="utf-8").read()
    except OSError:
        return {}
    m = re.match(r"---\n(.*?)\n---", s, re.S)
    fm = {}
    for line in (m.group(1).splitlines() if m else []):
        kv = re.match(r"^([A-Za-z-]+):\s*(.*)$", line)
        if kv:
            v = kv.group(2).strip()
            if v.startswith("[") and v.endswith("]"):
                v = [x.strip().strip("\"'") for x in v[1:-1].split(",") if x.strip()]
            else:
                v = v.strip("\"'")
            fm[kv.group(1)] = v
    return fm


def page_url(rel):
    rel = rel.replace(os.sep, "/")
    return SITE + (rel[: -len("index.html")] if rel.endswith("index.html") else rel)


def tags_for(rel):
    url = page_url(rel)
    out = [f'<link rel="canonical" href="{url}">']
    src = os.path.splitext(rel)[0] + ".qmd"
    fm = front_matter(src)

    if rel.startswith("posts/") and fm:
        folder = url
        image = fm.get("image")
        data = {
            "@context": "https://schema.org",
            "@type": "BlogPosting",
            "headline": fm.get("title", ""),
            "description": fm.get("description", ""),
            "datePublished": fm.get("date", ""),
            "author": AUTHOR,
            "publisher": AUTHOR,
            "mainEntityOfPage": url,
            "url": url,
            "inLanguage": "en",
            "isPartOf": {"@type": "Blog", "name": "Canvass And Analyze", "url": SITE},
        }
        if image:
            data["image"] = image if image.startswith("http") else folder + image
        if isinstance(fm.get("categories"), list):
            data["keywords"] = ", ".join(fm["categories"])
        out += [
            '<meta name="author" content="Arun Koundinya Parasa">',
            f'<meta property="og:type" content="article">',
            f'<meta property="article:published_time" content="{fm.get("date", "")}">',
            f'<meta property="og:url" content="{url}">',
        ]
    elif rel == "index.html":
        data = {
            "@context": "https://schema.org",
            "@graph": [
                {"@type": "WebSite", "name": "Canvass And Analyze", "url": SITE,
                 "description": fm.get("description", ""), "author": AUTHOR,
                 "potentialAction": {"@type": "SearchAction",
                                     "target": SITE + "search.html?q={query}",
                                     "query-input": "required name=query"}},
                {"@type": "Blog", "name": "Canvass And Analyze", "url": SITE, "author": AUTHOR},
            ],
        }
    elif rel.startswith("series/") and fm:
        data = {"@context": "https://schema.org", "@type": "CollectionPage",
                "name": fm.get("title", ""), "description": fm.get("description", ""),
                "url": url, "author": AUTHOR}
    elif rel == "about.html":
        data = {"@context": "https://schema.org", "@type": "ProfilePage", "mainEntity": AUTHOR}
    else:
        data = None

    if not rel.startswith("posts/"):
        out += ['<meta property="og:type" content="website">', f'<meta property="og:url" content="{url}">']
    if data:
        out.append('<script type="application/ld+json">' + json.dumps(data, ensure_ascii=False) + "</script>")
    return MARK + "\n" + "\n".join(out) + "\n"


files = os.environ.get("QUARTO_PROJECT_OUTPUT_FILES", "").split("\n")
files = [f for f in files if f.endswith(".html")] or [
    os.path.join(d, f) for d, _, fs in os.walk(OUT) for f in fs if f.endswith(".html")]

done = 0
for path in files:
    rel = os.path.relpath(path, OUT)
    if rel.startswith("site_libs"):
        continue
    html = open(path, encoding="utf-8").read()
    if MARK in html or "</head>" not in html:
        continue
    if "old_index" in rel:
        # Superseded drafts stay reachable but shouldn't compete with the new version in search.
        new = page_url(rel.replace("old_index.html", "index.html"))
        tag = f'{MARK}\n<meta name="robots" content="noindex, follow">\n<link rel="canonical" href="{new}">\n'
        html = html.replace('<meta name="robots" content="index, follow, max-image-preview:large">', "")
        open(path, "w", encoding="utf-8").write(html.replace("</head>", tag + "</head>", 1))
        continue
    html = re.sub(r'\s*<meta property="og:(type|url)"[^>]*>', "", html)
    # WhatsApp and LinkedIn previews are pickier than Google: give the image's type and alt text
    # right next to og:image.
    m = re.search(r'<meta property="og:image" content="([^"]+)">', html)
    if m:
        ext = m.group(1).rsplit(".", 1)[-1].lower()
        kind = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png", "webp": "webp", "gif": "gif"}.get(ext)
        title = re.search(r'<meta property="og:title" content="([^"]*)"', html)
        extra = (f'\n<meta property="og:image:type" content="image/{kind}">' if kind else "") + \
                (f'\n<meta property="og:image:alt" content="{title.group(1)}">' if title else "")
        html = html.replace(m.group(0), m.group(0) + extra, 1)
    html = html.replace("</head>", tags_for(rel) + "</head>", 1)
    open(path, "w", encoding="utf-8").write(html)
    done += 1
sm = os.path.join(OUT, "sitemap.xml")
if os.path.exists(sm):
    xml = open(sm, encoding="utf-8").read()
    xml = re.sub(r"\s*<url>\s*<loc>[^<]*old_index[^<]*</loc>.*?</url>", "", xml, flags=re.S)
    open(sm, "w", encoding="utf-8").write(xml)

print(f"seo.py: tagged {done} pages")
