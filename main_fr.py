"""
csv_to_spotify_playlist.py
--------------------------
Creates a Spotify playlist from a CSV file exported by tools like
Exportify (columns include: Track URI, Track Name, Artist Name(s), etc.)

Setup:
    pip install spotipy python-dotenv tqdm pandas

Create a .env file alongside this script with:
    CLIENT_ID=your_client_id
    CLIENT_SECRET=your_client_secret
    REDIRECT_URI=http://127.0.0.1:8888/callback
    SPOTIFY_CSV_PATH=C:/Users/tiffa/Downloads/Liked_Songs.csv
    PLAYLIST_NAME=june2026
    SPOTIFY_EXPORT_PATH=C:/Users/tiffa/Downloads/Liked_Songs1.csv

Get credentials at: https://developer.spotify.com/dashboard
"""

import os
import time
import pandas as pd
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from tqdm import tqdm
from dotenv import load_dotenv
from pathlib import Path


# ── Config ────────────────────────────────────────────────────────────────────

CHUNK_SIZE = 100      # Spotify add-tracks limit per request
RETRY_WAIT = 5        # seconds to wait on rate-limit (429) errors
MAX_RETRIES = 3


# ── Auth ──────────────────────────────────────────────────────────────────────

def get_spotify_client() -> spotipy.Spotify:
    """Authenticate and return an authorised Spotify client."""
    load_dotenv()

    client_id     = os.getenv("CLIENT_ID")
    client_secret = os.getenv("CLIENT_SECRET")
    redirect_uri  = os.getenv("REDIRECT_URI", "http://127.0.0.1:8888/callback")

    if not client_id or not client_secret:
        raise ValueError(
            "Missing CLIENT_ID or CLIENT_SECRET in your .env file."
        )

    scope = "playlist-modify-public playlist-modify-private"
    return spotipy.Spotify(
        auth_manager=SpotifyOAuth(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            scope=scope,
        )
    )


# ── CSV loading ───────────────────────────────────────────────────────────────

def load_track_uris(file_path: str) -> list[str]:
    """
    Load track URIs from a CSV file.

    Supports two formats:
    - Exportify-style: 'Track URI' column with values like 'spotify:track:...'
    - Plain ID column: 'Track ID' or 'id' column with bare Spotify IDs
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"CSV not found: {file_path}")

    df = pd.read_csv(path)
    df.columns = df.columns.str.strip().str.lstrip("\ufeff")  # strip BOM + whitespace

    if "Track URI" in df.columns:
        uris = df["Track URI"].dropna().tolist()
        uris = [u if u.startswith("spotify:track:") else f"spotify:track:{u}" for u in uris]

    elif "Track ID" in df.columns or "id" in df.columns:
        col = "Track ID" if "Track ID" in df.columns else "id"
        uris = [f"spotify:track:{tid}" for tid in df[col].dropna().tolist()]

    else:
        raise ValueError(
            "CSV must have a 'Track URI', 'Track ID', or 'id' column. "
            f"Found columns: {list(df.columns)}"
        )

    print(f"  Loaded {len(uris):,} tracks from {path.name}")
    return uris


# ── Playlist creation ─────────────────────────────────────────────────────────

def add_tracks_in_chunks(
    sp: spotipy.Spotify,
    playlist_id: str,
    uris: list[str],
) -> None:
    """Add tracks to a playlist in chunks of CHUNK_SIZE, with retry on 429."""
    chunks = [uris[i : i + CHUNK_SIZE] for i in range(0, len(uris), CHUNK_SIZE)]

    for chunk in tqdm(chunks, desc="Adding tracks", unit="batch"):
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                # Use the new /items endpoint directly (Spotify's Feb 2026 migration
                # deprecated /tracks in favor of /items for Development Mode apps).
                sp._post(f"playlists/{playlist_id}/items", payload={"uris": chunk})
                break
            except spotipy.exceptions.SpotifyException as e:
                if e.http_status == 429 and attempt < MAX_RETRIES:
                    wait = int(e.headers.get("Retry-After", RETRY_WAIT))
                    print(f"\n  Rate-limited. Waiting {wait}s before retry {attempt}/{MAX_RETRIES}...")
                    time.sleep(wait)
                else:
                    raise


def create_playlist_from_csv(
    file_path: str,
    playlist_name: str,
    public: bool = False,
) -> str:
    """
    Create a Spotify playlist from a CSV file.

    Parameters
    ----------
    file_path     : Path to the CSV file (from SPOTIFY_CSV_PATH).
    playlist_name : Name for the new Spotify playlist (from PLAYLIST_NAME).
    public        : Whether the playlist should be public (default: False).

    Returns
    -------
    str : URL of the created playlist.
    """
    print("\n── Connecting to Spotify ──────────────────────────────────────")
    sp = get_spotify_client()
    user_id = sp.current_user()["id"]
    print(f"  Logged in as: {user_id}")

    print("\n── Loading CSV ────────────────────────────────────────────────")
    uris = load_track_uris(file_path)

    print("\n── Creating playlist ──────────────────────────────────────────")
    # Use /me/playlists directly (Spotify's Feb 2026 migration removed
    # /users/{id}/playlists for Development Mode apps).
    playlist = sp._post(
        "me/playlists",
        payload={"name": playlist_name, "public": public},
    )
    playlist_id  = playlist["id"]
    playlist_url = playlist["external_urls"]["spotify"]
    print(f"  Created: '{playlist_name}'  →  {playlist_url}")

    print("\n── Adding tracks ──────────────────────────────────────────────")
    add_tracks_in_chunks(sp, playlist_id, uris)

    print(f"\n✅ Done!  {len(uris):,} tracks added.")
    print(f"   Playlist URL: {playlist_url}\n")
    return playlist_url


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    load_dotenv()

    csv_path      = os.getenv("SPOTIFY_CSV_PATH")
    playlist_name = os.getenv("PLAYLIST_NAME")

    if not csv_path:
        raise ValueError("SPOTIFY_CSV_PATH is not set in your .env file.")
    if not playlist_name:
        raise ValueError("PLAYLIST_NAME is not set in your .env file.")

    create_playlist_from_csv(
        file_path=csv_path,
        playlist_name=playlist_name,
    )