from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import QPixmap, QImage, QKeySequence
from skimage import io
from gui import Ui_JunctionAnnotator
from loader import Loader
import numpy as np
import sys
import time
from matplotlib import pyplot as plt

class App(QMainWindow, Ui_JunctionAnnotator):
    def __init__(self):
        super(self.__class__, self).__init__()
        self.setupUi(self)
        # Setup variables
        self.path = self.select_path()
        self.loader = Loader(path=self.path)
        self.labels = [False for _ in range(4)]
        self.current_time = time.time()
        self.time_steps = []

        # Image settings
        self.zoom_level = np.float32(1.0)
        self.drag_x, self.drag_y = 0, 0
        self.mouse_x, self.mouse_y = 0, 0
        self.dragging = False

        # Initial image
        self.next_crop()
        self.display_crop()

        # Connect buttons and stuff
        self.button_skip.clicked.connect(self.skip)
        self.button_submit.clicked.connect(self.submit)
        self.button_pause.clicked.connect(self.pause)
        self.slider_intensity_ch0.valueChanged.connect(self.display_crop)
        self.slider_intensity_ch1.valueChanged.connect(self.display_crop)
        #self.button_zoom.clicked.connect(self.zoom)  # Zoom buttons not connected for now (doesn't work properly)
        #self.button_dezoom.clicked.connect(self.dezoom)
        self.label_image.mousePressEvent = self.image_click
        self.label_image.mouseMoveEvent = self.image_drag
        self.label_image.mouseReleaseEvent = self.image_release

        # Shortcuts/hotkeys

        shortcuts = {}
        for n, check in enumerate(self.frame_choices.children()):
            check.clicked.connect(self.update_classification)
            shortcuts[str(n+1)] = QShortcut(QKeySequence(str(n+1)), self)
        shortcuts['1'].activated.connect(lambda: self.check_shortcut('1'))
        shortcuts['2'].activated.connect(lambda: self.check_shortcut('2'))
        shortcuts['3'].activated.connect(lambda: self.check_shortcut('3'))
        shortcuts['4'].activated.connect(lambda: self.check_shortcut('4'))
        QShortcut(QKeySequence('Return'), self).activated.connect(self.submit)
        QShortcut(QKeySequence('P'), self).activated.connect(self.pause)

        self.show()

    def select_path(self):
        """
        Select the directory containing the images to label
        :return:
        """
        path = str(QFileDialog.getExistingDirectory(self, "Select Directory"))
        return path

    def display_crop(self):
        """
        Update the displayed crop
        """
        self.label_image.clear()
        self.displayed_crop = self.crop.copy()
        self.update_contrast()
        h, w, c = self.displayed_crop.shape
        img = np.transpose(self.displayed_crop, (1,0,2)).copy()
        pixmap = QImage(img, w, h, QImage.Format_RGB888)
        self.label_image.setPixmap(QPixmap(pixmap))
        self.show()

    def submit(self):
        """
        Submit the classification of the current crop and display the next one
        """
        self.time_steps.append(time.time() - self.current_time)
        time_taken = np.sum(self.time_steps)
        self.next_crop()

    def skip(self):
        """
        Skip the current crop?
        """
        self.next_crop()

    def next_crop(self):
        """
        Display the next crop to label
        """
        self.time_steps = []
        self.current_time = time.time()
        for i, check in enumerate(self.frame_choices.children()):
            check.setChecked(False)
            self.labels[i] = False

        try:
            self.crop = self.loader.__next__()
        except StopIteration:
            end_dialog = QMessageBox()
            end_dialog.setIcon(QMessageBox.Information)
            end_dialog.setText('Labeled all of the data in the directory!')
            end_dialog.setWindowTitle('Finished')
            end_dialog.exec()

        self.zoom_level = np.float32(1.0)
        self.display_crop()
        self.show()

    def update_classification(self):
        """
        Update current classification vector
        """
        for i, check in enumerate(self.frame_choices.children()):
            self.labels[i] = check.isChecked()

    def check_shortcut(self, event):
        """
        Shortcut event to check classes using 1,2,3,4
        :param event: key pressed
        """
        for i, check in enumerate(self.frame_choices.children()):
            if str(i+1) == event:
                check.setChecked(not check.isChecked())
        self.update_classification()

    def update_contrast(self):
        """
        Update the contrast of the image
        """
        # Intensity
        # channel 0
        self.displayed_crop[...,0] = np.clip(self.crop[...,0].astype('float') * self.slider_intensity_ch0.value()/100, 0, 255).astype('uint8').copy()

        # channel 1
        self.displayed_crop[...,1] = np.clip(self.crop[...,1].astype('float') * self.slider_intensity_ch1.value()/100, 0, 255).astype('uint8').copy()

        # Zoom and Drag
        h, w, c = self.displayed_crop.shape
        edge = int((h - int(h/self.zoom_level))/2)
        y_min, y_max = max(0, edge + self.drag_y), min(h, h - edge + self.drag_y)
        x_min, x_max = max(0, edge + self.drag_x), min(w, w - edge + self.drag_x)

        self.displayed_crop = self.displayed_crop.copy()[y_min:y_max, x_min:x_max]

    def zoom(self):
        """
        Trying to add a zoom+pan function. Does not work yet.
        """
        if self.zoom_level < 2.0:
            self.zoom_level += np.float32(0.20)
        self.display_crop()

    def dezoom(self):
        """
        Trying to add a zoom+pan function. Does not work yet.
        """
        if self.zoom_level > 1.0:
            self.zoom_level -= np.float32(0.20)
        if self.zoom_level == 1.0:
            self.drag_x, self.drag_y = 0, 0
        self.display_crop()

    def image_click(self, event):
        """
        Trying to add a zoom+pan function. Does not work yet.
        """
        self.mouse_x = event.pos().x()
        self.mouse_y = event.pos().y()
        self.dragging = True

    def image_drag(self, event):
        """
        Trying to add a zoom+pan function. Does not work yet.
        """
        if self.dragging and self.zoom_level != 1.0:
            ratio = self.displayed_crop.shape[1] / self.label_image.width()

            drag_y = event.pos().x() * ratio
            drag_x = event.pos().y() * ratio
            
            delta_y, delta_x = drag_y - self.mouse_y*ratio, drag_x - self.mouse_x*ratio
            self.drag_y += delta_y
            self.drag_x += delta_x
            #print(self.drag_x, self.drag_y)
            self.mouse_y, self.mouse_x = drag_y, drag_x

            self.drag_y, self.drag_x = int(self.drag_y), int(self.drag_x)
            self.display_crop()

    def image_release(self, event):
        """
        Trying to add a zoom+pan function. Does not work yet.
        """
        self.dragging = False

    def pause(self):
        """
        Toggle pause. Prevents counting time during pauses, hides the image and disable widgets
        """

        self.label_image.clear()  # Hide image so no one cheats
        self.show()

        self.time_steps.append(time.time() - self.current_time)  # Add time step to prevent counting time while paused

        pause_dialog = QMessageBox()
        pause_dialog.setIcon(QMessageBox.Warning)
        pause_dialog.setText('Program is paused!')
        pause_dialog.setWindowTitle('Pause')
        pause_dialog.setStandardButtons(QMessageBox.Yes)
        button = pause_dialog.button(QMessageBox.Yes)
        button.setText('Unpause')
        pause_dialog.exec()
        self.display_crop()

        self.current_time = time.time()

if __name__=='__main__':
    from PyQt5.QtWidgets import QApplication, QSplashScreen

    app = QApplication(sys.argv)
    ex = App()
    sys.exit(app.exec_())