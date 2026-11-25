from __future__ import annotations
import glob, mmap, os, select, time, math
from types import SimpleNamespace
import pygame
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from evdev import InputDevice, ecodes

W, H = 320, 170
BG = (7, 9, 15)
SURFACE = (15, 19, 29)
SURFACE_2 = (22, 27, 40)
LINE = (39, 47, 65)
ACCENT = (255, 112, 76)
ACCENT_2 = (173, 122, 255)
WHITE = (242, 245, 252)
MUTED = (126, 139, 160)
GREEN = (105, 222, 174)

class UI:
    def __init__(self, size=(W, H)):
        self.width, self.height = size
        self.fb_path = self._find_fb()
        self.stride = self._get_stride()
        self.fb_fd = os.open(self.fb_path, os.O_RDWR | os.O_SYNC)
        self.fb = mmap.mmap(self.fb_fd, self.stride * self.height, mmap.MAP_SHARED,
                            mmap.PROT_READ | mmap.PROT_WRITE)
        self.image = Image.new("RGB", (self.width, self.height), BG)
        self.drawctx = ImageDraw.Draw(self.image)
        self.font = self._font(12, True)
        self.body = self._font(10)
        self.small = self._font(9)
        self.tiny = self._font(8)
        self.hero = self._font(21, True)
        self.devices = self._open_keyboards()
        self.shift_down = False
        self.last_draw = 0.0
        self.anim_phase = 0.0
        self.last_input_log = 0.0
        self._unblank()
        print(f"FB: {self.fb_path} {self.width}x{self.height} RGB565 stride={self.stride}", flush=True)
        print("INPUT DEVICES: " + (", ".join(f"{d.path} [{d.name}]" for d in self.devices) or "NONE"), flush=True)

    def _find_fb(self):
        for i in range(4):
            try:
                name = open(f"/sys/class/graphics/fb{i}/name").read().lower()
                if "panel-mipi-dbi" in name or "st7789v_m5st" in name:
                    return f"/dev/fb{i}"
            except OSError:
                pass
        if os.path.exists("/dev/fb0"): return "/dev/fb0"
        raise RuntimeError("Cardputer LCD framebuffer not found")

    def _get_stride(self):
        try:
            i = int(self._find_fb().replace("/dev/fb", ""))
            return int(open(f"/sys/class/graphics/fb{i}/stride").read().strip())
        except Exception:
            return self.width * 2

    def _font(self, size, bold=False):
        names = (["DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf"] if bold else
                 ["DejaVuSans.ttf", "LiberationSans-Regular.ttf"])
        dirs = ["/usr/share/fonts/truetype/dejavu", "/usr/share/fonts/truetype/liberation2"]
        for directory in dirs:
            for name in names:
                path = os.path.join(directory, name)
                if os.path.exists(path): return ImageFont.truetype(path, size)
        return ImageFont.load_default()

    def _open_keyboards(self):
        found = []
        for path in sorted(glob.glob("/dev/input/event*")):
            try:
                dev = InputDevice(path)
                caps = dev.capabilities().get(ecodes.EV_KEY, [])
                if not caps:
                    dev.close(); continue
                os.set_blocking(dev.fd, False)
                found.append(dev)
                print(f"INPUT OPEN: {path} name={dev.name!r} key_count={len(caps)}", flush=True)
            except Exception as exc:
                print(f"INPUT SKIP: {path}: {type(exc).__name__}: {exc}", flush=True)
        return found

    def _unblank(self):
        try:
            index = self.fb_path.replace("/dev/fb", "")
            with open(f"/sys/class/graphics/fb{index}/blank", "w") as f: f.write("0")
        except Exception: pass

    def _key_event(self, code):
        mapping = {
            ecodes.KEY_UP: pygame.K_UP, ecodes.KEY_DOWN: pygame.K_DOWN,
            ecodes.KEY_LEFT: pygame.K_LEFT, ecodes.KEY_RIGHT: pygame.K_RIGHT,
            ecodes.KEY_ENTER: pygame.K_RETURN, ecodes.KEY_KPENTER: pygame.K_KP_ENTER,
            ecodes.KEY_ESC: pygame.K_ESCAPE, ecodes.KEY_BACKSPACE: pygame.K_BACKSPACE,
            ecodes.KEY_SPACE: pygame.K_SPACE, ecodes.KEY_Q: pygame.K_q, ecodes.KEY_F: pygame.K_f,
            ecodes.KEY_P: pygame.K_p, ecodes.KEY_R: pygame.K_r,
            ecodes.KEY_V: pygame.K_v, ecodes.KEY_A: pygame.K_a,
            ecodes.KEY_S: pygame.K_s, ecodes.KEY_D: pygame.K_d,
            ecodes.KEY_W: pygame.K_w, ecodes.KEY_X: pygame.K_x,
            ecodes.KEY_Z: pygame.K_z, ecodes.KEY_C: pygame.K_c,
            ecodes.KEY_EQUAL: pygame.K_EQUALS, ecodes.KEY_KPPLUS: pygame.K_PLUS,
            ecodes.KEY_MINUS: pygame.K_MINUS, ecodes.KEY_KPMINUS: pygame.K_MINUS,
            ecodes.KEY_TAB: pygame.K_TAB,
        }
        return mapping.get(code)

    def _unicode(self, code):
        letters = [ecodes.KEY_Q,ecodes.KEY_W,ecodes.KEY_E,ecodes.KEY_R,ecodes.KEY_T,
                   ecodes.KEY_Y,ecodes.KEY_U,ecodes.KEY_I,ecodes.KEY_O,ecodes.KEY_P,
                   ecodes.KEY_A,ecodes.KEY_S,ecodes.KEY_D,ecodes.KEY_F,ecodes.KEY_G,
                   ecodes.KEY_H,ecodes.KEY_J,ecodes.KEY_K,ecodes.KEY_L,
                   ecodes.KEY_Z,ecodes.KEY_X,ecodes.KEY_C,ecodes.KEY_V,ecodes.KEY_B,
                   ecodes.KEY_N,ecodes.KEY_M]
        chars = "qwertyuiopasdfghjklzxcvbnm"
        if code in letters:
            char = chars[letters.index(code)]
            return char.upper() if self.shift_down else char
        digits = [ecodes.KEY_1,ecodes.KEY_2,ecodes.KEY_3,ecodes.KEY_4,ecodes.KEY_5,
                  ecodes.KEY_6,ecodes.KEY_7,ecodes.KEY_8,ecodes.KEY_9]
        if code in digits:
            plain, shifted = "123456789", "!@#$%^&*("
            return (shifted if self.shift_down else plain)[digits.index(code)]
        if code == ecodes.KEY_0: return ")" if self.shift_down else "0"
        if code == ecodes.KEY_SPACE: return " "
        if code == ecodes.KEY_DOT: return ">" if self.shift_down else "."
        if code == ecodes.KEY_COMMA: return "<" if self.shift_down else ","
        if code == ecodes.KEY_MINUS: return "_" if self.shift_down else "-"
        if code == ecodes.KEY_SLASH: return "?" if self.shift_down else "/"
        if code == ecodes.KEY_APOSTROPHE: return '"' if self.shift_down else "'"
        return ""

    def events(self):
        out = []
        if not self.devices: return out
        try: ready, _, _ = select.select([d.fd for d in self.devices], [], [], 0)
        except (OSError, ValueError): return out
        for dev in self.devices:
            if dev.fd not in ready: continue
            try:
                while True:
                    try: event = dev.read_one()
                    except BlockingIOError: break
                    if event is None: break
                    if event.type != ecodes.EV_KEY: continue
                    if event.code in (ecodes.KEY_LEFTSHIFT, ecodes.KEY_RIGHTSHIFT):
                        self.shift_down = event.value != 0; continue
                    if event.value == 0: continue
                    key = self._key_event(event.code)
                    char = self._unicode(event.code)
                    if key is not None or char:
                        out.append(SimpleNamespace(type=pygame.KEYDOWN, key=key if key is not None else 0, unicode=char))
                        now = time.monotonic()
                        if now - self.last_input_log > 2:
                            print(f"INPUT KEY: {dev.path} code={event.code} key={key} char={char!r}", flush=True)
                            self.last_input_log = now
            except OSError as exc: print(f"INPUT READ ERROR: {dev.path}: {exc}", flush=True)
        return out

    def _text(self, value, x, y, font=None, fill=WHITE, maxw=None):
        font = font or self.body
        value = str(value).replace("\n", " ")
        if maxw:
            while value and self.drawctx.textbbox((0, 0), value, font=font)[2] > maxw:
                value = value[:-1]
        self.drawctx.text((x, y), value, font=font, fill=fill)

    def _background(self):
        # Draw a restrained halo with a handful of shapes; avoid per-pixel work
        # in the 24 FPS render loop on the small ARM board.
        self.image.paste(BG, (0, 0, W, H))
        self.drawctx = ImageDraw.Draw(self.image)
        for i in range(8):
            inset = i * 7
            self.drawctx.ellipse((224-inset, -58-inset, 370+inset, 88+inset),
                                 outline=(12+i, 14+i, 25+i*2), width=5)
        for x in range(0, W, 32):
            self.drawctx.line((x, 25, x, 150), fill=(11, 14, 22), width=1)

    def _brand(self, section, right="ONLINE"):
        d = self.drawctx
        d.rectangle((0, 0, W, 25), fill=(10, 13, 21))
        d.line((0, 24, W, 24), fill=(36, 43, 59), width=1)
        d.rounded_rectangle((8, 5, 25, 21), radius=5, fill=ACCENT)
        d.polygon([(14, 9), (14, 17), (20, 13)], fill=(17, 19, 27))
        self._text("A U R O R A", 32, 7, self.font, WHITE)
        self._text(section.upper(), 153, 9, self.tiny, MUTED, 65)
        d.ellipse((277, 10, 283, 16), fill=GREEN if self.devices else ACCENT_2)
        self._text(right, 288, 9, self.tiny, MUTED, 27)

    def _footer(self, left="F / X MOVE", right="ENTER SELECT"):
        d = self.drawctx
        d.line((8, 151, 312, 151), fill=(37, 44, 59), width=1)
        self._text(left, 9, 157, self.tiny, MUTED, 145)
        self._text(right, 171, 157, self.tiny, MUTED, 140)

    def _draw_rows(self, items, selected, y0, visible):
        d = self.drawctx
        start = max(0, min(selected - visible + 1, max(0, len(items) - visible)))
        for offset, item in enumerate(items[start:start + visible]):
            idx = start + offset; y = y0 + offset * 16
            active = idx == selected
            if active:
                d.rounded_rectangle((8, y, 312, y+14), radius=4, fill=(39, 31, 42), outline=(164, 94, 94), width=1)
                d.rounded_rectangle((8, y+3, 11, y+11), radius=1, fill=ACCENT)
            else:
                d.line((14, y+14, 306, y+14), fill=(27, 33, 46), width=1)
            title, subtitle = item, ""
            if isinstance(item, dict):
                title = item.get("title") or item.get("name") or "Untitled track"
                subtitle = (item.get("user") or {}).get("username", "")
                if not subtitle and item.get("tracks") is not None: subtitle = f"{len(item.get('tracks', []))} tracks"
            self._text(title, 17 if active else 13, y+2, self.small, WHITE if active else (187, 197, 214), 220)
            if subtitle: self._text(subtitle, 245, y+3, self.tiny, MUTED, 60)

    def draw(self, section, items, selected, status, track, player_status, user=None, message="", search_text=""):
        self._background(); d = self.drawctx
        self._brand(section, "KEYS OK" if self.devices else "NO KEYS")
        if section == "Home":
            self._text("SOUND, IN.", 11, 34, self.hero, WHITE)
            self._text("Your next favourite starts here.", 12, 59, self.small, MUTED)
            tiles = [("01", "DISCOVER"), ("02", "LIBRARY"), ("03", "PLAYLISTS"),
                     ("04", "RECENT"), ("05", "PLAYER"), ("06", "SETTINGS")]
            for i, (num, label) in enumerate(tiles):
                x = 10 + (i % 2) * 153
                y = 82 + (i // 2) * 21
                active = i == selected
                d.rounded_rectangle((x, y, x+146, y+18), radius=5,
                    fill=(43, 31, 43) if active else (17, 22, 33),
                    outline=(164, 94, 108) if active else (43, 52, 70), width=1)
                self._text(num, x+7, y+4, self.tiny, ACCENT_2 if active else MUTED)
                self._text(label, x+28, y+4, self.tiny, WHITE if active else (177, 188, 207))
            self._footer("F / X MOVE", "ENTER OPEN")
        elif section == "Search":
            self._text("FIND SOMETHING GOOD", 10, 32, self.font, WHITE)
            d.rounded_rectangle((9, 52, 311, 74), radius=6, fill=(18, 23, 35), outline=(112, 83, 92), width=1)
            self._text("⌕", 16, 55, self.font, ACCENT)
            self._text(search_text or "Artist, track, mood...", 35, 58, self.small, WHITE if search_text else MUTED, 266)
            self._text(f"{len(items):02d} MATCHES", 11, 79, self.tiny, ACCENT_2)
            self._draw_rows(items, selected, 91, 3)
            self._footer("TYPE TO SEARCH  DEL ERASE", "ENTER SEARCH / PLAY")
        elif section == "Now Playing":
            self._draw_player(track, player_status)
            self._footer("Z / C SEEK   A / D VOL", "Q PLAY / PAUSE")
        else:
            title = {"Favorites":"SAVED TRACKS", "Playlists":"YOUR COLLECTION",
                     "Playlist":"PLAYLIST", "Recently played":"LISTENING HISTORY",
                     "Settings":"PLAYER SETTINGS", "My Tracks":"MY TRACKS"}.get(section, section.upper())
            self._text(title, 10, 33, self.font, WHITE)
            self._text(f"{len(items):02d} ITEMS", 11, 51, self.tiny, ACCENT_2)
            if section == "Settings":
                rows = [f"Output volume     {getattr(self, 'volume', 70)}%",
                        "Clear listening history", "About AURORA", "Back"]
                self._draw_rows(rows, selected, 64, 4)
            else: self._draw_rows(items, selected, 64, 4)
            self._footer("F / X MOVE   V SAVE", "ENTER OPEN")
        if message and section not in ("Home", "Now Playing"):
            d.rounded_rectangle((8, 137, 312, 148), radius=4, fill=(35, 25, 31), outline=(75, 49, 57), width=1)
            self._text(message, 13, 139, self.tiny, (255, 170, 148), 292)
        self._present()

    def _draw_player(self, track, state):
        d = self.drawctx; phase = self.anim_phase
        d.rounded_rectangle((8, 31, 312, 145), radius=10, fill=(16, 21, 33), outline=(49, 59, 79), width=1)
        cx, cy = 48, 79
        d.ellipse((cx-31, cy-31, cx+31, cy+31), fill=(26, 24, 39), outline=(99, 73, 105), width=2)
        for radius in (25, 20, 15):
            d.ellipse((cx-radius, cy-radius, cx+radius, cy+radius), outline=(72, 57, 83), width=1)
        d.ellipse((cx-8, cy-8, cx+8, cy+8), fill=ACCENT)
        d.ellipse((cx-2, cy-2, cx+2, cy+2), fill=BG)
        angle = phase * 1.7
        px, py = cx + int(25*math.cos(angle)), cy + int(25*math.sin(angle))
        d.ellipse((px-2, py-2, px+2, py+2), fill=(211, 170, 255))
        title = (track or {}).get("title", "Nothing playing") if isinstance(track, dict) else "Nothing playing"
        artist = ((track or {}).get("user") or {}).get("username", "") if isinstance(track, dict) else ""
        self._text(title, 89, 43, self.font, WHITE, 211)
        self._text(artist or "SOUNDCLOUD  /  PUBLIC", 90, 62, self.tiny, MUTED, 210)
        for i in range(27):
            wave = (math.sin(phase*2.2+i*.62)+1)*.5
            wave2 = (math.sin(phase*1.1-i*.31)+1)*.5
            height = 3 + int(9*(.25*wave+.75*wave2))
            x = 91+i*7
            d.rounded_rectangle((x, 91-height, x+3, 92), radius=1,
                                fill=ACCENT if i%4==0 else (104, 75, 111))
        pos = float(state.get("time", 0) or 0); dur = float(state.get("duration", 0) or 0)
        d.rounded_rectangle((18, 108, 302, 113), radius=3, fill=(48, 55, 72))
        if dur > 0:
            progress = max(0, min(1, pos/dur)); end = 18+int(284*progress)
            d.rounded_rectangle((18, 108, end, 113), radius=3, fill=ACCENT)
            d.ellipse((end-4, 106, end+4, 115), fill=WHITE)
        self._text(f"{int(pos)//60:02}:{int(pos)%60:02}", 18, 117, self.tiny, MUTED)
        self._text(f"{int(dur)//60:02}:{int(dur)%60:02}", 268, 117, self.tiny, MUTED)
        self._text(f"VOL {int(getattr(self,'volume',70)):02d}%", 125, 117, self.tiny, ACCENT_2)
        self._pill((9, 130, 101, 148), "Z   -10 SEC")
        self._pill((114, 130, 206, 148), "Q  PLAY / PAUSE", True)
        self._pill((219, 130, 311, 148), "C   +10 SEC")

    def _pill(self, box, label, selected=False):
        d = self.drawctx
        d.rounded_rectangle(box, radius=5, fill=(45, 31, 43) if selected else (24, 30, 44),
                            outline=(135, 82, 100) if selected else (53, 63, 83), width=1)
        self._text(label, box[0]+7, box[1]+5, self.tiny, ACCENT if selected else WHITE,
                   box[2]-box[0]-12)

    def _present(self):
        arr = np.asarray(self.image, dtype=np.uint8)
        r = (arr[:,:,0].astype(np.uint16)>>3)<<11
        g = (arr[:,:,1].astype(np.uint16)>>2)<<5
        b = arr[:,:,2].astype(np.uint16)>>3
        raw = (r|g|b).astype("<u2").tobytes()
        if self.stride == self.width*2:
            self.fb.seek(0); self.fb.write(raw)
        else:
            for y in range(self.height):
                self.fb.seek(y*self.stride)
                self.fb.write(raw[y*self.width*2:(y+1)*self.width*2])

    def tick(self):
        elapsed = time.monotonic()-self.last_draw
        if elapsed < 1/24: time.sleep(1/24-elapsed)
        self.last_draw = time.monotonic()
        self.anim_phase = (self.anim_phase+.055)%1000

    def quit(self):
        try: self.fb.seek(0); self.fb.write(b"\x00"*(self.stride*self.height))
        except Exception: pass
        try: self.fb.close(); os.close(self.fb_fd)
        except Exception: pass
        for dev in self.devices:
            try: dev.close()
            except Exception: pass
