#!/usr/bin/python3

import re
import unicodedata
import urllib.request
import os
import subprocess
import json
import time
import sys
from bs4 import BeautifulSoup
import ytmusicapi
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TIT2, TPE1, TALB, APIC
import acoustid
import musicbrainzngs

musicbrainzngs.set_useragent("spotipy-downloader", "1.0", "")

yt = ytmusicapi.YTMusic()

# Check for interactive mode
interactive_mode = "-i" in sys.argv

os.system("rm -f audio.mp3")
os.system("rm -f audio.jpg")

try:
    f = open("downloaded.txt", "r")
    downloaded = f.readlines()
    f.close()
except:
    downloaded = []

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

def get_fingerprint(file_path):
    """Generate Chromaprint fingerprint using fpcalc"""
    try:
        result = subprocess.run(["fpcalc", "-json", file_path], capture_output=True, text=True)
        data = json.loads(result.stdout)
        return data["fingerprint"], data["duration"]
    except Exception as e:
        print(f"Fingerprinting failed: {e}")
        return None, None

def lookup_metadata(fingerprint, duration):
    """Look up recording metadata via AcoustID and MusicBrainz"""
    try:
        # Query AcoustID with fingerprint
        print(f"Querying AcoustID with fingerprint (duration: {duration}s)...")
        results = acoustid.lookup("Suz4zYYuTp", fingerprint, duration)
        print(f"AcoustID response: {results}")
        
        if results and "results" in results and len(results["results"]) > 0:
            # Get the first (best) match
            best_match = results["results"][0]
            print(f"Best match from AcoustID: {best_match}")
            
            if "recordings" in best_match and len(best_match["recordings"]) > 0:
                recording = best_match["recordings"][0]
                recording_id = recording.get("id")
                print(f"Found recording ID: {recording_id}")
                
                if recording_id:
                    # Query MusicBrainz for full details
                    print(f"Querying MusicBrainz for recording {recording_id}...")
                    mb_recording = musicbrainzngs.get_recording_by_id(
                        recording_id,
                        includes=["artists", "releases"]
                    )
                    rec = mb_recording["recording"]
                    
                    title = rec.get("title", "Unknown")
                    artist = rec["artist-credit"][0]["artist"]["name"] if rec.get("artist-credit") else "Unknown"
                    
                    # Get album from first release
                    album = "Unknown"
                    album_id = None
                    if rec.get("release-list"):
                        album = rec["release-list"][0].get("title", "Unknown")
                        album_id = rec["release-list"][0].get("id")
                    
                    print(f"Found metadata: {title} by {artist} from {album}")
                    return title, artist, album, album_id
            else:
                print("No recordings found in AcoustID response")
        else:
            print("No results from AcoustID")
    except Exception as e:
        print(f"AcoustID/MusicBrainz lookup failed: {e}")
        import traceback
        traceback.print_exc()
    return None, None, None, None

def tag_mp3(file_path, title, artist, album, album_id=None):
    """Tag MP3 file with metadata and album art"""
    try:
        audio = MP3(file_path, ID3=ID3)
        audio.tags.add(TIT2(encoding=3, text=title))
        audio.tags.add(TPE1(encoding=3, text=artist))
        audio.tags.add(TALB(encoding=3, text=album))
        
        # Get album art from MusicBrainz Cover Art Archive if album_id available
        if album_id:
            try:
                import urllib.request
                cover_url = f"https://coverartarchive.org/release/{album_id}/front-250.jpg"
                print(f"Fetching album art from {cover_url}...")
                with urllib.request.urlopen(cover_url) as response:
                    cover_data = response.read()
                    audio.tags.add(APIC(encoding=3, mime="image/jpeg", type=3, desc="Cover", data=cover_data))
                    print("Album art added")
            except Exception as e:
                print(f"Could not fetch album art: {e}")
        
        audio.save()
        print(f"Tagged: {title} by {artist} ({album})")
    except Exception as e:
        print(f"Tagging failed: {e}")

try:
    f = open("downloaded.txt", "r")
    downloaded = f.readlines()
    f.close()
except:
    downloaded = []

if not interactive_mode:
    f = open("tracks.txt", "r")
    tracks = f.readlines()
    f.close()
    tracknum = len(tracks)
    currtrack = 0
    
    for surl in tracks:
        currtrack = currtrack + 1

        if currtrack % 300 == 0:
            print(f"Processed {currtrack} tracks. Taking a 60 second break...")
            time.sleep(60)

        # Check if this is a custom entry
        if surl.startswith("#custom:"):
            trackid = surl.replace("#custom:", "").strip()
            query = trackid
            artist = trackid.split(" - ")[0] if " - " in trackid else "Unknown"
            title = trackid.split(" - ")[1] if " - " in trackid else trackid
            year = ""
            albumtitle = ""
            track = ""
            album_maxtracks = ""
            cover = None
        else:
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
                artist = soup.find("meta", {"name": "music:musician_description"})["content"].split(",")[0]
                title = soup.find("meta", {"property": "og:title"})["content"]
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
            
            query = artist + " - " + title

        filename = artist.replace(" ", "-").replace("/", "-") + "_" + title.replace(" ", "-").replace("/", "-")
        filename = slugify(filename) + ".mp3"
        if not os.path.exists(filename):
            if cover:
                os.system("wget -O audio.jpg \"" + cover + "\"")
            print(title)
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
            lame_cmd = ["lame", "-b", "320"]
            if cover:
                lame_cmd.extend(["--ti", "audio.jpg"])
            lame_cmd.extend(["--ta", artist, "--tt", title])
            if year:
                lame_cmd.extend(["--ty", year])
            if albumtitle:
                lame_cmd.extend(["--tl", albumtitle])
            if track and album_maxtracks:
                lame_cmd.extend(["--tn", track+"/"+album_maxtracks])
            lame_cmd.extend(["audio.mp3", filename])
            subprocess.Popen(lame_cmd, shell=False).wait()
            os.system("rm audio.mp3")
            if cover:
                os.system("rm audio.jpg")
            print("Done!")
            
            # Enhance metadata for custom songs using MusicBrainz
            if surl.startswith("#custom:"):
                print("Looking up metadata from MusicBrainz...")
                try:
                    fp, dur = get_fingerprint(filename)
                    if fp and dur:
                        print(f"Fingerprint generated successfully (length: {len(fp)})")
                        mb_title, mb_artist, mb_album, album_id = lookup_metadata(fp, dur)
                        if mb_title:
                            tag_mp3(filename, mb_title, mb_artist, mb_album, album_id)
                        else:
                            print("No MusicBrainz match found, keeping original metadata")
                    else:
                        print("Failed to generate fingerprint")
                except Exception as e:
                    print(f"Metadata lookup error: {e}")
        f = open("downloaded.txt", "a+")
        f.write(trackid + "\n")
        f.close()
else:
    # Interactive mode - process each track immediately
    print("\n🎵 spoti.py Interactive Downloader")
    print("=" * 40)
    print("Format: Artist - Title")
    print("Example: The Beatles - Hey Jude")
    print("Press Ctrl+C or type \"exit\" to quit\n")
    
    currtrack = 0
    canrun = True
    while canrun:
        try:
            query = input("➜ ").strip()
            if not query:
                continue
            if query.lower() == "exit":
                canrun = False
                print("Exiting...")
                break
            
            currtrack += 1
            surl = "#custom:" + query
            trackid = query
            artist = query.split(" - ")[0] if " - " in query else "Unknown"
            title = query.split(" - ")[1] if " - " in query else query
            year = ""
            albumtitle = ""
            track = ""
            album_maxtracks = ""
            cover = None
            
            filename = artist.replace(" ", "-").replace("/", "-") + "_" + title.replace(" ", "-").replace("/", "-")
            filename = slugify(filename) + ".mp3"
            
            if not os.path.exists(filename):
                print(title)
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
                lame_cmd = ["lame", "-b", "320"]
                lame_cmd.extend(["--ta", artist, "--tt", title])
                lame_cmd.extend(["audio.mp3", filename])
                subprocess.Popen(lame_cmd, shell=False).wait()
                os.system("rm audio.mp3")
                print("Done!")
                
                print("Looking up metadata from MusicBrainz...")
                try:
                    fp, dur = get_fingerprint(filename)
                    if fp and dur:
                        print(f"Fingerprint generated successfully (length: {len(fp)})")
                        mb_title, mb_artist, mb_album, album_id = lookup_metadata(fp, dur)
                        if mb_title:
                            tag_mp3(filename, mb_title, mb_artist, mb_album, album_id)
                        else:
                            print("No MusicBrainz match found, keeping original metadata")
                    else:
                        print("Failed to generate fingerprint")
                except Exception as e:
                    print(f"Metadata lookup error: {e}")
                
                f = open("downloaded.txt", "a+")
                f.write(trackid + "\n")
                f.close()
            else:
                print(f"File already exists: {filename}")
            
            print()
        except KeyboardInterrupt:
            print("\n\nExiting...")
            break
