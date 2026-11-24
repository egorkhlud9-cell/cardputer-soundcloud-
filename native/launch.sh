#!/bin/sh
set -eu
export PYTHONUNBUFFERED=1
export SDL_VIDEO_WINDOW_POS=0,0
export PYTHONPATH="/opt/soundcloud-cardputer${PYTHONPATH:+:$PYTHONPATH}"
# Cardputer Zero images may expose the panel through fbcon or KMSDRM.
if [ -e /dev/fb0 ] && [ -z "${SDL_VIDEODRIVER:-}" ]; then
  export SDL_VIDEODRIVER=fbcon
  export SDL_FBDEV=/dev/fb0
fi
exec /usr/bin/python3 -m soundcloud_cardputer.main "$@"
