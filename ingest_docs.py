
from ingest_common import _run
def ingest_docs(path, out_jsonl, language="en"):
    return _run(["python","raglite.py","ingest-docs","--path",path,"--out",out_jsonl,"--language",language])
