import contextlib
import os
import sys
from datetime import datetime, timedelta

from PyQt5 import QtCore, QtGui, QtMultimedia
from PyQt5.QtWidgets import QApplication
from PyQt5.QtWidgets import (
    QDialog, QMainWindow, QFileDialog, QProgressBar, QMessageBox, QSizePolicy
)
from selenium import webdriver
from selenium.common.exceptions import WebDriverException, StaleElementReferenceException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

import Biigle_scraping as bs
import media_utils as mu
import navigation

import configparser

from main_window_ui import Ui_MainWindow

class Window(QMainWindow, Ui_MainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)

        self.setWindowIcon(QtGui.QIcon('logo.png'))

        self.config = configparser.ConfigParser()
        self.config.read('config.ini')

        self.video_directory_1 = self.config['DEFAULT']['video_directory_1']
        self.video_directory_2 = self.config['DEFAULT']['video_directory_2']
        self.image_directory = self.config['DEFAULT']['image_directory']
        self.nav_path = self.config['DEFAULT']['nav_path']

        self.annotating = False
        self.connected = False
        self.mode = 'image'
        self.paused = True
        self.current_dt = None
        self.first_dt = None
        self.image_count = 0

        self.updateAllTimer = QtCore.QTimer(self)
        self.updateAllTimer.setInterval(1000)  # 1 seconds
        self.updateAllTimer.timeout.connect(self.update_all)
        self.updateAllTimer.start()

        self.videoTimer = QtCore.QTimer(self)
        self.videoTimer.setInterval(8000)  # 5 seconds
        self.videoTimer.timeout.connect(self.restart_video)
        self.videoTimer.start()


        self.progress_bar = QProgressBar()
        self.statusBar().addPermanentWidget(self.progress_bar)
        self.progress_bar.hide()

        # setting  the geometry of window
        self.setGeometry(100, 100, 900, 600)

        self.mediaPlayer1 = QtMultimedia.QMediaPlayer(self)
        self.mediaPlayer2 = QtMultimedia.QMediaPlayer(self)
        self.mediaPlayer1.setVideoOutput(self.video_1_widget)
        self.mediaPlayer2.setVideoOutput(self.video_2_widget)
        self.mediaPlayer1.error.connect(lambda: self.handleError(self.mediaPlayer1))
        self.mediaPlayer2.error.connect(lambda: self.handleError(self.mediaPlayer2))
        self.video1 = None
        self.video2 = None
        self.image = None

        if len(self.video_directory_1) != 0:
            self.video_db_1 = mu.parse_video_dir(self.video_directory_1)
        else:
            self.actionVideo.setCheckable(False)
        self.frame_v1.setVisible(False)

        if len(self.video_directory_2) != 0:
            self.video_db_2 = mu.parse_video_dir(self.video_directory_2)
        else:
            self.actionVideo_2.setCheckable(False)
        self.frame_v2.setVisible(False)

        if len(self.image_directory) != 0:
            self.image_db = mu.parse_image_dir(self.image_directory)
        else:
            self.actionImage.setCheckable(False)
        self.frame_i.setVisible(False)

        if len(self.nav_path) != 0:
            self.nav_db = navigation.read_dim2(self.nav_path)
        else:
            self.actionNavigation.setCheckable(False)

        self.connectActions()

    def popup(self, text):
        QMessageBox.about(self, "Info", text)

    def handleError(self, mediaPlayer):
        print(mediaPlayer.errorString())

    def setPosition(self, mediaPlayer, position):
        if abs(mediaPlayer.position() - position) > 200:
            mediaPlayer.setPosition(position)

    def connectActions(self):
        # Preprocessing
        self.Connect_b.clicked.connect(self.launch_chrome)
        self.start_b.clicked.connect(self.launch_medias)

        self.actionVideo.toggled.connect(lambda: self.update_window(self.frame_v1, self.actionVideo))
        self.actionVideo_2.toggled.connect(lambda: self.update_window(self.frame_v2, self.actionVideo_2))
        self.actionImage.toggled.connect(lambda: self.update_window(self.frame_i, self.actionImage))

    def update_window(self, frame, menu):
        frame.setVisible(menu.isChecked())



    def add_video(self, mediaPlayer, filename):
        url = QtCore.QUrl.fromLocalFile(filename)
        mediaPlayer.setMedia(QtMultimedia.QMediaContent(url))
        mediaPlayer.play()

    def add_image(self, filename):
        pixmap = QtGui.QPixmap(filename)
        self.image_frame.setPixmap(pixmap)
        self.image = filename
        self.image_count += 1

    def launch_medias(self):
        if self.current_dt is not None:
            if self.actionVideo.isChecked():
                self.video1 = self.launch_video(self.mediaPlayer1, self.video_db_1, self.filename_v1)
            if self.actionVideo_2.isChecked():
                self.video2 = self.launch_video(self.mediaPlayer2, self.video_db_2, self.filename_v2)
            if self.actionImage.isChecked():
                image_filename = mu.get_current_image(self.image_db, self.current_dt)
                if self.image is None or self.image != image_filename:
                    self.add_image(image_filename)

    def launch_video(self, mediaplayer, video_db, filename_label):
        video = mu.RunningVideo(video_db, self.current_dt)
        if video.state:
            self.add_video(mediaplayer, video.filename)
            filename_label.setText(os.path.basename(video.filename))
            tc = video.update_timecode(self.current_dt)
            self.setPosition(mediaplayer, tc)
        return video

    def update_video(self, mediaplayer, video):
        if video.in_video(self.current_dt):
            tc = video.update_timecode(self.current_dt)
            if tc != video.timecode:
                self.setPosition(mediaplayer, tc)
                video.timecode = tc

        return video

    def restart_video(self):
        if self.video1 is not None and self.video1.state:
            new_tc = max(self.video1.timecode - 2000, 0)
            self.setPosition(self.mediaPlayer1, new_tc)
        if self.video2 is not None and self.video2.state:
            new_tc = max(self.video2.timecode - 2000, 0)
            self.setPosition(self.mediaPlayer2, new_tc)

    def update_navigation(self):
        nav = navigation.get_navigation(self.nav_db, self.current_dt)
        if nav is not None:
            alt = nav['altitude'].values[0]
            depth = nav['depth'].values[0]
            self.Altitude.setText(f'{alt} m')
            self.Depth.setText(f'{depth} m')
        else:
            self.Altitude.setText('')
            self.Depth.setText('')

    def launch_chrome(self):
        print('launching chrome')
        try:
            chrome_user_session = f"user-data-dir={self.config['DEFAULT']['chrome']}"
            chrome_options = Options()
            chrome_options.set_capability('UnexpectedAlertBehaviour', 'ignore')
            chrome_options.add_argument(chrome_user_session)

            self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

            self.driver.get(self.config['DEFAULT']['server'])

            self.connected = True
            self.start_b.setEnabled(True)
        except WebDriverException:
            self.popup("Error, please close all other Chrome windows")

    def get_driver_status(self):
        try:
            _ = self.driver.title
            self.set_connect_b(
                True, 'Connected', 'color: green', False
            )
        except (WebDriverException, AttributeError):
            self.set_connect_b(
                False, 'Connect', "color: black", True
            )

    def set_connect_b(self, arg0, arg1, arg2, arg3):
        self.connected = arg0
        self.Connect_b.setText(arg1)
        self.Connect_b.setStyleSheet(arg2)
        self.Connect_b.setEnabled(arg3)

    def try_parsing_date(self, text):
        for fmt, i in (["%y%m%d%H%M%S", 12], ["%Y%m%d%H%M%S", 14]):
            with contextlib.suppress(ValueError):
                return datetime.strptime(text[:i], fmt)
        raise ValueError('no valid date format found')

    def get_time(self):
        if self.mode == 'image':
            filename = bs.get_image_filename(self.driver)
            return datetime.strptime(filename[:22], "%Y%m%dT%H%M%S.%f"), True
        elif self.mode == 'video':
            filename = bs.get_video_filename(self.driver)
            initial_dt = self.try_parsing_date(filename.split('_')[2])
            time_s = bs.extract_video_time(self.driver)
            paused = bs.is_paused(self.driver)
            return initial_dt + timedelta(0, time_s), paused
        else:
            return None

    def update_all(self):
        self.get_driver_status()
        if (
            self.connected
            and bs.is_annotating(self.driver)
        ):
            self.mode = bs.image_or_video(self.driver)
            with contextlib.suppress(TypeError, ValueError, StaleElementReferenceException):
                self.current_dt, paused = self.get_time()
                if self.first_dt is None:
                    self.first_dt = self.current_dt
                if paused != self.paused:
                    if self.paused:
                        self.videoTimer.stop()
                    else:
                        self.videoTimer.start()
                    self.paused = paused
            self.Time.setText(datetime.strftime(self.current_dt, "%y/%m/%d %H:%M:%S"))
            if self.actionVideo.isChecked() and self.video1 is not None:
                self.video1 = self.update_video(self.mediaPlayer1, self.video1)
                if not self.video1.state:
                    self.popup('Video 1 changed')
                    self.video1 = self.launch_video(self.mediaPlayer1, self.video_db_1, self.filename_v1)
            if self.actionVideo_2.isChecked() and self.video2 is not None:
                self.video2 = self.update_video(self.mediaPlayer2, self.video2)
                if not self.video2.state:
                    self.popup('Video 2 changed')
                    self.video2 = self.launch_video(self.mediaPlayer2, self.video_db_2, self.filename_v2)
            if self.actionNavigation.isChecked():
                self.update_navigation()
            if self.actionImage.isChecked():
                image_filename = mu.get_current_image(self.image_db, self.current_dt)
                if self.image is not None and self.image != image_filename:
                    self.add_image(image_filename)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = Window()
    win.show()
    sys.exit(app.exec())