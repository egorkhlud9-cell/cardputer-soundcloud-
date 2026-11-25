# SoundCloud Cardputer — AURORA 2.0

A native, offline-friendly-feeling SoundCloud player for Cardputer Zero. It uses the device's Linux framebuffer and keyboard input, MPV for audio, and yt-dlp for public SoundCloud search and stream resolution. There is no browser, WebView, phone bridge, API key, paid subscription or SoundCloud login.

## What it does

- Public SoundCloud search and playback.
- Native 320×170 interface designed for the Cardputer screen.
- Home, Search, Favorites, Playlists, Recently Played, Now Playing and Settings screens.
- Local favorites, local playlists and listening history.
- Keyboard navigation, play/pause, ±10-second seek and volume adjustment.
- MPV network cache and stream reconnect options to make playback more resilient on unstable Wi-Fi.
- Launcher entry and app icon installed for APPLaunch and the desktop application menu.
- Local data is stored in `~/.config/soundcloud-cardputer/`.

## Important limitations

This is a public-content player, not an official SoundCloud client. It does not sign in, synchronize private likes/playlists, upload tracks or access private content. Search and playback depend on public content and yt-dlp compatibility with SoundCloud; changes on SoundCloud's side can temporarily affect search or playback. Network buffering reduces interruptions but cannot guarantee uninterrupted playback when Wi-Fi or the source itself drops.

## Install on Cardputer Zero over SSH

Run these commands from your computer, replacing `CARDPUTER_IP` with the Cardputer Zero's current IP address:

```bash
ssh egor@CARDPUTER_IP
```

Then on the Cardputer:

```bash
sudo apt update
sudo apt install -y git ca-certificates
cd ~
git clone --branch release/2.0-aurora-player --depth 1 https://github.com/egorkhlud9-cell/cardputer-soundcloud-.git
cd cardputer-soundcloud-
chmod +x build_deb.sh
./build_deb.sh
sudo apt install -y ./dist/soundcloud-cardputer_2.0.0_all.deb
```

After installation, return to APPLaunch and refresh/reopen its application list. Launch **SoundCloud**. You can also start it from SSH with:

```bash
soundcloud-cardputer
```

To inspect startup and crash logs:

```bash
tail -n 100 ~/.local/state/soundcloud-cardputer/launch.log
tail -n 100 ~/.local/state/soundcloud-cardputer/crash.log
```

## Controls

| Key | Action |
|---|---|
| Up / Down | Move through menus |
| Enter | Open / select / play |
| Space | Pause / resume |
| Left / Right | Seek −10 / +10 seconds in Now Playing |
| Up / Down in Now Playing | Volume +5 / −5 |
| + / = | Volume up |
| − | Volume down |
| F | Add or remove local favorite |
| P | Add selected track to the first local playlist |
| R | Refresh the current section |
| Escape / Backspace | Back / exit |
| Type text in Search | Build a search query |
| Enter in Search | Search public SoundCloud tracks |

## Build a package

```bash
./build_deb.sh
```

The package is created at `dist/soundcloud-cardputer_2.0.0_all.deb`.

## Uninstall

```bash
sudo apt remove soundcloud-cardputer
```

Uninstalling the package does not delete the user's local favorites, playlists, history or settings.
