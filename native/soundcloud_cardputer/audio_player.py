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
    """MPV player that verifies IPC before handing it a network stream."""

    def __init__(self):
        self.process: subprocess.Popen | None = None
        # A per-instance socket avoids collisions with stale sockets or another player.
        self.ipc_path = f"/tmp/sc-{os.getuid()}-{os.getpid()}-{id(self):x}.sock"
        self.volume = 70
        self.current = None
        self.last_error = ""
        self.log_path = Path.home() / ".local/state/soundcloud-cardputer/mpv.log"

    def available(self):
        return shutil.which("mpv") is not None

    def _ipc(self, command, timeout=1.0):
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

    def _wait_for_ipc(self, timeout=8.0):
        deadline = time.monotonic() + timeout
        last_response = None
        while time.monotonic() < deadline:
            if not self.process or self.process.poll() is not None:
                return False
            # A successful property response proves the socket accepts and processes IPC.
            last_response = self._ipc({"command": ["get_property", "idle-active"]}, timeout=0.5)
            if last_response and last_response.get("error") == "success":
                return True
            time.sleep(0.1)
        self.last_error = f"IPC handshake timed out; last response={last_response!r}"
        return False

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

        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        env = os.environ.copy()
        env["MPV_VERBOSE"] = "no"
        args = [
            "mpv",
            "--no-config",
            "--idle=yes",
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
            "--msg-level=all=warn",
            "--log-file=" + str(self.log_path),
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

        if not self._wait_for_ipc():
            detail = self.last_error
            self.stop()
            if detail:
                raise AudioError(f"MPV control channel failed: {detail}. See {self.log_path}")
            raise AudioError("MPV exited before its control channel became ready. See mpv.log")

        response = self._ipc({"command": ["loadfile", str(url), "replace"]}, timeout=3.0)
        if not response or response.get("error") != "success":
            detail = response or self.last_error or "no IPC response"
            self.stop()
            raise AudioError(f"MPV could not accept the track: {detail}. See {self.log_path}")

        self.current = str(title or "Unknown track")
        self.last_error = ""

    def command(self, name, *args):
        return self._ipc({"command": [name, *args]})

    def toggle(self):
        self.command("cycle", "pause")

    def stop(self):
        process = self.process
        if process and process.poll() is None:
            self._ipc({"command": ["quit"]}, timeout=0.5)
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
