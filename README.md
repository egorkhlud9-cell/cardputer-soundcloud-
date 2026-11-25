# SoundCloud Cardputer — AURORA 2.1

A native SoundCloud player for Cardputer Zero. It uses the device's Linux framebuffer and keyboard input, MPV for audio, and yt-dlp for public SoundCloud search and stream resolution.

## Features

- Public SoundCloud search and playback.
- Native 320×170 interface for Cardputer Zero.
- Home, Search, Favorites, Playlists, Recently Played, Now Playing and Settings screens.
- Animated vinyl/orbit visual, equalizer animation, playback progress and volume readout.
- Local favorites, playlists and listening history.
- Keyboard navigation, play/pause, seek and volume controls.
- MPV network cache and reconnect options to improve resilience on unstable Wi-Fi.
- APPLaunch launcher entry and application icon.
- User data is stored in `~/.config/soundcloud-cardputer/`.

## Limitations

This is a public-content player, not an official SoundCloud client. It does not sign in, synchronize private likes/playlists, upload tracks or access private content. Search and playback depend on public content and yt-dlp compatibility with SoundCloud. Network buffering cannot guarantee uninterrupted playback if Wi-Fi or the source itself becomes unavailable.

## Install on Cardputer Zero (one command)

The Debian package is built by **GitHub Actions**, not on the Cardputer. The device only downloads and installs the finished ARM64 package. No Git clone, compilation, Python build step or package building is needed on the Cardputer.

Connect to the Cardputer over SSH from your computer, then paste this single command:

```bash
curl -fsSL https://raw.githubusercontent.com/egorkhlud9-cell/cardputer-soundcloud-/release/2.0-aurora-player/install.sh | sudo bash
```

The installer checks that the device is ARM64, downloads the prebuilt `soundcloud-cardputer_2.1.0_all.deb` release asset and installs it with APT, including its dependencies.

After installation, open APPLaunch and select **AURORA SoundCloud**. You can also launch it over SSH with:

```bash
soundcloud-cardputer
```

If APPLaunch was already open during installation, close and reopen it to refresh the app list.

## Controls

| Key | Action |
|---|---|
| F / X | Navigate menus (physical up/down keys) |
| Enter | Open / select / play |
| Q (play/pause symbol) | Pause / resume |
| Z / C | Seek −10 / +10 seconds in Now Playing |
| A / S / D in Now Playing | Mute / volume down / volume up |
| + / = | Volume up |
| − | Volume down |
| V | Add or remove local favorite |
| P | Add selected track to the first local playlist |
| R | Refresh current section |
| Escape / Backspace | Back / exit |
| Type text in Search | Enter a search query |
| Enter in Search | Search public SoundCloud tracks |

## Logs

```bash
tail -n 100 ~/.local/state/soundcloud-cardputer/launch.log
tail -n 100 ~/.local/state/soundcloud-cardputer/crash.log
```

## Build (developer machine / GitHub Actions only)

Do not run the build script on Cardputer Zero. The package is built in GitHub Actions on an external runner. For development, a Debian/Ubuntu computer can build it with:

```bash
./build_deb.sh
```

The output is `dist/soundcloud-cardputer_2.1.0_all.deb`.

## Uninstall

```bash
sudo apt remove soundcloud-cardputer
```

Uninstalling the package does not delete the user's local favorites, playlists, history or settings.
