"""Email subscribers about new posts. Run after publishing:

    python3 scripts/notify.py              # announce posts not announced before
    python3 scripts/notify.py --dry-run    # show what would be sent, send nothing
    python3 scripts/notify.py --test you@example.com [post-folder]   # one sample email, records nothing

The first run only records every existing post as announced (no emails).
Announced posts are tracked in subscribe/announced.json (commit it).

Settings and secrets live outside the repo in ~/.config/canvass-and-analyze/notify.env
(created by scripts/setup_subscribe_secrets.sh):
    WORKER_URL, ADMIN_TOKEN, GMAIL_ADDRESS, GMAIL_APP_PASSWORD
"""
import email.utils, glob, json, os, smtplib, ssl, sys, time, urllib.request
from email.message import EmailMessage

sys.path.insert(0, os.path.dirname(__file__))
from email_templates import BRAND, SITE, new_post, post_info  # noqa: E402

STATE = "subscribe/announced.json"
ENV = os.path.expanduser("~/.config/canvass-and-analyze/notify.env")


def settings():
    cfg = {}
    if os.path.exists(ENV):
        for line in open(ENV):
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.strip().split("=", 1)
                cfg[k.strip()] = v.strip().strip("'\"")
    missing = [k for k in ("WORKER_URL", "ADMIN_TOKEN", "GMAIL_ADDRESS", "GMAIL_APP_PASSWORD") if not cfg.get(k)]
    if missing:
        sys.exit(f"notify.py: missing {', '.join(missing)} in {ENV}. Run scripts/setup_subscribe_secrets.sh first.")
    cfg["WORKER_URL"] = cfg["WORKER_URL"].rstrip("/")
    return cfg


def all_posts():
    return sorted(p.split("/")[1] for p in glob.glob("posts/*/index.qmd"))


def subscribers(cfg):
    req = urllib.request.Request(cfg["WORKER_URL"] + "/admin/subscribers",
                                 headers={"Authorization": "Bearer " + cfg["ADMIN_TOKEN"], "User-Agent": "notify.py"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)["subscribers"]


def wait_until_live(url, minutes=5):
    for _ in range(minutes * 6):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, method="HEAD"), timeout=15) as r:
                if r.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(10)
    return False


def message(cfg, post, to, token):
    unsub_page = f"{SITE}unsubscribe.html?token={token}"
    one_click = f"{cfg['WORKER_URL']}/unsubscribe?token={token}"
    subject, html, text = new_post(post, unsub_page)
    m = EmailMessage()
    m["From"] = email.utils.formataddr((BRAND["from_name"], cfg["GMAIL_ADDRESS"]))
    m["To"] = to
    m["Subject"] = subject
    m["Date"] = email.utils.formatdate(localtime=True)
    m["Message-ID"] = email.utils.make_msgid(domain="canvassandanalyze")
    m["List-Unsubscribe"] = f"<{one_click}>"
    m["List-Unsubscribe-Post"] = "List-Unsubscribe=One-Click"
    m.set_content(text)
    m.add_alternative(html, subtype="html")
    return m


def main(argv):
    dry = "--dry-run" in argv
    os.makedirs(os.path.dirname(STATE), exist_ok=True)

    if "--test" in argv:
        i = argv.index("--test")
        to = argv[i + 1]
        slug = argv[i + 2] if len(argv) > i + 2 and not argv[i + 2].startswith("--") else max(
            all_posts(), key=lambda s: post_info(s).get("date_iso", ""))
        cfg = settings()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ssl.create_default_context()) as smtp:
            smtp.login(cfg["GMAIL_ADDRESS"], cfg["GMAIL_APP_PASSWORD"])
            smtp.send_message(message(cfg, post_info(slug), to, "TEST-TOKEN"))
        print(f"notify.py: sent a test email about '{slug}' to {to}")
        return

    if not os.path.exists(STATE):
        json.dump({"announced": all_posts()}, open(STATE, "w"), indent=1)
        print(f"notify.py: first run. Recorded {len(all_posts())} existing posts as announced; no emails sent.")
        return

    announced = set(json.load(open(STATE))["announced"])
    new = [s for s in all_posts() if s not in announced]
    if not new:
        print("notify.py: no new posts to announce.")
        return
    posts = sorted((post_info(s) for s in new), key=lambda p: p.get("date_iso", ""))
    cfg = settings()
    subs = subscribers(cfg)
    print(f"notify.py: {len(posts)} new post(s), {len(subs)} subscriber(s).")
    if dry:
        for p in posts:
            print(f"  would send: {new_post(p, '')[0]}")
        return

    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ssl.create_default_context()) as smtp:
        smtp.login(cfg["GMAIL_ADDRESS"], cfg["GMAIL_APP_PASSWORD"])
        for p in posts:
            if not wait_until_live(p["url"]):
                print(f"  skipped {p['slug']}: not live yet at {p['url']} (will retry next run)")
                continue
            sent = failed = 0
            for s in subs:
                try:
                    smtp.send_message(message(cfg, p, s["email"], s["token"]))
                    sent += 1
                except smtplib.SMTPRecipientsRefused:
                    failed += 1
                time.sleep(1)                                    # stay well inside Gmail's rate limits
            announced.add(p["slug"])
            json.dump({"announced": sorted(announced)}, open(STATE, "w"), indent=1)
            print(f"  announced {p['slug']}: sent {sent}" + (f", {failed} refused" if failed else ""))


if __name__ == "__main__":
    main(sys.argv[1:])
