import csv
import spotipy
from spotipy.oauth2 import SpotifyOAuth

# Replace with your credentials
CLIENT_ID = 'your_spotify_client_id'
CLIENT_SECRET = 'your_spotify_client_secret'
REDIRECT_URI = 'http://localhost:8888/callback'

# access liked songs
SCOPE = 'user-library-read'

#Authenticate
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    redirect_uri=REDIRECT_URI,
    scope=SCOPE
))

# liked songs
def get_liked_songs(limit=50):
    results = []
    offset = 0

    while True:
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
                'Added At': item['added_at'],
                'Spotify URL': track['external_urls']['spotify']
            })
        
        offset += limit

    return results

# Save to CSV
def save_to_csv(tracks, filename='liked_songs.csv'):
    keys = tracks[0].keys() if tracks else []
    with open(filename, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(tracks)
    print(f"Saved {len(tracks)} songs to {filename}")

if __name__ == '__main__':
    liked_tracks = get_liked_songs()
    save_to_csv(liked_tracks)
