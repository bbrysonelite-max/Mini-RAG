
from ingest_common import _run
def ingest_transcript(path, out_jsonl, language="en"):
    return _run(["python","raglite.py","ingest-transcript","--path",path,"--out",out_jsonl,"--language",language])
