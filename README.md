# CloudZero

A SoundCloud-focused music player and companion UI for M5Stack Cardputer Zero (320x170, ARM64).

## Product direction

CloudZero is designed around the Cardputer's small screen and keyboard:
- Now Playing: artwork, title, artist, progress and transport controls.
- Queue: shows tracks supplied by the official SoundCloud widget.
- Sleep: sleep timer with pause at expiry.
- Search: opens SoundCloud's own search experience from the phone remote.
- Library: save SoundCloud track and playlist links locally on the Cardputer.
- Phone Link: use an Android browser as a companion screen and text-entry surface.

## Playback architecture

The current implementation uses SoundCloud's official embedded player in the phone browser. The Cardputer talks to a local HTTP bridge over Wi-Fi and can display metadata and send transport commands.

Direct playback on the Cardputer is a planned next milestone. Cardputer Zero has onboard audio hardware, but standalone SoundCloud playback requires an approved SoundCloud API application, supported stream access for each track, and a native audio output pipeline. Tracks can be restricted or unavailable for off-platform playback. CloudZero will not scrape private endpoints or bypass access restrictions.

## Local library

Saved tracks and playlist links are stored under /var/lib/cloudzero/library.json on the Cardputer and persist across restarts. The bridge accepts only SoundCloud URLs.

## Build

GitHub Actions cross-compiles the app using the official CardputerZero template and publishes a Debian arm64 package as a workflow artifact.

## Install concept

1. Install the Debian package on Cardputer Zero.
2. Enable and start cloudzero-bridge.service.
3. Connect Cardputer and phone to the same Wi-Fi.
4. Open http://CARDPUTER_IP:8765 on the phone.
5. Load a track or playlist; use the Cardputer screen and keyboard as the compact player interface.

## Status

Native LVGL player UI, phone synchronization, local bridge, SoundCloud remote, queue display, saved library, and cross-build workflow are under active development. CI success confirms compilation/package creation, not yet hardware playback validation.

## Access and attribution

Playback is delegated to SoundCloud's official embedded player. Direct API streaming will be implemented only through authorized API access, with required creator and SoundCloud attribution.