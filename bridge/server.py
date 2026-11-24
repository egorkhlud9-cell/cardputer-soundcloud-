#!/usr/bin/env python3
"""CloudZero local bridge and on-device saved library."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, urlsplit
import json, threading, time

ROOT = Path("/usr/share/cloudzero/web")
DATA = Path("/var/lib/cloudzero")
LIBRARY_FILE = DATA / "library.json"
DATA.mkdir(parents=True, exist_ok=True)
LOCK = threading.Lock()
STATE = {"title":"Nothing playing","artist":"Paste a SoundCloud URL on your phone","artwork":"","duration":0,"position":0,"playing":False,"queue":[],"updated":0}
COMMANDS = []
def load_library():
    try:
        value=json.loads(LIBRARY_FILE.read_text())
        return value if isinstance(value,list) else []
    except Exception:
        return []
LIBRARY=load_library()
def save_library():
    tmp=LIBRARY_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(LIBRARY,ensure_ascii=False,indent=2))
    tmp.replace(LIBRARY_FILE)
def valid_sc_url(value):
    try:
        host=(urlsplit(value).hostname or "").lower()
        return urlsplit(value).scheme in ("http","https") and (host=="soundcloud.com" or host.endswith(".soundcloud.com"))
    except Exception:
        return False

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_): pass
    def send(self, code, body, mime="application/json; charset=utf-8"):
        data=body if isinstance(body,bytes) else body.encode()
        self.send_response(code); self.send_header("Content-Type",mime)
        self.send_header("Content-Length",str(len(data))); self.send_header("Cache-Control","no-store")
        self.send_header("Access-Control-Allow-Origin","*"); self.end_headers(); self.wfile.write(data)
    def read_json(self):
        try: return json.loads(self.rfile.read(int(self.headers.get("Content-Length","0"))) or b"{}")
        except Exception: return None
    def do_OPTIONS(self):
        self.send_response(204); self.send_header("Access-Control-Allow-Origin","*")
        self.send_header("Access-Control-Allow-Headers","Content-Type"); self.send_header("Access-Control-Allow-Methods","GET,POST,DELETE,OPTIONS"); self.end_headers()
    def do_GET(self):
        path=urlparse(self.path).path
        if path=="/api/state":
            with LOCK: data=dict(STATE)
            data["queue_count"]=len(data.get("queue",[]))
            return self.send(200,json.dumps(data,ensure_ascii=False))
        if path=="/api/commands":
            with LOCK: data=list(COMMANDS); COMMANDS.clear()
            return self.send(200,json.dumps(data))
        if path=="/api/library":
            with LOCK: data=list(LIBRARY)
            return self.send(200,json.dumps(data,ensure_ascii=False))
        if path in ("/","/index.html"):
            try: return self.send(200,(ROOT/"index.html").read_bytes(),"text/html; charset=utf-8")
            except OSError: return self.send(404,"Web UI missing","text/plain")
        return self.send(404,"Not found","text/plain")
    def do_POST(self):
        global STATE
        path=urlparse(self.path).path
        data=self.read_json()
        if data is None: return self.send(400,'{"error":"bad json"}')
        if path=="/api/state":
            allowed=("title","artist","artwork","duration","position","playing","queue")
            with LOCK:
                for k in allowed:
                    if k in data: STATE[k]=data[k]
                STATE["updated"]=int(time.time())
            return self.send(200,'{"ok":true}')
        if path=="/api/command":
            cmd=data.get("command")
            if cmd not in ("play","pause","toggle","next","previous"): return self.send(400,'{"error":"bad command"}')
            with LOCK: COMMANDS.append({"command":cmd,"id":time.time_ns()})
            return self.send(200,'{"ok":true}')
        if path=="/api/library/add":
            url=str(data.get("url","")).strip()
            if not valid_sc_url(url): return self.send(400,'{"error":"only SoundCloud URLs are accepted"}')
            item={"kind":"playlist" if data.get("kind")=="playlist" else "track",
                  "title":str(data.get("title","Saved SoundCloud item"))[:180],
                  "artist":str(data.get("artist",""))[:120],"url":url,
                  "artwork":str(data.get("artwork",""))[:500],"saved":int(time.time())}
            with LOCK:
                if not any(x.get("url")==url for x in LIBRARY):
                    LIBRARY.insert(0,item); del LIBRARY[100:]
                    save_library()
            return self.send(200,'{"ok":true}')
        if path=="/api/library/remove":
            index=data.get("index")
            if not isinstance(index,int): return self.send(400,'{"error":"bad index"}')
            with LOCK:
                if 0<=index<len(LIBRARY):
                    LIBRARY.pop(index);save_library()
            return self.send(200,'{"ok":true}')
        return self.send(404,'{"error":"not found"}')
ThreadingHTTPServer(("0.0.0.0",8765),Handler).serve_forever()
