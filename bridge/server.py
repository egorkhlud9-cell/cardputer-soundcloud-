#!/usr/bin/env python3
"""CloudZero local phone bridge. Playback remains inside SoundCloud's official widget."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
import json, threading, time

ROOT = Path("/usr/share/cloudzero/web")
LOCK = threading.Lock()
STATE = {"title":"Nothing playing","artist":"Paste a SoundCloud URL on your phone","artwork":"","duration":0,"position":0,"playing":False,"updated":0}
COMMANDS = []
class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_): pass
    def send(self, code, body, mime="application/json; charset=utf-8"):
        data = body if isinstance(body, bytes) else body.encode()
        self.send_response(code); self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(data))); self.send_header("Cache-Control","no-store")
        self.send_header("Access-Control-Allow-Origin","*"); self.end_headers(); self.wfile.write(data)
    def do_OPTIONS(self):
        self.send_response(204); self.send_header("Access-Control-Allow-Origin","*")
        self.send_header("Access-Control-Allow-Headers","Content-Type"); self.send_header("Access-Control-Allow-Methods","GET,POST,OPTIONS"); self.end_headers()
    def do_GET(self):
        path=urlparse(self.path).path
        if path=="/api/state":
            with LOCK: data=dict(STATE)
            return self.send(200,json.dumps(data))
        if path=="/api/commands":
            with LOCK: data=list(COMMANDS); COMMANDS.clear()
            return self.send(200,json.dumps(data))
        if path in ("/","/index.html"):
            try: return self.send(200,(ROOT/"index.html").read_bytes(),"text/html; charset=utf-8")
            except OSError: return self.send(404,"Web UI missing","text/plain")
        return self.send(404,"Not found","text/plain")
    def do_POST(self):
        global STATE
        path=urlparse(self.path).path
        try: data=json.loads(self.rfile.read(int(self.headers.get("Content-Length","0"))) or b"{}")
        except Exception: return self.send(400,'{"error":"bad json"}')
        if path=="/api/state":
            allowed=("title","artist","artwork","duration","position","playing")
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
        return self.send(404,'{"error":"not found"}')
ThreadingHTTPServer(("0.0.0.0",8765),Handler).serve_forever()
