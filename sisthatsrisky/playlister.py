#!/usr/bin/python3

import urllib.request
import os
from bs4 import BeautifulSoup

arg = os.sys.argv[1]
f = open(arg, "r")
tracks = f.readlines()
f.close()
tracknum = len(tracks)
currtrack = 0

filenamewo = arg.split(".")[0]

os.system("rm -f "+filenamewo+".m3u")

for surl in tracks:
    currtrack = currtrack + 1
    try:
        trackid = surl.replace("https://open.spotify.com/track/", "").split("?")[0]
    except:
        trackid = surl.replace("https://open.spotify.com/track/", "")
    print("Track " + str(currtrack) + " of " + str(tracknum) + " (" + trackid.split("\n")[0] + ")")
    if not "http" in surl:
        surl = "https://open.spotify.com/track/" + surl
    print("Downloading...")
    with urllib.request.urlopen(surl) as response:
        r = response.read().decode()
    soup = BeautifulSoup(r, "lxml")
    artist = soup.find("meta", {"name": "music:musician_description"})["content"]
    title = soup.find("meta", {"property": "og:title"})["content"]
    filename = artist.replace(" ", "-").replace("/", "-") + "_" + title.replace(" ", "-").replace("/", "-") + ".mp3"
    if os.path.exists(filename):
        f = open(filenamewo+".m3u", "a+", encoding="utf-8")
        f.write(filename + "\n")
        f.close()