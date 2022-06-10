from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import QPixmap, QImage
import os
from gui import Ui_JunctionAnnotator
from loader import Loader, generate_box, HISTORY_F_NAME, OUTPUT_FILE_NAME
import numpy as np
import sys
import time

CROP_SIZE = 64
CROP_STEP = int(64*0.75)
TOTAL_SIZE = 128

class App(QMainWindow, Ui_JunctionAnnotator):
    def __init__(self):
        super(self.__class__, self).__init__()
        self.setupUi(self)
        # Setup variables
        self.loader = self.load_historyfile(crop_size=CROP_SIZE, crop_step=CROP_STEP, total_size=TOTAL_SIZE)
        if self.loader is None:
            self.path = self.select_path(title="Select source path")
            self.outputpath = self.select_path(title="Select patch destination path")
            self.loader = Loader(path=self.path, outputpath=self.outputpath, crop_size=CROP_SIZE, crop_step=CROP_STEP, total_size=TOTAL_SIZE)
            self.check_patch_file_exists()
        else:
            self.path = self.loader.path
            self.outputpath = self.loader.outputpath
        self.labels = [False for _ in range(4)]
        self.labelValues = [0.0 for _ in range(4)]
        self.ambiguous_labels = [False for _ in range(4)]
        self.current_time = time.time()
        self.time_steps = []
        self.time_steps_calc=[]
        self.hist_classes= []
        self.hist_structures=[]
        self.hist_ambiguous=[]

        # Image settings
        self.zoom_level = np.float32(1.0)
        self.drag_x, self.drag_y = 0, 0
        self.mouse_x, self.mouse_y = 0, 0
        self.dragging = False
        self.swap_colors = True

        # Group ambiguous checkboxes
        self.check_ambiguous_list = [self.check_ambigu_class_1, self.check_ambigu_class_2, self.check_ambigu_class_3, self.check_ambigu_class_4]
        self.slider_class_list = [self.slider_class_1, self.slider_class_2, self.slider_class_3, self.slider_class_4]
        self.spin_class_list = [self.Spin_class_1, self.Spin_class_2, self.Spin_class_3, self.Spin_class_4]


        # Initial image
        self.box = generate_box(self.loader.crop_size, self.loader.total_size)
        self.next_crop()
        self.display_crop()

        # Connect buttons and stuff
        self.button_skip.clicked.connect(self.skip)
        self.button_ambiguous.clicked.connect(self.ambiguous)
        self.button_submit.clicked.connect(self.submit)
        self.button_previous.clicked.connect(self.goBackward)
        self.button_pause.clicked.connect(self.pause)
        self.slider_intensity_ch0.valueChanged.connect(self.display_crop)
        self.slider_intensity_ch1.valueChanged.connect(self.display_crop)
        self.slider_intensity_ch0.mouseDoubleClickEvent = self.reset_contrast
        self.slider_intensity_ch1.mouseDoubleClickEvent = self.reset_contrast
        self.label_ch1.mousePressEvent = self.action_swap_colors
        self.label_ch2.mousePressEvent = self.action_swap_colors
        for check in self.check_ambiguous_list:
            check.clicked.connect(self.update_ambiguous_checks)

        self.slider_class_1.valueChanged.connect(lambda: self.update_class_value(1))
        self.slider_class_2.valueChanged.connect(lambda: self.update_class_value(2))
        self.slider_class_3.valueChanged.connect(lambda: self.update_class_value(3))
        self.slider_class_4.valueChanged.connect(lambda: self.update_class_value(4))

        self.Spin_class_1.valueChanged.connect(lambda: self.update_spin_class_value(1))
        self.Spin_class_2.valueChanged.connect(lambda: self.update_spin_class_value(2))
        self.Spin_class_3.valueChanged.connect(lambda: self.update_spin_class_value(3))
        self.Spin_class_4.valueChanged.connect(lambda: self.update_spin_class_value(4))

        self.timer = QTimer(self)

        self.button_start_timer.clicked.connect(self.start_action)
        # adding action to timer
        self.timer.timeout.connect(self.showTime)
        # update the timer every tenth second

        self.start= False
        self.count = -1
        self.timer.start(1000)

        self.curr_time = QTime(00,00,00)
        self.timeEdit_timer.setTime(self.curr_time)

        self.timenow=QDateTime.currentDateTime()

        self.show()


    def reset_class_values(self):
        self.labelValues = [0.5 for _ in range(4)]

        self.slider_class_1.setValue(50)
        self.slider_class_2.setValue(50)
        self.slider_class_3.setValue(50)
        self.slider_class_4.setValue(50)

        self.Spin_class_1.setValue(0.5)
        self.Spin_class_2.setValue(0.5)
        self.Spin_class_3.setValue(0.5)
        self.Spin_class_4.setValue(0.5)

        for check in self.check_ambiguous_list:
            check.setChecked(False)
        self.update_ambiguous_checks()
        
    def set_class_values(self, classes):
        self.labelValues = classes

        self.slider_class_1.setValue(int(self.labelValues[0]*100))
        self.slider_class_2.setValue(int(self.labelValues[1]*100))
        self.slider_class_3.setValue(int(self.labelValues[2]*100))
        self.slider_class_4.setValue(int(self.labelValues[3]*100))

        self.Spin_class_1.setValue(self.labelValues[0])
        self.Spin_class_2.setValue(self.labelValues[1])
        self.Spin_class_3.setValue(self.labelValues[2])
        self.Spin_class_4.setValue(self.labelValues[3])

    def timerUpdateTime(self):
        #
        self.curr_time = self.curr_time.addSecs(1)
        self.timeEdit_timer.setTime(self.curr_time)

    # method called by timer
    def showTime(self):
  
        # checking if flag is true
        if self.start:
            # incrementing the counter
            self.timerUpdateTime()

    def select_path(self, title= "Select Directory"):
        """
        Select the directory containing the images to label
        :return:
        """
        path = str(QFileDialog.getExistingDirectory(self, title))
        return path
    
    def check_patch_file_exists(self):
        if os.path.exists(os.path.join(self.outputpath,OUTPUT_FILE_NAME)):
            msgbox = QMessageBox(QMessageBox.Question,'Append patch list file',
                              f"The output directory <i>{self.outputpath}</i> already contains a patch list file. Do you want to append the new data to this old file ? <br/> (If you choose <b>No</b>, the old file will be automatically renamed and a new file will be created.)")
            msgbox.addButton(QMessageBox.Yes)
            msgbox.addButton(QMessageBox.No)
            msgbox.setDefaultButton(QMessageBox.No)

            rep = msgbox.exec()
            if rep == QMessageBox.No:
                self.loader.renamePatchListFile()
    
    def load_historyfile(self, crop_size, crop_step, total_size):
        if os.path.exists(HISTORY_F_NAME):
            msgbox = QMessageBox(QMessageBox.Question,
                                 'Load history', "Do you want to resume from last session?")
            msgbox.addButton(QMessageBox.Yes)
            msgbox.addButton(QMessageBox.No)
            msgbox.setDefaultButton(QMessageBox.No)            

            rep = msgbox.exec()
            if rep == QMessageBox.Yes:
                loader = Loader.loadFromHistory(crop_size=crop_size, crop_step=crop_step, total_size=TOTAL_SIZE)
                return loader

        return None


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
        q_pixmap = QPixmap(pixmap)
        self.label_image.setPixmap(q_pixmap.scaled(self.label_image.size()))
        self.label_image.resize(self.zoom_level * self.label_image.pixmap().size())

        self.show()

    def action_swap_colors(self, event):
        """
        Swap the green and red colors
        """
        self.swap_colors = not self.swap_colors
        if self.swap_colors:
            self.label_ch2.setStyleSheet("background-color: #00ff00")
            self.label_ch1.setStyleSheet("background-color: red")
        else:
            self.label_ch1.setStyleSheet("background-color: #00ff00")
            self.label_ch2.setStyleSheet("background-color: red")

        self.display_crop()


    def adjustScrollBar(self, scrollBar, factor):
        scrollBar.setValue(int(factor * scrollBar.value()
                               + ((factor - 1) * scrollBar.pageStep() / 2)))


    def submit(self):
        """
        Submit the classification of the current crop and display the next one; structure = 1
        """
        self.time_steps.append(time.time() - self.current_time)
        time_taken = np.sum(self.time_steps)
        self.time_steps_calc.append(self.curr_time.toString("hh:mm:ss"))
        #self.loader.save_patch(image=self.crop, classes=self.labelValues, labelling_time=self.curr_time.toString("hh:mm:ss"), ext="png")
        #self.save_crop_data(classes=self.labelValues, labelling_time=self.time_steps[-1].toString("hh:mm:ss"))
        self.loader.save_crop_data(classes=self.labelValues, labelling_time=self.curr_time.toString("hh:mm:ss"), structure=1, ambiguous=self.ambiguous_labels)
        self.hist_structures.append(1)
        self.hist_classes.append(self.labelValues)
        self.hist_ambiguous.append(self.ambiguous_labels)
        self.loader.saveHistory(self.hist_classes, self.hist_structures, self.hist_ambiguous)
        self.next_crop()
        self.curr_time =  QTime(00,00,00)
        self.start_action()

        
    def goBackward(self):
        """
        Return to previous crop to re-do annotation
        """
        self.previous_crop()
        
        
    def closeEvent(self, event):
        """
        Closing windows:
            save history
            save last edited file
        """
        self.loader.saveHistory(self.hist_classes, self.hist_structures, self.hist_ambiguouss)
        

    def skip(self):
        """
        NO structure in crop; structure = 0
        """
        self.time_steps.append(time.time() - self.current_time)
        time_taken = np.sum(self.time_steps)
        self.time_steps_calc.append(self.curr_time.toString("hh:mm:ss"))
        self.loader.save_crop_data(classes=self.labelValues, labelling_time=self.curr_time.toString("hh:mm:ss"), structure=0, ambiguous=self.ambiguous_labels)
        self.hist_structures.append(0)
        self.hist_classes.append(self.labelValues)
        self.hist_ambiguous.append(self.ambiguous_labels)
        self.loader.saveHistory(self.hist_classes, self.hist_structures, self.hist_ambiguous)
        self.next_crop()
        self.curr_time =  QTime(00,00,00)
        self.start_action()

    def ambiguous(self):
        """
        Mark crop as ambiguous; structure = 2
        """
        self.time_steps.append(time.time() - self.current_time)
        time_taken = np.sum(self.time_steps)
        self.time_steps_calc.append(self.curr_time.toString("hh:mm:ss"))
        self.loader.save_crop_data(classes=self.labelValues, labelling_time=self.curr_time.toString("hh:mm:ss"), structure=2, ambiguous=self.ambiguous_labels)
        self.hist_structures.append(2)
        self.hist_classes.append(self.labelValues)
        self.hist_ambiguous.append(self.ambiguous_labels)
        self.loader.saveHistory(self.hist_classes, self.hist_structures, self.hist_ambiguous)
        self.next_crop()
        self.curr_time =  QTime(00,00,00)
        self.start_action()


    def next_crop(self):
        """
        Display the next crop to label
        """
        self.time_steps = []
        self.current_time = time.time()
        self.reset_class_values()

        try:
            self.crop = self.loader.__next__()
            self.crop = np.transpose(self.crop, axes=[1,0,2])
        except StopIteration:
            end_dialog = QMessageBox()
            end_dialog.setIcon(QMessageBox.Information)
            end_dialog.setText('Labeled all of the data in the directory!')
            end_dialog.setWindowTitle('Finished')
            end_dialog.exec()
            

        self.zoom_level = np.float32(1.0)
        self.display_crop()
        self.show()

    def previous_crop(self):
        """
        Display the next crop to label
        """
        self.time_steps = []
        self.current_time = time.time()

        if len(self.hist_classes)==0:
            noprevious_dialog = QMessageBox()
            noprevious_dialog.setIcon(QMessageBox.Warning)
            noprevious_dialog.setText('Cannot go backward!')
            noprevious_dialog.setWindowTitle('Error')
            noprevious_dialog.exec()
            return
        try:
           p_crop = self.loader.__previous__()
           if p_crop is  None :
               noprevious_dialog = QMessageBox()
               noprevious_dialog.setIcon(QMessageBox.Warning)
               noprevious_dialog.setText('Cannot go backward!')
               noprevious_dialog.setWindowTitle('Error')
               noprevious_dialog.exec()
               return
           else:
               self.crop = p_crop
               self.crop = np.transpose(self.crop, axes=[1, 0, 2])
               self.reset_class_values()
               classes=self.hist_classes[-1]
               self.hist_classes=self.hist_classes[:-1]
               self.hist_structures=self.hist_structures[:-1]
               self.hist_ambiguous=self.hist_ambiguous[:-1]
               self.set_class_values(classes)
        except StopIteration:
            end_dialog = QMessageBox()
            end_dialog.setIcon(QMessageBox.Information)
            end_dialog.setText('Labeled all of the data in the directory!')
            end_dialog.setWindowTitle('Finished')
            end_dialog.exec()

        self.zoom_level = np.float32(1.0)
        self.display_crop()
        self.show()
        self.loader.saveHistory(self.hist_classes, self.hist_structures, self.hist_ambiguous, back=True)

        
    def start_action(self):
        # making flag true
        self.start = True

        self.timeEdit_timer.setTime(self.curr_time)
        self.button_start_timer.setEnabled(False)
  
    def pause_action(self):
        # making flag false
        self.start = False

        self.button_start_timer.setEnabled(True)

    def stop_action(self):
        # making flag false
        self.start = False

        # setting count value to 0
        self.count = 0
        self.curr_time = QTime(00,00,00)
        self.button_start_timer.setEnabled(True)

        
    def reset_action(self):
  
        # making flag false
        self.start = False
  
        # setting count value to 0
        self.count = 0
        self.label_timer.setText("00:00:00")
        self.curr_time = QTime(00,00,00)
        self.timeEdit_timer.setTime(self.curr_time)
        self.button_start_timer.setEnabled(True)



    def update_class_value(self, i):
        if i==1:
            self.labelValues[0]= self.slider_class_1.value()/100
            self.Spin_class_1.setValue(self.labelValues[0])
        if i==2:
            self.labelValues[1]= self.slider_class_2.value()/100
            self.Spin_class_2.setValue(self.labelValues[1])
        if i==3:
            self.labelValues[2]= self.slider_class_3.value()/100
            self.Spin_class_3.setValue(self.labelValues[2])
        if i==4:
            self.labelValues[3]= self.slider_class_4.value()/100
            self.Spin_class_4.setValue(self.labelValues[3])
       
    def update_spin_class_value(self, i):
        if i==1:
            self.labelValues[0]= self.Spin_class_1.value()
            self.slider_class_1.setValue(int(self.labelValues[0]*100))
        if i==2:
            self.labelValues[1]= self.Spin_class_2.value()
            self.slider_class_2.setValue(int(self.labelValues[1]*100))
        if i==3:
            self.labelValues[2]= self.Spin_class_3.value()
            self.slider_class_3.setValue(int(self.labelValues[2]*100))
        if i==4:
            self.labelValues[3]= self.Spin_class_4.value()
            self.slider_class_4.setValue(int(self.labelValues[3]*100))

    def update_ambiguous_checks(self):
        """
        Update currently checked ambiguous checkboxes (per class
        """
        for i, check in enumerate(self.check_ambiguous_list):
            self.ambiguous_labels[i] = check.isChecked()
            if self.ambiguous_labels[i]:
                self.slider_class_list[i].setDisabled(True)
                self.spin_class_list[i].setDisabled(True)
            else:
                self.slider_class_list[i].setDisabled(False)
                self.spin_class_list[i].setDisabled(False)


    def update_contrast(self):
        """
        Update the contrast of the image
        """
        # Intensity
        # channel 0
        self.displayed_crop[...,0] = np.clip(self.crop[...,0].astype('float') * self.slider_intensity_ch0.value()/100, 0, 255).astype('uint8').copy()

        # channel 1
        self.displayed_crop[...,1] = np.clip(self.crop[...,1].astype('float') * self.slider_intensity_ch1.value()/100, 0, 255).astype('uint8').copy()

        # Reverse colors if needed
        if self.swap_colors:
            buffer = self.displayed_crop[...,1].copy()
            self.displayed_crop[...,1] = self.displayed_crop[...,0].copy()
            self.displayed_crop[...,0] = buffer

        self.displayed_crop[self.box] = 255

    def reset_contrast(self, event):
        """
        Reset the contrast on right click
        :return:
        """
        self.slider_intensity_ch0.setValue(100)
        self.slider_intensity_ch1.setValue(100)
        self.display_crop()

    def pause(self):
        """
        Toggle pause. Prevents counting time during pauses, hides the image and disable widgets
        """

        self.label_image.clear()  # Hide image so no one cheats
        self.show()

        self.time_steps.append(time.time() - self.current_time)  # Add time step to prevent counting time while paused
        self.pause_action()

        pause_dialog = QMessageBox()
        pause_dialog.setIcon(QMessageBox.Warning)
        pause_dialog.setText('Program is paused!')
        pause_dialog.setWindowTitle('Pause')
        pause_dialog.setStandardButtons(QMessageBox.Yes)
        button = pause_dialog.button(QMessageBox.Yes)
        button.setText('Unpause')
        pause_dialog.exec()
        self.display_crop()

        self.start_action()

        self.current_time = time.time()

if __name__=='__main__':
    from PyQt5.QtWidgets import QApplication, QSplashScreen

    app = QApplication(sys.argv)
    ex = App()
    sys.exit(app.exec_())
