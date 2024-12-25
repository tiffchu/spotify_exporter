import pandas as pd
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import time
from tqdm import tqdm
from dotenv import load_dotenv
import os

load_dotenv()  # Load environment variables from .env file

CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
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
        sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            scope="playlist-modify-public"
        ))
    except Exception as e:
        raise Exception(f"Failed to authenticate with Spotify: {str(e)}")

    # Load the CSV file
    try:
        songs = pd.read_csv(file_path)
        if 'Track Name' not in songs.columns or 'Artist Name(s)' not in songs.columns:
            raise ValueError("CSV must contain 'Track Name' and 'Artist Name(s)' columns")
    except Exception as e:
        raise Exception(f"Failed to read CSV file: {str(e)}")

    # Create playlist
    try:
        user_id = sp.current_user()['id']
        playlist = sp.user_playlist_create(user_id, name=playlist_name, public=True)
    except Exception as e:
        raise Exception(f"Failed to create playlist: {str(e)}")

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
            
            # Add delay to avoid rate limiting
            time.sleep(0.1)
        except Exception as e:
            print(f"Error searching for {query}: {str(e)}")
            continue

    # Add tracks to playlist in batches
    if track_uris:
        try:
            # Spotify API limits: maximum 100 tracks per request
            batch_size = 100
            for i in range(0, len(track_uris), batch_size):
                batch = track_uris[i:i + batch_size]
                sp.playlist_add_items(playlist['id'], batch)
                time.sleep(1)  # Add delay between batch uploads
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
    CLIENT_ID = '92a4d52030df43c0a515ad2862140b4e'
    CLIENT_SECRET = '24257d2c8540441f9b1170d91697927d'
    REDIRECT_URI = 'http://localhost:8888/callback'
    FILE_PATH = '/Users/Tiffany/Downloads/liked_songs.csv'
    PLAYLIST_NAME = 'My CSV Playlist'

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