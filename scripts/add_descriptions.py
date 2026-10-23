"""Give every post a `description:` (used for the meta description, Google/Bing
snippets, and LinkedIn/WhatsApp previews). Posts that already have one are left
alone, so hand-written descriptions always win. Re-run after adding new posts:

    python3 scripts/add_descriptions.py
"""
import glob, re

MAX = 158
SKIP = re.compile(r"^(!\[|#|<|:::|```|>|\||-{2,}|\*{3,}|\{|\[?(Note|Disclaimer)|Rewritten|Source|Continuing|\d+\.\s)", re.I)
SKIP_ANY = re.compile(r"click here|continuation of my|we have observed where the rishi|in this series of posts", re.I)

# Hand-written descriptions for posts whose opening paragraph makes a poor snippet.
OVERRIDES = {
    "covid19-factcheck": "Facts and a reality check on COVID-19 in March 2020: what we knew and what we didn't.",
    "covid19-netizenreactions": "How netizens reacted to COVID-19, checked against the WHO myth busters. Co-authored with Dr. Mahesh Kolli.",
    "covid19-lessonsfrom-inland": "Lessons for India from the South Korean model and its use of analytics to contain COVID-19 during the lockdown.",
    "covid19-medicalscience": "How medical science can help overcome the COVID-19 pandemic: the best learnings, summarised in a consumable way.",
    "covid19-deaths-lockdowns-recission": "Deaths, lockdowns and recession: an opinion on the trade-offs India faced during COVID-19.",
    "covid19-fear-stress-suicide": "Fear, stress and suicide during the COVID-19 lockdown: my view on the news from India.",
    "covid19-when-it-ends": "COVID-19 trend and forecast for India: a personal epidemic-forecasting project on when the pandemic might end.",
    "covid19-theconclusion": "The conclusion: my summary of 100 days of reading and learning about COVID-19.",
    "covid19-revisited-with-a-strain": "COVID-19 revisited with a new strain: the second wave in India and what everyone should know.",
    "covid19-steroids-drugs-deaths": "Steroids, drugs and deaths during India's second COVID-19 wave.",
    "can-we-claim-sucess": "Can we ever claim success? A reflection on what success really means, beyond the dictionary definition.",
}

def clean(t):
    t = re.sub(r"^[*_\s]*\[[^\]]{1,40}\][*_\s]*:\s*", "", t)
    t = re.sub(r"!\[[^\]]*\]\([^)]*\)(\{[^}]*\})?", "", t)
    t = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", t)
    t = re.sub(r"\{[^}]*\}", "", t)
    t = re.sub(r"<[^>]+>", "", t)
    t = re.sub(r"[*_`]+", "", t)
    t = t.replace("{", "").replace("}", "")
    return re.sub(r"\s+", " ", t).strip()

def shorten(t):
    if len(t) <= MAX:
        return t
    cut = t[:MAX]
    end = max(cut.rfind(". "), cut.rfind("? "), cut.rfind("! "))
    if end > 90:
        return cut[: end + 1]
    return cut[: cut.rfind(" ")].rstrip(",;:—- ") + "…"

def indian_culture(folder, title):
    tail = title.split("|")[-1].strip() if "|" in title else ""
    m = re.match(r"IndianCulture(Learning|Glossary)(\d+)", folder)
    if not m or not tail:
        return None
    if m.group(1) == "Glossary":
        return (f"{tail}: from my glossary of key ideas in Indian culture and Sanātana Dharma, "
                f"written as a companion to the Extended Learnings series.")
    return (f"{tail} Part {m.group(2)} of Extended Learnings, my series on Indian culture, "
            f"the Bhagavad Gita and Sanātana Dharma.")

def episode(title):
    m = re.search(r"(LOVE & TRUST|TRUST & BETRAYAL).*?Season\s*-?\s*(\d+).*?Episode\s*-?\s*(\d+)", title, re.I)
    if not m:
        return None
    story = "Love & Trust" if m.group(1).upper().startswith("LOVE") else "Trust & Betrayal"
    return (f"{story}, Season {m.group(2)} Episode {m.group(3)}: a chapter from "
            f"Threads of One Life, a novel in progress by Arun Koundinya Parasa.")

for f in sorted(glob.glob("posts/*/index.qmd")):
    s = open(f, encoding="utf-8").read()
    m = re.match(r"---\n(.*?)\n---\n", s, re.S)
    if not m or re.search(r"^description:", m.group(1), re.M):
        continue
    fm, body = m.group(1), s[m.end():]
    title = (re.search(r'^title:\s*"?(.*?)"?\s*$', fm, re.M) or [None, ""])[1]
    sub = (re.search(r'^subtitle:\s*"?(.*?)"?\s*$', fm, re.M) or [None, ""])[1]

    folder = f.split("/")[1]
    desc = OVERRIDES.get(folder) or episode(title) or indian_culture(folder, title)
    if not desc and len(sub) >= 50:
        desc = sub
    if not desc:
        for para in re.split(r"\n\s*\n", body):
            para = para.strip()
            if not para or SKIP.match(para.lstrip("*_ ")) or SKIP.match(para) or SKIP_ANY.search(para) or para.rstrip().endswith(":"):
                continue
            text = clean(para)
            if len(text) >= 60:
                desc = shorten(text)
                if len(desc) >= 40:
                    break
                desc = None
    if not desc:
        print("no description:", f)
        continue
    desc = desc.replace("\\", "").replace('"', "'")
    s = s.replace(fm, fm + f'\ndescription: "{desc}"', 1)
    open(f, "w", encoding="utf-8").write(s)
    print(f"{f.split('/')[1][:32]:32} {desc}")
