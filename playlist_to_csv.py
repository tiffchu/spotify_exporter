import pandas as pd
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import time
from tqdm import tqdm
from dotenv import load_dotenv
import os
import csv

load_dotenv()  # environment variables from .env file

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id = os.getenv('CLIENT_ID'),
    client_secret = os.getenv('CLIENT_SECRET'),
    redirect_uri='http://localhost:8888/callback',
    scope='user-library-read'
))

# liked songs
def get_liked_songs(limit=50):
    results = []
    offset = 0
    total = sp.current_user_saved_tracks(limit=1)['total']  # get total liked songs

    with tqdm(total=total, desc='Fetching liked songs') as pbar:
        while offset < total:
            response = sp.current_user_saved_tracks(limit=limit, offset=offset)
            items = response['items']
            if not items:
                break

            for item in items:
                track = item['track']
                results.append({
                    'Track Name': track['name'],
                    'Artist(s)': ', '.join([artist['name'] for artist in track['artists']]),
                    'Album': track['album']['name'],
                    'Release Date': track['album']['release_date'],
                    'Duration (ms)': track['duration_ms'],
                    'Explicit': track['explicit'],
                    'Popularity': track['popularity'],
                    'Track ID': track['id'],
                    'Track URI': track['uri'],
                    'Spotify URL': track['external_urls']['spotify'],
                    'Added At': item['added_at']
                })

            offset += limit
            pbar.update(len(items))

    return results

# Save to CSV
def save_to_csv(tracks, filename='liked_songs2025.csv'):
    keys = tracks[0].keys() if tracks else []
    with open(filename, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(tracks)
    print(f"Saved {len(tracks)} songs to {filename}")

if __name__ == '__main__':
    liked_tracks = get_liked_songs()
    save_to_csv(liked_tracks)
