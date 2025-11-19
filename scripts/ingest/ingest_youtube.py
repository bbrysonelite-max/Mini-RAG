
from ingest_common import _run
def ingest_youtube(url, out_jsonl, language="en"):
    return _run(["python","raglite.py","ingest-youtube","--url",url,"--out",out_jsonl,"--language",language])
