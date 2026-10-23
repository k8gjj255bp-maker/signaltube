"""Resolve YouTube @handles to channel IDs and verify each RSS feed. Writes channels.json."""
import json, re, urllib.request, concurrent.futures as cf
# (handle, tier) tier: 1=deep/technical, 2=solid explainer/news, 3=popular/hype-prone
H = """
aiexplained-official 1|TwoMinutePapers 1|YannicKilcher 1|AndrejKarpathy 1|3blue1brown 1|lexfridman 2|MachineLearningStreetTalk 1|samwitteveenai 1|umarjamilai 1|stanfordonline 1|mitocw 1|DeepMind 1|OpenAI 2|anthropic-ai 2|GoogleDevelopers 2|NVIDIA 2|huggingface 1|WelchLabsVideo 1|ArtemKirsanov 1|statquest 1|sentdex 1|jeremyhoward 1|AICoffeeBreak 1|DwarkeshPatel 1|latentspacepod 1|NoPriors 2|ycombinator 2|a16z 2|computerphile 1|Numberphile 2|veritasium 2|kurzgesagt 2|AlphaSignalAI 2|DataIndependent 2|jamesbriggs 1|ArjanCodes 1|Fireship 2|TheAIGRID 3|MatthewBerman 3|mreflow 3|aiadvantage 3|WesRoth 3|DavidShapiro 3|AllAboutAI 3|ColeMedin 2|IndyDevDan 2|ThePrimeTimeagen 3|TechWithTim 2|freecodecamp 1|CodeEmporium 1|AssemblyAI 2|weights_biases 1|LangChain 1|LlamaIndex 2|DeepLearningAI 1|serranoacademy 1|ritvikmath 1|mathemaniac 1|GregKamradt 1|ai-jason 3|engineerprompt 2|1littlecoder 2|Mervinpraison 3|WorldofAI 3|intheworldofai 3|AIRevolutionX 3|bycloudAI 2|krishnaik06 2|codebasics 2|CodeBullet 3|NetworkChuck 3|LinusTechTips 3|mkbhd 3|ColdFusion 2|AsmonAI 3|TheVerge 3|CNBC 3|BloombergTechnology 2|WIRED 3|TwoMinutePapers 1|Computerphile 1|PyTorch 1|TensorFlow 2|googlecloudtech 2|MicrosoftResearch 1|Microsoft 3|MetaAI 2|AIatMeta 2|mistralai 2|xai 3|perplexity_ai 3|cursor_ai 2|GoogleDeepMind 1|aiDotEngineer 1|SimonWillison 1|nateherk 3|LiamOttley 3|DaveShap 3|matthew_berman 3|TheoBrowne 3|t3dotgg 3|ByteByteGo 2|hamelhusain 1|yacinemtb 3|Sabine Hossenfelder 2|SabineHossenfelder 2|AngelaCollier 2|Hyperspace 2|EdanMeyer 1|MutualInformation 1|NeelNanda 1|RobertMilesAI 1|AISafetyMemes 3|Lexfridman 2|PeterDiamandis 3|BrianRoemmele 3|ManningPublications 1|ByCloud 2|AIJasonZ 3|Ycombinator 2|MIT 2|harvard 2|SimonsInstitute 1|IPAMUCLA 1|TOEwithCurtJaimungal 2|MachineLearningwithPhil 1|AladdinPersson 1|NicholasRenotte 2|JeffHeaton 1|ShawhinTalebi 1|DaveEbbelaar 2|AIAnytime 2|PromptEngineering 2|AIFoundations 3|SkillLeapAI 3|KevinStratvert 3|AIMasters 3|IgorPogany 3|TheAIAdvantage 3|MattVidPro 3|olivio 3|OlivioSarikas 2|SebastianKamph 2|NerdyRodent 2|TroubleChute 3|aitrepreneur 3|Aitrepreneur 3|futurepedia_io 3|AIDailyBrief 2|TheAIDailyBrief 2|lastweekinai 2|Bloomberg 3|60minutes 3|BigThink 3|TED 3|StanfordGSB 2|CS50 1|Sebastian_Raschka 1|SebastianRaschka 1|chrishayuk 1|vrsen 3|DrWaku 2|GoogleforDevelopers 2|AWSEventsChannel 2|IBMTechnology 2|PaulGAllen 2|AnastasiInTech 2|TechAltar 2|LowLevelTV 2|NeetCode 2|ByteMonk 2|AICodeKing 3|GosuCoder 2|JeffSu 3
"""
items=[]; seen=set()
for x in H.replace("\n","").split("|"):
    h,t=x.rsplit(" ",1); h=h.replace(" ","")
    if h.lower() in seen: continue
    seen.add(h.lower()); items.append((h,int(t)))
UA={"User-Agent":"Mozilla/5.0","Accept-Language":"en"}
def get(u): return urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=20).read().decode("utf8","ignore")
def res(it):
    h,t=it
    try:
        p=get(f"https://www.youtube.com/@{h}")
        cid=re.search(r'"externalId":"(UC[\w-]{22})"',p).group(1)
        name=re.search(r'<meta property="og:title" content="([^"]*)"',p).group(1)
        f=get(f"https://www.youtube.com/feeds/videos.xml?channel_id={cid}")
        if "<entry>" not in f: return None
        return {"handle":"@"+h,"name":name,"channel_id":cid,"tier":t}
    except Exception: return None
with cf.ThreadPoolExecutor(12) as ex: out=[r for r in ex.map(res,items) if r]
d={};[d.setdefault(r["channel_id"],r) for r in out]
out=sorted(d.values(),key=lambda r:(r["tier"],r["name"].lower()))
json.dump(out,open("channels.json","w"),indent=1,ensure_ascii=False)
print(len(items),"tried",len(out),"verified")
