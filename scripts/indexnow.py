"""Tell Bing (and so DuckDuckGo, Yahoo, Ecosia), Yandex, Seznam and Naver
about every page in the sitemap via IndexNow, so new posts get crawled
within hours instead of weeks. Run after publishing:

    quarto publish gh-pages && python3 scripts/indexnow.py

Google doesn't use IndexNow; it picks the sitemap up from Search Console.
"""
import glob, json, os, re, sys, urllib.request

site = re.search(r"^\s*site-url:\s*(\S+)", open("_quarto.yml").read(), re.M).group(1).rstrip("/") + "/"
keyfile = next(f for f in glob.glob("*.txt") if re.fullmatch(r"[0-9a-f]{32}\.txt", f))
key = keyfile[:-4]
sitemap = open(os.path.join("_site", "sitemap.xml"), encoding="utf-8").read()
urls = [u for u in re.findall(r"<loc>(.*?)</loc>", sitemap) if "old_index" not in u]
if not urls:
    sys.exit("No URLs found in _site/sitemap.xml - render the site first.")

body = json.dumps({
    "host": re.match(r"https?://([^/]+)", site).group(1),
    "key": key,
    "keyLocation": site + keyfile,
    "urlList": urls,
}).encode()
req = urllib.request.Request("https://api.indexnow.org/indexnow", data=body,
                             headers={"Content-Type": "application/json; charset=utf-8"})
try:
    with urllib.request.urlopen(req, timeout=30) as r:
        print(f"IndexNow: submitted {len(urls)} URLs -> HTTP {r.status}")
except urllib.error.HTTPError as e:
    # 202 = accepted, key pending verification; 4xx means something is misconfigured
    print(f"IndexNow: HTTP {e.code} {e.read().decode()[:200]}")
