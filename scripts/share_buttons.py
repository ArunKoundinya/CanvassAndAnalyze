"""Quarto post-render step: add share buttons to every post.

A compact row sits under the title (above the Listen player) and a fuller
"Share this post" card sits at the end of the article. Links go to WhatsApp,
LinkedIn, X, Facebook, Telegram and email, plus "Copy link"; on phones the
native share sheet is offered too. Shared links use the post's canonical URL,
so WhatsApp/LinkedIn show the preview card that scripts/seo.py sets up.
"""
import html, os, re
from urllib.parse import quote

OUT = "_site"
MARK = "<!-- share_buttons -->"


def links(url, title):
    u, t = quote(url, safe=""), quote(title, safe="")
    return [
        ("whatsapp", "WhatsApp", f"https://wa.me/?text={t}%0A{u}"),
        ("linkedin", "LinkedIn", f"https://www.linkedin.com/sharing/share-offsite/?url={u}"),
        ("twitter-x", "X", f"https://twitter.com/intent/tweet?url={u}&text={t}"),
        ("facebook", "Facebook", f"https://www.facebook.com/sharer/sharer.php?u={u}"),
        ("telegram", "Telegram", f"https://t.me/share/url?url={u}&text={t}"),
        ("envelope", "Email", f"mailto:?subject={t}&body={t}%0A%0A{u}"),
    ]


def share_row(url, title, big=False):
    out = []
    for icon, name, href in links(url, title):
        target = "" if icon == "envelope" else ' target="_blank" rel="noopener"'
        label = f"<span>{name}</span>" if big else ""
        out.append(f'<a class="share-btn share-{icon}" href="{html.escape(href)}"{target} '
                   f'aria-label="Share on {name}" title="{name}"><i class="bi bi-{icon}"></i>{label}</a>')
    out.append('<button class="share-btn share-copy" type="button" aria-label="Copy link" title="Copy link">'
               '<i class="bi bi-link-45deg"></i><span>Copy link</span></button>')
    out.append('<button class="share-btn share-native" type="button" hidden aria-label="More sharing options">'
               '<i class="bi bi-share"></i><span>Share</span></button>')
    attrs = f'data-url="{html.escape(url)}" data-title="{html.escape(title)}"'
    if big:
        return (f'<div class="share-card" {attrs}>\n  <p class="kicker">Know someone who\'d enjoy this?</p>\n'
                f'  <h3>Share this post</h3>\n  <div class="share-row">{"".join(out)}</div>\n</div>\n')
    return f'<div class="share-row share-top" {attrs}><span class="share-label">Share</span>{"".join(out)}</div>\n'


SCRIPT = """<script>
document.querySelectorAll(".share-top, .share-card").forEach(function (box) {
  var url = box.dataset.url, title = box.dataset.title;
  var copy = box.querySelector(".share-copy"), native = box.querySelector(".share-native");
  copy.addEventListener("click", function () {
    var label = copy.querySelector("span");
    function done() { copy.classList.add("copied"); label.textContent = "Copied!";
      setTimeout(function () { copy.classList.remove("copied"); label.textContent = "Copy link"; }, 1800); }
    if (navigator.clipboard) navigator.clipboard.writeText(url).then(done, function () { prompt("Copy this link:", url); });
    else prompt("Copy this link:", url);
  });
  if (navigator.share) {
    native.hidden = false;
    native.addEventListener("click", function () { navigator.share({ title: title, url: url }).catch(function () {}); });
  }
});
</script>"""

done = 0
for slug in sorted(os.listdir(os.path.join(OUT, "posts"))):
    path = os.path.join(OUT, "posts", slug, "index.html")
    if not os.path.exists(path):
        continue
    page = open(path, encoding="utf-8").read()
    if MARK in page or '<header id="title-block-header"' not in page:
        continue
    m = re.search(r'<link rel="canonical" href="([^"]+)"', page)
    t = re.search(r'<h1 class="title">(.*?)</h1>', page, re.S)
    if not (m and t):
        continue
    url, title = m.group(1), html.unescape(re.sub(r"<[^>]+>", "", t.group(1))).strip()
    end = page.find("</header>", page.find('<header id="title-block-header"')) + len("</header>")
    page = page[:end] + "\n" + MARK + "\n" + share_row(url, title) + page[end:]
    # End of the article: before the series navigation / comments (the subscribe card follows).
    anchor = next((a for a in ['<nav class="series-nav"', '<script src="https://giscus.app', "</main>"] if a in page), None)
    if anchor:
        page = page.replace(anchor, share_row(url, title, big=True) + anchor, 1)
    page = page.replace("</body>", SCRIPT + "\n</body>", 1)
    open(path, "w", encoding="utf-8").write(page)
    done += 1
print(f"share_buttons.py: added share buttons to {done} posts")
