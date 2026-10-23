# SignalTube

New AI YouTube videos ranked every day by **substance, not hype**, plus a weekly newsletter of the top 10.
Pure Python 3 standard library. No API keys or paid services.

## Run
```bash
python3 run.py                 # fetch RSS -> score -> build site/ and newsletter/
python3 -m http.server -d site 8000   # preview at http://localhost:8000
python3 resolve_channels.py    # optional: rebuild channels.json from the @handle list (checks every RSS feed)
```
Outputs:
- `site/`: static site with today's top 10, the last 7 days, the no-hype leaderboard, per-channel pages (`c/`), methodology, and newsletter and advertise placeholders.
- `newsletter/weekly-YYYY-MM-DD.{md,html}`: draft of the weekly top 10.
- `data/videos.json`: rolling 60-day history. The RSS feed only shows about 15 recent videos per channel, so the 7-day view and leaderboard depend on this history.

## Layout
- `channels.json`: 130 verified channels (`handle`, `name`, `channel_id`, `tier` 1 = deep/technical, 2 = solid, 3 = popular/hype-prone). Edit tiers here.
- `signaltube/fetch.py`: RSS fetcher. Pulls views and stars from `media:statistics` and `media:starRating`. Videos from general (non-AI) channels are kept only if they mention AI.
- `signaltube/score.py`: transparent heuristic. Each video stores a `breakdown`. **LLM hook:** `register_transcript_scorer(fn)`, where `fn(video) -> {"score", "summary", "notes"}`. Its score is blended with the heuristic at `LLM_WEIGHT=0.6` and its summary replaces the description-based one.
- `signaltube/build.py`: site and newsletter templates.

## Going live (free)
**Hosting:** GitHub Pages + GitHub Actions cron (`.github/workflows/daily.yml` runs daily at 06:00 SAST, commits history and deploys). In the repo settings, set Pages → Source = "GitHub Actions". Cloudflare Pages also works: connect the repo, set the build command to `python3 run.py` and the output dir to `site`, and trigger daily rebuilds with a deploy hook called from the Actions cron.

**Newsletter:** Buttondown (free up to 100 subscribers, accepts Markdown so the `.md` draft can be pasted in, has an API) or Beehiiv (free up to 2,500 subscribers, has a built-in ad network that fits the Advertise page). Paste their embed form into the placeholder in `site/newsletter.html` (in `build.py`).

**Accounts Jon needs:**
1. GitHub account + public repo (Pages + Actions are free for public repos).
2. Newsletter account: Beehiiv *or* Buttondown (free tier).
3. Optional: Cloudflare account (if using Cloudflare Pages instead of GitHub Pages, and/or for a custom domain's DNS).
4. Optional: a domain (around US$10/yr, the only cost) and a contact email for the Advertise page.
5. Later, for the LLM transcript scorer: an LLM API key stored as a GitHub Actions secret.

## Known limitations
- The RSS feed lists only the latest ~15 uploads per channel. Shorts are included.
- Star ratings in the feed are nearly always 5.0, so they're display-only. Views refresh on each run.
- The heuristic uses only the title, description and channel tier. Tiers were assigned by hand and are subjective.
