"""Quarto post-render step: add a "Listen" player to posts that have narration.

Audio is made by scripts/narrate.py into audio/<post-folder>.mp3 and copied to
the site as a project resource. Posts without audio are left untouched.
"""
import json, os, re

OUT = "_site"
MARK = "<!-- audio_player -->"
NAMES = {"ava": "Ava", "aria": "Aria", "emma": "Emma"}
manifest_path = os.path.join("audio", "manifest.json")
manifest = json.load(open(manifest_path)) if os.path.exists(manifest_path) else {}

SCRIPT = """<script>
document.querySelectorAll(".listen").forEach(function (box) {
  var audio = box.querySelector("audio"), play = box.querySelector(".listen-play"),
      bar = box.querySelector(".listen-bar"), time = box.querySelector(".listen-time"),
      speed = box.querySelector(".listen-speed"), rates = [1, 1.25, 1.5, 0.9], r = 0;
  function fmt(s) { s = Math.max(0, Math.floor(s || 0)); return Math.floor(s / 60) + ":" + String(s % 60).padStart(2, "0"); }
  play.addEventListener("click", function () { audio.paused ? audio.play() : audio.pause(); });
  audio.addEventListener("play", function () { box.classList.add("playing"); play.setAttribute("aria-label", "Pause"); });
  audio.addEventListener("pause", function () { box.classList.remove("playing"); play.setAttribute("aria-label", "Play"); });
  audio.addEventListener("timeupdate", function () {
    if (audio.duration) bar.value = (audio.currentTime / audio.duration) * 1000;
    time.textContent = fmt(audio.currentTime) + " / " + fmt(audio.duration || box.dataset.seconds);
  });
  bar.addEventListener("input", function () { if (audio.duration) audio.currentTime = (bar.value / 1000) * audio.duration; });
  speed.addEventListener("click", function () { r = (r + 1) % rates.length; audio.playbackRate = rates[r]; speed.textContent = rates[r] + "×"; });
  if (location.hash === "#listen") {           // arrived from a "Listen" badge
    box.classList.add("listen-arrived");
    box.scrollIntoView({ block: "center" });
    audio.play().catch(function () {});          // browsers may block autoplay; the button still works
  }
});
</script>"""


def player(slug, info):
    mins = max(1, round(info["seconds"] / 60))
    voice = NAMES.get(info["voice"], info["voice"].title())
    return f"""{MARK}
<div class="listen" id="listen" data-seconds="{info['seconds']}">
  <button class="listen-play" type="button" aria-label="Play"><span class="i-play">▶</span><span class="i-pause">❚❚</span></button>
  <div class="listen-body">
    <div class="listen-head"><strong>Listen to this post</strong><span>{mins} min · AI narration by {voice}</span></div>
    <input class="listen-bar" type="range" min="0" max="1000" value="0" aria-label="Seek">
  </div>
  <span class="listen-time">0:00 / {info['seconds'] // 60}:{info['seconds'] % 60:02d}</span>
  <button class="listen-speed" type="button" aria-label="Playback speed">1×</button>
  <audio preload="none" src="../../audio/{slug}.mp3"></audio>
</div>
"""


# Listing pages (home, series, archive): a small script marks cards of narrated posts.
BADGES = """<script>
(function () {
  var audio = %s;
  function mark() { document.querySelectorAll(".list a[href], .quarto-listing a[href]").forEach(function (a) {
    var m = a.getAttribute("href").match(/posts\\/([^\\/]+)\\//);
    if (!m || !audio[m[1]]) return;
    var card = a.closest(".quarto-post, article, .essay-card, .episode") || a;
    if (card.querySelector(".listen-badge")) return;
    var badge = document.createElement("a");
    badge.className = "listen-badge";
    badge.href = a.getAttribute("href").replace(/index\\.html$/, "") + "#listen";
    badge.textContent = "▶ Listen · " + audio[m[1]] + " min";
    badge.title = "AI narration";
    badge.addEventListener("click", function (e) { e.stopPropagation(); });
    var meta = card.querySelector(".meta, .listing-reading-time, .listing-date");
    if (card.tagName === "A") {                    // cards that are links themselves can't hold another link
      var span = document.createElement("span");
      span.className = "listen-badge";
      span.textContent = badge.textContent;
      (meta || card).appendChild(span);
    } else {
      (meta ? meta.parentNode : card).insertBefore(badge, meta ? meta.nextSibling : null);
    }
  }); }
  mark();
  // Paging, sorting and filtering in listings redraw the cards; mark the new ones too.
  var t; new MutationObserver(function () { clearTimeout(t); t = setTimeout(mark, 50); })
    .observe(document.body, { childList: true, subtree: true });
})();
</script>"""

done = 0
for slug, info in manifest.items():
    page_path = os.path.join(OUT, "posts", slug, "index.html")
    if not (os.path.exists(page_path) and os.path.exists(os.path.join(OUT, "audio", f"{slug}.mp3"))):
        continue
    page = open(page_path, encoding="utf-8").read()
    if MARK in page:
        continue
    start = page.find('<header id="title-block-header"')
    end = page.find("</header>", start) if start >= 0 else -1
    if end < 0:
        continue
    end += len("</header>")
    page = page[:end] + "\n" + player(slug, info) + page[end:]
    page = page.replace("</body>", SCRIPT + "\n</body>", 1)
    open(page_path, "w", encoding="utf-8").write(page)
    done += 1
minutes = {slug: max(1, round(info["seconds"] / 60)) for slug, info in manifest.items()
           if os.path.exists(os.path.join(OUT, "audio", f"{slug}.mp3"))}
marked = 0
if minutes:
    for page_path in ["index.html", "archive.html"] + [os.path.join("series", f) for f in os.listdir(os.path.join(OUT, "series"))]:
        page_path = os.path.join(OUT, page_path)
        if not page_path.endswith(".html") or not os.path.exists(page_path):
            continue
        page = open(page_path, encoding="utf-8").read()
        if "listen-badge" in page:
            continue
        page = page.replace("</body>", BADGES % json.dumps(minutes) + "\n</body>", 1)
        open(page_path, "w", encoding="utf-8").write(page)
        marked += 1
print(f"audio_player.py: added players to {done} posts, listen badges on {marked} listing pages")
