#!/usr/bin/python3

import re
import unicodedata
import urllib.request
import os
from bs4 import BeautifulSoup
import time

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
    if currtrack % 300 == 0:
        print(f"Processed {currtrack} tracks. Taking a 60 second break...")
        time.sleep(60)
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
    filename = artist.replace(" ", "-").replace("/", "-") + "_" + title.replace(" ", "-").replace("/", "-")
    filename = slugify(filename) + ".mp3"
    if os.path.exists(filename):
        f = open(filenamewo+".m3u", "a+", encoding="utf-8")
        f.write(filename + "\n")
        f.close()