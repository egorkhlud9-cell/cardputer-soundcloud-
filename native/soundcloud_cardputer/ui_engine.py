from __future__ import annotations
import glob, mmap, os, select, time
from types import SimpleNamespace
import pygame
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from evdev import InputDevice, ecodes

W, H = 320, 170
BG = (11, 12, 15)
SURFACE = (20, 22, 27)
SURFACE_2 = (29, 32, 39)
LINE = (43, 47, 56)
ACCENT = (255, 91, 36)
ACCENT_SOFT = (62, 34, 27)
WHITE = (244, 245, 247)
MUTED = (139, 146, 158)
GREEN = (112, 205, 151)

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
        self.hero = self._font(19, True)
        self.devices = self._open_keyboards()
        self.shift_down = False
        self.last_draw = 0.0
        self.last_input_log = 0.0
        self._unblank()
        print(f"FB: {self.fb_path} {self.width}x{self.height} RGB565 stride={self.stride}", flush=True)
        print("INPUT DEVICES: " + (", ".join(f"{d.path} [{d.name}]" for d in self.devices) or "NONE - check /dev/input permissions"), flush=True)

    def _find_fb(self):
        for i in range(4):
            try:
                name = open(f"/sys/class/graphics/fb{i}/name").read().lower()
                if "panel-mipi-dbi" in name or "st7789v_m5st" in name:
                    return f"/dev/fb{i}"
            except OSError:
                pass
        if os.path.exists("/dev/fb0"):
            return "/dev/fb0"
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
                if os.path.exists(path):
                    return ImageFont.truetype(path, size)
        return ImageFont.load_default()

    def _open_keyboards(self):
        found = []
        for path in sorted(glob.glob("/dev/input/event*")):
            try:
                dev = InputDevice(path)
                caps = dev.capabilities().get(ecodes.EV_KEY, [])
                if not caps:
                    dev.close()
                    continue
                os.set_blocking(dev.fd, False)
                found.append(dev)
                print(f"INPUT OPEN: {path} name={dev.name!r} key_count={len(caps)}", flush=True)
            except Exception as exc:
                print(f"INPUT SKIP: {path}: {type(exc).__name__}: {exc}", flush=True)
        return found

    def _unblank(self):
        try:
            index = self.fb_path.replace("/dev/fb", "")
            with open(f"/sys/class/graphics/fb{index}/blank", "w") as f:
                f.write("0")
        except Exception:
            pass

    def _key_event(self, code):
        mapping = {
            ecodes.KEY_UP: pygame.K_UP, ecodes.KEY_DOWN: pygame.K_DOWN,
            ecodes.KEY_LEFT: pygame.K_LEFT, ecodes.KEY_RIGHT: pygame.K_RIGHT,
            ecodes.KEY_ENTER: pygame.K_RETURN, ecodes.KEY_KPENTER: pygame.K_KP_ENTER,
            ecodes.KEY_ESC: pygame.K_ESCAPE, ecodes.KEY_BACKSPACE: pygame.K_BACKSPACE,
            ecodes.KEY_SPACE: pygame.K_SPACE, ecodes.KEY_F: pygame.K_f,
            ecodes.KEY_P: pygame.K_p, ecodes.KEY_R: pygame.K_r,
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
        if not self.devices:
            return out
        try:
            ready, _, _ = select.select([d.fd for d in self.devices], [], [], 0)
        except (OSError, ValueError):
            return out
        for dev in self.devices:
            if dev.fd not in ready:
                continue
            try:
                while True:
                    try:
                        event = dev.read_one()
                    except BlockingIOError:
                        break
                    if event is None:
                        break
                    if event.type != ecodes.EV_KEY:
                        continue
                    if event.code in (ecodes.KEY_LEFTSHIFT, ecodes.KEY_RIGHTSHIFT):
                        self.shift_down = event.value != 0
                        continue
                    if event.value == 0:
                        continue
                    key = self._key_event(event.code)
                    char = self._unicode(event.code)
                    if key is not None or char:
                        out.append(SimpleNamespace(type=pygame.KEYDOWN, key=key if key is not None else 0, unicode=char))
                        now = time.monotonic()
                        if now - self.last_input_log > 2:
                            print(f"INPUT KEY: {dev.path} code={event.code} key={key} char={char!r}", flush=True)
                            self.last_input_log = now
            except OSError as exc:
                print(f"INPUT READ ERROR: {dev.path}: {exc}", flush=True)
        return out

    def _text(self, value, x, y, font=None, fill=WHITE, maxw=None):
        font = font or self.body
        value = str(value).replace("\n", " ")
        if maxw:
            while value and self.drawctx.textbbox((0, 0), value, font=font)[2] > maxw:
                value = value[:-1]
        self.drawctx.text((x, y), value, font=font, fill=fill)

    def _pill(self, box, label, selected=False):
        d = self.drawctx
        d.rounded_rectangle(box, radius=6, fill=ACCENT_SOFT if selected else SURFACE_2,
                            outline=ACCENT if selected else LINE, width=1)
        self._text(label, box[0] + 7, box[1] + 5, self.small, ACCENT if selected else WHITE,
                   box[2] - box[0] - 12)

    def _header(self, section, right="PUBLIC"):
        d = self.drawctx
        d.rectangle((0, 0, W, 25), fill=SURFACE)
        d.rounded_rectangle((7, 6, 19, 18), radius=4, fill=ACCENT)
        d.polygon([(11, 9), (11, 15), (16, 12)], fill=BG)
        self._text("SOUND", 25, 5, self.font, WHITE)
        self._text("CLOUD", 67, 5, self.font, ACCENT)
        self._text(section.upper(), 153, 8, self.tiny, MUTED, 90)
        d.rounded_rectangle((263, 7, 313, 19), radius=6, fill=(28, 45, 38))
        self._text(right, 273, 9, self.tiny, GREEN, 38)

    def _footer(self, left="↑↓ MOVE", right="ENTER SELECT"):
        d = self.drawctx
        d.line((7, 151, 313, 151), fill=LINE, width=1)
        self._text(left, 9, 157, self.tiny, MUTED, 140)
        self._text(right, 183, 157, self.tiny, MUTED, 128)

    def draw(self, section, items, selected, status, track, player_status, user=None, message="", search_text=""):
        self.image.paste(BG, (0, 0))
        self.drawctx = ImageDraw.Draw(self.image)
        d = self.drawctx
        self._header(section, "INPUT OK" if self.devices else "NO KEYS")
        if section == "Home":
            self._text("YOUR SOUNDTRACK.", 9, 31, self.hero, WHITE)
            self._text("Discover and play. No login required.", 10, 54, self.small, MUTED)
            tiles = [("01", "DISCOVER"), ("02", "FAVORITES"), ("03", "PLAYLISTS"),
                     ("04", "RECENT"), ("05", "PLAYER"), ("06", "SETTINGS")]
            for i, (num, label) in enumerate(tiles):
                col, row = i % 2, i // 2
                x, y = 8 + col * 155, 72 + row * 24
                d.rounded_rectangle((x, y, x + 148, y + 20), radius=5,
                                    fill=ACCENT_SOFT if i == selected else SURFACE,
                                    outline=ACCENT if i == selected else LINE, width=1)
                self._text(num, x + 7, y + 5, self.tiny, ACCENT)
                self._text(label, x + 27, y + 4, self.small, WHITE if i == selected else MUTED)
            self._footer("↑↓ MOVE  ENTER OPEN", "R REFRESH")
        elif section == "Search":
            self._text("FIND YOUR NEXT TRACK", 9, 31, self.font, WHITE)
            d.rounded_rectangle((8, 50, 312, 70), radius=5, fill=SURFACE_2, outline=ACCENT, width=1)
            self._text(">", 15, 53, self.font, ACCENT)
            self._text(search_text or "Type a track or artist...", 31, 55, self.small,
                       WHITE if search_text else MUTED, 270)
            self._text(f"{len(items)} RESULTS", 10, 74, self.tiny, MUTED)
            self._draw_rows(items, selected, 86, 3)
            self._footer("TYPE TO SEARCH  BACKSPACE", "ENTER SEARCH / PLAY")
        elif section == "Now Playing":
            self._draw_player(track, player_status)
            self._footer("←→ SEEK  ↑↓ VOLUME", "SPACE PAUSE  ESC BACK")
        else:
            title = {"Favorites":"YOUR FAVORITES", "Playlists":"YOUR PLAYLISTS",
                     "Playlist":"PLAYLIST TRACKS", "Recently played":"RECENTLY PLAYED",
                     "Settings":"PREFERENCES", "My Tracks":"MY TRACKS"}.get(section, section.upper())
            self._text(title, 9, 31, self.font, WHITE)
            self._text(f"{len(items)} ITEMS", 10, 49, self.tiny, MUTED)
            if section == "Settings":
                rows = [f"Playback volume     {getattr(self, 'volume', 70)}%",
                        "Clear play history", "About this player", "Back"]
                self._draw_rows(rows, selected, 62, 4)
            else:
                self._draw_rows(items, selected, 62, 4)
            self._footer("↑↓ MOVE  ENTER PLAY", "F SAVE  P ADD")
        if message and section not in ("Home", "Now Playing"):
            d.rounded_rectangle((7, 137, 313, 148), radius=4, fill=(35, 29, 26))
            self._text(message, 12, 139, self.tiny, ACCENT, 292)
        self._present()

    def _draw_rows(self, items, selected, y0, visible):
        d = self.drawctx
        start = max(0, min(selected - visible + 1, max(0, len(items) - visible)))
        for offset, item in enumerate(items[start:start + visible]):
            idx = start + offset
            y = y0 + offset * 16
            active = idx == selected
            d.rounded_rectangle((8, y, 312, y + 14), radius=4,
                                fill=ACCENT_SOFT if active else SURFACE,
                                outline=ACCENT if active else SURFACE, width=1)
            title = item
            subtitle = ""
            if isinstance(item, dict):
                title = item.get("title") or item.get("name") or "Untitled track"
                subtitle = (item.get("user") or {}).get("username", "")
                if not subtitle and item.get("tracks") is not None:
                    subtitle = f"{len(item.get('tracks', []))} tracks"
            self._text(title, 14, y + 2, self.small, WHITE if active else (215, 219, 225), 226)
            if subtitle:
                self._text(subtitle, 246, y + 3, self.tiny, MUTED, 58)

    def _draw_player(self, track, state):
        d = self.drawctx
        d.rounded_rectangle((8, 32, 312, 125), radius=9, fill=SURFACE, outline=LINE, width=1)
        d.rounded_rectangle((17, 42, 75, 100), radius=7, fill=(44, 29, 26))
        d.rounded_rectangle((27, 52, 65, 90), radius=5, fill=ACCENT)
        d.polygon([(41, 60), (41, 82), (57, 71)], fill=BG)
        title = (track or {}).get("title", "Nothing playing") if isinstance(track, dict) else "Nothing playing"
        artist = ((track or {}).get("user") or {}).get("username", "") if isinstance(track, dict) else ""
        self._text(title, 86, 44, self.font, WHITE, 215)
        self._text(artist or "SOUNDCLOUD PUBLIC", 87, 63, self.tiny, MUTED, 210)
        pos = float(state.get("time", 0) or 0)
        dur = float(state.get("duration", 0) or 0)
        d.rounded_rectangle((18, 108, 302, 113), radius=3, fill=LINE)
        if dur > 0:
            d.rounded_rectangle((18, 108, 18 + int(284 * min(1, pos / dur)), 113), radius=3, fill=ACCENT)
        self._text(f"{int(pos)//60:02}:{int(pos)%60:02}", 18, 116, self.tiny, MUTED)
        self._text(f"{int(dur)//60:02}:{int(dur)%60:02}", 268, 116, self.tiny, MUTED)
        self._pill((8, 129, 102, 148), "LEFT  -10 SEC")
        self._pill((113, 129, 207, 148), "SPACE  PAUSE", selected=True)
        self._pill((218, 129, 312, 148), "RIGHT  +10 SEC")

    def _present(self):
        arr = np.asarray(self.image, dtype=np.uint8)
        r = (arr[:, :, 0].astype(np.uint16) >> 3) << 11
        g = (arr[:, :, 1].astype(np.uint16) >> 2) << 5
        b = arr[:, :, 2].astype(np.uint16) >> 3
        raw = (r | g | b).astype("<u2").tobytes()
        if self.stride == self.width * 2:
            self.fb.seek(0)
            self.fb.write(raw)
        else:
            for y in range(self.height):
                self.fb.seek(y * self.stride)
                self.fb.write(raw[y * self.width * 2:(y + 1) * self.width * 2])

    def tick(self):
        elapsed = time.monotonic() - self.last_draw
        if elapsed < 1 / 30:
            time.sleep(1 / 30 - elapsed)
        self.last_draw = time.monotonic()

    def quit(self):
        try:
            self.fb.seek(0)
            self.fb.write(b"\x00" * (self.stride * self.height))
        except Exception:
            pass
        try:
            self.fb.close()
            os.close(self.fb_fd)
        except Exception:
            pass
        for dev in self.devices:
            try:
                dev.close()
            except Exception:
                pass
