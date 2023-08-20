from io import BytesIO
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QIcon
from PyQt5.QtMultimedia import QSoundEffect
from PyQt5.QtWidgets import QDialog, QFileDialog, QHBoxLayout, QLabel, QMainWindow, QPushButton, QStyle, QTextEdit, \
    QVBoxLayout

import os
import requests
import wave


class MusicConfirmDialog(QDialog):
    """Dialog used to confirm or load music selection with the ability to preview selection by listening to the music.
    If neither music_name nor music_url are provided, allows import from local file.

        Args:
            parent_window (MainWindow): Parent window that created the dialog.
            music_name (str) : Name of the music file; used only to show name in dialog
            music_url (str) : URL to a raw music file; should be formatted for use on SF2000 (raw signed 16-bit PCM,
                mono, little-endian, 22050 hz)
    """
    def __init__(self, parent_window, music_name: str = "", music_url: str = ""):
        super().__init__()

        # Save Arguments
        self.parent_window = parent_window
        self.music_name = music_name
        self.music_url = music_url
        self.music_file = ""  # used to store filename for local files

        # Configure Window
        self.setWindowTitle("Change Background Music")
        self.setWindowIcon(QIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaVolume)))
        self.sound = QSoundEffect(self)  # Used to Play Music File

        # Setup Main Layout
        self.layout_main = QVBoxLayout()
        self.setLayout(self.layout_main)

        # Main Text
        self.label_confirm = QLabel("<h3>Change Background Music</h3><a href='#'>Select File</a>", self)
        if self.music_name == "" and self.music_url == "":
            self.label_confirm.linkActivated.connect(self.load_from_file)
            pass
        self.label_confirm.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        self.layout_main.addWidget(self.label_confirm)

        # Music Preview Button
        self.button_play = QPushButton(QIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay)),
                                       " Preview",
                                       self)
        self.button_play.setDisabled(True)  # disable by default

        self.layout_main.addWidget(self.button_play)
        self.button_play.clicked.connect(self.toggle_audio)

        # Main Buttons Layout (Save/Cancel)
        self.layout_buttons = QHBoxLayout()
        self.layout_main.addLayout(self.layout_buttons)

        # Save Button
        self.button_save = QPushButton("Save")
        self.button_save.setDisabled(True)  # disable by default
        self.button_save.clicked.connect(self.accept)
        self.layout_buttons.addWidget(self.button_save)

        # Cancel Button
        self.button_cancel = QPushButton("Cancel")
        self.button_cancel.clicked.connect(self.reject)
        self.layout_buttons.addWidget(self.button_cancel)

        if music_name and music_url:  # enable features only if using preset options
            self.label_confirm.setText("<h3>Change Background Music</h3><em>{}</em>".format(self.music_name))
            self.button_save.setEnabled(True)
            self.button_play.setEnabled(True)

    def toggle_audio(self) -> bool:
        """toggles music preview on or off

            Returns:
                bool: True if file is playing; false if not
        """
        if self.sound.isPlaying():
            self.sound.stop()
            self.button_play.setIcon(QIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay)))
            self.button_play.setText(" Preview")
            return False

        else:
            if not self.sound.source().path():  # fetch and convert raw file if not already done
                self.button_play.setDisabled(True)  # disable button while processing
                file_data = self.get_and_format_music_file()
                if file_data[0]:  # fetch/conversion succeeds
                    self.sound.setSource(QUrl.fromLocalFile(file_data[1]))
                    self.button_play.setEnabled(True)
                    self.button_save.setEnabled(True)  # enable saving as well since file seems OK
                else:  # fetch/conversion fails
                    self.button_play.setText(file_data[1])
                    self.button_play.setIcon(QIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxCritical)))
                    return False

            # format button and play
            self.button_play.setIcon(QIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaStop)))
            self.button_play.setText(" Stop")
            self.sound.setLoopCount(1000)
            self.sound.play()
            return True

    def get_and_format_music_file(self) -> (bool, str):
        """Downloads/loads and re-formats the raw music file as wav.

            Returns:
                tuple (bool, str): True or false based on success in fetching/converting file, and path to resulting
                    temporary wav file, error message if failed.
        """
        if self.music_url:  # handle internet downloads
            try:
                r = requests.get(self.music_url)
                if r.status_code == 200:  # download succeeds
                    raw_data = BytesIO(r.content)  # read raw file into memory
            except requests.exceptions.RequestException:  # catches exceptions for multiple reasons
                return False, "Download Failed"
        else:  # handle local files
            with open(self.music_file, "rb") as mf:
                raw_data = BytesIO(mf.read())

        wav_filename = os.path.join(self.parent_window.base_dir, "preview.wav")
        with wave.open(wav_filename, "wb") as wav_file:
            wav_file.setparams((1, 2, 22050, 0, 'NONE', 'NONE'))
            wav_file.writeframes(raw_data.read())
            if wav_file.getnframes() > (22050*90):  # check that file length does not exceed 90 seconds (max for Froggy)
                return False, "Duration Too Long (90s max)"
        return True, wav_filename

    def load_from_file(self) -> bool:
        file_name = QFileDialog.getOpenFileName(self, 'Open file', '',
                                                "Raw Signed 16-bit PCM - Mono, Little-Endian, 22050hz (*.*)")[0]
        if file_name:
            self.music_file = file_name
            self.music_name = os.path.split(file_name)[-1]
            self.label_confirm.setText("<h3>Change Background Music</h3><em>{}</em>".format(self.music_name))
            self.button_play.setEnabled(True)
            self.toggle_audio()
            return True
        return False


class ReadmeDialog(QMainWindow):
    """
    Dialog used to display README.md file from program root.

    Args:
        parent_window (QMainWindow): Parent window dialog was called from.
    """
    def __init__(self, parent_window):
        super().__init__()

        self.parent_window = parent_window

        self.setWindowTitle("Read Me")
        self.setWindowIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_TitleBarContextHelpButton))

        self.text_edit = QTextEdit(self)
        self.text_edit.setReadOnly(True)
        self.text_edit.setMinimumSize(500, 500)
        self.setCentralWidget(self.text_edit)
        try:
            with open(os.path.join(self.parent_window.base_dir, "README.md"), "r") as readme_file:
                self.text_edit.setMarkdown(readme_file.read())
        except FileNotFoundError:  # gracefully fail if file not present
            self.text_edit.setText(f"Unable to locate README.md file in program root folder {self.parent_window.base_dir}.")
