"""Quarto post-render step: add a "Listen" player to posts that have narration.

Audio is made by scripts/narrate.py into audio/<post-folder>.mp3 and copied to
the site as a project resource. Posts without audio are left untouched.
"""
import html, json, os, re

OUT = "_site"
MARK = "<!-- audio_player -->"
NAMES = {"ava": "Ava", "aria": "Aria", "emma": "Emma"}
manifest_path = os.path.join("audio", "manifest.json")
manifest = json.load(open(manifest_path)) if os.path.exists(manifest_path) else {}

SCRIPT = """<script>
document.querySelectorAll(".listen").forEach(function (box) {
  var audio = box.querySelector("audio"), play = box.querySelector(".listen-play"),
      bar = box.querySelector(".listen-bar"), time = box.querySelector(".listen-time"),
      speed = box.querySelector(".listen-speed"), art = box.querySelector(".listen-art"),
      title = box.dataset.title, rates = [1, 1.25, 1.5, 2, 0.8], r = 0,
      key = "listen:" + box.dataset.slug, dismissed = false, onScreen = true;
  function fmt(s) { s = Math.max(0, Math.floor(s || 0)); return Math.floor(s / 60) + ":" + String(s % 60).padStart(2, "0"); }
  function dur() { return audio.duration || +box.dataset.seconds; }
  function store(v) { try { v ? localStorage.setItem(key, v) : localStorage.removeItem(key); } catch (e) {} }
  function toggle() { audio.paused ? audio.play() : audio.pause(); }

  // Mini player docked at the bottom while the post plays and the main player has scrolled away.
  var mini = document.createElement("div");
  mini.className = "listen-mini";
  mini.innerHTML = '<div class="listen-mini-progress"><span></span></div>' +
    '<button class="listen-play" type="button" aria-label="Play"><span class="i-play">▶</span><span class="i-pause">❚❚</span></button>' +
    '<button class="listen-mini-info" type="button" aria-label="Go to the player"><span class="listen-mini-title"></span><span class="listen-mini-time"></span></button>' +
    '<button class="listen-mini-close" type="button" aria-label="Stop and close">✕</button>';
  mini.querySelector(".listen-mini-title").textContent = title;
  document.body.appendChild(mini);
  var miniPlay = mini.querySelector(".listen-play"), miniBar = mini.querySelector(".listen-mini-progress span"),
      miniTime = mini.querySelector(".listen-mini-time");
  function showMini() { mini.classList.toggle("show", box.classList.contains("started") && !onScreen && !dismissed); }
  if ("IntersectionObserver" in window)
    new IntersectionObserver(function (e) { onScreen = e[0].isIntersecting; showMini(); }).observe(box);
  miniPlay.addEventListener("click", toggle);
  mini.querySelector(".listen-mini-info").addEventListener("click", function () { box.scrollIntoView({ behavior: "smooth", block: "center" }); });
  mini.querySelector(".listen-mini-close").addEventListener("click", function () { audio.pause(); dismissed = true; showMini(); });

  function paint() {
    var d = dur(), t = audio.currentTime, p = d ? t / d : 0;
    bar.value = p * 1000;
    bar.style.setProperty("--p", (p * 100) + "%");
    miniBar.style.width = (p * 100) + "%";
    time.textContent = miniTime.textContent = fmt(t) + " / " + fmt(d);
  }

  // Pick up where the reader left off last time.
  var saved = 0;
  try { saved = +localStorage.getItem(key) || 0; } catch (e) {}
  if (saved > 5 && saved < +box.dataset.seconds - 5) { audio.currentTime = saved; paint(); }

  play.addEventListener("click", toggle);
  audio.addEventListener("play", function () {
    box.classList.add("playing", "started"); mini.classList.add("playing"); dismissed = false; showMini();
    play.setAttribute("aria-label", "Pause"); miniPlay.setAttribute("aria-label", "Pause");
  });
  audio.addEventListener("pause", function () {
    box.classList.remove("playing"); mini.classList.remove("playing");
    play.setAttribute("aria-label", "Play"); miniPlay.setAttribute("aria-label", "Play");
    store(audio.currentTime > 5 && !audio.ended ? Math.floor(audio.currentTime) : 0);
  });
  audio.addEventListener("ended", function () { store(0); });
  var last = 0;
  audio.addEventListener("timeupdate", function () {
    paint();
    if (Math.abs(audio.currentTime - last) > 5) { last = audio.currentTime; store(Math.floor(last)); }
  });
  audio.addEventListener("loadedmetadata", paint);
  bar.addEventListener("input", function () { audio.currentTime = (bar.value / 1000) * dur(); paint(); });
  box.querySelectorAll(".listen-skip").forEach(function (b) {
    b.addEventListener("click", function () { audio.currentTime = Math.min(dur(), Math.max(0, audio.currentTime + +b.dataset.skip)); paint(); });
  });
  speed.addEventListener("click", function () { r = (r + 1) % rates.length; audio.playbackRate = rates[r]; speed.textContent = rates[r] + "×"; });

  // Lock-screen / headphone controls on phones.
  if ("mediaSession" in navigator) {
    audio.addEventListener("play", function () {
      navigator.mediaSession.metadata = new MediaMetadata({ title: title, artist: "Arun Koundinya Parasa",
        album: "Canvass And Analyze", artwork: art ? [{ src: art.src }] : [] });
    });
    navigator.mediaSession.setActionHandler("play", function () { audio.play(); });
    navigator.mediaSession.setActionHandler("pause", function () { audio.pause(); });
    navigator.mediaSession.setActionHandler("seekbackward", function () { audio.currentTime = Math.max(0, audio.currentTime - 15); });
    navigator.mediaSession.setActionHandler("seekforward", function () { audio.currentTime = Math.min(dur(), audio.currentTime + 30); });
  }

  if (location.hash === "#listen") {           // arrived from a "Listen" badge
    box.classList.add("listen-arrived");
    box.scrollIntoView({ block: "center" });
    audio.play().catch(function () {});          // browsers may block autoplay; the button still works
  }
});
</script>"""


def player(slug, info, title, image):
    mins = max(1, round(info["seconds"] / 60))
    voice = NAMES.get(info["voice"], info["voice"].title())
    secs = info["seconds"]
    art = f'<img class="listen-art" src="{image}" alt="" loading="lazy">\n  ' if image else ""
    return f"""{MARK}
<div class="listen" id="listen" data-seconds="{secs}" data-slug="{slug}" data-title="{html.escape(title)}">
  {art}<button class="listen-play" type="button" aria-label="Play"><span class="i-play">▶</span><span class="i-pause">❚❚</span></button>
  <div class="listen-body">
    <div class="listen-head"><strong>Listen to this post</strong><span>{mins} min · AI narration by {voice}</span></div>
    <input class="listen-bar" type="range" min="0" max="1000" value="0" aria-label="Seek">
  </div>
  <button class="listen-skip" type="button" data-skip="-15" aria-label="Back 15 seconds"><i class="bi bi-arrow-counterclockwise"></i><span>15</span></button>
  <button class="listen-skip" type="button" data-skip="30" aria-label="Forward 30 seconds"><i class="bi bi-arrow-clockwise"></i><span>30</span></button>
  <span class="listen-time">0:00 / {secs // 60}:{secs % 60:02d}</span>
  <button class="listen-speed" type="button" aria-label="Playback speed">1×</button>
  <audio preload="none" src="../../audio/{slug}.mp3"></audio>
</div>
"""


def page_title_and_image(page):
    """The post's title and its sharing image (made relative so it also works locally)."""
    m = re.search(r'<h1 class="title">(.*?)</h1>', page, re.S)
    title = html.unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip() if m else ""
    m = re.search(r'<meta property="og:image" content="([^"]+)"', page)
    image = m.group(1) if m else ""
    site = re.search(r'<link rel="canonical" href="(https?://[^"]*?/)posts/', page)
    if image and site and image.startswith(site.group(1)):
        image = "../../" + image[len(site.group(1)):]
    return title, image


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
    page = page[:end] + "\n" + player(slug, info, *page_title_and_image(page)) + page[end:]
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
