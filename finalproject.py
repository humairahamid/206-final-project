import unittest
import sqlite3
import json
import os
import requests
from bs4 import BeautifulSoup

SPOTIFY_CLIENT_ID = '9a39ed37594746adb22fd7d21861d0d7'
SPOTIFY_CLIENT_SECRET = 'bb1b23ffebfc46cb863f28d9a410fedd'

LASTFM_API_key = '6580d4a5940a4714ed0990d3bc4083a2'
LASTFM_Shared_secret = '10f7e2fc26589318d0adad5a4c612e55'

def open_database(db_name):
    path = os.path.dirname(os.path.abspath(__file__))
    conn = sqlite3.connect(path+'/'+db_name)
    cur = conn.cursor()
    return cur, conn

def read_spotify_data():
    SPOTIFY_AUTH_URL = 'https://accounts.spotify.com/api/token'

    # POST
    spotify_auth_response = requests.post(SPOTIFY_AUTH_URL, {
        'grant_type': 'client_credentials',
        'client_id': SPOTIFY_CLIENT_ID,
        'client_secret': SPOTIFY_CLIENT_SECRET,
    })

    # convert the response to JSON
    spotify_auth_response_data = spotify_auth_response.json()

    # save the access token
    spotify_access_token = spotify_auth_response_data['access_token']

    spotify_headers = {
        'Authorization': 'Bearer {token}'.format(token=spotify_access_token)
    }

    # base URL of all Spotify API endpoints
    SPOTIFY_BASE_URL = 'https://api.spotify.com/v1/'

    # Get ID
    # https://open.spotify.com/playlist/1GVezl4vnm9QuMQs5Wg3oa
    # 37i9dQZF1EUMDoJuT8yJsl

    # actual GET request with proper header
    r = requests.get(SPOTIFY_BASE_URL + 'playlists/' + "1GVezl4vnm9QuMQs5Wg3oa" + "/tracks", headers=spotify_headers)
    data = r.json()

    return data

def make_aayana_table(data, cur, conn):
    cur.execute("DROP TABLE IF EXISTS AayanasTSSongs") 
    cur.execute("CREATE TABLE IF NOT EXISTS AayanasTSSongs (track_name TEXT, album_id INTEGER)") 
    
    # print results and update table with tracks
    count = 0
    for x in range(len(data["items"])):
        if data["items"][x]["track"]["is_local"] == False: # ignore local files

            track_name = data["items"][x]["track"]["name"]
            album_id = data["items"][x]["track"]["album"]["name"]

            cur.execute("SELECT id FROM Albums WHERE name = ?", (album_id, ))
            album_id = cur.fetchone()[0]

            cur.execute("INSERT OR IGNORE INTO AayanasTSSongs (track_name, album_id) VALUES (?,?)", (track_name, album_id))

            print(track_name, "from", album_id) 
            count += 1

    conn.commit() 
    print(count, "tracks added to AayanasTSSongs") 
 

"""
LASTFM DATA

name, listeners, playcount, summary 

"""

def read_lastfm_data():
    url = "https://ws.audioscrobbler.com/2.0/?method=artist.getinfo&artist=Taylor+Swift&api_key=" + LASTFM_API_key + "&format=json"
    page = requests.get(url)
    data = page.json()
    print(data)

def read_genius_data():
    url = "https://music.apple.com/us/artist/taylor-swift/159260351"
    resp = requests.get(url)
    soup = BeautifulSoup(resp.content, "html.parser")
    tags = soup.find_all('p')
    print(tags)

def main():
    spotify_data = read_spotify_data()
    scur, sconn = open_database('music.db')
    make_aayana_table(spotify_data, scur, sconn)

main()