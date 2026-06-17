# spotify_exporter - moves all your liked songs into a playlist 

edit path to .csv file containing spotify songs and edit name of outputted playlist. workaround to using spotify premium when blacklisted for using xmanager

## Setup
1. Copy `.env.example` to `.env`, make an app on developer.spotify.com to get keys. can also export client_id, client_secret="123abc" in terminal
2. Fill in your Spotify API credentials in `.env`
3. Install dependencies: `pip install -r requirements.txt`
4. turn liked songs into a csv file, run playlist_to_csv.py
5. run main.py to get url to playlist with all liked songs

For `test.py`, use separate paths so the export step does not overwrite the CSV you want to import later:

```env
SPOTIFY_CSV_PATH=C:/Users/tiffa/Downloads/Liked_Songs.csv
SPOTIFY_EXPORT_PATH=C:/Users/tiffa/Downloads/Liked_Songs_export.csv
```

`test.py` writes to `SPOTIFY_EXPORT_PATH`. `main.py` and `test2.py` read from `SPOTIFY_CSV_PATH`.

## Windows Bash note

If you are using Git Bash or another Bash-style shell on Windows, use `export` so `main.py` can see the CSV path:

```bash
export SPOTIFY_CSV_PATH='C:\Users\tiffa\Downloads\Liked_Songs.csv'
C:/Users/tiffa/miniforge3/python.exe c:/Users/tiffa/Desktop/projects/spotify_exporter/main.py
```

Or set it for a single command:

```bash
SPOTIFY_CSV_PATH='C:\Users\tiffa\Downloads\Liked_Songs.csv' C:/Users/tiffa/miniforge3/python.exe c:/Users/tiffa/Desktop/projects/spotify_exporter/main.py
```
