"""
spotify_playlist_to_csv.py
---------------------------
Exports a Spotify playlist (or your Liked Songs by default) to a CSV file
compatible with csv_to_spotify_playlist.py.

Setup:
    pip install spotipy python-dotenv tqdm pandas

Create a .env file alongside this script with:
    CLIENT_ID=your_client_id
    CLIENT_SECRET=your_client_secret
    REDIRECT_URI=http://127.0.0.1:8888/callback
    SPOTIFY_EXPORT_PATH=C:/Users/tiffa/Downloads/Liked_Songs1.csv
    SPOTIFY_PLAYLIST_ID=          # leave blank to export Liked Songs instead

Get credentials at: https://developer.spotify.com/dashboard

Note: As of Spotify's Feb/March 2026 API changes, Development Mode apps
no longer receive 'popularity', 'available_markets', or 'isrc' fields, and
batch track-fetch endpoints were removed in favor of per-track requests.
This script fetches track details individually and fills those columns
with blanks when unavailable.
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

PAGE_SIZE   = 50     # Spotify's max page size for playlist/saved-tracks endpoints
RETRY_WAIT  = 5       # seconds to wait on rate-limit (429) errors
MAX_RETRIES = 3

# Column order matches Exportify, so files are interchangeable either direction.
CSV_COLUMNS = [
    "Track URI",
    "Track Name",
    "Artist Name(s)",
    "Album Name",
    "Album Release Date",
    "Duration (ms)",
    "Added By",
    "Added At",
]


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

    scope = "playlist-read-private playlist-read-collaborative user-library-read"
    return spotipy.Spotify(
        auth_manager=SpotifyOAuth(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            scope=scope,
        )
    )


# ── Fetching helpers ──────────────────────────────────────────────────────────

def _call_with_retry(fn, *args, **kwargs):
    """Call a spotipy function with retry on 429 rate limits."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return fn(*args, **kwargs)
        except spotipy.exceptions.SpotifyException as e:
            if e.http_status == 429 and attempt < MAX_RETRIES:
                wait = int(e.headers.get("Retry-After", RETRY_WAIT))
                print(f"\n  Rate-limited. Waiting {wait}s before retry {attempt}/{MAX_RETRIES}...")
                time.sleep(wait)
            else:
                raise


def fetch_liked_songs(sp: spotipy.Spotify) -> list[dict]:
    """Fetch all tracks from the current user's Liked Songs."""
    items = []
    offset = 0

    # Get total count for a progress bar
    first_page = _call_with_retry(sp.current_user_saved_tracks, limit=1)
    total = first_page["total"]

    with tqdm(total=total, desc="Fetching Liked Songs", unit="track") as pbar:
        while True:
            page = _call_with_retry(
                sp.current_user_saved_tracks, limit=PAGE_SIZE, offset=offset
            )
            batch = page["items"]
            if not batch:
                break

            for entry in batch:
                track = entry.get("track")
                if track:
                    items.append({"track": track, "added_at": entry.get("added_at"), "added_by": None})

            pbar.update(len(batch))
            offset += len(batch)
            if len(batch) < PAGE_SIZE:
                break

    return items


def fetch_playlist_tracks(sp: spotipy.Spotify, playlist_id: str) -> list[dict]:
    """Fetch all tracks from a given playlist."""
    items = []
    offset = 0

    first_page = _call_with_retry(sp.playlist_items, playlist_id, limit=1)
    total = first_page["total"]

    with tqdm(total=total, desc="Fetching playlist tracks", unit="track") as pbar:
        while True:
            page = _call_with_retry(
                sp.playlist_items, playlist_id, limit=PAGE_SIZE, offset=offset
            )
            batch = page["items"]
            if not batch:
                break

            for entry in batch:
                track = entry.get("track")
                if track:
                    added_by = (entry.get("added_by") or {}).get("id")
                    items.append({
                        "track": track,
                        "added_at": entry.get("added_at"),
                        "added_by": added_by,
                    })

            pbar.update(len(batch))
            offset += len(batch)
            if len(batch) < PAGE_SIZE:
                break

    return items


# ── Row building ──────────────────────────────────────────────────────────────

def track_to_row(entry: dict) -> dict:
    """Convert a fetched track entry into a CSV row matching CSV_COLUMNS."""
    track = entry["track"] or {}

    artists = ", ".join(a.get("name", "") for a in track.get("artists", []))
    album = track.get("album") or {}

    return {
        "Track URI":           track.get("uri", ""),
        "Track Name":          track.get("name", ""),
        "Artist Name(s)":      artists,
        "Album Name":          album.get("name", ""),
        "Album Release Date":  album.get("release_date", ""),
        "Duration (ms)":       track.get("duration_ms", ""),
        "Added By":            entry.get("added_by") or "",
        "Added At":            entry.get("added_at") or "",
    }


# ── Main export logic ─────────────────────────────────────────────────────────

def export_playlist_to_csv(
    output_path: str,
    playlist_id: str | None = None,
) -> str:
    """
    Export a Spotify playlist (or Liked Songs if playlist_id is None) to CSV.

    Parameters
    ----------
    output_path : Path to write the CSV file to.
    playlist_id  : Spotify playlist ID to export. If None, exports Liked Songs.

    Returns
    -------
    str : Path to the written CSV file.
    """
    print("\n── Connecting to Spotify ──────────────────────────────────────")
    sp = get_spotify_client()
    user_id = sp.current_user()["id"]
    print(f"  Logged in as: {user_id}")

    print("\n── Fetching tracks ────────────────────────────────────────────")
    if playlist_id:
        entries = fetch_playlist_tracks(sp, playlist_id)
    else:
        entries = fetch_liked_songs(sp)

    print(f"  Retrieved {len(entries):,} tracks")

    print("\n── Building CSV ───────────────────────────────────────────────")
    rows = [track_to_row(e) for e in entries]
    df = pd.DataFrame(rows, columns=CSV_COLUMNS)

    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False, encoding="utf-8-sig")  # BOM for Excel compatibility

    print(f"\n✅ Done! Wrote {len(df):,} tracks to {out_path}\n")
    return str(out_path)


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    load_dotenv()

    output_path = os.getenv("SPOTIFY_EXPORT_PATH")
    playlist_id = os.getenv("SPOTIFY_PLAYLIST_ID") or None

    if not output_path:
        raise ValueError("SPOTIFY_EXPORT_PATH is not set in your .env file.")

    export_playlist_to_csv(
        output_path=output_path,
        playlist_id=playlist_id,
    )