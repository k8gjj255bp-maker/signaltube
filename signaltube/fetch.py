"""Fetch latest uploads from each channel's public YouTube RSS feed."""
import json, urllib.request, xml.etree.ElementTree as ET, concurrent.futures as cf
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
        return ch, [], str(e)
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
        if ch["handle"] in GENERAL:
            txt = f" {v['title']} {v['description'][:500]} ".lower()
            if not any(f" {w} " in txt or f" {w}s " in txt or f"{w}-" in txt or f" {w}," in txt or f" {w}." in txt or f" {w}:" in txt for w in AI_WORDS):
                continue
        vids.append(v)
    return ch, vids, None

def fetch_all(channels, workers=16):
    out, errors = [], []
    with cf.ThreadPoolExecutor(workers) as ex:
        for ch, vids, err in ex.map(_fetch, channels):
            out += vids
            if err: errors.append((ch["handle"], err))
    return out, errors
