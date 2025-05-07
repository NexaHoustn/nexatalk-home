import subprocess
import os
import time
import threading
import configparser

from modules.cams.video_sort import watch_folder
from datetime import datetime, timedelta

config = configparser.ConfigParser()
config.read('modules/cams/config.ini')

def get_config():
    segment_duration = int(config['recorder']['segment_duration'])
    interval_minutes = int(config['recorder']['interval_minutes'])
    main_dir = config['recorder']['main_dir']

    return {
        "segment_duration": segment_duration,
        "interval_minutes": interval_minutes,
        "main_dir": main_dir
    }

def get_cams():
    cams = []

    for i in range(1, 3):
        cam_name = config['cams'][f'cam{i}_name']
        cam_url = config['cams'][f'cam{i}_url']
        cams.append({"name": cam_name, "stream_url": cam_url})

    return cams

## === Build ffmpeg command pattern ===
def build_ffmpeg_command(cam, recorder_config):
    output_pattern = os.path.join(
        recorder_config['main_dir'],
        f"{cam['name']}_%Y-%m-%d_%H-%M.mp4"
    )
    
    return [
        "ffmpeg",
        "-fflags", "+genpts",
        "-rtsp_transport", "tcp",
        "-use_wallclock_as_timestamps", "1",
        "-i", cam['stream_url'],
        "-analyzeduration", "10000000",
        "-probesize", "10000000",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-tune", "zerolatency",
        "-crf", "23",
        "-c:a", "aac",
        "-f", "segment",
        "-segment_time", str(recorder_config['segment_duration']),
        "-segment_format", "mp4",
        "-strftime", "1",
        "-reset_timestamps", "1",
        "-flush_packets", "1",
        "-avoid_negative_ts", "make_zero",
        "-loglevel", "warning",
        output_pattern
    ]


def record_cam(cam):
    recorder_config = get_config()
    os.makedirs(recorder_config["main_dir"], exist_ok=True)

    ## === Wait until the next full X-minute ===
    now = datetime.now()
    next_start_time = (now + timedelta(minutes=recorder_config['interval_minutes'])).replace(second=0, microsecond=0)
    next_start_time -= timedelta(minutes=next_start_time.minute % recorder_config['interval_minutes'])

    wait_seconds = (next_start_time - now).total_seconds()

    print(f"[{now.strftime('%H:%M:%S')}] Waiting {wait_seconds:.1f} seconds until the next full {recorder_config['interval_minutes']}-minute mark ({next_start_time.strftime('%H:%M:%S')})...")
    time.sleep(wait_seconds)

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Starting segmented recording loop...")
    ffmpeg_command = build_ffmpeg_command(cam, recorder_config)

    ## === Run ffmpeg in a loop with error handling ===
    while True:
        formattedTimeStamp = datetime.now().strftime('%H:%M:%S')
        try:
            result = subprocess.run(ffmpeg_command)
            if result.returncode != 0:
                print(f"[{formattedTimeStamp}] ffmpeg exited with code {result.returncode}, restarting...")
            else:
                print(f"[{formattedTimeStamp}] ffmpeg exited normally, restarting in 5 seconds...")
            time.sleep(5)  # Short pause before restart
        except Exception as e:
            print(f"[{formattedTimeStamp}] Unexpected error: {e}. Restarting in 5 seconds...")
            time.sleep(5)

def start_recording():
    threading.Thread(target=watch_folder).start()

    cams = get_cams()
    for cam in cams:
        threading.Thread(target=record_cam, args=(cam,)).start()
    

    
