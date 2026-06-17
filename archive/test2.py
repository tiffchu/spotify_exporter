import os
import time
from pathlib import Path

import pandas as pd
import requests
import spotipy
from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyOAuth
from tqdm import tqdm


def load_local_env():
    env_path = Path(__file__).resolve().parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)


def create_spotify_client(client_id, client_secret, redirect_uri, scope):
    try:
        auth_manager = SpotifyOAuth(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            scope=scope,
            open_browser=False,
            show_dialog=True
        )

        print("\nOpen this Spotify authorization URL in your browser:")
        print(auth_manager.get_authorize_url())
        print("After Spotify redirects to 127.0.0.1 and the page fails to load, copy the full URL from your browser and paste it below.")
        redirected_url = input("Paste the full redirected URL here: ").strip()
        code = auth_manager.parse_response_code(redirected_url)
        token_info = auth_manager.get_access_token(code=code, check_cache=False)
        print(f"Granted token scopes: {token_info.get('scope', '(not returned)')}")

        return spotipy.Spotify(auth=token_info["access_token"]), token_info
    except Exception as e:
        raise Exception(f"Failed to authenticate with Spotify: {str(e)}")


def create_spotify_playlist(file_path, playlist_name, client_id, client_secret, redirect_uri):
    sp, token_info = create_spotify_client(
        client_id,
        client_secret,
        redirect_uri,
        "playlist-modify-public playlist-modify-private"
    )

    try:
        songs = pd.read_csv(file_path, encoding="utf-8-sig")
        songs.columns = songs.columns.str.strip()
        if 'Track Name' not in songs.columns or 'Artist Name(s)' not in songs.columns:
            raise ValueError("CSV must contain 'Track Name' and 'Artist Name(s)' columns")
        if songs.empty:
            raise ValueError("CSV contains no tracks to add to a playlist")
    except Exception as e:
        raise Exception(f"Failed to read CSV file: {str(e)}")

    try:
        current_user = sp.current_user()
        user_id = current_user['id']
        print(f"Authenticated Spotify user ID: {user_id}")
        playlist = sp._post(
            "me/playlists",
            payload={"name": playlist_name, "public": False}
        )
        print(
            "Created playlist:"
            f" id={playlist['id']}"
            f" owner={playlist['owner']['id']}"
            f" public={playlist.get('public')}"
        )
    except Exception as e:
        raise Exception(f"Failed to create playlist: {str(e)}")

    uri_column = None
    for candidate in ("Spotify URI", "Track URI"):
        if candidate in songs.columns:
            uri_column = candidate
            break

    if uri_column:
        print(f"Using direct track URIs from CSV column: {uri_column}")
        track_uris = songs[uri_column].dropna().astype(str).tolist()
        not_found = []
    else:
        track_uris = []
        not_found = []

        print("No URI column found in CSV, falling back to Spotify search.")
        print("Searching for songs...")
        for _, row in tqdm(songs.iterrows(), total=len(songs)):
            query = f"{row['Track Name']} {row['Artist Name(s)']}"
            try:
                results = sp.search(q=query, type='track', limit=1)
                if results['tracks']['items']:
                    track_uris.append(results['tracks']['items'][0]['uri'])
                else:
                    not_found.append(f"{row['Track Name']} by {row['Artist Name(s)']}")
                time.sleep(0.1)
            except Exception as e:
                print(f"Error searching for {query}: {str(e)}")
                continue

    if track_uris:
        headers = {
            "Authorization": f"Bearer {token_info['access_token']}",
            "Content-Type": "application/json",
        }
        test_payload = {"uris": ["spotify:track:4uLU6hMCjMI75M1A2tKUQC"]}
        response = requests.post(
            f"https://api.spotify.com/v1/playlists/{playlist['id']}/tracks",
            headers=headers,
            json=test_payload,
            timeout=30,
        )
        print(f"Raw add-tracks status: {response.status_code}")
        try:
            print(f"Raw add-tracks response: {response.json()}")
        except ValueError:
            print(f"Raw add-tracks response text: {response.text}")

    print("\nPlaylist created successfully!")
    print(f"Total tracks found: {len(track_uris)}")
    print(f"Tracks not found: {len(not_found)}")
    if not_found:
        print("\nThe following tracks were not found:")
        for track in not_found:
            print(f"- {track}")

    return playlist['external_urls']['spotify']


if __name__ == "__main__":
    load_local_env()

    CLIENT_ID = os.getenv('CLIENT_ID')
    CLIENT_SECRET = os.getenv('CLIENT_SECRET')
    REDIRECT_URI = os.getenv('REDIRECT_URI', 'http://127.0.0.1:8888/callback')
    FILE_PATH = os.getenv('SPOTIFY_CSV_PATH')
    PLAYLIST_NAME = os.getenv('PLAYLIST_NAME', 'My CSV Playlist')

    if not CLIENT_ID or not CLIENT_SECRET:
        print("Error: Set CLIENT_ID and CLIENT_SECRET in your .env file or environment variables.")
        raise SystemExit(1)

    if not FILE_PATH:
        print("Error: Set SPOTIFY_CSV_PATH in your .env file or environment variables.")
        raise SystemExit(1)

    print("Starting Spotify playlist creation with:")
    print(f"CLIENT_ID={CLIENT_ID}")
    print(f"REDIRECT_URI={REDIRECT_URI}")
    print(f"SPOTIFY_CSV_PATH={FILE_PATH}")

    try:
        playlist_url = create_spotify_playlist(
            FILE_PATH,
            PLAYLIST_NAME,
            CLIENT_ID,
            CLIENT_SECRET,
            REDIRECT_URI
        )
        print(f"\nPlaylist URL: {playlist_url}")
    except Exception as e:
        print(f"Error: {str(e)}")
