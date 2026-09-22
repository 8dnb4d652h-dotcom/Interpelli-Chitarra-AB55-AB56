import json,re,datetime,feedparser,requests
from bs4 import BeautifulSoup
from urllib.parse import quote
from pathlib import Path

ROOT=Path(__file__).resolve().parent
DATA=ROOT/"data"/"data.json"
SOURCES=ROOT/"data"/"sources.json"
HEADERS={"User-Agent":"Mozilla/5.0 interpelli-chitarra-monitor/1.0"}
QUERIES=[
    '"AB55" interpello chitarra',
    '"AB56" interpello chitarra',
    '"AB55" "interpello per supplenza"',
    '"AB56" "interpello per supplenza"',
]
def rss(q):
    u="https://news.google.com/rss/search?q="+quote(q+" when:30d")+"&hl=it&gl=IT&ceid=IT:it"
    try: return feedparser.parse(requests.get(u,headers=HEADERS,timeout=20).content).entries
    except Exception: return []
def page_text(url):
    try:
        r=requests.get(url,headers=HEADERS,timeout=20,allow_redirects=True)
        if "text/html" not in r.headers.get("content-type",""): return ""
        return BeautifulSoup(r.text,"html.parser").get_text(" ",strip=True)[:250000]
    except Exception: return ""
def detect_cdc(s):
    found=[]
    for c in ("AB55","AB56"):
        if re.search(r"\b"+c+r"\b",s,re.I): found.append(c)
    return found
def infer_region(s, regions):
    su=s.lower()
    for reg,provs in regions.items():
        if reg.lower() in su or any(p.lower() in su for p in provs):
            for p in provs:
                if p.lower() in su: return reg,p
            return reg,""
    return "",""
def main():
    cfg=json.loads(SOURCES.read_text(encoding="utf-8"))
    old=json.loads(DATA.read_text(encoding="utf-8"))
    items=old.get("items",[])
    byurl={x.get("url"):x for x in items if x.get("url")}
    now=datetime.datetime.now(datetime.timezone.utc).isoformat()
    for q in QUERIES:
        for e in rss(q):
            title=e.get("title",""); url=e.get("link","")
            if not url: continue
            txt=page_text(url)
            cdc=detect_cdc(title+" "+txt)
            if not cdc: continue
            for c in cdc:
                reg,prov=infer_region(title+" "+txt,cfg["regions"])
                obj={"id":str(abs(hash((c,url)))),"cdc":c,"region":reg,"province":prov,
                     "school":"","published":e.get("published","")[:10],
                     "expiry":"","title":title,"url":url,"source":"Ricerca web/RSS","status":"da verificare"}
                if url not in byurl: items.append(obj); byurl[url]=obj
                else:
                    byurl[url].update({k:v for k,v in obj.items() if v and k not in ("status",)})
    items.sort(key=lambda x:x.get("published",""),reverse=True)
    DATA.write_text(json.dumps({"updated_at":now,"items":items},ensure_ascii=False,indent=2),encoding="utf-8")
if __name__=="__main__": main()
