from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import time
from pathlib import Path


class AudioError(RuntimeError):
    pass


class AudioPlayer:
    """MPV-backed player with a local IPC channel and network-stream buffering."""

    def __init__(self):
        self.process: subprocess.Popen | None = None
        self.ipc_path = f"/tmp/sc-cardputer-{os.getuid()}.sock"
        self.volume = 70
        self.current = None
        self.last_error = ""

    def available(self):
        return shutil.which("mpv") is not None

    def _ipc(self, command, timeout=0.65):
        process = self.process
        if not process or process.poll() is not None:
            return None
        request_id = int(time.monotonic_ns() % 2_000_000_000)
        payload = dict(command)
        payload["request_id"] = request_id
        deadline = time.monotonic() + timeout
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
                sock.settimeout(timeout)
                sock.connect(self.ipc_path)
                sock.sendall((json.dumps(payload, separators=(",", ":")) + "\n").encode())
                buffer = b""
                while time.monotonic() < deadline:
                    chunk = sock.recv(4096)
                    if not chunk:
                        break
                    buffer += chunk
                    while b"\n" in buffer:
                        line, buffer = buffer.split(b"\n", 1)
                        try:
                            response = json.loads(line)
                        except (ValueError, UnicodeDecodeError):
                            continue
                        if response.get("request_id") == request_id:
                            return response
        except (OSError, TimeoutError):
            return None
        return None

    def play(self, url, title=""):
        if not self.available():
            raise AudioError("MPV is missing. Reinstall SoundCloud Cardputer dependencies.")
        if not url or not str(url).startswith(("http://", "https://")):
            raise AudioError("The track did not return a valid public audio stream.")
        self.stop()
        try:
            Path(self.ipc_path).unlink(missing_ok=True)
        except OSError:
            pass

        env = os.environ.copy()
        env["MPV_VERBOSE"] = "no"
        args = [
            "mpv",
            "--no-video",
            "--no-terminal",
            "--force-window=no",
            "--audio-display=no",
            "--input-ipc-server=" + self.ipc_path,
            "--volume=" + str(self.volume),
            "--volume-max=100",
            "--cache=yes",
            "--cache-secs=30",
            "--demuxer-readahead-secs=30",
            "--network-timeout=30",
            "--stream-lavf-o=reconnect=1,reconnect_streamed=1,reconnect_delay_max=5",
            "--msg-level=all=error",
            "--",
            str(url),
        ]
        try:
            self.process = subprocess.Popen(
                args,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                env=env,
                close_fds=True,
                start_new_session=True,
            )
        except OSError as exc:
            self.process = None
            raise AudioError(f"Could not start MPV: {exc}") from exc

        self.current = str(title or "Unknown track")
        deadline = time.monotonic() + 3.0
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                self.process = None
                self.current = None
                raise AudioError("MPV stopped before playback started. Check the audio output.")
            if os.path.exists(self.ipc_path):
                break
            time.sleep(0.05)
        if not os.path.exists(self.ipc_path):
            self.stop()
            raise AudioError("MPV started but its control channel did not become ready.")

    def command(self, name, *args):
        return self._ipc({"command": [name, *args]})

    def toggle(self):
        self.command("cycle", "pause")

    def stop(self):
        process = self.process
        if process and process.poll() is None:
            self._ipc({"command": ["quit"]}, timeout=0.3)
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.terminate()
                try:
                    process.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    process.kill()
        self.process = None
        self.current = None
        try:
            Path(self.ipc_path).unlink(missing_ok=True)
        except OSError:
            pass

    def set_volume(self, value):
        self.volume = max(0, min(100, int(value)))
        self.command("set_property", "volume", self.volume)
        return self.volume

    def seek(self, seconds):
        self.command("seek", float(seconds), "relative")

    def status(self):
        if not self.process or self.process.poll() is not None:
            return {"playing": False, "time": 0, "duration": 0, "pause": True, "volume": self.volume}

        def get(prop, default=0):
            response = self._ipc({"command": ["get_property", prop]})
            if not response or response.get("error") != "success":
                return default
            return response.get("data", default)

        return {
            "playing": True,
            "time": get("time-pos", 0) or 0,
            "duration": get("duration", 0) or 0,
            "pause": bool(get("pause", False)),
            "volume": int(get("volume", self.volume) or self.volume),
        }
