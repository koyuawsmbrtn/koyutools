#!/usr/bin/python3

import re
import unicodedata
import urllib.request
import os
import subprocess
import json
import time
from bs4 import BeautifulSoup
import ytmusicapi

yt = ytmusicapi.YTMusic()
f = open("tracks.txt", "r")
tracks = f.readlines()
f.close()
tracknum = len(tracks)
currtrack = 0

os.system("rm -f audio.mp3")
os.system("rm -f audio.jpg")

# Taken from https://github.com/django/django/blob/main/django/utils/text.py
def slugify(value, allow_unicode=False):
    """
    Convert to ASCII if 'allow_unicode' is False. Convert spaces or repeated
    dashes to single dashes. Remove characters that aren't alphanumerics,
    underscores, or hyphens. Convert to lowercase. Also strip leading and
    trailing whitespace, dashes, and underscores.
    """
    value = str(value)
    if allow_unicode:
        value = unicodedata.normalize("NFKC", value)
    else:
        value = (
            unicodedata.normalize("NFKD", value)
            .encode("ascii", "ignore")
            .decode("ascii")
        )
    value = re.sub(r"[^\w\s-]", "", value.lower())
    return re.sub(r"[-\s]+", "-", value).strip("-_")

try:
    f = open("downloaded.txt", "r")
    downloaded = f.readlines()
    f.close()
except:
    downloaded = []

for surl in tracks:
    currtrack = currtrack + 1

    if currtrack % 300 == 0:
        print(f"Processed {currtrack} tracks. Taking a 60 second break...")
        time.sleep(60)

    try:
        trackid = surl.replace("https://open.spotify.com/track/", "").split("?")[0]
    except:
        trackid = surl.replace("https://open.spotify.com/track/", "")
    if not trackid in downloaded:
        print("Track " + str(currtrack) + " of " + str(tracknum) + " (" + trackid.split("\n")[0] + ")")
        if not "http" in surl:
            surl = "https://open.spotify.com/track/" + surl
        print("Downloading...")
        with urllib.request.urlopen(surl) as response:
            r = response.read().decode()
        soup = BeautifulSoup(r, "lxml")
        artist = soup.find("meta", {"name": "music:musician_description"})["content"]
        title = soup.find("meta", {"property": "og:title"})["content"]
        filename = artist.replace(" ", "-").replace("/", "-") + "_" + title.replace(" ", "-").replace("/", "-")
        filename = slugify(filename) + ".mp3"
        if not os.path.exists(filename):
            data = json.loads(soup.find("script", {"type": "application/ld+json"}).contents[0])
            cover = soup.find("meta", {"property": "og:image"})["content"]
            year = data["datePublished"]
            track = soup.find("meta", {"name": "music:album:track"})["content"]
            albumurl = soup.find("meta", {"name": "music:album"})["content"]
            with urllib.request.urlopen(albumurl) as response2:
                r2 = response2.read().decode()
            soup2 = BeautifulSoup(r2, "lxml")
            albumtitle = soup2.find("meta", {"property": "og:title"})["content"]
            album_maxtracks = soup2.find("meta", {"property": "og:description"})["content"].split(" · ")[3].split(" ")[0]
            os.system("wget -O audio.jpg \"" + cover + "\"")
            print(title)
            query = artist + " - " + title
            print(query)
            try:
                videoId = yt.search(query, "songs")[0]["videoId"]
            except:
                videoId = None
            if not videoId == None:
                cmd = ["yt-dlp", "--no-continue", "--add-metadata", "-x", "--prefer-ffmpeg", "--extract-audio", "-v", "--audio-format", "mp3", "--output", "audio.%(ext)s", "https://youtu.be/"+videoId]
            else:
                cmd = ["yt-dlp", "--no-continue", "--add-metadata", "-v", "--prefer-ffmpeg", "--extract-audio", "-v", "--audio-format", "mp3", "--output", "audio.%(ext)s", "ytsearch:\"" + query + "\"", "--no-playlist"]
            subprocess.Popen(cmd, shell=False).wait()
            print("Converting...")
            subprocess.Popen(["lame", "-b", "320", "--ti", "audio.jpg", "--ta", artist, "--tt", title, "--ty", year, "--tl", albumtitle, "--tn", track+"/"+album_maxtracks, "audio.mp3", filename], shell=False).wait()
            os.system("rm audio.mp3")
            os.system("rm audio.jpg")
            print("Done!")
        f = open("downloaded.txt", "a+")
        f.write(trackid + "\n")
        f.close()
