# spotify_exporter - moves all your liked songs into a playlist 

workaround to using spotify premium when blacklisted for using xmanager. I just make a new free trial spotify account for however long the trial lasts for, then I make a csv of all my liked songs from my original spotify account, and convert them into a sharable playlist using these scripts. 

### Prereqs
1. You must be a premium user with a [Spotify Developer Dashboard](https://developer.spotify.com/dashboard) account
2. In the developer dashboard, in your app under **Redirect URIs**, add exactly:
```
   http://127.0.0.1:8888/callback
```
3. Add the email address of the Spotify account you'll log in with in the user management tab on the dashboard
4. Save, then open the app and copy your **Client ID** and **Client Secret**

## Setup
1. Copy `.env.example` to `.env`, make an app on developer.spotify.com to get keys. can also export client_id, client_secret="123abc" in terminal
2. Fill in your Spotify API credentials in `.env`
3. Install dependencies: `pip install -r requirements.txt`
4. turn liked songs into a csv file, run playlist_to_csv.py
5. run main.py to get url to playlist with all liked songs

## Windows Bash note

If not using the .env file AND you are using Git Bash or another Bash-style shell on Windows, use `export` so `main.py` can see the CSV path:

```bash
export SPOTIFY_CSV_PATH='C:\Users\tiffa\Downloads\Liked_Songs.csv'
C:/Users/tiffa/miniforge3/python.exe c:/Users/tiffa/Desktop/projects/spotify_exporter/main.py
```

Or set it for a single command:

```bash
SPOTIFY_CSV_PATH='C:\Users\tiffa\Downloads\Liked_Songs.csv' C:/Users/tiffa/miniforge3/python.exe c:/Users/tiffa/Desktop/projects/spotify_exporter/main.py
```

| Variable | Description |
|---|---|
| `CLIENT_ID` | From your Spotify Developer app |
| `CLIENT_SECRET` | From your Spotify Developer app |
| `REDIRECT_URI` | Must match the Redirect URI registered in your app |
| `SPOTIFY_CSV_PATH` | Full path to the CSV file to import |
| `PLAYLIST_NAME` | Name of the playlist that will be created |


## CSV format
 
The CSV must contain one of the following columns:
 
- `Track URI` — values like `spotify:track:xxxxxxxxxxxx` (Exportify default)
- `Track ID` or `id` — bare Spotify track IDs

## Usage
 
```bash
python csv_to_spotify_playlist.py
```
 
On first run, a browser window will open asking you to log in to Spotify and authorize the app. After that, the script will:
 
1. Connect to Spotify
2. Load track URIs from your CSV
3. Create a new playlist with the name from `PLAYLIST_NAME`
4. Add all tracks in batches of 100, with automatic retry on rate limits


## Troubleshooting
 
**403 Forbidden on playlist creation or adding tracks**
Make sure you've added your account under **User Management** in the app dashboard (step 3 above), and that the app owner has Spotify Premium.
 
**Stuck using an old/cached login**
Delete the cached token file in the project folder and re-run:
 
```bash
rm .cache*
```
 
**`SPOTIFY_CSV_PATH is not set` or `PLAYLIST_NAME is not set`**
Double check your `.env` file is in the same folder as the script and has no typos in the variable names.

## Notes
 
- The playlist is created as **private** by default.
- Spotify limits Development Mode apps to 5 users and requires the app owner to have Premium (as of the March 2026 API changes).