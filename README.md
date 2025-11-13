# spotify_exporter - moves all your liked songs into a playlist 

edit path to .csv file containing spotify songs and edit name of outputted playlist. workaround to using spotify premium when blacklisted for using xmanager

## Setup
1. Copy `.env.example` to `.env`
2. Fill in your Spotify API credentials in `.env`
3. Install dependencies: `pip install -r requirements.txt`
4. turn liked songs into a csv file, run playlist_to_csv.py
5. run main.py to get url to playlist with all liked songs