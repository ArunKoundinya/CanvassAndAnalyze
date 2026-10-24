"""Narrate posts as MP3 audio with Microsoft's neural voices (via edge-tts).

    python3 scripts/narrate.py                    # every post (skips unchanged ones)
    python3 scripts/narrate.py image-and-person   # just these post folders
    python3 scripts/narrate.py --dry-run SLUG     # print the narration text, no audio
    python3 scripts/narrate.py --jobs=6           # record up to 6 posts at once (default 4)

Audio goes to audio/<post-folder>.mp3 (kept out of git, published with the
site). A post is re-recorded only when its text or voice changes.

Voices (one per kind of writing; a series always keeps one voice):
  ava   - storyteller: the novel, Indian Culture, stories and personal pieces
  aria  - analyst: Thinking in Systems, COVID-19, analytics, economics, society
  emma  - companion: everyday reflections on the mind and habits
Override for a single post with `voice: ava|aria|emma` in its front matter.

edge-tts is installed locally:  pip install --target .tts-lib edge-tts
"""
import asyncio, glob, hashlib, json, os, re, sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".tts-lib"))
import edge_tts  # noqa: E402

AUDIO = "audio"
MANIFEST = os.path.join(AUDIO, "manifest.json")
AUTHOR = "Arun Koundinya Parasa"

VOICES = {
    "ava": ("en-US-AvaMultilingualNeural", "-5%"),
    "aria": ("en-US-AriaNeural", "-5%"),
    "emma": ("en-US-EmmaMultilingualNeural", "-5%"),
}
SERIES_VOICE = {"novel": "ava", "spirituality": "ava", "systems": "aria", "covid19": "aria"}
STORY = {"story", "love", "trust", "betrayal", "festive"}
ANALYTIC = {"AI", "analytics", "data science", "systems thinking", "business", "strategy",
            "economics", "poverty", "COVID-19", "crime", "crimes against women", "suicides",
            "self-harm", "mental health", "consumer behaviour", "game theory", "management",
            "leadership", "career", "analytical"}
SERIES_TITLE = {"novel": "Threads of One Life"}

# Paragraphs that are notes to readers of the web page, not part of the piece.
SKIP_PARA = re.compile(r"^(Rewritten and update|Source:|Sources?:|Link:|Click here)", re.I)
STOP_HEADING = re.compile(r"^#+\s*.*\b(references|sources|bibliography|further reading|works cited|notes)\s*$", re.I)


def front_matter(text):
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
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
    return fm, text[m.end():] if m else text


def pick_voice(fm):
    if fm.get("voice") in VOICES:
        return fm["voice"]
    if fm.get("series") in SERIES_VOICE:
        return SERIES_VOICE[fm["series"]]
    cats = set(fm.get("categories") or [])
    if cats & STORY:
        return "ava"
    if cats & ANALYTIC:
        return "aria"
    return "emma"


def spoken_title(title):
    m = re.search(r"(LOVE & TRUST|TRUST & BETRAYAL).*?Season\s*-?\s*(\d+).*?Episode\s*-?\s*(\d+)", title, re.I)
    if m:
        story = "Love and Trust" if m.group(1).upper().startswith("LOVE") else "Trust and Betrayal"
        return f"{story}. Season {m.group(2)}, Episode {m.group(3)}."
    t = title.replace("|", ".").replace("&", "and")
    if t.isupper():  # ALL-CAPS titles read better in title case
        t = t.title()
    return t.rstrip(".") + "."


def inline(t):
    t = re.sub(r"\S*\\\*\S*", "…", t)                              # censored words like \*ss\*\*le -> pause
    t = re.sub(r"!\[[^\]]*\]\([^)]*\)(\{[^}]*\})?", "", t)        # images
    t = re.sub(r"\[\^[^\]]*\]", "", t)                             # footnote refs
    t = re.sub(r"\[([^\]]*)\]\([^)]*\)(\{[^}]*\})?", r"\1", t)     # links -> text
    t = re.sub(r"\[([^\]]*)\]\{[^}]*\}", r"\1", t)                 # spans
    t = re.sub(r"\{[.#][^}]*\}", "", t)                            # attributes
    t = re.sub(r"<[^>]+>", "", t)                                  # html
    t = re.sub(r"https?://\S+", "", t)                             # bare urls
    t = re.sub(r"[*_`~]+", "", t)                                  # emphasis / code marks
    t = re.sub(r"\{\s*([^{}]*?)\s*\}", r", \1,", t)                   # { aside } -> , aside ,
    t = re.sub(r"\b([A-Z][a-z]+(?:[A-Z][a-z]+){2,})\b",                 # HashTagWords -> Hash Tag Words
               lambda m: re.sub(r"(?<=[a-z])(?=[A-Z])", " ", m.group(1)), t)
    t = re.sub(r"\s=\s", " means ", t)
    t = re.sub(r"-{3,}", " ", t).replace("\\", " ")
    t = t.replace("&", " and ").replace("|", ",")
    t = re.sub(r"\s+", " ", t).strip()
    t = re.sub(r"\s*,\s*([.!?:;])", r"\1", t)                           # "word,." -> "word."
    t = re.sub(r"([.!?:;])\s*,\s*", r"\1 ", t)                          # ". , Who" -> ". Who"
    return re.sub(r"(^,\s*|\s*,$)", "", t)


def narration(path):
    fm, body = front_matter(open(path, encoding="utf-8").read())
    body = re.sub(r"```.*?```", "", body, flags=re.S)                # code and raw html blocks
    paras, buf = [], []

    def flush():
        if buf:
            p = inline(" ".join(buf))
            if p and not SKIP_PARA.match(p) and re.search(r"[A-Za-z]", p):
                paras.append(p if p[-1] in ".!?:;\"'”’)" else p + ".")
            buf.clear()

    for raw in body.splitlines():
        line = raw.strip()
        if STOP_HEADING.match(line):
            break
        if not line or re.fullmatch(r"(:::.*|[-*_ ]{3,})", line) or line.startswith("|"):
            flush()
            continue
        if line.startswith("<") or line.startswith("!["):
            continue
        if line.startswith("#"):
            flush()
            buf.append(line.lstrip("#").strip())
            flush()
            continue
        line = re.sub(r"^>\s?", "", line)
        if re.match(r"^([-*+]|\d+\.)\s+", line):                     # list items: one sentence each
            flush()
            buf.append(re.sub(r"^([-*+]|\d+\.)\s+", "", line))
            flush()
            continue
        if line.endswith("\\"):                                     # hard line break ends the sentence
            buf.append(line[:-1])
            flush()
            continue
        buf.append(line)
    flush()

    intro = [spoken_title(fm.get("title", ""))]
    if fm.get("subtitle"):
        intro.append(inline(fm["subtitle"]).rstrip(".") + ".")
    if fm.get("series") in SERIES_TITLE:
        intro.append(f"From {SERIES_TITLE[fm['series']]}, by {AUTHOR}.")
    else:
        intro.append(f"By {AUTHOR}.")
    heard = spoken_title(fm.get("title", "")).rstrip(".").replace(". Season", ", Season")
    outro = f"You have been listening to {heard}, on Canvass And Analyze."
    return fm, "\n\n".join(intro + paras + [outro])


async def record(text, voice, out):
    name, rate = VOICES[voice]
    tmp = out + ".part"
    await edge_tts.Communicate(text, name, rate=rate).save(tmp)
    os.replace(tmp, out)


def main(argv):
    dry = "--dry-run" in argv
    jobs = int(next((a.split("=")[1] for a in argv if a.startswith("--jobs=")), "4"))
    slugs = [a for a in argv if not a.startswith("--")]
    os.makedirs(AUDIO, exist_ok=True)
    manifest = json.load(open(MANIFEST)) if os.path.exists(MANIFEST) else {}
    paths = [f"posts/{s}/index.qmd" for s in slugs] if slugs else sorted(glob.glob("posts/*/index.qmd"))

    todo = []
    for path in paths:
        slug = path.split("/")[1]
        fm, text = narration(path)
        voice = pick_voice(fm)
        if dry:
            print(f"--- {slug} · voice: {voice} · {len(text.split())} words ---\n{text}\n")
            continue
        digest = hashlib.sha256(f"{voice}|{VOICES[voice]}|{text}".encode()).hexdigest()[:16]
        out = os.path.join(AUDIO, f"{slug}.mp3")
        if manifest.get(slug, {}).get("hash") != digest or not os.path.exists(out):
            todo.append((slug, voice, text, digest, out))
    if dry:
        return

    async def run_all():
        gate = asyncio.Semaphore(jobs)

        async def one(slug, voice, text, digest, out):
            async with gate:
                print(f"narrating {slug} ({voice}, {len(text.split())} words)...", flush=True)
                for attempt in range(3):                              # the service drops the odd connection
                    try:
                        await record(text, voice, out)
                        break
                    except Exception as e:
                        print(f"  retry {slug}: {e}", flush=True)
                        await asyncio.sleep(10 * (attempt + 1))
                else:
                    print(f"  FAILED {slug}", flush=True)
                    return
                size = os.path.getsize(out)
                manifest[slug] = {"voice": voice, "hash": digest, "bytes": size,
                                  "seconds": round(size * 8 / 48000)}  # edge-tts writes 48 kbps CBR
                json.dump(manifest, open(MANIFEST, "w"), indent=1, sort_keys=True)
                open(os.path.join(AUDIO, f"{slug}.txt"), "w", encoding="utf-8").write(text)
                print(f"  done {slug} ({size // 1024} KB)", flush=True)

        await asyncio.gather(*(one(*t) for t in todo))

    asyncio.run(run_all())
    print(f"narrate.py: {len(manifest)} posts have audio")


if __name__ == "__main__":
    main(sys.argv[1:])
