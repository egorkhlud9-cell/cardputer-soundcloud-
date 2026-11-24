# SoundCloud Cardputer — Native Player

A native Linux player for Cardputer Zero. The player UI is Pygame/SDL2; audio is handled by MPV. It does not embed a browser, WebView, iframe, Electron, or phone-based playback bridge.

## Features
- 320×170 landscape interface designed for the Cardputer display.
- MPV audio playback with play/pause, seeking and volume controls.
- SoundCloud OAuth 2.1 Authorization Code + PKCE.
- Account sync: profile, liked tracks, playlists and uploaded tracks.
- Search, favorites, playlist browsing, recently played history.
- Public track playback fallback through the installed yt-dlp resolver.
- Local configuration and library under `~/.config/soundcloud-cardputer/`; config files are created with owner-only permissions.
- Debian package build with GitHub Actions.

## Important: SoundCloud API credentials
SoundCloud requires each API client to have its own Client ID and Client Secret. Its current registration guide says API app registration requires Artist Pro. Do not put credentials in this repository. Open Settings in the player and enter your own values. The app stores them locally with file mode 0600.

Register this exact redirect URI in your SoundCloud application settings:
`http://127.0.0.1:8765/callback`

The OAuth login opens the system's external browser and receives the authorization response through a local loopback callback. The player never embeds a browser. SoundCloud OAuth uses PKCE; access tokens are refreshed automatically. If SoundCloud changes API permissions or your app is not approved for a scope, the player reports the API error instead of faking sync.

## Install dependencies (Debian 13 / Cardputer Zero)
The .deb declares these runtime dependencies: `python3`, `python3-pygame`, `mpv`, `yt-dlp`, and `python3-requests`.

## Build
```sh
./build_deb.sh
```
Output: `dist/soundcloud-cardputer_1.0.0_all.deb`

GitHub Actions builds the package on pushes and pull requests. A tagged release `v1.0.0` publishes the .deb.

## Controls
- Up / Down: move through lists
- Enter: open / play / select
- Space: pause / resume
- Left / Right (Now Playing): seek ±10 seconds
- + / -: volume
- R: refresh current section
- Esc / Backspace: back
- Settings: C connect, S sync

## Current implementation notes
- Account endpoints require a valid user OAuth token and registered API credentials.
- Playback may be unavailable for tracks marked blocked or preview-only by SoundCloud.
- The fallback resolver only handles public URLs supported by yt-dlp; it does not bypass private-track permissions.
- No passwords, browser cookies, or session cookies are collected.
