# CloudZero

CloudZero is an independent, on-device music player shell for M5Stack Cardputer Zero. The UI, queue, saved library and user-created playlists run locally on the Cardputer. A phone is not part of playback.

## What this build does

- Launches a custom CloudZero interface on the Cardputer display using the installed Zero Browser QtWebKit engine.
- Uses SoundCloud's official HTML5 Widget API as the playback engine for public tracks and playlists.
- Plays audio on the Cardputer itself through the system audio output (speaker or 3.5 mm output), subject to the device's audio configuration.
- Controls play/pause, previous/next, seek and widget volume.
- Stores a local saved library, queue and user-created playlists under /var/lib/cloudzero/.
- Starts its local-only service automatically when the package is installed.
- Does not require the phone companion, a phone browser, or a phone-to-Cardputer connection.

## Honest SoundCloud limitations

This project deliberately uses the documented SoundCloud Widget. It does not scrape private endpoints, copy browser cookies, steal session tokens, or bypass track restrictions.

Without an approved SoundCloud API application, CloudZero cannot provide a native in-app SoundCloud catalogue search or synchronize private account data such as likes and private playlists. SoundCloud's current developer registration requirements restrict creation of API credentials. This build therefore accepts public SoundCloud track/playlist links and lets you organize them into CloudZero-local playlists. Those playlists are stored on the Cardputer, not in your SoundCloud account.

The embedded player is official SoundCloud playback, not an independently implemented decoder. The custom CloudZero interface surrounds and controls it; the browser engine must remain installed. The device must have Wi-Fi for online playback.

## Browser requirement and security

CloudZero launches the command zero-browser --mode qtwebkit. Install the Cardputer Zero Zero Browser application first. Its QtWebKit engine is experimental and based on an old WebKit revision. It is not suitable for logging into accounts, entering passwords, or handling sensitive information. CloudZero does not ask for SoundCloud credentials and does not store cookies or OAuth tokens. Only load public SoundCloud links.

If Zero Browser is unavailable, the CloudZero launcher exits with a clear error instead of silently falling back to the phone remote.

## Install

The package is built for ARM64 Debian on Cardputer Zero. On the device, run:

    curl -fL https://github.com/egorkhlud9-cell/cardputer-soundcloud-/releases/download/cloudzero-latest/CloudZero_0.1.0_rev1_arm64.deb -o /tmp/cloudzero.deb && sudo apt-get install -y /tmp/cloudzero.deb

Open CloudZero from APPLaunch. The cloudzero-bridge.service local application server is enabled automatically. The UI is served only on 127.0.0.1:8765; it is not exposed to the LAN.

## Controls

| Key | Action |
|---|---|
| Q | Play / pause |
| A | Previous |
| D | Next |
| W | Volume up |
| S | Volume down |
| 1–5 | Player / Add / Queue / Library / Playlists |
| Enter | Activate focused control |
| Esc | Return to Player |

The browser's own keyboard shortcuts may take precedence for some keys depending on the installed Zero Browser version. The on-screen controls remain available.

## Data and privacy

- Local data: /var/lib/cloudzero/library.json, playlists.json, state.json.
- These files contain public SoundCloud URLs, display metadata, queue and local playlist contents.
- No passwords, API secrets, cookies or access tokens are collected or stored.
- The service binds to loopback only and is not intended to be exposed to a network.
- Uninstalling the package does not intentionally delete the local library.

## Build and validation

GitHub Actions cross-compiles the native launcher and packages the local service and UI. CI validates Python syntax and backend URL validation. SoundCloud Widget compatibility, audio output and keyboard behavior must still be tested on the physical Cardputer Zero; the browser engine and network playback are runtime dependencies.
