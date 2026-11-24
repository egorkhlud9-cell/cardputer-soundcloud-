from __future__ import annotations
import os, subprocess, time
import pygame
from .storage import load_config, save_config, load_library, save_library
from .soundcloud_api import SoundCloudClient, SoundCloudError
from .audio_player import AudioPlayer, AudioError
from .ui_engine import UI

SECTIONS=["Home","Search","Favorites","Playlists","My Tracks","Now Playing","Settings"]
def track_url(track):
    return track.get("permalink_url") or track.get("uri") or ""

class App:
    def __init__(self):
        self.config=load_config(); self.library=load_library()
        self.ui=UI(); self.player=AudioPlayer(); self.client=SoundCloudClient(self.config)
        self.section=self.config.get("last_section","Home"); self.section=self.section if self.section in SECTIONS else "Home"
        self.items=[]; self.selected=0; self.track=None; self.user=None; self.message="Ready"
        self.search_text=""; self.busy=False; self.running=True
        self.refresh_local()
        if self.config.get("access_token"): self.start_task(self.load_profile)
    def refresh_local(self):
        self.library.setdefault("favorites",[]); self.library.setdefault("playlists",[]); self.library.setdefault("history",[])
    def start_task(self, fn):
        if self.busy: return
        self.busy=True; self.message="Working…"
        def run():
            try: fn()
            except Exception as exc: self.message=str(exc)[:90]
            finally: self.busy=False
        import threading
        threading.Thread(target=run,daemon=True).start()
    def load_profile(self):
        self.user=self.client.me(); self.message="Connected: "+self.user.get("username","SoundCloud")
    def load_section(self):
        if self.section=="Home": self.items=["Search tracks","Your favorites","Your playlists","Your uploads","Now playing","Settings"]
        elif self.section=="Favorites":
            self.items=self.client.likes() if self.config.get("access_token") else self.library["favorites"]
        elif self.section=="Playlists":
            self.items=self.client.playlists() if self.config.get("access_token") else self.library["playlists"]
        elif self.section=="My Tracks": self.items=self.client.my_tracks() if self.config.get("access_token") else self.library.get("my_tracks",[])
        elif self.section=="Search": self.items=[]
        elif self.section=="Settings":
            self.items=["Connect / reconnect SoundCloud","Sync account library","Set Client ID","Set Client Secret","Set redirect URI","Disconnect account","Back"]
        self.selected=0
    def navigate(self, section):
        self.section=section; self.config["last_section"]=section; save_config(self.config); self.load_section()
    def play_track(self, track):
        url=self.client.stream_url(track) if self.config.get("access_token") else None
        if not url:
            page=track_url(track)
            if not page: raise AudioError("Track has no public URL.")
            import shutil
            if not shutil.which("yt-dlp"): raise AudioError("yt-dlp is not installed.")
            result=subprocess.run(["yt-dlp","-g","-f","bestaudio/best",page],capture_output=True,text=True,timeout=45)
            if result.returncode: raise AudioError(result.stderr[-180:] or "Could not resolve stream.")
            url=result.stdout.strip().splitlines()[0]
        self.player.play(url,track.get("title",""))
        self.track=track; self.navigate("Now Playing")
        self.config["last_track"]=track; save_config(self.config)
        self.library["history"]=[track]+self.library.get("history",[])[:49]; save_library(self.library)
    def sync(self):
        if not self.config.get("access_token"): raise SoundCloudError("Connect SoundCloud first.")
        likes=self.client.likes(); playlists=self.client.playlists(); uploads=self.client.my_tracks()
        self.library["favorites"]=likes; self.library["playlists"]=playlists; self.library["my_tracks"]=uploads
        self.library["synced_at"]=int(time.time()); save_library(self.library)
        if self.section=="Favorites": self.items=likes
        elif self.section=="Playlists": self.items=playlists
        elif self.section=="My Tracks": self.items=uploads
        self.message=f"Synced {len(likes)} likes, {len(playlists)} playlists, {len(uploads)} uploads"
    def login(self):
        self.message="Approve in external browser…"
        self.user=self.client.login(); self.message="Connected as "+self.user.get("username","user")
        self.sync()
    def edit_setting(self, idx):
        labels=["Client ID","Client Secret","Redirect URI"]
        key=["client_id","client_secret","redirect_uri"][idx]
        value=self.config.get(key,"")
        self.message="Type "+labels[idx]+":"
        pygame.key.start_text_input()
        editing=True
        while editing and self.running:
            for e in pygame.event.get():
                if e.type==pygame.QUIT: self.running=False; editing=False
                elif e.type==pygame.KEYDOWN:
                    if e.key==pygame.K_RETURN: editing=False
                    elif e.key==pygame.K_ESCAPE: editing=False
                    elif e.key==pygame.K_BACKSPACE: value=value[:-1]
                    elif e.unicode and e.unicode.isprintable(): value+=e.unicode
            shown=("•"*len(value)) if idx==1 else value
            self.ui.draw("Settings",self.items,self.selected,self.message,self.track,self.player.status(),self.user,self.message,shown)
            self.ui.tick()
        pygame.key.stop_text_input()
        if value.strip(): self.config[key]=value.strip(); save_config(self.config)
        self.message="Saved locally (owner-only file permissions)"
    def activate(self):
        if self.section=="Home":
            target=["Search","Favorites","Playlists","My Tracks","Now Playing","Settings"][self.selected]
            self.navigate(target)
        elif self.section=="Settings":
            if self.selected==0: self.start_task(self.login)
            elif self.selected==1: self.start_task(self.sync)
            elif self.selected in (2,3,4): self.edit_setting(self.selected-2)
            elif self.selected==5:
                self.config.update({"access_token":"","refresh_token":"","expires_at":0}); save_config(self.config); self.user=None; self.message="Disconnected locally"
            elif self.selected==6: self.navigate("Home")
        elif self.section=="Search":
            if self.items and self.selected<len(self.items): self.start_task(lambda:self.play_track(self.items[self.selected]))
        elif self.section=="Playlists":
            if self.items:
                playlist=self.items[self.selected]
                self.start_task(lambda:self.show_playlist(playlist))
        elif self.section in ("Favorites","My Tracks","Playlist"):
            if self.items and self.selected<len(self.items): self.start_task(lambda:self.play_track(self.items[self.selected]))
        elif self.section=="Now Playing": self.player.toggle()
    def show_playlist(self, playlist):
        self.items=self.client.playlist_tracks(playlist); self.section="Playlist"; self.selected=0; self.message="Playlist tracks"
    def search(self):
        if self.config.get("access_token"):
            self.items=self.client.search_tracks(self.search_text)
        else:
            import shutil
            if not shutil.which("yt-dlp"): raise SoundCloudError("Connect SoundCloud or install yt-dlp for public search.")
            result=subprocess.run(["yt-dlp","--flat-playlist","-J","scsearch10:"+self.search_text],capture_output=True,text=True,timeout=60)
            if result.returncode: raise SoundCloudError(result.stderr[-160:] or "Public search failed.")
            data=__import__("json").loads(result.stdout)
            self.items=[{"title":x.get("title","Untitled"),"permalink_url":x.get("url") or x.get("webpage_url"),"user":{"username":x.get("uploader","")}} for x in data.get("entries",[]) if x]
        self.selected=0; self.message=f"{len(self.items)} results"
    def handle(self, event):
        if event.type==pygame.QUIT: self.running=False
        if event.type==pygame.KEYDOWN:
            if self.section=="Search" and event.key==pygame.K_BACKSPACE:
                self.search_text=self.search_text[:-1]; return
            if self.section=="Search" and event.key==pygame.K_RETURN:
                self.start_task(self.search); return
            if self.section=="Search" and event.unicode and event.unicode.isprintable() and event.key not in (pygame.K_ESCAPE,):
                self.search_text+=event.unicode; return
            if event.key in (pygame.K_ESCAPE,pygame.K_BACKSPACE):
                if self.section=="Now Playing": self.navigate("Home")
                elif self.section=="Playlist": self.navigate("Playlists")
                elif self.section!="Home": self.navigate("Home")
                else: self.running=False
            elif event.key in (pygame.K_UP,pygame.K_k): self.selected=max(0,self.selected-1)
            elif event.key in (pygame.K_DOWN,pygame.K_j): self.selected=min(max(0,len(self.items)-1),self.selected+1)
            elif event.key in (pygame.K_RETURN,pygame.K_KP_ENTER): self.activate()
            elif event.key==pygame.K_SPACE:
                if self.section=="Now Playing": self.player.toggle()
                elif self.items and isinstance(self.items[self.selected],dict): self.start_task(lambda:self.play_track(self.items[self.selected]))
            elif event.key==pygame.K_LEFT and self.section=="Now Playing": self.player.seek(-10)
            elif event.key==pygame.K_RIGHT and self.section=="Now Playing": self.player.seek(10)
            elif event.key in (pygame.K_PLUS,pygame.K_EQUALS): self.player.set_volume(self.player.volume+5)
            elif event.key==pygame.K_MINUS: self.player.set_volume(self.player.volume-5)
            elif event.key==pygame.K_r: self.start_task(self.load_section)
            elif event.key==pygame.K_s and self.section=="Settings": self.start_task(self.sync)
            elif event.key==pygame.K_c and self.section=="Settings": self.start_task(self.login)
    def run(self):
        self.load_section()
        while self.running:
            for event in pygame.event.get(): self.handle(event)
            self.ui.draw(self.section,self.items,self.selected,self.message,self.track,self.player.status(),self.user,self.message,self.search_text)
            self.ui.tick()
        self.player.stop(); self.ui.quit()
def main():
    os.environ.setdefault("SDL_VIDEO_WINDOW_POS","0,0")
    App().run()
if __name__=="__main__": main()
