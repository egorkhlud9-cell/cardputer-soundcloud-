# CloudZero

A SoundCloud-focused player/controller for M5Stack Cardputer Zero (320x170, aarch64).

## Goal

A compact dark player UI on the Cardputer Zero, with an Android phone acting as the SoundCloud playback source and remote. The phone will use SoundCloud's official embedded player and Widget API; the Cardputer will display track metadata/progress and provide transport controls over local Wi-Fi.

This avoids unofficial stream extraction and does not require SoundCloud credentials embedded in the device.

## Hardware / target

- Cardputer Zero, Debian 13, aarch64
- 320x170 ST7789 display
- LVGL 9.x application based on the official CardputerZero template
- Debian arm64 package

## Build

GitHub Actions cross-compiles the app using the official CardputerZero template and publishes the Debian package as a workflow artifact.

Push to main or run the Build CardputerZero package workflow manually.

## Planned interaction

1. Connect Cardputer and phone to the same Wi-Fi network.
2. Open the Cardputer's local control page from the phone.
3. Paste a SoundCloud track/playlist URL; playback runs in SoundCloud's official embed on the phone.
4. The Cardputer shows artwork/title/artist/progress and sends play/pause/next/previous commands.

## Status

Initial repository, dark player UI shell, and cross-build pipeline. The phone bridge and real playback controls are not implemented yet; a successful CI build is not the same as verified playback on hardware.

## Legal / access

Playback is delegated to SoundCloud's official embedded player in the phone browser. No DRM circumvention, private API scraping, or embedded account tokens.
