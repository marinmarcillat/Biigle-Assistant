import subprocess, json, os
from datetime import datetime, timedelta
import pandas as pd


def get_video_time_interval(filename, video_dir):
    initial_dt = datetime.strptime(filename.split('_')[2], "%y%m%d%H%M%S")
    duration = timedelta(0, get_video_len(os.path.join(video_dir, filename)))
    end_dt = initial_dt + duration
    return [os.path.join(video_dir, filename), initial_dt, duration, end_dt]


def get_image_time(image_filename, image_dir):
    return [os.path.join(image_dir, image_filename), datetime.strptime(image_filename[:22], "%Y%m%dT%H%M%S.%f")]


def get_video_len(filename):
    result = subprocess.check_output(
            f'ffprobe -v quiet -show_streams -select_streams v:0 -of json "{filename}"',
            shell=True).decode()
    fields = json.loads(result)['streams'][0]

    return float(fields['duration'])


def parse_video_dir(video_dir):
    allfiles = os.listdir(video_dir)
    video_list = [fname for fname in allfiles if fname.endswith('.mp4')]
    video_time = [
        get_video_time_interval(video, video_dir) for video in video_list
    ]
    return pd.DataFrame(video_time, columns=['filename', 'start', 'dur', 'end'])


def parse_image_dir(image_dir):
    allfiles = os.listdir(image_dir)
    image_list = [fname for fname in allfiles if fname.endswith('.png') or fname.endswith('.jpg')]
    image_time = [get_image_time(image, image_dir) for image in image_list]
    image_pd = pd.DataFrame(image_time, columns=['filename', 'datetime'])
    image_pd = image_pd.set_index('datetime').drop_duplicates(keep = 'first')
    return image_pd


def get_current_video(video_db, current_datetime):
    return next(
        (
            (row['filename'], row['start'], row['end'])
            for index, row in video_db.iterrows()
            if row['start'] <= current_datetime <= row['end']
        ),
        None,
    )

def get_current_image(image_db, current_dt):
    row = image_db.iloc[image_db.index.get_indexer([current_dt], method='nearest')]
    delta_dt = current_dt - row.index
    return row['filename'] if delta_dt <= timedelta(0, 5) else None


class RunningVideo:
    def __init__(self, video_db, current_dt):
        result = get_current_video(video_db, current_dt)
        if result is not None:
            self.filename, self.start, self.end = result
            self.timecode = 0
            self.state = True
        else:
            self.state = False

    def in_video(self, dt):
        if self.state:
            if self.start <= dt <= self.end:
                self.state = True
                return True
            else:
                self.state = False
        return False

    def update_timecode(self, current_dt):
        td = current_dt - self.start
        return int(td.total_seconds() * 1000)


