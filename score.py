
import re
_WORD = re.compile(r"[A-Za-z0-9_]+")
def _tok(s): return [w.lower() for w in _WORD.findall(s or "")]
def score_answer(query, answer, top_chunks):
    corpus=" ".join(c.get("content","") for c in top_chunks)
    a=set(_tok(answer)); c=set(_tok(corpus))
    overlap=len(a & c)/max(1,len(a))
    coverage=round(overlap*100,1)
    has_cite=("http" in (answer or "")) or ("sources:" in (answer or "").lower())
    citations=100 if has_cite else 0
    groundedness=98 if has_cite else 70
    brevity=max(60, 100 - max(0, len(answer)-900)/9)
    total=round(coverage*0.35 + groundedness*0.35 + citations*0.15 + brevity*0.15,1)
    return {"coverage":coverage,"groundedness":round(groundedness,1),"citations":citations,"brevity":round(brevity,1),"total":total}
