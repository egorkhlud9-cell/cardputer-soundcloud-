from __future__ import annotations
import json, os, shutil, socket, subprocess, tempfile, time
class AudioError(RuntimeError): pass

class AudioPlayer:
    def __init__(self):
        self.process = None
        self.ipc_path = f"/tmp/sc-cardputer-{os.getuid()}.sock"
        self.volume = 70
        self.current = None

    def available(self): return shutil.which("mpv") is not None

    def _ipc(self, command):
        if not self.process or self.process.poll() is not None: return None
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
                sock.settimeout(.25); sock.connect(self.ipc_path)
                sock.sendall((json.dumps(command) + "\n").encode())
                return sock.recv(4096).decode(errors="replace")
        except OSError: return None

    def play(self, url, title=""):
        if not self.available(): raise AudioError("MPV is not installed. Install package dependencies.")
        self.stop()
        try: os.unlink(self.ipc_path)
        except OSError: pass
        env = os.environ.copy()
        self.process = subprocess.Popen([
            "mpv", "--no-video", "--no-terminal", "--force-window=no",
            "--input-ipc-server=" + self.ipc_path, "--volume=" + str(self.volume),
            "--", url
        ], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env)
        self.current = title
        time.sleep(.25)
        if self.process.poll() is not None:
            raise AudioError("MPV could not start playback. Check the audio output.")
    def command(self, name, *args):
        self._ipc({"command":[name, *args]})
    def toggle(self): self.command("cycle", "pause")
    def stop(self):
        if self.process and self.process.poll() is None:
            self.command("quit")
            try: self.process.wait(timeout=2)
            except subprocess.TimeoutExpired: self.process.terminate()
        self.process = None; self.current = None
    def set_volume(self, value):
        self.volume = max(0, min(100, int(value)))
        self.command("set_property", "volume", self.volume)
    def seek(self, seconds): self.command("seek", seconds, "relative")
    def status(self):
        if not self.process or self.process.poll() is not None: return {"playing":False,"time":0,"duration":0,"pause":True}
        def get(prop):
            raw = self._ipc({"command":["get_property",prop]})
            try: return json.loads(raw.splitlines()[0]).get("data", 0)
            except Exception: return 0
        return {"playing":True,"time":get("time-pos") or 0,"duration":get("duration") or 0,"pause":bool(get("pause"))}
