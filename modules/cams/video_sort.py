import time
import threading
import configparser
import os

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

def get_config():
    config = configparser.ConfigParser()
    config.read('modules/cams/config.ini')
    return config

## === Start counting files ===
def count_files(path, extension=".mp4", recursive=False):
    if recursive:
        count = sum(
            1 for root, dirs, files in os.walk(path)
            for file in files if file.endswith(extension)
        )
    else:
        count = sum(
            1 for file in os.listdir(path)
            if file.endswith(extension) and os.path.isfile(os.path.join(path, file))
        )
    return count

def move_file(file_path):
    """Moves the file when ffmpeg is done writing."""
    dir_path = os.path.dirname(file_path)
    file_name = file_path.split("/")[-1]
    splitted_file_name = file_name.split("_")

    cam_name = splitted_file_name[0]
    file_date = splitted_file_name[1]
    file_time = splitted_file_name[2]

    new_dir_path = f"{dir_path}/{cam_name}/{file_date}/{file_time.split('-')[0]}"
    os.makedirs(new_dir_path, exist_ok=True)
    os.rename(file_path, f"{new_dir_path}/{file_name}")

class NewFileHandler(FileSystemEventHandler):
    def on_created(self, event):
        config = get_config()
        file_extension = config['recorder']['file_extension']

        if event.is_directory:
            return

        if event.src_path.endswith(file_extension):
            move_file(event.src_path)

def watch_folder():
    config = get_config()

    folder_path = config['recorder']['main_dir']
    file_extension = config['recorder']['file_extension']

    observer = Observer()
    event_handler = NewFileHandler()
    observer.schedule(event_handler, path=folder_path, recursive=False)

    observer.start()
    print(f"📂 Start watching: {folder_path}")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()

    observer.join()