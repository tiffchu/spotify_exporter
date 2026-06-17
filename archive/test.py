#turn all liked songs into csv then into playlist

#ignore this file


import pandas as pd
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import time
from tqdm import tqdm
from datetime import datetime
import os
from pathlib import Path
from dotenv import load_dotenv

CSV_COLUMNS = [
    'Track Name',
    'Artist Name(s)',
    'Album',
    'Added At',
    'Duration (ms)',
    'Spotify URI',
]

def load_local_env():
    env_path = Path(__file__).resolve().parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)

def export_liked_songs_to_csv(sp, output_path=None):
    """
    Export user's liked songs to a CSV file.
    
    Parameters:
    sp (spotipy.Spotify): Authenticated Spotify client
    output_path (str): Optional path for CSV file. If None, creates in current directory
    
    Returns:
    str: Path to the created CSV file
    """
    if output_path is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = f'liked_songs_{timestamp}.csv'

    print("Fetching liked songs...")
    test = sp.current_user_saved_tracks(limit=1, offset=0)
    print(f"DEBUG total liked songs reported by API: {test['total']}")
    print(f"DEBUG items returned: {len(test['items'])}")
    tracks = []
    offset = 0
    limit = 50  # Maximum allowed by Spotify API
    
    while True:
        results = sp.current_user_saved_tracks(limit=limit, offset=offset)
        if not results['items']:
            break
            
        for item in tqdm(results['items'], desc=f"Processing songs {offset+1}-{offset+len(results['items'])}"):
            track = item['track']
            artist_names = ', '.join([artist['name'] for artist in track['artists']])
            
            track_data = {
                'Track Name': track['name'],
                'Artist Name(s)': artist_names,
                'Album': track['album']['name'],
                'Added At': item['added_at'],
                'Duration (ms)': track['duration_ms'],
                'Spotify URI': track['uri']
            }
            tracks.append(track_data)
        
        offset += limit
        time.sleep(0.1)  # Rate limiting
    
    # Create DataFrame and save to CSV
    df = pd.DataFrame(tracks, columns=CSV_COLUMNS)
    df.to_csv(output_path, index=False)
    print(f"\nExported {len(tracks)} liked songs to {output_path}")
    return output_path

def create_spotify_playlist(file_path, playlist_name, client_id, client_secret, redirect_uri):
    """
    Create a Spotify playlist from a CSV file containing songs.
    
    Parameters:
    file_path (str): Path to the CSV file containing songs
    playlist_name (str): Name for the new playlist
    client_id (str): Spotify API client ID
    client_secret (str): Spotify API client secret
    redirect_uri (str): Redirect URI for Spotify authentication
    
    Returns:
    str: URL of the created playlist
    """

    try:
        auth_manager = SpotifyOAuth(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            scope="playlist-modify-public playlist-modify-private user-library-read",
            open_browser=False,
            show_dialog=True
        )
        print("\nOpen this Spotify authorization URL in your browser:")
        print(auth_manager.get_authorize_url())
        print("")
        sp = spotipy.Spotify(auth_manager=auth_manager)

        me = sp.current_user()
        print(f"Logged in as: {me['display_name']} ({me['id']}) | Email: {me.get('email', 'N/A')}")
    except Exception as e:
        raise Exception(f"Failed to authenticate with Spotify: {str(e)}")

    # Load the CSV file
    try:
        songs = pd.read_csv(file_path)
        if 'Track Name' not in songs.columns or 'Artist Name(s)' not in songs.columns:
            raise ValueError("CSV must contain 'Track Name' and 'Artist Name(s)' columns")
        if songs.empty:
            raise ValueError("CSV contains no tracks to add to a playlist")
    except Exception as e:
        raise Exception(f"Failed to read CSV file: {str(e)}")

    # Create playlist
    try:
        current_user = sp.current_user()
        user_id = current_user['id']
        print(f"Authenticated Spotify user ID: {user_id}")
        playlist = sp._post(
            "me/playlists",
            payload={"name": playlist_name, "public": True}
        )
    except Exception as e:
        raise Exception(f"Failed to create playlist: {str(e)}")

    # If we have Spotify URIs in the CSV, use them directly
    if 'Spotify URI' in songs.columns:
        track_uris = songs['Spotify URI'].tolist()
        not_found = []
    else:
        # Search for songs and collect URIs
        track_uris = []
        not_found = []
        
        print("Searching for songs...")
        for index, row in tqdm(songs.iterrows(), total=len(songs)):
            query = f"{row['Track Name']} {row['Artist Name(s)']}"
            try:
                results = sp.search(q=query, type='track', limit=1)
                if results['tracks']['items']:
                    track_uris.append(results['tracks']['items'][0]['uri'])
                else:
                    not_found.append(f"{row['Track Name']} by {row['Artist Name(s)']}")
                
                time.sleep(0.1)  # Rate limiting
            except Exception as e:
                print(f"Error searching for {query}: {str(e)}")
                continue

    # Add tracks to playlist in batches
    if track_uris:
        try:
            batch_size = 100
            for i in range(0, len(track_uris), batch_size):
                batch = track_uris[i:i + batch_size]
                sp._post(
                    f"playlists/{playlist['id']}/tracks",
                    payload={"uris": batch}
                )
                time.sleep(1)
        except Exception as e:
            raise Exception(f"Failed to add tracks to playlist: {str(e)}")

    # Print summary
    print(f"\nPlaylist created successfully!")
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
    PLAYLIST_NAME = os.getenv('PLAYLIST_NAME', 'My Liked Songs Playlist')
    INPUT_CSV_PATH = os.getenv('SPOTIFY_CSV_PATH')
    OUTPUT_CSV_PATH = os.getenv('SPOTIFY_EXPORT_PATH')

    if not CLIENT_ID or not CLIENT_SECRET:
        print("Error: Set CLIENT_ID and CLIENT_SECRET in your .env file or environment variables.")
        raise SystemExit(1)

    if not OUTPUT_CSV_PATH:
        print("Error: Set SPOTIFY_EXPORT_PATH in your .env file or environment variables.")
        raise SystemExit(1)

    print("Starting Spotify export with:")
    print(f"CLIENT_ID={CLIENT_ID}")
    print(f"REDIRECT_URI={REDIRECT_URI}")
    print(f"SPOTIFY_EXPORT_PATH={OUTPUT_CSV_PATH}")
    if INPUT_CSV_PATH:
        print(f"SPOTIFY_CSV_PATH={INPUT_CSV_PATH}")

    try:
        # Initialize Spotify client
        auth_manager = SpotifyOAuth(
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            redirect_uri=REDIRECT_URI,
            scope="playlist-modify-public playlist-modify-private user-library-read",
            open_browser=False,
            show_dialog=True
        )
        print("\nOpen this Spotify authorization URL in your browser:")
        print(auth_manager.get_authorize_url())
        print("After Spotify redirects and the page fails to load, copy the full URL and paste it below.")
        redirected_url = input("Paste the full redirected URL here: ").strip()
        code = auth_manager.parse_response_code(redirected_url)
        token_info = auth_manager.get_access_token(code=code, check_cache=False)
        sp = spotipy.Spotify(auth=token_info["access_token"])

        me = sp.current_user()
        print(f"Logged in as: {me['display_name']} ({me['id']})")
        
        # Export liked songs to CSV
        csv_path = export_liked_songs_to_csv(sp, OUTPUT_CSV_PATH)

        exported_songs = pd.read_csv(csv_path)
        if exported_songs.empty:
            print("No liked songs were found for this Spotify account, so no playlist was created.")
            raise SystemExit(0)
        
        # Create playlist from the exported CSV
        playlist_url = create_spotify_playlist(
            csv_path,
            PLAYLIST_NAME,
            CLIENT_ID,
            CLIENT_SECRET,
            REDIRECT_URI
        )
        print(f"\nPlaylist URL: {playlist_url}")
        
    except Exception as e:
        print(f"Error: {str(e)}")
