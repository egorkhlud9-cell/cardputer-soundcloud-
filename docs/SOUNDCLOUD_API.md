# SoundCloud integration

CloudZero is designed to run on the Cardputer Zero itself. The native launcher opens the local CloudZero interface in Zero Browser's QtWebKit engine. The UI uses SoundCloud's documented HTML5 Widget API for public track and playlist playback.

## Current standalone architecture

- The Cardputer hosts the local UI and backend at 127.0.0.1:8765.
- SoundCloud's official Widget is embedded invisibly inside the CloudZero interface.
- Playback controls are issued by the Widget API: play, pause, toggle, previous, next, seekTo and setVolume.
- The Cardputer's browser engine handles network media playback and sends audio through the device audio system.
- Queue, saved links and user-created CloudZero playlists are stored locally on the device.
- No phone, phone browser, remote-control server or account cookie is needed.

## Public Widget playback

The Widget API accepts a public SoundCloud track or playlist URL through its load method. It exposes playback state, current sound metadata, duration, position, queue contents and volume. It does not provide a general catalogue-search method or private account-library API.

CloudZero therefore accepts public SoundCloud links. A full in-app catalogue search, account likes, private playlists and account synchronization are not implemented in this build.

## API credentials and account security

The documented SoundCloud Web API uses OAuth for user-scoped API operations and app credentials for API access. Current developer registration requirements may restrict who can register an application and obtain those credentials. This project does not try to work around those requirements.

Zero Browser's QtWebKit engine is experimental and based on an old WebKit revision. It is not suitable for entering passwords or handling sensitive account information. CloudZero does not request or store SoundCloud passwords, browser cookies, OAuth access tokens, refresh tokens, client secrets or other account credentials.

## Device storage

The backend stores only local player state and public URLs:
- /var/lib/cloudzero/library.json
- /var/lib/cloudzero/playlists.json
- /var/lib/cloudzero/state.json

The service binds to 127.0.0.1 only. It is not a LAN server and must not be exposed to the public internet.

## Official references

- https://developers.soundcloud.com/docs/api/html5-widget.html
- https://developers.soundcloud.com/docs/api/guide
- https://developers.soundcloud.com/docs/api/register-app
- https://docs.m5stack.com/en/CardputerZero

## Runtime validation still required

CI can verify that the native launcher compiles, the Python backend parses and URL validation tests pass. Only the physical Cardputer Zero can confirm that the installed QtWebKit revision loads the current SoundCloud Widget, that a selected public track is playable, and that audio reaches the built-in speaker or 3.5 mm output.
