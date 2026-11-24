#!/bin/sh
set -u
LOG_DIR="${HOME}/.local/state/soundcloud-cardputer"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/launch.log"
exec >>"$LOG" 2>&1
echo "===== SoundCloud launch: $(date -Is) ====="
export PYTHONUNBUFFERED=1
export SDL_VIDEO_WINDOW_POS=0,0
export PYTHONPATH="/opt/soundcloud-cardputer${PYTHONPATH:+:$PYTHONPATH}"
# Do not force fbcon: let SDL use the active Cardputer/APPLaunch display backend.
unset SDL_VIDEODRIVER SDL_FBDEV
echo "DISPLAY=${DISPLAY:-unset} WAYLAND_DISPLAY=${WAYLAND_DISPLAY:-unset}"
echo "SDL_VIDEODRIVER=auto"
echo "Python: $(/usr/bin/python3 --version 2>&1)"
echo "pygame: $(/usr/bin/python3 -c 'import pygame; print(pygame.version.ver)' 2>&1)"
echo "mpv: $(command -v mpv || true)"
echo "yt-dlp: $(command -v yt-dlp || true)"
exec /usr/bin/python3 -m soundcloud_cardputer.main "$@"
