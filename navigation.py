import pandas as pd
from datetime import datetime, timedelta


def read_dim2(nav_file):
    nav = pd.read_csv(nav_file, sep = ';', header = None).iloc[:, 0:13]
    nav.columns = ['_', 'date', 'time', 'a', 'b', 'filename', 'lat', 'long', 'depth', 'altitude', 'heading', 'yaw', 'pitch']
    nav["datetime"] = pd.to_datetime(nav['date'] + nav['time'], format='%d/%m/%Y%H:%M:%S.%f')
    nav = nav.loc[:, ['datetime', 'filename', 'depth', 'altitude']]
    return nav.set_index('datetime').drop_duplicates(keep = 'first')


def get_navigation(nav_db, current_dt):
    row = nav_db.iloc[nav_db.index.get_indexer([current_dt], method='nearest')]
    delta_dt = current_dt - row.index
    return row if delta_dt <= timedelta(0, 5) else None
