#!/usr/bin/env python3
"""CloudZero on-device library and local application server.

No SoundCloud passwords, browser cookies, OAuth tokens or API secrets are read.
Only public SoundCloud URLs and user-created local playlists are stored.
"""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
import json
import os
import threading
import time
import uuid

ROOT = Path("/usr/share/cloudzero/web")
DATA = Path("/var/lib/cloudzero")
DATA.mkdir(parents=True, exist_ok=True)
try:
    os.chmod(DATA, 0o750)
except OSError:
    pass
LOCK = threading.RLock()
STATE_FILE = DATA / "state.json"
LIBRARY_FILE = DATA / "library.json"
PLAYLIST_FILE = DATA / "playlists.json"
STATE = {"title": "Nothing playing", "artist": "Load a public SoundCloud URL",
         "artwork": "", "duration": 0, "position": 0, "playing": False,
         "volume": 75, "updated": 0}
QUEUE = []

def read_json(path, fallback):
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value
    except (OSError, ValueError, TypeError):
        return fallback

def write_json(path, value):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    os.chmod(tmp, 0o640)
    tmp.replace(path)

def valid_sc_url(value):
    try:
        parsed = urlsplit(str(value).strip())
        host = (parsed.hostname or "").lower()
        return (parsed.scheme in ("http", "https") and
                (host == "soundcloud.com" or host.endswith(".soundcloud.com")) and
                not parsed.username and not parsed.password)
    except (TypeError, ValueError):
        return False

def clean_text(value, limit=180):
    return " ".join(str(value or "").replace("\x00", "").split())[:limit]

LIBRARY = read_json(LIBRARY_FILE, [])
PLAYLISTS = read_json(PLAYLIST_FILE, [])
_saved = read_json(STATE_FILE, {})
if isinstance(_saved, dict):
    STATE.update({k: v for k, v in _saved.items() if k in STATE})
    if isinstance(_saved.get("queue"), list):
        QUEUE = [x for x in _saved["queue"] if isinstance(x, dict) and valid_sc_url(x.get("url", ""))]

class Handler(BaseHTTPRequestHandler):
    server_version = "CloudZero/1.0"
    def log_message(self, *_):
        pass

    def send_json(self, code, value):
        data = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(data)

    def read_body(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length < 0 or length > 65536:
                return None
            value = json.loads(self.rfile.read(length) or b"{}")
            return value if isinstance(value, dict) else None
        except (ValueError, TypeError):
            return None

    def do_GET(self):
        path = urlsplit(self.path).path
        with LOCK:
            if path == "/api/state":
                data = dict(STATE)
                data["queue"] = list(QUEUE)
                data["queue_count"] = len(QUEUE)
                data["library_count"] = len(LIBRARY)
                data["playlist_count"] = len(PLAYLISTS)
                return self.send_json(200, data)
            if path == "/api/library":
                return self.send_json(200, LIBRARY)
            if path == "/api/playlists":
                return self.send_json(200, PLAYLISTS)
            if path == "/api/queue":
                return self.send_json(200, QUEUE)
        if path in ("/", "/index.html"):
            try:
                data = (ROOT / "index.html").read_bytes()
            except OSError:
                return self.send_error(404, "CloudZero UI missing")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            return self.wfile.write(data)
        if path == "/api/health":
            return self.send_json(200, {"ok": True, "app": "CloudZero"})
        return self.send_json(404, {"error": "not found"})

    def do_POST(self):
        global STATE, LIBRARY, PLAYLISTS, QUEUE
        path = urlsplit(self.path).path
        data = self.read_body()
        if data is None:
            return self.send_json(400, {"error": "invalid request body"})

        with LOCK:
            if path == "/api/state":
                for key in ("title", "artist", "artwork", "duration", "position", "playing", "volume"):
                    if key in data:
                        STATE[key] = data[key]
                STATE["updated"] = int(time.time())
                write_json(STATE_FILE, dict(STATE, queue=QUEUE))
                return self.send_json(200, {"ok": True})

            if path == "/api/library/add":
                url = str(data.get("url", "")).strip()
                if not valid_sc_url(url):
                    return self.send_json(400, {"error": "only SoundCloud URLs are accepted"})
                item = {"id": uuid.uuid4().hex[:12], "kind": "playlist" if data.get("kind") == "playlist" else "track",
                        "title": clean_text(data.get("title"), 180) or "Saved SoundCloud item",
                        "artist": clean_text(data.get("artist"), 120), "url": url,
                        "artwork": clean_text(data.get("artwork"), 500), "saved": int(time.time())}
                if not any(x.get("url") == url for x in LIBRARY):
                    LIBRARY.insert(0, item)
                    LIBRARY = LIBRARY[:200]
                    write_json(LIBRARY_FILE, LIBRARY)
                return self.send_json(200, {"ok": True})

            if path == "/api/library/remove":
                item_id = str(data.get("id", ""))
                LIBRARY = [x for x in LIBRARY if x.get("id") != item_id]
                write_json(LIBRARY_FILE, LIBRARY)
                return self.send_json(200, {"ok": True})

            if path == "/api/queue/add":
                url = str(data.get("url", "")).strip()
                if not valid_sc_url(url):
                    return self.send_json(400, {"error": "only SoundCloud URLs are accepted"})
                QUEUE.append({"id": uuid.uuid4().hex[:12], "url": url,
                              "title": clean_text(data.get("title"), 180) or "Queued track",
                              "artist": clean_text(data.get("artist"), 120)})
                QUEUE = QUEUE[:100]
                write_json(STATE_FILE, dict(STATE, queue=QUEUE))
                return self.send_json(200, {"ok": True, "count": len(QUEUE)})

            if path == "/api/queue/remove":
                item_id = str(data.get("id", ""))
                QUEUE = [x for x in QUEUE if x.get("id") != item_id]
                write_json(STATE_FILE, dict(STATE, queue=QUEUE))
                return self.send_json(200, {"ok": True})

            if path == "/api/queue/clear":
                QUEUE = []
                write_json(STATE_FILE, dict(STATE, queue=QUEUE))
                return self.send_json(200, {"ok": True})

            if path == "/api/playlists/create":
                name = clean_text(data.get("name"), 48)
                if not name:
                    return self.send_json(400, {"error": "playlist name is required"})
                if any(x.get("name", "").casefold() == name.casefold() for x in PLAYLISTS):
                    return self.send_json(409, {"error": "playlist already exists"})
                PLAYLISTS.append({"id": uuid.uuid4().hex[:12], "name": name, "items": [], "created": int(time.time())})
                write_json(PLAYLIST_FILE, PLAYLISTS)
                return self.send_json(200, {"ok": True})

            if path == "/api/playlists/delete":
                item_id = str(data.get("id", ""))
                PLAYLISTS = [x for x in PLAYLISTS if x.get("id") != item_id]
                write_json(PLAYLIST_FILE, PLAYLISTS)
                return self.send_json(200, {"ok": True})

            if path == "/api/playlists/add":
                item_id = str(data.get("id", ""))
                url = str(data.get("url", "")).strip()
                if not valid_sc_url(url):
                    return self.send_json(400, {"error": "only SoundCloud URLs are accepted"})
                target = next((x for x in PLAYLISTS if x.get("id") == item_id), None)
                if target is None:
                    return self.send_json(404, {"error": "playlist not found"})
                if not any(x.get("url") == url for x in target["items"]):
                    target["items"].append({"id": uuid.uuid4().hex[:12], "url": url,
                                            "title": clean_text(data.get("title"), 180) or "SoundCloud track",
                                            "artist": clean_text(data.get("artist"), 120)})
                write_json(PLAYLIST_FILE, PLAYLISTS)
                return self.send_json(200, {"ok": True})

            if path == "/api/playlists/remove":
                item_id, track_id = str(data.get("id", "")), str(data.get("track_id", ""))
                target = next((x for x in PLAYLISTS if x.get("id") == item_id), None)
                if target:
                    target["items"] = [x for x in target["items"] if x.get("id") != track_id]
                    write_json(PLAYLIST_FILE, PLAYLISTS)
                return self.send_json(200, {"ok": True})

        return self.send_json(404, {"error": "not found"})

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Allow", "GET, POST, OPTIONS")
        self.end_headers()

if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", 8765), Handler).serve_forever()
