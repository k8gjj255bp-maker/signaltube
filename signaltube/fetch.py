"""Fetch latest uploads from each channel's public YouTube RSS feed."""
from datetime import datetime, timezone, timedelta
import json, re, time, random, urllib.request, xml.etree.ElementTree as ET, concurrent.futures as cf
NS = {"a": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015",
      "media": "http://search.yahoo.com/mrss/"}
FEED = "https://www.youtube.com/feeds/videos.xml?channel_id={}"
# Channels whose content is not AI-only: keep only videos that mention AI.
GENERAL = {"@60minutes","@CNBC","@TED","@TheVerge","@WIRED","@LinusTechTips","@mkbhd","@veritasium",
  "@kurzgesagt","@Numberphile","@BigThink","@harvard","@MIT","@StanfordGSB","@Microsoft","@SabineHossenfelder",
  "@TechAltar","@LowLevelTV","@NeetCode","@CS50","@CodeBullet","@NetworkChuck","@3blue1brown","@mitocw",
  "@stanfordonline","@ycombinator","@a16z","@ThePrimeTimeagen","@t3dotgg","@ColdFusion","@KevinStratvert",
  "@JeffSu","@AWSEventsChannel","@googlecloudtech","@GoogleDevelopers","@IBMTechnology","@NVIDIA",
  "@freecodecamp","@ArjanCodes","@TechWithTim","@ByteByteGo","@ByteMonk","@IPAMUCLA","@SimonsInstitute",
  "@mathemaniac","@ritvikmath","@statquest","@Fireship","@lexfridman","@PeterDiamandis","@DwarkeshPatel","@AnastasiInTech"}
AI_WORDS = ("ai","a.i.","gpt","llm","machine learning","neural","deep learning","openai","anthropic","claude",
  "gemini","agent","transformer","model","chatbot","diffusion","agi","copilot","deepmind","llama","nvidia","robot")

def _fetch(ch):
    try:
        req = urllib.request.Request(FEED.format(ch["channel_id"]), headers={"User-Agent": "SignalTube/0.1"})
        root = ET.fromstring(urllib.request.urlopen(req, timeout=20).read())
    except Exception as e:
        try:  # RSS has 404'd for all channels since ~2026-10-24: scrape the /videos page instead
            return ch, [v for v in _scrape(ch) if _keep(ch, v)], None
        except Exception as e2:
            return ch, [], f"rss: {e}; page: {e2}"
    vids = []
    for e in root.findall("a:entry", NS):
        g = e.find("media:group", NS)
        stats = g.find("media:community/media:statistics", NS) if g is not None else None
        rating = g.find("media:community/media:starRating", NS) if g is not None else None
        v = {
            "id": e.findtext("yt:videoId", namespaces=NS),
            "title": e.findtext("a:title", namespaces=NS) or "",
            "published": e.findtext("a:published", namespaces=NS),
            "description": (g.findtext("media:description", namespaces=NS) if g is not None else "") or "",
            "thumbnail": f"https://i.ytimg.com/vi/{e.findtext('yt:videoId', namespaces=NS)}/mqdefault.jpg",
            "views": int(stats.get("views", 0)) if stats is not None else None,
            "stars": float(rating.get("average", 0)) if rating is not None else None,
            "star_count": int(rating.get("count", 0)) if rating is not None else None,
            "channel_id": ch["channel_id"], "channel": ch["name"], "handle": ch["handle"], "tier": ch["tier"],
        }
        v["url"] = f"https://www.youtube.com/watch?v={v['id']}"
        if _keep(ch, v): vids.append(v)
    return ch, vids, None

def _keep(ch, v):
    if ch["handle"] not in GENERAL: return True
    txt = f" {v['title']} {v['description'][:500]} ".lower()
    return any(f" {w} " in txt or f" {w}s " in txt or f"{w}-" in txt or f" {w}," in txt or f" {w}." in txt or f" {w}:" in txt for w in AI_WORDS)

# ---- Fallback: parse ytInitialData from https://www.youtube.com/channel/<id>/videos ----
PAGE = "https://www.youtube.com/channel/{}/videos?hl=en&gl=US"
WATCH = "https://www.youtube.com/watch?v={}&hl=en&gl=US"
HDRS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9", "Cookie": "CONSENT=YES+cb; SOCS=CAI"}  # skip EU consent interstitial
UNITS = {"second": 1, "minute": 60, "hour": 3600, "day": 86400, "week": 7 * 86400, "month": 30 * 86400, "year": 365 * 86400}
DESC_MAX_AGE_H = 72   # fetch full description (watch page) only for fresh videos

def _get(url):
    req = urllib.request.Request(url, headers=HDRS)
    html = urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "replace")
    if "consent.youtube.com" in html[:5000] or "before you continue" in html[:20000].lower():
        raise RuntimeError("consent page")
    return html

def _json_var(html, name):
    m = re.search(name + r"\s*=\s*", html)
    if not m: raise RuntimeError(f"{name} not found")
    return json.JSONDecoder().raw_decode(html, m.end())[0]

def _walk(o, key):
    if isinstance(o, dict):
        if key in o: yield o[key]
        for x in o.values(): yield from _walk(x, key)
    elif isinstance(o, list):
        for x in o: yield from _walk(x, key)

def _ago(text, now):
    m = re.search(r"(\d+)\s*(second|minute|hour|day|week|month|year)", text or "")
    if not m: return None
    return (now - timedelta(seconds=int(m.group(1)) * UNITS[m.group(2)])).isoformat(timespec="seconds")

def _views(text):
    m = re.search(r"([\d.,]+)\s*(thousand|million|billion|K|M|B)?", (text or "").replace(",", ""), re.I)
    if not m or "view" not in (text or "").lower(): return None
    mult = {"k": 1e3, "thousand": 1e3, "m": 1e6, "million": 1e6, "b": 1e9, "billion": 1e9}.get((m.group(2) or "").lower(), 1)
    return int(float(m.group(1)) * mult)

def _txt(o):
    if not o: return ""
    return o.get("simpleText") or "".join(r.get("text", "") for r in o.get("runs", []))

def _scrape(ch, now=None):
    now = now or datetime.now(timezone.utc)
    data = _json_var(_get(PAGE.format(ch["channel_id"])), "ytInitialData")
    raw = []
    for r in _walk(data, "videoRenderer"):   # older layout
        raw.append((r.get("videoId"), _txt(r.get("title")), _txt(r.get("publishedTimeText")),
                    _txt(r.get("viewCountText")), _txt(r.get("descriptionSnippet"))))
    for l in _walk(data, "lockupViewModel"):  # 2026 layout
        if l.get("contentType", "LOCKUP_CONTENT_TYPE_VIDEO") != "LOCKUP_CONTENT_TYPE_VIDEO": continue
        md = l.get("metadata", {}).get("lockupMetadataViewModel", {})
        parts = [p.get("accessibilityLabel") or p.get("text", {}).get("content", "")
                 for row in md.get("metadata", {}).get("contentMetadataViewModel", {}).get("metadataRows", [])
                 for p in row.get("metadataParts", [])]
        raw.append((l.get("contentId"), md.get("title", {}).get("content", ""),
                    next((p for p in parts if "ago" in p), ""), next((p for p in parts if "view" in p.lower()), ""), ""))
    vids, seen = [], set()
    for vid, title, ago, views, desc in raw:
        pub = _ago(ago, now)
        if not vid or vid in seen or not pub: continue   # skips live/upcoming without a date
        seen.add(vid)
        if now - datetime.fromisoformat(pub) <= timedelta(hours=DESC_MAX_AGE_H):
            try:
                time.sleep(0.5)
                desc = _json_var(_get(WATCH.format(vid)), "ytInitialPlayerResponse")["videoDetails"].get("shortDescription") or desc
            except Exception:
                pass
        vids.append({"id": vid, "title": title, "published": pub, "description": desc or "",
                     "thumbnail": f"https://i.ytimg.com/vi/{vid}/mqdefault.jpg", "views": _views(views),
                     "stars": None, "star_count": None, "channel_id": ch["channel_id"], "channel": ch["name"],
                     "handle": ch["handle"], "tier": ch["tier"], "url": f"https://www.youtube.com/watch?v={vid}",
                     "source": "page", "published_approx": True})
    return vids

def _fetch_polite(ch):
    time.sleep(random.uniform(0.5, 1.5))  # spread requests out
    return _fetch(ch)

def fetch_all(channels, workers=4):
    out, errors = [], []
    with cf.ThreadPoolExecutor(workers) as ex:
        for ch, vids, err in ex.map(_fetch_polite, channels):
            out += vids
            if err: errors.append((ch["handle"], err))
    return out, errors
