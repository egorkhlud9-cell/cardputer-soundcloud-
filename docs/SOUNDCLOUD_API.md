# SoundCloud API and account synchronization

The native player uses SoundCloud's documented Web API. User account access is implemented with OAuth 2.1 Authorization Code + PKCE; the player does not collect passwords or browser cookies.

## OAuth setup
1. Register an API application in SoundCloud's developer settings. SoundCloud's current registration guide requires Artist Pro to obtain API credentials.
2. Configure the registered redirect URI as `http://127.0.0.1:8765/callback`.
3. Enter the resulting Client ID and Client Secret in the player's Settings.
4. Select Connect. The player opens the system browser for consent and receives the callback on loopback.
5. The access token and rotating refresh token are stored in `~/.config/soundcloud-cardputer/config.json` with owner-only permissions (0600).

The OAuth state value is checked and PKCE S256 is used. Refresh tokens are replaced after successful refresh. Disconnect clears the local token set.

## Synchronization
The connected account can load:
- Profile: `GET /me`
- Liked tracks: `GET /me/likes/tracks`
- Playlists: `GET /me/playlists`
- Uploaded tracks: `GET /me/tracks`
- Playlist contents: `GET /playlists/{playlist_urn}/tracks`

Pagination follows `next_href`. Local copies are stored in `~/.config/soundcloud-cardputer/library.json`. Private content is requested only through the user's own OAuth authorization; inaccessible or unplayable items return the API's error.

## Playback
When an authenticated stream endpoint is available, MPV plays the returned stream URL. For public SoundCloud tracks, yt-dlp is used as a resolver fallback. This does not bypass private-track permissions or blocked content.

## References
- https://developers.soundcloud.com/docs
- https://developers.soundcloud.com/docs/api/explorer/
- https://developers.soundcloud.com/docs/api/register-app.html
