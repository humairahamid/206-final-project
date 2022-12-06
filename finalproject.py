import unittest
import sqlite3
import json
import os
import requests
from bs4 import BeautifulSoup
import re

SPOTIFY_CLIENT_ID = '9a39ed37594746adb22fd7d21861d0d7'
SPOTIFY_CLIENT_SECRET = 'bb1b23ffebfc46cb863f28d9a410fedd'
SPOTIFY_AUTH_URL = 'https://accounts.spotify.com/api/token'
SPOTIFY_BASE_URL = 'https://api.spotify.com/v1/'

LASTFM_API_key = '6580d4a5940a4714ed0990d3bc4083a2'
LASTFM_Shared_secret = '10f7e2fc26589318d0adad5a4c612e55'

albums = []

"""

open_database(db_name)
----------------------------

creates the cursor and connection to the database
to be used throughout the program

"""

def open_database(db_name):
    path = os.path.dirname(os.path.abspath(__file__))
    conn = sqlite3.connect(path+'/'+db_name)
    cur = conn.cursor()
    return cur, conn


"""

read_spotify_data(uri)
----------------------------

reads in the spotify data from the api, setting it
up to be used to make tables

credit to https://stmorse.github.io/journal/spotify-api.html
for helping us get started :)

"""

def read_spotify_data(uri):

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

    # Get ID
    # https://open.spotify.com/playlist/1GVezl4vnm9QuMQs5Wg3oa

    # actual GET request with proper header
    r = requests.get(SPOTIFY_BASE_URL + 'playlists/' + uri + "/tracks", headers=spotify_headers)
    data = r.json()

    return data

"""

make_albums_table(cur, conn)
----------------------------

taylor swift albums are receieved from the lastfm api

if an album name is not currently in the albums list, that name
will be appended to the album list

once the list is made, the items from the list will be inserted
into the Albums table

"""

def make_albums_table(cur, conn):

    r = requests.get("http://ws.audioscrobbler.com/2.0/?method=artist.gettopalbums&artist=Taylor+Swift&api_key=" + LASTFM_API_key + "?limit=200&format=json")
    data = r.json()

    for item in data["topalbums"]["album"]:
        albums.append(item["name"].lower())
    albums.append("no album")

    cur.execute("CREATE TABLE IF NOT EXISTS Albums (id INTEGER PRIMARY KEY, name TEXT)")

    # Query the data into 2 parts
    cur.execute("SELECT COUNT(*) as row_count FROM Albums")
    row_count = cur.fetchall()[0][0]
    print(row_count, "rows in Albums")
    if row_count >= 0 and row_count < 25:
        newdata = albums[0:25]
        i = 0
    elif row_count >= 25 and row_count < 50:
        newdata = albums[25:50]
        i = 25
    elif row_count >= 50 and row_count < 51:
        newdata = albums[50:]
        i = 50
    else:
        print("0 new albums added to Albums") 
        return None

    count = 0
    for x in range(len(newdata)):
        cur.execute("INSERT OR IGNORE INTO Albums (id, name) VALUES (?,?)", (i, newdata[x].lower()))
        count += 1
        i += 1
    
    conn.commit()

    print(count, "new albums added to Albums")

"""

make_aayana_table(data, cur, conn)
----------------------------

reads in data from aayana's taylor swift ranked playlist
using the spotify api

stores the album id and track name for each song in order

1 = absolute favorite
100 = 100th favorite

"""

def make_aayana_table(data, cur, conn):
    cur.execute("CREATE TABLE IF NOT EXISTS AayanasTSSongs (track_name TEXT, album_id INTEGER)") 
    
    # Query the data into 4 parts
    cur.execute("SELECT COUNT(*) as row_count FROM AayanasTSSongs")
    row_count = cur.fetchall()[0][0]
    print(row_count, "rows in AayanasTSRankings")
    if row_count == 25:
        newdata = data["items"][25:50]
    elif row_count == 50:
        newdata = data["items"][50:75]
    elif row_count == 75:
        newdata = data["items"][75:100]
    elif row_count == 100:
        print("0 new tracks added to AayanasTSSongs") 
        return None
    else:
        newdata = data["items"][:25]

    count = 0
    for x in range(len(newdata)):
        if newdata[x]["track"]["is_local"] == False: # ignore local files
            
            track_name = newdata[x]["track"]["name"]

            # handle the many variations in track names
            if "(deluxe edition)" in newdata[x]["track"]["album"]["name"]:
                index = newdata[x]["track"]["album"]["name"].find("(deluxe edition)")
                album_id = (newdata[x]["track"]["album"]["name"])[:index].strip()
            elif "(3am edition)" in newdata[x]["track"]["album"]["name"]:
                index = newdata[x]["track"]["album"]["name"].find("(3am edition)")
                album_id = (newdata[x]["track"]["album"]["name"])[:index].strip()
            else:
                album_id = newdata[x]["track"]["album"]["name"]

            cur.execute("SELECT id FROM Albums WHERE name = ?", (album_id.lower(), ))
            album_id = cur.fetchone()[0]

            cur.execute("INSERT OR IGNORE INTO AayanasTSSongs (track_name, album_id) VALUES (?,?)", (track_name.lower(), album_id))

            count += 1

    conn.commit() 
    print(count, "new tracks added to AayanasTSSongs") 

"""

read_website_data()
----------------------------

scrapes data from https://andrewledbetter.com/taylor-swifts-songs-ranked-by-a-40-something-professor/
to be used throughout the program

"""

def read_website_data():
    url = "https://andrewledbetter.com/taylor-swifts-songs-ranked-by-a-40-something-professor/"
    page = requests.get(url)
    soup = BeautifulSoup(page.content, "html.parser")
    data = []
    album = []
    tracks = []

    stags = soup.find_all("strong")

    for tag in stags:
        song = re.findall("\d+. (\w.+):" ,tag.text)
        if song:
            track_name = song[0].split("(")[0].strip(")") # handle the syntax of the website
            album_name = song[0].split("(")[1].strip(")")
            tracks.append(track_name.lower()) 
            if album_name.lower() in albums and album_name.lower() not in album:
                album.append(album_name.lower())
            tup = (track_name.lower().strip(), album_name.lower().strip())
            data.append(tup)

    # sort the rankings in the same order as aayana did with hers :)
    rankings = []
    for x in range(len(data)-1, -1, -1):
        rankings.append(data[x])
    
    return rankings

"""

make_website_table(data, cur, conn)
----------------------------

create a table of rankings from the above website
based on the data that has been scraped

similar to the aayana table

"""

def make_website_table(data, cur, conn):
    cur.execute("CREATE TABLE IF NOT EXISTS WebsiteRankings (track_name TEXT, album_id INTEGER)") 

    newdata = []
    for tup in data:
        if tup[1] in albums:
            newdata.append(tup)

    # Query the data
    cur.execute("SELECT COUNT(*) as row_count FROM WebsiteRankings")
    row_count = cur.fetchall()[0][0]
    print(row_count, "rows in WebsiteRankings")
    if row_count < 25 and row_count >= 0:
        newdata = newdata[:25]
    elif row_count < 50 and row_count >= 25:
        newdata = newdata[25:50]
    elif row_count < 75 and row_count >= 50:
        newdata = newdata[50:75]
    elif row_count < 100 and row_count >= 75:
        newdata = newdata[75:100]
    elif row_count < 125 and row_count >= 100:
        newdata = newdata[100:125]
    elif row_count < 150 and row_count >= 125:
        newdata = newdata[125:150]
    elif row_count < 175 and row_count >= 150:
        newdata = newdata[150:175]
    elif row_count < 200 and row_count >= 175:
        newdata = newdata[175:200]
    else:
        print("0 new tracks added to WebsiteRankings") 
        cur.execute("DELETE FROM WebsiteRankings WHERE track_name = 'only the young' AND album_id = '50'")
        return None 

    count = 0
    i = 0

    while i < len(newdata):
        for pair in newdata:
            track_name = pair[0]
            album_id = pair[1]

            for name in albums:
                if album_id == name:
                    cur.execute("SELECT id FROM Albums WHERE name = ?", (album_id,))
                    album_id = cur.fetchall()
                    if len(album_id) != 0:
                        cur.execute("INSERT OR IGNORE INTO WebsiteRankings (track_name, album_id) VALUES (?, ?)", (track_name.lower(), album_id[0][0]))
                        count += 1
            i += 1

    print(count, "new songs added to WebsiteRankings")
    
    conn.commit()

"""

read_lastfm_data()
----------------------------

reads in data from the lastfm api of top tracks
by country, in this case, the united states

only records the top 100 tracks

"""

def read_lastfm_data():
    r = requests.get("http://ws.audioscrobbler.com/2.0/?method=geo.gettoptracks&country=" + "united states" + "&api_key=" + LASTFM_API_key + "&limit=100&format=json")
    data = r.json()

    return data

"""

make_last_fm_table(data, cur, conn)
----------------------------

create a table of the data from the lastfm
top 100 charts in the united states according
to the collected lastfm api data.

specifically collects track name, artist name, and total listeners

"""

def make_last_fm_table(data, cur, conn):
    cur.execute("CREATE TABLE IF NOT EXISTS LastfmCharts(track_name TEXT, artist_name TEXT, listeners INTEGER)") 
    
    cur.execute("SELECT COUNT(*) as row_count FROM LastfmCharts")
    row_count = cur.fetchall()[0][0]
    print(row_count, "rows in LastfmCharts")
    if row_count < 25 and row_count >= 0:
        newdata =data["tracks"]["track"][row_count:25]
    elif row_count < 50 and row_count >= 25:
        newdata = data["tracks"]["track"][row_count:50]
    elif row_count < 75 and row_count >= 50:
        newdata = data["tracks"]["track"][row_count:75]
    elif row_count < 100 and row_count >= 75:
        newdata = data["tracks"]["track"][row_count:100]
    else:
        print("0 new tracks added to LastfmCharts") 
        return None

    count = 0
    for item in newdata:
        track_name = item["name"]
        artist_name = item["artist"]["name"]
        listeners = item["listeners"]

        cur.execute("INSERT OR IGNORE INTO LastfmCharts (track_name, artist_name, listeners) VALUES (?, ?, ?)", (track_name, artist_name, listeners))
        count += 1

    print(count, "new songs added to LastfmCharts")

    conn.commit()


def main():
    cur, conn = open_database('music.db')
    make_albums_table(cur, conn)

    song_data = read_spotify_data("1GVezl4vnm9QuMQs5Wg3oa")
    website_data = read_website_data()
    lastfm_data = read_lastfm_data()

    make_aayana_table(song_data, cur, conn)
    make_website_table(website_data, cur, conn)
    make_last_fm_table(lastfm_data, cur, conn)

main()