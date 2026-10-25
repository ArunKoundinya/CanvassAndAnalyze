"""Quarto post-render step: wire up the email subscribe form.

Reads subscribe/site.json (the Worker URL and the public Turnstile site key).
Until the Worker is deployed and those are filled in, nothing is added.
  - every .subscribe-form placeholder gets data-endpoint / data-sitekey
  - every post gets a subscribe card at the end of the article
  - pages with a form load assets/subscribe.js
  - confirm.html and unsubscribe.html learn the Worker URL
"""
import json, os, re

OUT = "_site"
cfg = json.load(open("subscribe/site.json"))
endpoint, sitekey = cfg.get("worker_url", "").rstrip("/"), cfg.get("turnstile_site_key", "")

CARD = """<div class="subscribe-card">
  <p class="kicker">Enjoyed this?</p>
  <h3>Get the next one in your inbox</h3>
  <div class="subscribe-form"></div>
</div>
"""

changed = 0
if endpoint:
    for d, _, files in os.walk(OUT):
        if "site_libs" in d:
            continue
        for f in files:
            if not f.endswith(".html"):
                continue
            path = os.path.join(d, f)
            page = open(path, encoding="utf-8").read()
            if "data-endpoint=" in page:                   # already wired
                continue
            rel = os.path.relpath(path, OUT).replace(os.sep, "/")
            root = "../" * rel.count("/")
            new = page
            if rel.startswith("posts/") and rel.endswith("/index.html") and "<main" in new:
                anchor = next((a for a in ['<nav class="series-nav"', '<script src="https://giscus.app', "</main>"] if a in new), None)
                if anchor:
                    new = new.replace(anchor, CARD + anchor, 1)
            if 'class="subscribe-form"' in new:
                new = new.replace('class="subscribe-form"',
                                  f'class="subscribe-form" data-endpoint="{endpoint}" data-sitekey="{sitekey}"')
                new = new.replace("</body>", f'<script src="{root}assets/subscribe.js" defer></script>\n</body>', 1)
            if rel in ("unsubscribe.html", "confirm.html"):
                new = re.sub(r"<body([^>]*)>", lambda m: f'<body{m.group(1)} data-subscribe-endpoint="{endpoint}">', new, count=1)
            if new != page:
                open(path, "w", encoding="utf-8").write(new)
                changed += 1
print(f"subscribe_box.py: {'wired ' + str(changed) + ' pages' if endpoint else 'skipped (subscribe/site.json has no worker_url yet)'}")
