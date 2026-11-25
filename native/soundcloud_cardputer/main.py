from __future__ import annotations
import json, os, shutil, subprocess, threading, time
import pygame
from .storage import load_config,save_config,load_library,save_library
from .audio_player import AudioPlayer,AudioError
from .ui_engine import UI
print("BOOT: module imports complete", flush=True)

SECTIONS=["Home","Search","Favorites","Playlists","My Tracks","Now Playing","Settings"]
def public_search(query):
    """Search public SoundCloud with bounded retries and readable network errors."""
    if not shutil.which("yt-dlp"):
        raise RuntimeError("yt-dlp is missing. Reinstall AURORA dependencies.")
    args = ["yt-dlp", "--flat-playlist", "-J", "--no-warnings",
        "--force-ipv4", "--socket-timeout", "15", "--retries", "2",
        "--extractor-retries", "2", "scsearch15:" + query]
    last_error = ""
    network_terms = ("transporterror", "connection", "timed out", "timeout",
        "name or service not known", "temporary failure", "network is unreachable",
        "maxretryerror", "newconnectionerror", "ssl")
    for attempt in range(3):
        try:
            result = subprocess.run(args, capture_output=True, text=True, timeout=45)
        except subprocess.TimeoutExpired:
            last_error = "SoundCloud search timed out. Check Wi-Fi and press R to retry."
            continue
        except OSError as exc:
            raise RuntimeError("Could not start yt-dlp: " + str(exc)[:70])
        if result.returncode == 0:
            try:
                data = json.loads(result.stdout)
            except json.JSONDecodeError:
                raise RuntimeError("SoundCloud returned an unreadable search response.")
            tracks = []
            for x in data.get("entries", []):
                if not x:
                    continue
                url = x.get("webpage_url") or x.get("url")
                if url and not str(url).startswith("http"):
                    url = "https://soundcloud.com/" + str(url).lstrip("/")
                tracks.append({"title": x.get("title") or "Untitled",
                    "permalink_url": url,
                    "user": {"username": x.get("uploader") or x.get("channel") or ""}})
            return tracks
        last_error = (result.stderr or "SoundCloud public search failed")[-500:]
        if not any(term in last_error.lower() for term in network_terms):
            break
        if attempt < 2:
            time.sleep(1.2 * (attempt + 1))
    if any(term in last_error.lower() for term in network_terms):
        raise RuntimeError("SoundCloud connection failed. Check Wi-Fi/DNS, then press R to retry.")
    clean = " ".join(last_error.split())
    raise RuntimeError(("SoundCloud search failed: " + clean[-100:])[:110])

class App:
    def __init__(self):
        print("BOOT: loading local config", flush=True)
        self.config=load_config(); self.library=load_library()
        print("BOOT: creating UI", flush=True)
        self.ui=UI()
        print("BOOT: UI ready; creating audio player", flush=True)
        self.player=AudioPlayer()
        print("BOOT: audio player ready", flush=True)
        self.section="Home"; self.items=[]; self.selected=0; self.track=self.config.get("last_track")
        self.message="Public mode · no account or API key"; self.search_text=""
        self.busy=False; self.running=True
        self.player.volume=int(self.config.get("volume",70))
        self.muted=False
        self.pre_mute_volume=self.player.volume
        self.ui.volume=self.player.volume
        self.load_section()
    def start_task(self,fn):
        if self.busy: return
        self.busy=True; self.message="Working…"
        def run():
            try: fn()
            except Exception as exc: self.message=str(exc)[:100]
            finally: self.busy=False
        threading.Thread(target=run,daemon=True).start()
    def load_section(self):
        if self.section=="Home":
            self.items=["Search SoundCloud","Favorites","Playlists","Recently played","Now Playing","Settings"]
        elif self.section=="Favorites": self.items=self.library["favorites"]
        elif self.section=="Playlists": self.items=self.library["playlists"]
        elif self.section=="My Tracks": self.items=[]
        elif self.section=="Recently played": self.items=self.library["history"]
        elif self.section=="Search": self.items=[]
        elif self.section=="Settings":
            self.items=["Playback volume: "+str(self.player.volume)+"%","Clear play history","About / no API keys required","Back"]
        self.selected=max(0,min(self.selected,len(self.items)-1))
    def navigate(self,section):
        self.section=section; self.selected=0
        self.config["last_section"]=section; save_config(self.config); self.load_section()
    def play_track(self,track):
        page=track.get("permalink_url") or track.get("url") or track.get("webpage_url")
        if not page: raise AudioError("This result has no public SoundCloud URL.")
        if not shutil.which("yt-dlp"): raise AudioError("yt-dlp is not installed.")
        result=subprocess.run(["yt-dlp","-g","-f","bestaudio/best",page],
            capture_output=True,text=True,timeout=60)
        if result.returncode or not result.stdout.strip():
            raise AudioError((result.stderr or "Could not resolve this public track")[-160:])
        self.player.play(result.stdout.strip().splitlines()[0],track.get("title",""))
        self.track=track; self.config["last_track"]=track; self.config["volume"]=self.player.volume
        save_config(self.config)
        self.library["history"]=[track]+[x for x in self.library["history"] if x.get("permalink_url")!=page]
        self.library["history"]=self.library["history"][:80]; save_library(self.library)
        self.navigate("Now Playing")
    def search(self):
        if not self.search_text.strip(): self.message="Type a search phrase first"; return
        self.items=public_search(self.search_text.strip()); self.selected=0
        self.message=f"{len(self.items)} public results"
    def toggle_favorite(self,track):
        key=track.get("permalink_url") or track.get("id")
        fav=self.library["favorites"]
        old=next((x for x in fav if (x.get("permalink_url") or x.get("id"))==key),None)
        if old: fav.remove(old); self.message="Removed from local favorites"
        else: fav.insert(0,track); self.message="Saved to local favorites"
        save_library(self.library); self.load_section()
    def add_to_playlist(self,track):
        playlists=self.library["playlists"]
        if not playlists:
            playlists.append({"name":"My playlist","tracks":[]})
        playlists[0].setdefault("tracks",[]).append(track)
        save_library(self.library); self.message="Added to "+playlists[0]["name"]
    def activate(self):
        if self.section=="Home":
            target=["Search","Favorites","Playlists","Recently played","Now Playing","Settings"][self.selected]
            self.navigate(target)
        elif self.section=="Settings":
            if self.selected==0:
                self.player.set_volume(self.player.volume+5); self.config["volume"]=self.player.volume; save_config(self.config)
                self.load_section()
            elif self.selected==1:
                self.library["history"]=[]; save_library(self.library); self.message="History cleared"; self.load_section()
            elif self.selected==2: self.message="No login, API key or subscription required"
            else: self.navigate("Home")
        elif self.section=="Playlists":
            if self.items:
                playlist=self.items[self.selected]
                self.items=playlist.get("tracks",[]); self.section="Playlist"; self.selected=0
        elif self.section=="Playlist":
            if self.items and isinstance(self.items[self.selected],dict):
                self.start_task(lambda:self.play_track(self.items[self.selected]))
        elif self.section in ("Search","Favorites","Recently played"):
            if self.items and isinstance(self.items[self.selected],dict):
                self.start_task(lambda:self.play_track(self.items[self.selected]))
        elif self.section=="Now Playing": self.player.toggle()
    def handle(self,event):
        if event.type==pygame.QUIT: self.running=False; return
        if event.type!=pygame.KEYDOWN: return
        key=event.key
        if self.section=="Search":
            if key==pygame.K_BACKSPACE:
                self.search_text=self.search_text[:-1]; self.items=[]; self.selected=0; return
            if key in (pygame.K_RETURN,pygame.K_KP_ENTER):
                if self.items: self.activate()
                else: self.start_task(self.search)
                return
            if key==pygame.K_ESCAPE: self.navigate("Home"); return
            if event.unicode and event.unicode.isprintable():
                self.search_text+=event.unicode; self.items=[]; self.selected=0; return
        if key in (pygame.K_ESCAPE,pygame.K_BACKSPACE):
            if self.section=="Now Playing": self.navigate("Home")
            elif self.section=="Playlist": self.navigate("Playlists")
            elif self.section!="Home": self.navigate("Home")
            else: self.running=False
        elif self.section=="Now Playing" and key == pygame.K_a:
            if self.muted:
                self.muted=False
                self.player.set_volume(self.pre_mute_volume)
            else:
                self.pre_mute_volume=max(5,self.player.volume)
                self.muted=True
                self.player.set_volume(0)
            self.message = "Muted" if self.muted else f"Volume {self.player.volume}%"
        elif self.section=="Now Playing" and key in (pygame.K_d, pygame.K_PLUS, pygame.K_EQUALS):
            self.pre_mute_volume=min(100,(self.pre_mute_volume if self.muted else self.player.volume)+5)
            if not self.muted: self.player.set_volume(self.pre_mute_volume)
            self.ui.volume=self.player.volume; self.message=f"Volume {self.pre_mute_volume}%"
        elif self.section=="Now Playing" and key in (pygame.K_s, pygame.K_MINUS):
            self.pre_mute_volume=max(0,(self.pre_mute_volume if self.muted else self.player.volume)-5)
            if not self.muted: self.player.set_volume(self.pre_mute_volume)
            self.ui.volume=self.player.volume; self.message=f"Volume {self.pre_mute_volume}%"
        elif key in (pygame.K_UP, pygame.K_f): self.selected=max(0,self.selected-1)
        elif key in (pygame.K_DOWN, pygame.K_x): self.selected=min(max(0,len(self.items)-1),self.selected+1)
        elif key in (pygame.K_RETURN,pygame.K_KP_ENTER): self.activate()
        elif key==pygame.K_SPACE:
            if self.section=="Now Playing": self.player.toggle()
            elif self.section in ("Search","Favorites","Recently played","Playlist") and self.items:
                self.start_task(lambda:self.play_track(self.items[self.selected]))
        elif key in (pygame.K_v, pygame.K_f) and self.section in ("Search","Favorites","Recently played") and self.items:
            self.toggle_favorite(self.items[self.selected])
        elif key==pygame.K_p and self.section in ("Search","Favorites","Recently played") and self.items:
            self.add_to_playlist(self.items[self.selected])
        elif key in (pygame.K_LEFT, pygame.K_z) and self.section=="Now Playing": self.player.seek(-10)
        elif key in (pygame.K_RIGHT, pygame.K_c) and self.section=="Now Playing": self.player.seek(10)
        elif key==pygame.K_r: self.start_task(self.load_section)
        elif key in (pygame.K_PLUS,pygame.K_EQUALS) and self.section!="Now Playing":
            self.player.set_volume(self.player.volume+5); self.message=f"Volume {self.player.volume}%"
    def run(self):
        print("BOOT: entering main event loop", flush=True)
        while self.running:
            for event in self.ui.events(): self.handle(event)
            self.ui.volume=self.player.volume
            self.ui.draw(self.section,self.items,self.selected,self.message,self.track,
                self.player.status(),None,self.message,self.search_text)
            self.ui.tick()
        self.player.stop(); self.ui.quit()
def main():
    try: App().run()
    except Exception as exc:
        log=os.path.expanduser("~/.local/state/soundcloud-cardputer/crash.log")
        os.makedirs(os.path.dirname(log),exist_ok=True)
        with open(log,"a",encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {type(exc).__name__}: {exc}\n")
        raise
if __name__=="__main__": main()
