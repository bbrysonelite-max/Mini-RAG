
import subprocess, json
def _run(cmd):
    p=subprocess.run(cmd, capture_output=True, text=True)
    out=(p.stdout or "") + "\n" + (p.stderr or "")
    # try to parse the last JSON-looking line
    for line in reversed(out.splitlines()):
        line=line.strip()
        if line.startswith("{") and line.endswith("}"):
            try: return json.loads(line)
            except: pass
    return {"written":0,"stdout":p.stdout,"stderr":p.stderr}
