"""
Spotify User OAuth2 Token Generator — one-time setup for SPOTIFY_USER_REFRESH_TOKEN.

Uses Spotify Authorization Code Flow with Railway app as redirect URI.

Usage:
    python scripts/get_spotify_token.py

How it works:
    1. Opens a browser to authorize with playlist-read-private + playlist-read-collaborative scopes.
       You must be logged in as the user who OWNS the target playlists.
    2. After authorizing, Spotify redirects to the Railway web app.
    3. The web app exchanges the code for a refresh token and displays it.
    4. Copy the refresh token from the web page into Railway .env as SPOTIFY_USER_REFRESH_TOKEN.
"""

import json
import sys
import urllib.parse
import webbrowser

SCOPES = "playlist-read-private playlist-read-collaborative"
AUTH_URL = "https://accounts.spotify.com/authorize"


def main():
    client_id = input("Spotify Client ID: ").strip()
    input("Spotify Client Secret: (tidak dipakai, tekan Enter) ").strip()

    redirect_uri = input(
        "Redirect URI (Enter untuk default Railway): "
    ).strip() or "https://my-discord-bot-my-discord-bot.up.railway.app/spotify-callback"

    print()
    print("=" * 60)
    print("Step 1: Add this Redirect URI to your Spotify App:")
    print("=" * 60)
    print(f"  {redirect_uri}")
    print()
    print("  Go to https://developer.spotify.com/dashboard")
    print("  -> App -> Settings -> Redirect URIs -> Add")
    print()
    input("  Press Enter after you've added it...")
    print()

    params = urllib.parse.urlencode({
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "scope": SCOPES,
        "show_dialog": "true",
    })
    authorize_url = f"{AUTH_URL}?{params}"

    print("=" * 60)
    print("Step 2: Open this URL in your browser and authorize:")
    print("=" * 60)
    print(authorize_url)
    print()
    webbrowser.open(authorize_url)
    print("After authorizing, you will be redirected to:")
    print(f"  {redirect_uri}")
    print()
    print("The Railway web app will show your refresh token.")
    print("Copy SPOTIFY_USER_REFRESH_TOKEN from the page into your .env")
    print()


if __name__ == "__main__":
    main()
