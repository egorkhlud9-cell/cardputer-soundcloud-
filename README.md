# SoundCloud Cardputer — Native Public Player

A native Linux player for Cardputer Zero. Pygame/SDL2 renders the 320×170 UI and MPV plays audio. No browser, WebView, phone bridge, API key, paid SoundCloud subscription or account login is required.

## Features
- Public SoundCloud search through yt-dlp.
- Public track playback through MPV.
- Local favorites, playlists, and recently played history.
- Play/pause, seeking, volume controls.
- Local library at `~/.config/soundcloud-cardputer/library.json`.
- No SoundCloud credentials or subscription required.

## Important limits
This release intentionally does not promise account synchronization. SoundCloud does not provide an unrestricted free third-party API registration path. The app therefore works without login and only searches/plays public content supported by yt-dlp. Private likes, private playlists and account uploads cannot be synced without an authorized official API application.

## Install dependencies
The Debian package installs `python3-pygame`, `mpv` and `yt-dlp`.

## Build
`./build_deb.sh`

## Controls
- Up/Down: navigate; in Now Playing: volume.
- Enter/Space: select or pause.
- Left/Right: seek ±10 seconds while playing.
- F: add/remove local favorite.
- P: add selected track to the first local playlist.
- Search: type text, Enter to search, Backspace to edit.
- Esc/Backspace: back.
- +/-: volume.
