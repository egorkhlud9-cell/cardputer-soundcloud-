# CloudZero

CloudZero is a dark, SoundCloud-inspired player interface for M5Stack Cardputer Zero (320x170, ARM64), paired with a phone browser.

## Included in this build

- Native LVGL interface sized for the 320x170 display.
- Animated playback equalizer, animated progress, title transitions and orange-accented UI.
- Physical keyboard navigation: keys 4/5/6 for previous, play/pause and next; 7 changes screen; 8 cycles the sleep timer.
- Now Playing, Up Next and Sleep screens.
- Phone companion with SoundCloud's official embedded player.
- Local library for saving SoundCloud track and playlist URLs on the Cardputer.
- Queue metadata synchronization from the official Widget API.
- Local HTTP bridge with a systemd service that is enabled on package installation.
- ARM64 Debian package built by GitHub Actions.

## Playback and account integration

The current release delegates SoundCloud playback to its official embedded player in the phone browser. The Cardputer is the compact controller/display; it does not yet decode SoundCloud streams natively.

The companion can search using SoundCloud's own search page, load public track/playlist URLs, control playback, display queue information and save links in the Cardputer's local library.

Direct native playback and full account synchronization require an approved SoundCloud API app and OAuth 2.1 credentials. Current SoundCloud developer registration requires Artist Pro to create Client ID/Client Secret credentials, even though API requests are currently free. CloudZero will not extract browser cookies, reuse private session tokens, scrape private endpoints or bypass track restrictions. See docs/SOUNDCLOUD_API.md.

## Install

On Cardputer Zero, once the latest CI build has published the release asset, install with:

```bash
curl -fL https://github.com/egorkhlud9-cell/cardputer-soundcloud-/releases/download/cloudzero-latest/CloudZero_0.1.0_rev1_arm64.deb -o /tmp/cloudzero.deb
sudo apt-get install -y /tmp/cloudzero.deb
```

The package enables and starts cloudzero-bridge.service automatically. Connect the phone and Cardputer to the same Wi-Fi, then open `http://CARDPUTER_IP:8765` in the phone browser. Load a SoundCloud URL and use the Cardputer keyboard to control it.

## Keyboard

| Key | Action |
|---|---|
| 4 | Previous |
| 5 | Play / pause |
| 6 | Next |
| 7 | Cycle Now Playing / Up Next / Sleep |
| 8 | Cycle sleep timer: OFF / 15 / 30 / 60 minutes |

## Build and validation

GitHub Actions cross-compiles the app using the official CardputerZero template. A successful CI run confirms the ARM64 application compiles and packages; hardware playback and physical-key behavior still require testing on the actual device.

## Security

The local bridge is intended for a trusted home Wi-Fi network. Do not expose port 8765 to the public internet. Never commit SoundCloud credentials, OAuth tokens or browser session cookies.