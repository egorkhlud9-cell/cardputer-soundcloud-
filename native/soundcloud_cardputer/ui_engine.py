from __future__ import annotations
import glob, mmap, os, time
from types import SimpleNamespace
import pygame
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from evdev import InputDevice, ecodes

BG=(18,18,18); PANEL=(29,29,29); ORANGE=(255,85,0); WHITE=(245,245,245); MUTED=(160,160,160)
W,H=320,170

class UI:
    def __init__(self,size=(W,H)):
        self.width,self.height=size
        self.fb_path=self._find_fb()
        self.stride=self.width*2
        for p in ("/sys/class/graphics/fb0/stride","/sys/class/graphics/fb1/stride"):
            try:
                if os.path.realpath("/dev/fb0")==self.fb_path:
                    self.stride=int(open("/sys/class/graphics/fb0/stride").read().strip()); break
            except Exception: pass
        self.fb_fd=os.open(self.fb_path,os.O_RDWR|os.O_SYNC)
        self.fb=mmap.mmap(self.fb_fd,self.stride*self.height,mmap.MAP_SHARED,mmap.PROT_READ|mmap.PROT_WRITE)
        self.image=Image.new("RGB",(self.width,self.height),BG)
        self.drawctx=ImageDraw.Draw(self.image)
        self.font=self._font(17); self.small=self._font(13); self.big=self._font(21)
        self.device=self._find_keyboard()
        self.last_draw=0.0
        self._unblank()
        print(f"FB: {self.fb_path} {self.width}x{self.height} RGB565 stride={self.stride}",flush=True)
        print(f"INPUT: {self.device.path if self.device else 'no keyboard found'}",flush=True)

    def _find_fb(self):
        for i in range(4):
            try:
                name=open(f"/sys/class/graphics/fb{i}/name").read().lower()
                if "panel-mipi-dbi" in name or "st7789v_m5st" in name:
                    return f"/dev/fb{i}"
            except OSError: pass
        if os.path.exists("/dev/fb0"): return "/dev/fb0"
        raise RuntimeError("Cardputer LCD framebuffer not found")

    def _font(self,n):
        for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf","/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"):
            if os.path.exists(p): return ImageFont.truetype(p,n)
        return ImageFont.load_default()

    def _find_keyboard(self):
        for path in sorted(glob.glob("/dev/input/event*")):
            try:
                d=InputDevice(path); caps=d.capabilities().get(ecodes.EV_KEY,[])
                if ecodes.KEY_ENTER in caps and ecodes.KEY_UP in caps and ecodes.KEY_DOWN in caps:
                    return d
                d.close()
            except Exception: pass
        return None

    def _unblank(self):
        try:
            p=self.fb_path.replace("/dev/","/sys/class/graphics/")+"/blank"
            open(p,"w").write("0")
        except Exception: pass

    def _key_event(self,code):
        mapping={
            ecodes.KEY_UP:pygame.K_UP, ecodes.KEY_DOWN:pygame.K_DOWN,
            ecodes.KEY_LEFT:pygame.K_LEFT, ecodes.KEY_RIGHT:pygame.K_RIGHT,
            ecodes.KEY_ENTER:pygame.K_RETURN, ecodes.KEY_KPENTER:pygame.K_KP_ENTER,
            ecodes.KEY_ESC:pygame.K_ESCAPE, ecodes.KEY_BACKSPACE:pygame.K_BACKSPACE,
            ecodes.KEY_SPACE:pygame.K_SPACE, ecodes.KEY_F:pygame.K_f,
            ecodes.KEY_P:pygame.K_p, ecodes.KEY_R:pygame.K_r,
            ecodes.KEY_EQUAL:pygame.K_EQUALS, ecodes.KEY_KPPLUS:pygame.K_PLUS,
            ecodes.KEY_MINUS:pygame.K_MINUS, ecodes.KEY_KPMINUS:pygame.K_MINUS,
        }
        return mapping.get(code)

    def _unicode(self,code,shift):
        if ecodes.KEY_A <= code <= ecodes.KEY_Z:
            c=chr(ord("a")+code-ecodes.KEY_A); return c.upper() if shift else c
        if ecodes.KEY_1 <= code <= ecodes.KEY_9: return "123456789"[code-ecodes.KEY_1] if not shift else "!@#$%^&*("[code-ecodes.KEY_1]
        if code==ecodes.KEY_0: return ")" if shift else "0"
        if code==ecodes.KEY_SPACE: return " "
        if code in (ecodes.KEY_DOT,): return ">" if shift else "."
        if code==ecodes.KEY_COMMA: return "<" if shift else ","
        if code==ecodes.KEY_MINUS: return "_" if shift else "-"
        if code==ecodes.KEY_SLASH: return "?" if shift else "/"
        return ""

    def events(self):
        if not self.device: return []
        out=[]
        try:
            for e in self.device.read():
                if e.type!=ecodes.EV_KEY or e.value==0: continue
                key=self._key_event(e.code)
                shift=bool(self.device.active_keys() and any(k in self.device.active_keys() for k in (ecodes.KEY_LEFTSHIFT,ecodes.KEY_RIGHTSHIFT)))
                if key is not None:
                    out.append(SimpleNamespace(type=pygame.KEYDOWN,key=key,unicode=self._unicode(e.code,shift)))
                elif self._unicode(e.code,shift):
                    out.append(SimpleNamespace(type=pygame.KEYDOWN,key=0,unicode=self._unicode(e.code,shift)))
        except BlockingIOError: pass
        except OSError: self.device=None
        return out

    def text(self,value,x,y,color=WHITE,font=None,maxw=300):
        font=font or self.font; s=str(value).replace("\\n"," ")
        while s and self.drawctx.textbbox((0,0),s,font=font)[2]>maxw: s=s[:-1]
        self.drawctx.text((x,y),s,fill=color,font=font)

    def draw(self,section,items,selected,status,track,player_status,user=None,message="",search_text=""):
        d=self.drawctx; d.rectangle((0,0,W,H),fill=BG); d.rectangle((0,0,W,23),fill=PANEL)
        self.text("SOUNDCLOUD",6,2,ORANGE,self.big,140); self.text(section.upper(),164,5,MUTED,self.small,150)
        if section=="Search":
            d.rounded_rectangle((5,27,315,47),radius=3,fill=(38,38,38))
            self.text("> "+(search_text or "Type to search..."),10,29,WHITE,self.small,300); y0=52
        else: y0=27
        if section=="Now Playing":
            self.text(track.get("title","Nothing playing") if track else "Nothing playing",8,34,WHITE,self.big,300)
            self.text((track.get("user") or {}).get("username","") if track else "",8,57,MUTED,self.small,300)
            dur=player_status.get("duration",0) or 0; pos=player_status.get("time",0) or 0
            d.rounded_rectangle((8,88,312,93),radius=2,fill=(55,55,55))
            if dur: d.rounded_rectangle((8,88,8+int(304*min(1,pos/dur)),93),radius=2,fill=ORANGE)
            self.text(f"{int(pos)//60:02}:{int(pos)%60:02} / {int(dur)//60:02}:{int(dur)%60:02}",8,98,MUTED,self.small,120)
            self.text("ENTER/SPACE: pause   LEFT/RIGHT: seek",8,128,WHITE,self.small,300)
            self.text("UP/DOWN: volume   ESC: back",8,145,MUTED,self.small,300)
        else:
            visible=6 if section=="Search" else 7; start=max(0,selected-visible+1)
            for i,item in enumerate(items[start:start+visible]):
                idx=start+i; y=y0+i*17
                if idx==selected: d.rounded_rectangle((4,y-1,316,y+15),radius=2,fill=(49,36,28)); c=ORANGE
                else: c=WHITE
                if isinstance(item,dict):
                    title=item.get("title") or item.get("name") or "Untitled"
                    artist=(item.get("user") or {}).get("username","")
                    self.text(title+(" · "+artist if artist else ""),9,y,c,self.small,300)
                else: self.text(item,9,y,c,self.small,300)
            if not items: self.text(status or "No items",8,y0+8,MUTED,self.small,300)
            if section=="Search": self.text("ENTER search  F favorite  P playlist",8,145,MUTED,self.small,300)
            elif section in ("Favorites","Recently played","Playlist"): self.text("ENTER play  F favorite  P playlist",8,145,MUTED,self.small,300)
            elif section=="Settings": self.text("ENTER select   +/- volume",8,145,MUTED,self.small,300)
        if message:
            d.rectangle((0,155,W,170),fill=(45,35,25)); self.text(message,5,155,ORANGE,self.small,310)
        self._present()

    def _present(self):
        arr=np.asarray(self.image,dtype=np.uint8)
        r=(arr[:,:,0].astype(np.uint16)>>3)<<11
        g=(arr[:,:,1].astype(np.uint16)>>2)<<5
        b=arr[:,:,2].astype(np.uint16)>>3
        raw=(r|g|b).astype("<u2").tobytes()
        if self.stride==self.width*2:
            self.fb.seek(0); self.fb.write(raw)
        else:
            for y in range(self.height):
                self.fb.seek(y*self.stride); self.fb.write(raw[y*self.width*2:(y+1)*self.width*2])

    def tick(self):
        elapsed=time.monotonic()-self.last_draw
        if elapsed<1/25: time.sleep(1/25-elapsed)
        self.last_draw=time.monotonic()

    def quit(self):
        try: self.fb.seek(0); self.fb.write(b"\\x00"*(self.stride*self.height))
        except Exception: pass
        try: self.fb.close(); os.close(self.fb_fd)
        except Exception: pass
        if self.device:
            try: self.device.close()
            except Exception: pass
