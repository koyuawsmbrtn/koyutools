import os
from urllib.parse import unquote

# Converts a PLS Playlist to M3u
mount = "/media/koyu/LEOPOD"
protocol = "file://"
files = os.listdir(".")
for fs in files:
    if fs.endswith(".pls"):
        with open(fs) as f:
            lines = f.readlines()
        with open(fs.replace(".pls", ".m3u"), "w") as m3u:
            for line in lines:
                if line.startswith("File"):
                    line = line.split("=")[1]
                    line = line.replace(protocol, "")
                    line = line.replace(mount, "")
                    line = unquote(line)
                    m3u.write(line)