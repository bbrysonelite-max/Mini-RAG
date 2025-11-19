
from ingest_common import _run
def ingest_docs(path, out_jsonl, language="en", user_id=None):
    # Note: user_id is not passed to subprocess (raglite.py CLI doesn't support it yet)
    # For now, server.py will call raglite functions directly with user_id
    return _run(["python","raglite.py","ingest-docs","--path",path,"--out",out_jsonl,"--language",language])
