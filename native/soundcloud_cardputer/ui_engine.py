from __future__ import annotations
import pygame
BG=(18,18,18); PANEL=(29,29,29); ORANGE=(255,85,0); WHITE=(245,245,245); MUTED=(160,160,160)
class UI:
    def __init__(self,size=(320,170)):
        pygame.init(); pygame.font.init()
        self.screen=pygame.display.set_mode(size)
        pygame.display.set_caption("SoundCloud")
        self.font=pygame.font.Font(None,18); self.small=pygame.font.Font(None,14); self.big=pygame.font.Font(None,23)
        self.clock=pygame.time.Clock()
    def text(self,surface,value,x,y,color=WHITE,font=None,maxw=300):
        font=font or self.font; s=str(value).replace("\n"," ")
        while s and font.size(s)[0]>maxw: s=s[:-1]
        surface.blit(font.render(s,True,color),(x,y))
    def draw(self,section,items,selected,status,track,player_status,user=None,message="",search_text=""):
        s=self.screen; s.fill(BG); pygame.draw.rect(s,PANEL,(0,0,320,22))
        self.text(s,"SOUNDCLOUD",6,4,ORANGE,self.big,140); self.text(s,section.upper(),164,6,MUTED,self.small,150)
        if section=="Search":
            pygame.draw.rect(s,(38,38,38),(5,27,310,20),border_radius=3)
            self.text(s,"> "+(search_text or "Type to search…"),10,30,WHITE,self.small,300); y0=52
        else: y0=27
        if section=="Now Playing":
            self.text(s,track.get("title","Nothing playing") if track else "Nothing playing",8,35,WHITE,self.big,300)
            self.text(s,(track.get("user") or {}).get("username","") if track else "",8,57,MUTED,self.small,300)
            dur=player_status.get("duration",0) or 0; pos=player_status.get("time",0) or 0
            pygame.draw.rect(s,(55,55,55),(8,88,304,5),border_radius=2)
            if dur: pygame.draw.rect(s,ORANGE,(8,88,int(304*min(1,pos/dur)),5),border_radius=2)
            self.text(s,f"{int(pos)//60:02}:{int(pos)%60:02} / {int(dur)//60:02}:{int(dur)%60:02}",8,98,MUTED,self.small,120)
            self.text(s,"ENTER/SPACE: pause   LEFT/RIGHT: seek",8,128,WHITE,self.small,300)
            self.text(s,"UP/DOWN: volume   ESC: back",8,145,MUTED,self.small,300)
        else:
            visible=6 if section=="Search" else 7
            start=max(0,selected-visible+1)
            for i,item in enumerate(items[start:start+visible]):
                idx=start+i; y=y0+i*17
                if idx==selected: pygame.draw.rect(s,(49,36,28),(4,y-1,312,16),border_radius=2); c=ORANGE
                else: c=WHITE
                if isinstance(item,dict):
                    title=item.get("title") or item.get("name") or "Untitled"
                    artist=(item.get("user") or {}).get("username","")
                    self.text(s,title+(" · "+artist if artist else ""),9,y+1,c,self.small,300)
                else: self.text(s,item,9,y+1,c,self.small,300)
            if not items: self.text(s,status or "No items",8,y0+8,MUTED,self.small,300)
            if section=="Search": self.text(s,"ENTER search  F favorite  P playlist",8,145,MUTED,self.small,300)
            elif section in ("Favorites","Recently played","Playlist"): self.text(s,"ENTER play  F favorite  P playlist",8,145,MUTED,self.small,300)
            elif section=="Settings": self.text(s,"ENTER select   +/- volume",8,145,MUTED,self.small,300)
        if message:
            pygame.draw.rect(s,(45,35,25),(0,155,320,15)); self.text(s,message,5,157,ORANGE,self.small,310)
        pygame.display.flip()
    def tick(self): self.clock.tick(30)
    def quit(self): pygame.quit()
