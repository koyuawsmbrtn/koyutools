#!/usr/bin/env python3
import re
import subprocess
from pathlib import Path

# Quellordner = aktuelles Verzeichnis
SRC_DIR = Path(".").resolve()
# Home-Videos-Ordner
VIDEOS_DIR = Path.home() / "Videos"

# Episode-Regex
EP_PATTERN = re.compile(r"(.*?)[._-]?(S\d{2}E\d{2})", re.IGNORECASE)

# === Alias-Liste für Seriennamen ===
ALIASES = {
    "gen v": "Generation V",
    "gen.v": "Generation V",
    "generation v": "Generation V"
}

def run(cmd):
    print(">>", " ".join(cmd))
    subprocess.run(cmd, check=True)

def normalize_series(raw):
    """Punkte/Unterstriche raus, trimmen und Alias anwenden"""
    cleaned = re.sub(r"[._-]+", " ", raw).strip()
    key = cleaned.lower()
    # zuerst exakte Keys prüfen
    if key in ALIASES:
        return ALIASES[key]
    # auch ohne Punkte/Unterstriche
    for alias, canonical in ALIASES.items():
        if key.replace(" ", "") == alias.replace(" ", ""):
            return canonical
    return cleaned

for f in SRC_DIR.glob("*.mp4"):
    m = EP_PATTERN.search(f.stem)
    if not m:
        continue
    series_raw, ep_tag = m.groups()
    series_name = normalize_series(series_raw)
    season = re.search(r"S(\d{2})E\d{2}", ep_tag, re.I).group(1)

    # Alle Dateien derselben Episode sammeln
    ep_key = ep_tag.lower()
    vids, subs, auds = [], [], []
    for g in SRC_DIR.iterdir():
        name_lower = g.name.lower()
        if ep_key in name_lower:
            if g.suffix.lower() in [".mp4", ".mkv"]:
                vids.append(g)
            elif g.suffix.lower() in [".srt", ".vtt"]:
                subs.append(g)
            elif g.suffix.lower() in [".aac", ".m4a", ".mp3"]:
                auds.append(g)

    if not vids:
        continue

    base_video = max(vids, key=lambda p: p.stat().st_size)
    dest_dir = VIDEOS_DIR / series_name / f"S{season}"
    dest_dir.mkdir(parents=True, exist_ok=True)

    out_name = f"{series_name} - {ep_tag.upper()}.mkv"
    out_path = dest_dir / out_name

    cmd = ["ffmpeg", "-y", "-i", str(base_video)]
    for a in auds: cmd += ["-i", str(a)]
    for s in subs: cmd += ["-i", str(s)]

    map_opts = ["-map", "0:v", "-map", "0:a?", "-map", "0:s?"]
    for i, _ in enumerate(auds, start=1):
        map_opts += ["-map", f"{i}:a:0"]
    for j, _ in enumerate(subs, start=1 + len(auds)):
        map_opts += ["-map", f"{j}:s:0"]

    run(["ffmpeg", "-y", "-i", str(base_video)]
        + sum([["-i", str(x)] for x in auds + subs], [])
        + map_opts
        + ["-c", "copy", str(out_path)]
    )

print("✅ Fertig – Dateien liegen in ~/Videos/<Serienname>/SXX/ mit Alias-Behandlung.")
