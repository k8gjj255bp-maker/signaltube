"""Transparent substance-vs-hype heuristic (0-100).

Every video gets a `breakdown` dict so readers can see why it scored what it did.
LLM HOOK: `transcript_scorer` is a pluggable callable(video) -> dict|None returning
{"score": 0-100, "summary": str, "notes": str}. When set (see register_transcript_scorer),
its score is blended with the heuristic using LLM_WEIGHT and its summary replaces ours.
"""
import re
HYPE_WORDS = ["shocking","insane","crazy","unbelievable","mind-blowing","mind blowing","changes everything",
  "game changer","game-changer","you won't believe","destroys","just killed","is dead","is over","goes viral",
  "stunned","terrifying","scary","explodes","secret","nobody is talking","no one is talking","everyone is",
  "100x","10x","huge","massive","wild","jaw-dropping","shocked","finally here","holy","bombshell","breaks the internet",
  "insanely","must see","don't miss","literally","omg","wtf","agi is here","free money","make money","$10k","passive income"]
SUBSTANCE_WORDS = ["paper","explained","tutorial","lecture","course","deep dive","analysis","benchmark","research",
  "how to","implementation","from scratch","math","theory","interview","talk","architecture","walkthrough",
  "evaluation","review","study","guide","build","code","training","fine-tuning","fine tune","reinforcement","dataset"]
EMOJI = re.compile("[\U0001F300-\U0001FAFF\u2600-\u27BF\U0001F000-\U0001F2FF]")
TIER_PTS = {1: 20, 2: 8, 3: -8}
LLM_WEIGHT = 0.6
transcript_scorer = None

def register_transcript_scorer(fn):
    """Plug in an LLM transcript scorer later, e.g. fetch captions, send to a model, return dict."""
    global transcript_scorer
    transcript_scorer = fn

def _clean_desc(d):
    lines = [l for l in d.splitlines() if l.strip()]
    keep = [l for l in lines if not re.search(r"https?://|^#|sponsor|patreon|subscribe|follow me|discord|twitter|instagram|tiktok|linkedin|affiliate|use code|join my|newsletter|merch|\d+:\d\d", l, re.I)]
    return " ".join(keep)

def summarize(v, max_chars=260):
    text = re.sub(r"\s+", " ", _clean_desc(v["description"])).strip()
    if not text:
        return "No description provided by the creator."
    sents = re.split(r"(?<=[.!?])\s+", text)
    out = ""
    for s in sents[:2]:
        if len(out) + len(s) > max_chars and out: break
        out += (" " if out else "") + s
    return out[:max_chars].rstrip() + ("…" if len(out) > max_chars else "")

def heuristic(v):
    t, d = v["title"], v["description"]
    tl = t.lower(); b = {"base": 50}
    letters = [c for c in t if c.isalpha()]
    caps_words = [w for w in re.findall(r"[A-Za-z]{3,}", t) if w.isupper() and w not in {"GPT","LLM","API","AGI","NVIDIA","MIT","CEO","GPU","TPU","RAG","SDK","AWS","IBM","CNN","USA","LLMS","MCP","CLI","IDE"}]
    b["caps_words"] = -6 * min(len(caps_words), 4)
    if letters and sum(c.isupper() for c in letters) / len(letters) > 0.6 and len(letters) > 10: b["all_caps_title"] = -10
    b["hype_words"] = -8 * min(sum(w in tl for w in HYPE_WORDS), 4)
    b["exclamations"] = -4 * min(t.count("!"), 3) - (6 if "!!" in t else 0)
    b["question_bait"] = -4 if t.strip().endswith("?") and len(t) < 60 else 0
    b["emojis"] = -5 * min(len(EMOJI.findall(t)), 3)
    b["substance_words"] = 4 * min(sum(w in tl or w in d[:400].lower() for w in SUBSTANCE_WORDS), 4)
    clean = _clean_desc(d); n = len(clean.split())
    b["description_depth"] = -8 if n < 15 else (0 if n < 40 else (6 if n < 120 else 12))
    links = len(re.findall(r"https?://", d))
    b["link_spam"] = -6 if links > 15 else 0
    b["references"] = 6 if re.search(r"arxiv|paper:|doi\.org|github\.com", d, re.I) else 0
    b["timestamps"] = 4 if len(re.findall(r"\b\d{1,2}:\d{2}\b", d)) >= 4 else 0
    b["channel_tier"] = TIER_PTS.get(v["tier"], 0)
    return max(0, min(100, sum(b.values()))), b

def score(v):
    s, b = heuristic(v)
    v["heuristic_score"] = s; v["breakdown"] = b; v["summary"] = summarize(v); v["scorer"] = "heuristic-v1"
    if transcript_scorer:
        r = transcript_scorer(v)
        if r:
            s = round(LLM_WEIGHT * r["score"] + (1 - LLM_WEIGHT) * s)
            v["summary"] = r.get("summary") or v["summary"]; v["llm"] = r; v["scorer"] = "heuristic+llm"
    v["score"] = int(s)
    return v
