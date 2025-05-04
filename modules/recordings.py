from pathlib import Path
import urllib
import os
import subprocess
from collections import defaultdict
import json

def find_all_videos(base_path="/mnt/extern/cctv"):
    base = Path(base_path)
    grouped_videos = defaultdict(lambda: defaultdict(list))

    for file in base.rglob("*.mp4"):
        parts = file.relative_to(base).parts
        if len(parts) >= 3:
            hauptordner = parts[0]     # z. B. "wohnzimmer"
            unterordner = parts[1]     # z. B. "ordnerX"
            grouped_videos[hauptordner][unterordner].append(str(file))
        else:
            # Optional: Gruppiere alles andere unter "_root" oder ähnliches
            grouped_videos["_ungrouped"]["_root"].append(str(file))

    # defaultdicts in normale dicts umwandeln, damit json.dump funktioniert
    grouped_videos = {
        k: dict(v) for k, v in grouped_videos.items()
    }

    return grouped_videos

def get_thumbnail_path(video_path: str):
    replace_thumbnail_path = video_path.split("/")[-1].split("_")[0]    
    replace_day_path = video_path.split("/")[-2]
    thumbnail_path = video_path.replace(replace_thumbnail_path, "thumbnails", 1).replace(replace_day_path, "", 1).replace(".mp4", "_thumb.jpg")
    
    return thumbnail_path

# json_output = find_all_videos_grouped_as_json()
# print(json_output)
