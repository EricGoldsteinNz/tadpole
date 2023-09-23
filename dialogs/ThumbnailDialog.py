# GUI imports
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtMultimedia import QSoundEffect
from PyQt5.QtCore import Qt, QTimer, QUrl, QSize
# OS imports - these should probably be moved somewhere else
import os
import tadpole_functions

# Subclass Qidget to create a thumbnail viewing window        
class ThumbnailDialog(QDialog):
    """
        This window should be called without a parent widget so that it is created in its own window.
    """
    def __init__(self, filepath):
        super().__init__()
        layout = QVBoxLayout()
        
        self.setWindowIcon(QIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DesktopIcon)))
        self.setWindowTitle(f"Thumbnail - {filepath}")
        
        # Setup Main Layout
        self.layout_main = QVBoxLayout()
        self.setLayout(self.layout_main)

        # set up current image viewer
        self.layout_main.addWidget(QLabel("Current Image"))
        self.current_viewer = ROMCoverViewer(self)
        self.layout_main.addWidget(self.current_viewer, Qt.AlignCenter)

        self.layout_main.addWidget(QLabel(" "))  # spacer

        # set up new image viewer
        self.layout_main.addWidget(QLabel("New Image"))
        self.new_viewer = ROMCoverViewer(self, changeable=True)
        self.layout_main.addWidget(self.new_viewer, Qt.AlignCenter)

        # Main Buttons Layout (Save/Cancel)
        self.layout_buttons = QHBoxLayout()
        self.layout_main.addLayout(self.layout_buttons)
        
        #Save Existing Cover To File Button
        self.button_write = QPushButton("Save Existing to File")
        self.button_write.clicked.connect(self.WriteImgToFile)
        self.layout_buttons.addWidget(self.button_write)     

        # Save Button
        self.button_save = QPushButton("Overwrite Cover")
        self.button_save.setDefault(True)
        self.button_save.setDisabled(True)  # set disabled by default; need to wait for user to select new image
        self.button_save.clicked.connect(self.accept)
        self.layout_buttons.addWidget(self.button_save)

        # Cancel Button
        self.button_cancel = QPushButton("Cancel")
        self.button_cancel.clicked.connect(self.reject)
        self.layout_buttons.addWidget(self.button_cancel)

        # Load Initial Image
        # If it's a supported .z**, open it, otherwise leave it blank
        file_extension = file_extension = os.path.splitext(filepath)[1]
        if file_extension == '.zfb' or file_extension == '.zfc' or file_extension == '.zgb' or \
                                    file_extension == '.zmd' or file_extension == '.zsf': 
            self.current_viewer.load_from_ROM_inMemory(filepath)
        
    def WriteImgToFile(self):
        newCoverFileName = QFileDialog.getSaveFileName(self,
                                                       'Save Cover',
                                                       'c:\\',
                                                       "Image files (*.png)")[0]
        
        if newCoverFileName is None or newCoverFileName == "":
            print("user cancelled save select")
            return      
        try:
            tadpole_functions.extractImgFromROM(self.current_viewer.path, newCoverFileName)
        except tadpole_functions.Exception_InvalidPath:
            QMessageBox.about(self, "Save ROM Cover", "An error occurred.")
            return
        QMessageBox.about(self, "Save ROM Cover", "ROM cover saved successfully")
       


class ROMCoverViewer(QLabel):
    """
    Args:
        parent (thumbnailWindow): Parent widget. Used to enable/disable controls on parent.
        changeable (bool): If True, will allow importing new image. If False, will just allow static display.
    """
    def __init__(self, parent, changeable=False):
        super().__init__(parent)

        self.changeable = changeable
        self.path = ""  # Used to store path to the currently-displayed file

        self.setStyleSheet("background-color: white;")
        self.setMinimumSize(144, 208)  # resize to Froggy ROM logo dimensions
        self.setFixedSize(144, 208)  # resize to Froggy ROM logo dimensions

        if self.changeable:
            self.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
            self.setText("Click to Select New Image")

    def mousePressEvent(self, ev):
        """
        Overrides built-in function to handle mouse click events. Prompts user for image path and loads same.
        """
        if self.changeable:  # only do something if image is changeable
            file_name = QFileDialog.getOpenFileName(self, 'Open file', '',
                                                    "Image files (*.gif *jpeg *.jpg *.png *.webp);;All Files (*.*)")[0]
            if len(file_name) > 0:  # confirm if user selected a file
                self.load_image(file_name)

    def load_from_ROM_inMemory(self, pathToROM: str):
        """
        Extracts image from the bios and passes to load image function.

        Args:
            drive (str):  Path to the root of the Froggy drive.
        """
        basedir = os.path.dirname(__file__)
        print(f"loading cover from {pathToROM}")
        self.path = pathToROM  # update path
        with open(pathToROM, "rb") as rom_file:
            rom_content = bytearray(rom_file.read((144*208)*2))
        img = QImage(rom_content[0:((144*208)*2)], 144, 208, QImage.Format_RGB16)
        self.setPixmap(QPixmap().fromImage(img))
        print("Successfully pulled thumbnail in memory")
        if self.changeable:  # only enable saving for changeable dialogs; prevents enabling with load from bios
            self.parent().button_save.setDisabled(False)
        return True 
        

    def load_image(self, path: str) -> bool:
        """
        Loads an image into the viewer.  If the image is loaded successfully, may enable the parent Save button based
        on the changeable flag.

        Args:
            path (str): Path to the image.  Can be .raw or other format.  If .raw, assumed to be in RGB16 (RGB565 Little
                Endian) format used for Froggy boot logos.  Must be 512x200 pixels or it will not be accepted/displayed.

        Returns:
            bool: True if image was loaded, False if not.
        """
        if os.path.splitext(path)[1] == ".raw":  # if raw image, assume RGB16 (RGB565 Little Endian)
            with open(path, "rb") as f:
                img = QImage(f.read(), 144, 208, QImage.Format_RGB16)
        else:  # otherwise let QImage autodetection do its thing
            img = QImage(path)
            if (img.width(), img.height()) != (144, 208): 
                img = img.scaled(144, 208, Qt.KeepAspectRatio, Qt.SmoothTransformation) #Rescale new boot logo to correct size
        self.path = path  # update path
        self.setPixmap(QPixmap().fromImage(img))

        if self.changeable:  # only enable saving for changeable dialogs; prevents enabling with load from bios
            self.parent().button_save.setDisabled(False)
        return True   
