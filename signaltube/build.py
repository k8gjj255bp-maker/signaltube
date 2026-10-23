"""Static site + newsletter generator (no dependencies)."""
import html, json, os, re, shutil
from datetime import datetime, timedelta, timezone
SAST = timezone(timedelta(hours=2)); E = html.escape
CSS = """*{box-sizing:border-box}body{margin:0;font:16px/1.5 system-ui,-apple-system,Segoe UI,sans-serif;background:#0d1117;color:#e6edf3}
a{color:#58a6ff;text-decoration:none}a:hover{text-decoration:underline}header{background:#161b22;border-bottom:1px solid #30363d}
.wrap{max-width:1000px;margin:0 auto;padding:0 16px}nav{display:flex;gap:18px;align-items:center;height:56px;flex-wrap:wrap}
.logo{font-weight:800;font-size:20px;color:#fff}.logo span{color:#3fb950}h1{font-size:26px;margin:28px 0 4px}.sub{color:#8b949e;margin:0 0 20px}
.card{display:flex;gap:14px;background:#161b22;border:1px solid #30363d;border-radius:10px;padding:12px;margin:10px 0}
.card img{width:196px;height:110px;object-fit:cover;border-radius:6px;flex-shrink:0}.rank{font-size:22px;font-weight:800;color:#8b949e;width:30px}
.score{font-weight:800;border-radius:8px;padding:4px 9px;font-size:18px;height:fit-content}.hi{background:#1f6f3a}.mid{background:#7a5a12}.lo{background:#7d2121}
.meta{color:#8b949e;font-size:13px}.t{font-weight:600;font-size:17px;color:#e6edf3}details{font-size:12px;color:#8b949e}
table{width:100%;border-collapse:collapse}td,th{padding:8px;border-bottom:1px solid #30363d;text-align:left}footer{color:#8b949e;font-size:13px;padding:30px 0}
.box{background:#161b22;border:1px solid #30363d;border-radius:10px;padding:18px;margin:16px 0}input{padding:10px;border-radius:6px;border:1px solid #30363d;background:#0d1117;color:#fff;width:260px}
button{padding:10px 16px;border-radius:6px;border:0;background:#238636;color:#fff;font-weight:600}
@media(max-width:640px){.card img{width:120px;height:68px}.card{gap:8px}}"""
def cls(s): return "hi" if s >= 65 else ("mid" if s >= 45 else "lo")
def fmt(n): return "–" if n is None else (f"{n/1e6:.1f}M" if n >= 1e6 else f"{n/1e3:.1f}K" if n >= 1e3 else str(n))
def when(p): return datetime.fromisoformat(p).astimezone(SAST).strftime("%d %b %H:%M SAST")
def slug(h): return re.sub(r"[^a-z0-9]+", "-", h.lower()).strip("-")

def page(title, body, root=""):
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{E(title)} · SignalTube</title><meta name="description" content="New AI YouTube videos ranked daily by substance, not hype.">
<link rel="stylesheet" href="{root}style.css"></head><body><header><div class="wrap"><nav><a class="logo" href="{root}index.html">Signal<span>Tube</span></a>
<a href="{root}index.html">Today</a><a href="{root}week.html">Last 7 days</a><a href="{root}leaderboard.html">No-hype leaderboard</a><a href="{root}channels.html">Channels</a>
<a href="{root}about.html">Methodology</a><a href="{root}newsletter.html">Newsletter</a><a href="{root}advertise.html">Advertise</a></nav></div></header>
<main class="wrap">{body}</main><footer class="wrap">SignalTube · substance over hype · built by Jon Cameron, South Africa · data from public YouTube RSS feeds</footer></body></html>"""

def card(v, i=None, root=""):
    bd = ", ".join(f"{k} {'+' if x > 0 else ''}{x}" for k, x in v["breakdown"].items() if x and k != "base")
    return f"""<div class="card">{f'<div class="rank">{i}</div>' if i else ''}<a href="{v['url']}"><img loading="lazy" src="{v['thumbnail']}" alt=""></a>
<div style="flex:1"><a class="t" href="{v['url']}">{E(v['title'])}</a><div class="meta"><a href="{root}c/{slug(v['handle'])}.html">{E(v['channel'])}</a> · {when(v['published'])} · {fmt(v['views'])} views{f" · ★{v['stars']:.1f}" if v.get('stars') else ''}</div>
<div>{E(v['summary'])}</div><details><summary>Why this score</summary>base 50, {E(bd)}</details></div><div class="score {cls(v['score'])}">{v['score']}</div></div>"""

def leaderboard(vids, chans):
    rows = []
    for c in chans:
        vs = [v for v in vids if v["channel_id"] == c["channel_id"]]
        if vs: rows.append((round(sum(v["score"] for v in vs) / len(vs)), len(vs), c))
    return sorted(rows, key=lambda r: (-r[0], -r[1]))

def build(vids, chans, out, now):
    if os.path.exists(out): shutil.rmtree(out)
    os.makedirs(out + "/c")
    open(out + "/style.css", "w").write(CSS)
    W = lambda p, s: open(os.path.join(out, p), "w").write(s)
    recent = lambda h: [v for v in vids if now - datetime.fromisoformat(v["published"]) <= timedelta(hours=h)]
    today = recent(24); window = "24 hours"
    if len(today) < 10: today, window = recent(48), "48 hours"
    top = sorted(today, key=lambda v: -v["score"])[:10]
    week = sorted(recent(24 * 7), key=lambda v: -v["score"])
    stamp = now.astimezone(SAST).strftime("%A %d %B %Y, %H:%M SAST")
    W("index.html", page("Today's top 10", f"<h1>Today's top 10</h1><p class='sub'>Highest-substance AI videos from the last {window} across {len(chans)} channels · updated {stamp}</p>"
      + "".join(card(v, i + 1) for i, v in enumerate(top))
      + "<div class='box'><b>Get the weekly top 10 in your inbox.</b> <a href='newsletter.html'>Subscribe →</a></div>"))
    W("week.html", page("Last 7 days", f"<h1>Last 7 days</h1><p class='sub'>{len(week)} videos, ranked by substance score</p>" + "".join(card(v, i + 1) for i, v in enumerate(week[:100]))))
    lb = leaderboard(recent(24 * 30) or vids, chans)
    W("leaderboard.html", page("No-hype leaderboard", "<h1>No-hype leaderboard</h1><p class='sub'>Channels ranked by average substance score of their recent uploads (RSS shows ~15 latest per channel).</p><table><tr><th>#</th><th>Channel</th><th>Avg score</th><th>Videos</th></tr>"
      + "".join(f"<tr><td>{i+1}</td><td><a href='c/{slug(c['handle'])}.html'>{E(c['name'])}</a></td><td><span class='score {cls(s)}'>{s}</span></td><td>{n}</td></tr>" for i, (s, n, c) in enumerate(lb)) + "</table>"))
    W("channels.html", page("Channels", f"<h1>Channels tracked ({len(chans)})</h1><table><tr><th>Channel</th><th>Handle</th><th>Tier</th></tr>"
      + "".join(f"<tr><td><a href='c/{slug(c['handle'])}.html'>{E(c['name'])}</a></td><td>{E(c['handle'])}</td><td>{c['tier']}</td></tr>" for c in sorted(chans, key=lambda c: c['name'].lower())) + "</table>"))
    for c in chans:
        vs = sorted([v for v in vids if v["channel_id"] == c["channel_id"]], key=lambda v: v["published"], reverse=True)
        avg = round(sum(v["score"] for v in vs) / len(vs)) if vs else "–"
        W(f"c/{slug(c['handle'])}.html", page(c["name"], f"<h1>{E(c['name'])}</h1><p class='sub'><a href='https://www.youtube.com/channel/{c['channel_id']}'>{E(c['handle'])}</a> · tier {c['tier']} · avg score {avg}</p>" + "".join(card(v, root="../") for v in vs), root="../"))
    W("about.html", page("Methodology", """<h1>About & methodology</h1><div class='box'><p>SignalTube checks the public RSS feed of every tracked channel daily and gives each new video a <b>substance score from 0 to 100</b>. Every score is explainable: open "Why this score" on any video.</p>
<p><b>Starting point:</b> 50. <b>Penalties:</b> words in ALL CAPS (−6 each), an all-caps title (−10), hype phrases such as "shocking", "insane", "changes everything", "is dead" (−8 each), exclamation marks (−4 each, −6 more for "!!"), emojis in the title (−5 each), short question-bait titles (−4), a thin description (−8), link spam (−6).
<b>Bonuses:</b> substance words such as paper, tutorial, lecture, deep dive, from scratch (+4 each, up to 4), a detailed description (up to +12), references such as arXiv or GitHub (+6), chapter timestamps (+4), and the channel's editorial tier (tier 1 deep/technical +20, tier 2 +8, tier 3 popular/hype-prone −8).</p>
<p>Summaries come from the creator's own description, with promo lines removed. Next: a transcript-based LLM scorer, which will be blended with this heuristic.</p><p>Views and star ratings come from the feed's <code>media:statistics</code>/<code>starRating</code> and are shown for context only. They don't change the score.</p></div>"""))
    W("newsletter.html", page("Newsletter", """<h1>The SignalTube Weekly</h1><p class='sub'>The 10 most substantive AI videos of the week, every Monday. No hype.</p>
<div class='box'><!-- PLACEHOLDER: replace this form with the Buttondown/Beehiiv embed --><form onsubmit="alert('Signup coming soon!');return false"><input type="email" placeholder="you@example.com" required> <button>Subscribe</button></form><p class='meta'>Signups open soon.</p></div>"""))
    W("advertise.html", page("Advertise", """<h1>Advertise on SignalTube</h1><div class='box'><p>Put your brand in front of technical AI viewers who care about substance: engineers, researchers and founders.</p><ul><li>One sponsored slot in each weekly newsletter</li><li>A clearly labelled sponsor card on the site</li><li>We only take sponsors relevant to AI and dev tools</li></ul><p>Contact: <i>coming soon</i> <!-- PLACEHOLDER: add contact email --></p></div>"""))
    return top, week, today

def newsletter(week, outdir, now):
    top = week[:10]; d = now.astimezone(SAST).strftime("%d %B %Y")
    md = [f"# SignalTube Weekly – {d}", "", "The 10 most substantive AI videos of the past week, ranked by our substance score.", ""]
    for i, v in enumerate(top, 1):
        md += [f"## {i}. [{v['title']}]({v['url']}) — {v['score']}/100", f"*{v['channel']}* · {fmt(v['views'])} views", "", v["summary"], ""]
    md += ["---", "Full rankings: https://k8gjj255bp-maker.github.io/signaltube/week.html · Methodology: https://k8gjj255bp-maker.github.io/signaltube/about.html", "", "*[Sponsor slot – placeholder]*"]
    items = "".join(f"""<tr><td style="padding:12px 0;border-bottom:1px solid #eee"><a href="{v['url']}"><img src="{v['thumbnail']}" width="160" style="border-radius:6px;float:left;margin-right:12px"></a>
<b>{i}. <a href="{v['url']}" style="color:#0b57d0">{E(v['title'])}</a></b> <span style="background:#1f6f3a;color:#fff;border-radius:4px;padding:1px 6px">{v['score']}</span><br>
<small style="color:#666">{E(v['channel'])} · {fmt(v['views'])} views</small><br>{E(v['summary'])}</td></tr>""" for i, v in enumerate(top, 1))
    h = f"""<!doctype html><html><body style="font-family:Arial,sans-serif;max-width:640px;margin:auto;color:#222"><h1>Signal<span style="color:#1f883d">Tube</span> Weekly</h1>
<p>{d} · The 10 most substantive AI videos of the past week, with no hype.</p><table width="100%">{items}</table>
<p style="background:#f3f3f3;padding:10px">[Sponsor slot – placeholder]</p><p><small>See the full rankings at signaltube.example. You're getting this because you subscribed.</small></p></body></html>"""
    os.makedirs(outdir, exist_ok=True); stem = f"{outdir}/weekly-{now.astimezone(SAST):%Y-%m-%d}"
    open(stem + ".md", "w").write("\n".join(md)); open(stem + ".html", "w").write(h)
    return stem
