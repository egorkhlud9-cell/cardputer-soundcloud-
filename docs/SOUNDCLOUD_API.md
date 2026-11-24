# SoundCloud integration notes

CloudZero must use SoundCloud's documented API and embedded player. Do not read browser cookies, copy a web-session token, or depend on private api-v2.soundcloud.com routes.

## Current supported architecture

- The current shipped player delegates playback to SoundCloud's official embedded Widget in the companion browser.
- The Cardputer app controls the companion over the local bridge and displays title, artist, position, queue count and playback state.
- The local library stores SoundCloud URLs and metadata on the Cardputer. It is not the same thing as a synchronized SoundCloud account library.

## Official API requirements

The current SoundCloud developer guide documents OAuth 2.1, Authorization Code with PKCE for user-scoped actions, and Client Credentials for public resources. Requests use Authorization: OAuth ACCESS_TOKEN. Tokens expire and refresh tokens are single-use, so refresh handling and secure local storage are required.

As of the current developer registration guide, creating API app credentials (Client ID and Client Secret) requires an Artist Pro subscription. API requests themselves are currently described as free of charge. Therefore a personal player does not avoid the app-registration requirement simply by being non-commercial.

Official references:
- https://developers.soundcloud.com/docs/api/register-app
- https://developers.soundcloud.com/docs/api/guide
- https://developers.soundcloud.com/docs/api/explorer/open-api
- https://developers.soundcloud.com/docs/api/terms-of-use

## Planned API adapter

Once a valid app credential pair and an allowed redirect URI are configured, an API adapter can provide:
- public track and playlist search;
- account profile and user-authorized library access;
- likes and playlist management where the API grants the relevant scope;
- official stream resolution only for tracks whose access status permits off-platform playback.

The adapter must honor pagination, rate limits, track access status (playable, preview, blocked), attribution requirements, and SoundCloud's terms. A blocked track must never be forced through an alternate/private endpoint.

## Secrets

Never commit Client Secret, access token, refresh token, or session cookies. Keep any future credentials in a local configuration file with restrictive permissions or a secrets store. The public GitHub repository contains no personal account credentials.