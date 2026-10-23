#!/usr/bin/env python3
"""SignalTube pipeline: fetch -> score -> merge history -> build site + newsletter."""
import json, os, sys
from datetime import datetime, timezone, timedelta
from signaltube.fetch import fetch_all
from signaltube.score import score
from signaltube.build import build, newsletter
D = os.path.dirname(os.path.abspath(__file__))
def main():
    now = datetime.now(timezone.utc)
    chans = json.load(open(f"{D}/channels.json"))
    vids, errs = fetch_all(chans)
    hist_path = f"{D}/data/videos.json"
    hist = {v["id"]: v for v in json.load(open(hist_path))} if os.path.exists(hist_path) else {}
    for v in vids:
        hist[v["id"]] = score(v)          # refresh stats + score
    keep = [v for v in hist.values() if now - datetime.fromisoformat(v["published"]) <= timedelta(days=60)]
    os.makedirs(f"{D}/data", exist_ok=True); json.dump(keep, open(hist_path, "w"))
    top, week, today = build(keep, chans, f"{D}/site", now)
    stem = newsletter(week, f"{D}/newsletter", now)
    print(f"channels={len(chans)} fetched={len(vids)} errors={len(errs)} stored={len(keep)} today={len(today)} week={len(week)}")
    for e in errs: print("ERR", *e, file=sys.stderr)
    for i, v in enumerate(top[:3], 1): print(f"#{i} [{v['score']}] {v['channel']}: {v['title']}")
    print("newsletter:", stem)
if __name__ == "__main__": main()
