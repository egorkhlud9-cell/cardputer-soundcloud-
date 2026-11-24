from __future__ import annotations
import json, os
from pathlib import Path

APP_DIR = Path.home() / ".config" / "soundcloud-cardputer"
CONFIG_FILE = APP_DIR / "config.json"
LIBRARY_FILE = APP_DIR / "library.json"

DEFAULT_CONFIG = {
    "client_id": "", "client_secret": "", "redirect_uri": "http://127.0.0.1:8765/callback",
    "access_token": "", "refresh_token": "", "expires_at": 0, "scope": "",
    "volume": 70, "last_section": "Home", "last_track": None
}

def _secure_dir():
    APP_DIR.mkdir(parents=True, exist_ok=True)
    try: os.chmod(APP_DIR, 0o700)
    except OSError: pass

def _write(path: Path, data):
    _secure_dir()
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    try: os.chmod(tmp, 0o600)
    except OSError: pass
    tmp.replace(path)
    try: os.chmod(path, 0o600)
    except OSError: pass

def load_config():
    _secure_dir()
    try:
        data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        return {**DEFAULT_CONFIG, **data}
    except (OSError, ValueError, TypeError):
        return dict(DEFAULT_CONFIG)

def save_config(config):
    _write(CONFIG_FILE, {**DEFAULT_CONFIG, **config})

def load_library():
    _secure_dir()
    try:
        data = json.loads(LIBRARY_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError, TypeError):
        return {"favorites": [], "playlists": [], "history": []}

def save_library(data):
    _write(LIBRARY_FILE, data)
