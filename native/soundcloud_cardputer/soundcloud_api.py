from __future__ import annotations
import base64, hashlib, json, secrets, threading, time, urllib.parse, urllib.request, urllib.error, webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

API = "https://api.soundcloud.com"
AUTH = "https://secure.soundcloud.com"

class SoundCloudError(RuntimeError): pass

def _json_request(url, method="GET", headers=None, body=None, timeout=20):
    req = urllib.request.Request(url, data=body, headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read()
            return json.loads(raw.decode("utf-8")) if raw else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:500]
        raise SoundCloudError(f"SoundCloud HTTP {exc.code}: {detail}") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise SoundCloudError(f"Network error: {exc}") from exc

def _b64url(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")

class OAuthFlow:
    def __init__(self, client_id, client_secret, redirect_uri):
        self.client_id, self.client_secret, self.redirect_uri = client_id, client_secret, redirect_uri
        self.state = secrets.token_urlsafe(24)
        self.verifier = _b64url(secrets.token_bytes(48))
        self.code = None
        self.error = None
        self.event = threading.Event()

    def authorize_url(self):
        challenge = _b64url(hashlib.sha256(self.verifier.encode()).digest())
        query = urllib.parse.urlencode({
            "client_id": self.client_id, "redirect_uri": self.redirect_uri,
            "response_type": "code", "code_challenge": challenge,
            "code_challenge_method": "S256", "state": self.state
        })
        return f"{AUTH}/authorize?{query}"

    def wait_for_code(self, timeout=180):
        parsed = urllib.parse.urlparse(self.redirect_uri)
        if parsed.hostname not in ("127.0.0.1", "localhost") or not parsed.port:
            raise SoundCloudError("Redirect URI must use localhost with an explicit port.")
        flow = self
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                if params.get("state", [""])[0] != flow.state:
                    self.send_response(400); self.end_headers()
                    self.wfile.write(b"Invalid OAuth state. Return to the player.")
                    flow.error = "OAuth state mismatch"
                elif params.get("error"):
                    flow.error = params["error"][0]
                    self.send_response(400); self.end_headers()
                    self.wfile.write(b"SoundCloud authorization failed. Return to the player.")
                else:
                    flow.code = params.get("code", [None])[0]
                    self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.end_headers()
                    self.wfile.write(b"<h2>SoundCloud connected.</h2><p>You can close this page and return to Cardputer.</p>")
                flow.event.set()
            def log_message(self, *_): pass
        server = HTTPServer((parsed.hostname, parsed.port), Handler)
        server.timeout = 1
        deadline = time.time() + timeout
        try:
            while not self.event.is_set() and time.time() < deadline:
                server.handle_request()
        finally:
            server.server_close()
        if not self.code:
            raise SoundCloudError(self.error or "Login timed out. Check redirect URI and try again.")
        return self.code

class SoundCloudClient:
    def __init__(self, config, on_status=None):
        self.config = config
        self.on_status = on_status or (lambda _s: None)

    def _status(self, text): self.on_status(text)

    def _token_exchange(self, fields):
        fields = {"client_id": self.config["client_id"], "client_secret": self.config["client_secret"], **fields}
        body = urllib.parse.urlencode(fields).encode()
        data = _json_request(AUTH + "/oauth/token", "POST",
            {"Accept":"application/json", "Content-Type":"application/x-www-form-urlencoded"}, body)
        self.config["access_token"] = data.get("access_token", "")
        self.config["refresh_token"] = data.get("refresh_token", "")
        self.config["expires_at"] = int(time.time()) + int(data.get("expires_in", 3600)) - 60
        self.config["scope"] = data.get("scope", "")
        from .storage import save_config
        save_config(self.config)
        return data

    def login(self):
        if not self.config.get("client_id") or not self.config.get("client_secret"):
            raise SoundCloudError("Add your SoundCloud Client ID and Client Secret in Settings first.")
        redirect = self.config.get("redirect_uri", "http://127.0.0.1:8765/callback")
        flow = OAuthFlow(self.config["client_id"], self.config["client_secret"], redirect)
        url = flow.authorize_url()
        self._status("Opening SoundCloud authorization…")
        try: webbrowser.open(url)
        except Exception: pass
        self._status("Waiting for SoundCloud approval…")
        code = flow.wait_for_code()
        self._token_exchange({
            "grant_type":"authorization_code", "code":code,
            "redirect_uri":redirect, "code_verifier":flow.verifier
        })
        return self.me()

    def ensure_token(self):
        if not self.config.get("access_token"):
            raise SoundCloudError("Not connected. Open Settings → Connect SoundCloud.")
        if time.time() >= float(self.config.get("expires_at", 0)):
            refresh = self.config.get("refresh_token")
            if not refresh: raise SoundCloudError("Session expired. Connect SoundCloud again.")
            self._token_exchange({"grant_type":"refresh_token", "refresh_token":refresh})

    def request(self, path_or_url, method="GET", payload=None, auth=True):
        if auth: self.ensure_token()
        url = path_or_url if path_or_url.startswith("https://") else API + path_or_url
        headers = {"Accept":"application/json"}
        if auth: headers["Authorization"] = "OAuth " + self.config["access_token"]
        body = None
        if payload is not None:
            body = json.dumps(payload).encode()
            headers["Content-Type"] = "application/json"
        return _json_request(url, method, headers, body)

    def pages(self, path, limit=50, max_pages=10):
        url = API + path
        separator = "&" if "?" in url else "?"
        url += f"{separator}limit={limit}&linked_partitioning=true"
        output = []
        for _ in range(max_pages):
            data = self.request(url)
            if isinstance(data, list):
                output.extend(data); break
            output.extend(data.get("collection", []))
            nxt = data.get("next_href")
            if not nxt: break
            url = nxt
        return output

    def me(self): return self.request("/me")
    def search_tracks(self, query):
        return self.pages("/tracks?" + urllib.parse.urlencode({"q":query,"access":"playable"}), max_pages=4)
    def likes(self): return self.pages("/me/likes/tracks")
    def playlists(self): return self.pages("/me/playlists")
    def my_tracks(self): return self.pages("/me/tracks")
    def playlist_tracks(self, playlist):
        urn = playlist.get("urn") or f"soundcloud:playlists:{playlist.get('id')}"
        return self.pages("/playlists/" + urllib.parse.quote(urn, safe=":") + "/tracks")
    def like(self, track):
        urn = track.get("urn") or f"soundcloud:tracks:{track.get('id')}"
        return self.request("/likes/tracks/" + urllib.parse.quote(urn, safe=":"), "POST", {})
    def unlike(self, track):
        urn = track.get("urn") or f"soundcloud:tracks:{track.get('id')}"
        return self.request("/likes/tracks/" + urllib.parse.quote(urn, safe=":"), "DELETE")
    def stream_url(self, track):
        urn = track.get("urn") or f"soundcloud:tracks:{track.get('id')}"
        try:
            data = self.request("/tracks/" + urllib.parse.quote(urn, safe=":") + "/streams")
            if isinstance(data, dict):
                for key in ("http_mp3_128_url", "hls_mp3_128_url", "preview_mp3_128_url"):
                    if data.get(key): return data[key]
                for value in data.values():
                    if isinstance(value, dict) and value.get("url"): return value["url"]
        except SoundCloudError:
            pass
        return None
