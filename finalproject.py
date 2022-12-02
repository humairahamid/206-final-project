import unittest
import sqlite3
import json
import os
import requests
from bs4 import BeautifulSoup
import re

SPOTIFY_CLIENT_ID = '9a39ed37594746adb22fd7d21861d0d7'
SPOTIFY_CLIENT_SECRET = 'bb1b23ffebfc46cb863f28d9a410fedd'

LASTFM_API_key = '6580d4a5940a4714ed0990d3bc4083a2'
LASTFM_Shared_secret = '10f7e2fc26589318d0adad5a4c612e55'

albums = ["Taylor Swift", "Fearless", "Speak Now",
    "Red", "1989", "reputation", "Lover",
    "folklore",
    "evermore", "Midnights", "no album"]

def open_database(db_name):
    path = os.path.dirname(os.path.abspath(__file__))
    conn = sqlite3.connect(path+'/'+db_name)
    cur = conn.cursor()
    return cur, conn


"""

SPOTIFY DATA

API

"""
def read_spotify_data(uri):
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

    # actual GET request with proper header
    r = requests.get(SPOTIFY_BASE_URL + 'playlists/' + uri + "/tracks", headers=spotify_headers)
    data = r.json()

    return data

def make_albums_table(cur, conn):

    cur.execute("DROP TABLE IF EXISTS Albums") 
    cur.execute("CREATE TABLE IF NOT EXISTS Albums (id INTEGER PRIMARY KEY, name TEXT)")

    for x in range(len(albums)):
        cur.execute("INSERT OR IGNORE INTO Albums (id, name) VALUES (?,?)", (x, albums[x].lower()))
    
    conn.commit()
    print("Albums table created") 

def make_aayana_table(data, cur, conn):
    cur.execute("DROP TABLE IF EXISTS AayanasTSSongs") 
    cur.execute("CREATE TABLE IF NOT EXISTS AayanasTSSongs (track_name TEXT, album_id INTEGER)") 
    
    count = 0
    for x in range(len(data["items"])):
        if data["items"][x]["track"]["is_local"] == False: # ignore local files

            if "(" in data["items"][x]["track"]["name"]:
                index = data["items"][x]["track"]["name"].find("(")
                track_name = (data["items"][x]["track"]["name"])[:index].strip()
            else:
                track_name = data["items"][x]["track"]["name"]

            if "(" in data["items"][x]["track"]["album"]["name"]:
                index = data["items"][x]["track"]["album"]["name"].find("(")
                album_id = (data["items"][x]["track"]["album"]["name"])[:index].strip()
            else:
                album_id = data["items"][x]["track"]["album"]["name"]

            cur.execute("SELECT id FROM Albums WHERE name = ?", (album_id.lower(), ))
            album_id = cur.fetchone()[0]

            cur.execute("INSERT OR IGNORE INTO AayanasTSSongs (track_name, album_id) VALUES (?,?)", (track_name.lower(), album_id))

            #print(track_name, "from", album_id) 
            count += 1

    conn.commit() 
    print(count, "tracks added to AayanasTSSongs") 

"""

WEBSITE DATA

Website

"""

def read_website_data():
    url = "https://andrewledbetter.com/taylor-swifts-songs-ranked-by-a-40-something-professor/"
    page = requests.get(url)
    soup = BeautifulSoup(page.content, "html.parser")
    data = []
    albums = []
    tracks = []

    stags = soup.find_all("strong")

    for tag in stags:
        song = re.findall("\d+. (\w.+):" ,tag.text)
        if song:
            temp = song[0].split("(")
            tracks.append(temp[0].strip())
            albums.append(temp[1].strip(")"))
    
    for x in range(len(tracks)-1, -1, -1):
        tup = (tracks[x].lower(), albums[x].lower())
        data.append(tup)

    return data

def make_website_table(data, cur, conn):
    cur.execute("DROP TABLE IF EXISTS WebsiteRankings") 
    cur.execute("CREATE TABLE IF NOT EXISTS WebsiteRankings (track_name TEXT, album_id INTEGER)") 

    count = 0
    
    for pair in data:
        track_name = pair[0]
        album_id = pair[1]

        for item in albums:
            if item.lower() in album_id:
                cur.execute("SELECT id FROM Albums WHERE name = ?", (album_id,))
                album_id = cur.fetchall()
                if album_id: # we're just looking at top 100
                    cur.execute("INSERT OR IGNORE INTO WebsiteRankings (track_name, album_id) VALUES (?, ?)", (track_name.lower(), album_id[0][0]))
                    count += 1
    
    print(count, "songs added to WebsiteRankings")
    
    conn.commit()

"""

LASTFM DATA

Extra Credit API

"""

def read_lastfm_data():
    r = requests.get("https://ws.audioscrobbler.com/2.0/?method=artist.gettoptracks&artist=Taylor+Swift&api_key=" + LASTFM_API_key + "&limit=150&format=json")
    data = r.json()
    return data

def make_last_fm_table(data, cur, conn):
    cur.execute("DROP TABLE IF EXISTS LastfmRankings") 
    cur.execute("CREATE TABLE IF NOT EXISTS LastfmRankings (track_name TEXT, playcount INTEGER, album_id INTEGER)") 

    count = 0

    for song in data["toptracks"]["track"]:

        if "(" in song["name"]:
            index = song["name"].find("(")
            track_name = (song["name"].lower())[:index].strip()
        else:
            track_name = song["name"].lower()
        
        playcount = song["playcount"]
        album_id = ""

        cur.execute("SELECT album_id FROM WebsiteRankings WHERE track_name = ?", (track_name,))
        album_id = cur.fetchall()
        if album_id:
            cur.execute("INSERT OR IGNORE INTO LastfmRankings (track_name, playcount, album_id) VALUES (?, ?, ?)", (track_name.lower(), playcount, album_id[0][0]))
            count += 1
        
        #print(track_name, playcount)
    
    print(count, "songs added to LastfmRankings")



    conn.commit()


def main():
    cur, conn = open_database('music.db')

    spotify_data = read_spotify_data("1GVezl4vnm9QuMQs5Wg3oa")
    website_data = read_website_data()
    lastfm_data = read_lastfm_data()

    make_albums_table(cur, conn)
    make_aayana_table(spotify_data, cur, conn)
    make_website_table(website_data, cur, conn)
    make_last_fm_table(lastfm_data, cur, conn)


main()