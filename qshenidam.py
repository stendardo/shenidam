"""
    Copyright 2010 Nabil Stendardo <nabil@stendardo.org>

    This file is part of Shenidam.

    Shenidam is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) version 2 of the same License.

    Shenidam is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with Shenidam.  If not, see <http://www.gnu.org/licenses/>.

"""
from __future__ import print_function
from PyQt4 import QtGui,QtCore
from shenidam import encode as unicode
import shenidam
import os
import threading
import json
import os.path
import tempfile
import sys
import base64
try:
    import Queue as squeue
except ImportError:
    import queue as squeue

def launch(model):
    global done,error,canceled
    canceled = False
    queue = squeue.Queue()
    notifier = shenidam.CancelableProgressNotifier(queue,5 if model.mode == u"remix" else 3)
    fileprocessor = shenidam.ShenidamFileProcessor(model,notifier)
    progress = QtGui.QProgressDialog("","Abort",0,100,parent=frame)
    progress.setAutoClose(False)
    progress.setAutoReset(False)
    error = None
    done = False
    def on_cancel():
        global canceled
        canceled = True
    def run():
        global done,error
        try:
            fileprocessor.convert()
        except shenidam.CanceledException:
            pass
        except BaseException as e:
            error = unicode(e)
        finally:
            done = True
    thread = threading.Thread(target=run)
    
    progress.canceled.disconnect()
    progress.canceled.connect(on_cancel)
    
    progress.setModal(True)
    progress.show()
    thread.start()
    exception = None
    
    
    while(not done):
        try:
            application.processEvents()
            if canceled:
                progress.setLabelText("Aborting")
                progress.setCancelButton(None)
                notifier.cancel()
            try:
                x,y = queue.get(timeout=0.1)
                if x == "level":
                    progress.setValue(int(round(y*100)))
                    progress.setLabelText("")
                elif x == "text":
                    progress.setLabelText(y)
            except squeue.Empty:
                pass
        except (KeyboardInterrupt,SystemExit) as e:
            notifier.cancel()
            exception = e
    
    if exception is not None:
        raise exception
        
    if error is not None:
        message_box = QtGui.QMessageBox()
        message_box.setText("An error happened during processing")
        message_box.setDetailedText(error)
        message_box.exec_()
    progress.close()
latest_directory = None
def get_latest_directory():
    return latest_directory
class FileInput(QtGui.QWidget):
    def __init__(self,label,default_folder = None,set_default_folder = False,select_folder = False,file_mode=QtGui.QFileDialog.ExistingFile,accept_mode=QtGui.QFileDialog.AcceptOpen):
        QtGui.QWidget.__init__(self)
        if default_folder is None:
             default_folder = os.getcwd()
        self.default_folder = default_folder
        self.select_folder = select_folder
        filename = ""
        if set_default_folder:
            if callable(default_folder):
                filename = default_folder()
            else:
                filename = default_folder
        self.text_box = QtGui.QLineEdit(filename)
        self.button = QtGui.QPushButton("Browse")
        hbox = QtGui.QHBoxLayout()
        hbox.addWidget(self.text_box,1)
        hbox.addWidget(self.button)
        self.text_box.setMinimumWidth(300)
        
        vbox = QtGui.QVBoxLayout()
        if label:
            vbox.addWidget(QtGui.QLabel(label))
        vbox.addLayout(hbox)
        self.setLayout(vbox)
        self.file_mode = file_mode
        self.accept_mode = accept_mode
        self.button.clicked.connect(self.on_browse)
    def on_browse(self):
        global latest_directory
        dialog = QtGui.QFileDialog()
        dialog.setFileMode(self.file_mode)
        dialog.setAcceptMode(self.accept_mode)
        if self.file_mode == QtGui.QFileDialog.Directory:
            dialog.setOption(QtGui.QFileDialog.ShowDirsOnly)
        value = unicode(self.value())
        if not value.strip():
            if callable(self.default_folder):
                value = unicode(self.default_folder())
            else:
                value = unicode(self.default_folder)
        if value.strip():
            dialog.setDirectory(value)

        if dialog.exec_():
            latest_directory = os.path.dirname(unicode(dialog.selectedFiles()[0]))
            self.text_box.setText(dialog.selectedFiles()[0])
    def value(self):
        return unicode(self.text_box.text())
    def text(self):
        return self.value()
    def setValue(self,text):
        self.text_box.setText(text)
    def setText(self,text):
        self.setValue(text)
class LabelWrapper(QtGui.QWidget):
    def __init__(self,label):
        QtGui.QWidget.__init__(self)
        hbox = QtGui.QHBoxLayout() 
        hbox.addWidget(QtGui.QLabel(label))
        self.setLayout(hbox)
class TextBox(QtGui.QWidget):
    def __init__(self,label,value="",direction=QtGui.QBoxLayout.LeftToRight):
        QtGui.QWidget.__init__(self)
        self.text_box = QtGui.QLineEdit(value)
        self.text_box.setMinimumWidth(300)
        box = QtGui.QBoxLayout(direction)
        if label:
            box.addWidget(QtGui.QLabel(label))
        box.addWidget(self.text_box,1)
        self.setLayout(box)
    def value(self):
        return unicode(self.text_box.text())
    def text(self):
        return self.value()
    def setValue(self,text):
        self.text_box.setText(text)
    def setText(self,text):
        self.setValue(text)
class MultipleFileSelectionBox(QtGui.QWidget):
    def __init__(self):
        QtGui.QWidget.__init__(self)
        self.list_box = QtGui.QListWidget()
        self.b_add = QtGui.QPushButton("Add File")
        self.b_del = QtGui.QPushButton("Remove File")
        self.b_up = QtGui.QPushButton("Move up")
        self.b_down = QtGui.QPushButton("Move down")
        vbox1 = QtGui.QVBoxLayout()
        vbox2 = QtGui.QVBoxLayout()
        vbox1.addWidget(self.list_box,1)
        self.list_box.setMinimumWidth(600)
        vbox2.addWidget(self.b_add)
        vbox2.addWidget(self.b_del)
        vbox2.addWidget(self.b_up)
        vbox2.addWidget(self.b_down)
        vbox2.addStretch(1)
        hbox = QtGui.QHBoxLayout()
        
        hbox.addLayout(vbox1,1)
        hbox.addLayout(vbox2)
        self.b_add.clicked.connect(self.add)
        self.b_del.clicked.connect(self.remove)
        self.b_up.clicked.connect(self.move_up)
        self.b_down.clicked.connect(self.move_down)
        self.list_box.setResizeMode(QtGui.QListView.Adjust)
        self.setLayout(hbox)
    def move_up(self):
        x = self.list_box.currentItem()
        i = self.list_box.currentRow()
        if x is None or i == 0:
            return
        x = self.list_box.takeItem(i)
        self.list_box.insertItem(i-1,x)
        self.list_box.setCurrentRow(i-1)
    def move_down(self):
        x = self.list_box.currentItem()
        i = self.list_box.currentRow()
        if x is None or i > self.list_box.count()-1:
            return
        x = self.list_box.takeItem(i)
        self.list_box.insertItem(i+1,x)
        self.list_box.setCurrentRow(i+1)
    def remove(self):
        
        i = self.list_box.currentRow()
        if self.list_box.count() == 0:
            return
        self.list_box.takeItem(i)
    def add(self):
        files = QtGui.QFileDialog.getOpenFileNames(directory=latest_directory or "")
        for x in files:
            self.list_box.addItem(x)
    def value(self):
        return [unicode(self.list_box.item(i).text()) for i in range(self.list_box.count())]
class TableSelectionBox(QtGui.QWidget):
    def __init__(self):
        QtGui.QWidget.__init__(self)
        self.table = QtGui.QTableWidget()
        self.table.setMinimumWidth(600)
        self.b_add = QtGui.QPushButton("Add Output")
        self.b_del = QtGui.QPushButton("Remove Output")
        vbox1 = QtGui.QVBoxLayout()
        vbox2 = QtGui.QVBoxLayout()
        vbox1.addWidget(self.table,1)
        vbox2.addWidget(self.b_add)
        vbox2.addWidget(self.b_del)
        vbox2.addStretch(1)
        hbox = QtGui.QHBoxLayout()
        
        hbox.addLayout(vbox1,1)
        hbox.addLayout(vbox2)
        self.b_add.clicked.connect(self.add)
        self.b_del.clicked.connect(self.remove)
        self.setLayout(hbox)
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Output pattern","Audio-only output","AVCONV Remix Parameters"])
        self.add()
        self.table.horizontalHeader().setResizeMode(QtGui.QHeaderView.Stretch)
    def remove(self):
        if self.table.rowCount()==1 :
            return
        x = self.table.rowCount()-1
        
        self.table.removeRow(x)
    def add(self):
        i = self.table.rowCount()
        self.table.setRowCount(i+1)
        x = QtGui.QLineEdit("{dir}/{base}.shenidam.mkv")
        y = QtGui.QCheckBox()
        z = QtGui.QLineEdit("default")
        self.table.setCellWidget(i,0,x)
        self.table.setCellWidget(i,1,y)
        self.table.setCellWidget(i,2,z)
    def value(self):
        return [[unicode(self.table.cellWidget(i,0).text()).strip(),self.table.cellWidget(i,1).isChecked(),unicode(self.table.cellWidget(i,2).text()).strip()] for i in range(self.table.rowCount())]
class SingleFileConversionWindow(QtGui.QWidget):
    def __init__(self):
        QtGui.QWidget.__init__(self)
        self.base_field = FileInput("Base soundtrack",default_folder=get_latest_directory)
        self.input_field = FileInput("AV-Track to match",default_folder=get_latest_directory)
        self.output_field = FileInput("Output file",default_folder=get_latest_directory,file_mode=QtGui.QFileDialog.AnyFile,accept_mode=QtGui.QFileDialog.AcceptSave)
        self.checkbox = QtGui.QCheckBox()
        self.remix_params_field = TextBox("AVCONV remix parameters","default")
        hbox = QtGui.QHBoxLayout()
        hbox.addWidget(QtGui.QLabel("Audio-only output"))
        hbox.addWidget(self.checkbox)
        hbox.addStretch(1)
        cb_wgt = QtGui.QWidget()
        cb_wgt.setLayout(hbox)
        vbox = QtGui.QVBoxLayout()
        vbox.addWidget(self.base_field)
        vbox.addWidget(self.input_field)
        vbox.addWidget(self.output_field)
        vbox.addWidget(cb_wgt)
        vbox.addWidget(self.remix_params_field)
        self.setLayout(vbox)
    def base(self):
        return self.base_field.value()
    def input(self):
        return [self.input_field.value()]
    def output(self):
        return [[unicode(self.output_field.value().strip()),self.checkbox.isChecked(),unicode(self.remix_params_field.text()).strip()]]
class MultipleFileConversionWindow(QtGui.QWidget):
    def __init__(self):
        QtGui.QWidget.__init__(self)
        self.base_field = FileInput("Base soundtrack",default_folder=get_latest_directory)
        self.input_field = MultipleFileSelectionBox()
        self.output_field = TableSelectionBox()
        
        vbox = QtGui.QVBoxLayout()
        vbox.addWidget(self.base_field)
        vbox.addWidget(LabelWrapper("AV-Tracks to match"))
        vbox.addWidget(self.input_field)
        vbox.addWidget(LabelWrapper("Outputs"))
        vbox.addWidget(self.output_field)
        self.setLayout(vbox)
    def base(self):
        return self.base_field.value()
    def input(self):
        return self.input_field.value()
    def output(self):
        return self.output_field.value()
class Frame(QtGui.QMainWindow):
    def __init__(self):
        QtGui.QWidget.__init__(self)

	import qshenidam_icon as qi
	pixmap = QtGui.QPixmap()
	pixmap.loadFromData(base64.b64decode(qi.__data__))
	

	self.setCentralWidget(QtGui.QWidget())
        self.tabs = QtGui.QTabWidget()
        self.single = SingleFileConversionWindow()
        self.multi = MultipleFileConversionWindow()
        self.prefs = PreferencesWindow()
        self.setWindowTitle("QShenidam")
	application.setWindowIcon(QtGui.QIcon(pixmap))
        self.tabs.addTab(self.single,"Simple Mode (Single Track)")
        self.tabs.addTab(self.multi,"Advanced Mode (Multiple Tracks and Outputs)")
        b_prefs = QtGui.QPushButton("Preferences")
        b_run = QtGui.QPushButton("Run")
        b_prefs.clicked.connect(self.edit_prefs)
        b_run.clicked.connect(self.run)
        hbox = QtGui.QHBoxLayout()
        hbox.addStretch(1)
        hbox.addWidget(b_prefs)
        hbox.addWidget(b_run)
        vbox = QtGui.QVBoxLayout()
        vbox.addWidget(self.tabs)
        vbox.addLayout(hbox)
        self.centralWidget().setLayout(vbox)
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.keep_alive)
        self.timer.start(100)
        if self.prefs.first_time:
            self.edit_prefs()
    def edit_prefs(self):
        self.prefs.show()
        if self.prefs.first_time:
            messageBox = QtGui.QMessageBox()
            messageBox.setText("Please check these parameters\nand change them if necessary\n")
            messageBox.exec_()
        self.prefs.exec_()
    def run(self):
        wgt = self.tabs.currentWidget()
        model = shenidam.FileProcessorModel()
        model.base_fn = wgt.base()
        model.input_tracks = wgt.input()
        model.output_params = wgt.output()
        model.__dict__.update(self.prefs.data())
        try:
            shenidam.check_model(model)
        except shenidam.ModelException as e:
            message_box = QtGui.QMessageBox()
            message_box.setText("ERROR: "+unicode(e))
            message_box.exec_()
            return
        launch(model)
        
    def keep_alive(self):
        return
def get_qshenidam_file_name():
    return os.path.join(os.path.expanduser("~"),".qshenidam.cfg")
class PreferencesWindow(QtGui.QDialog):
    def __init__(self):
        QtGui.QWidget.__init__(self)
        self.tmp_dir_field =  FileInput(None,file_mode=QtGui.QFileDialog.Directory,accept_mode=QtGui.QFileDialog.AcceptOpen)
        self.output_tmp_dir_field = FileInput(None,file_mode=QtGui.QFileDialog.Directory,accept_mode=QtGui.QFileDialog.AcceptOpen)
        self.avconv_field =  QtGui.QLineEdit("")
        self.shenidam_field =  QtGui.QLineEdit("")
        self.shenidam_extra_args_field = QtGui.QLineEdit("")
        self.audio_export_params_field = QtGui.QLineEdit("")
        self.default_audio_remix_params_field = QtGui.QLineEdit("")
        self.default_av_audio_remix_params_field = QtGui.QLineEdit("")
        grid = QtGui.QGridLayout()
        grid.addWidget(QtGui.QLabel("Temporary Directory (should be in RAM if you have enough of it)"),0,0)
        grid.addWidget(QtGui.QLabel("Output Temporary Directory (Should be optimally on same drive/volume/partition as outputs)"),1,0)
        grid.addWidget(QtGui.QLabel("AVCONV Command/Executable"),2,0)
        grid.addWidget(QtGui.QLabel("Shenidam Command/Executable"),3,0)
        grid.addWidget(QtGui.QLabel("Extra parameters to pass to shenidam\n(typically working sample rate)"),4,0)
        grid.addWidget(QtGui.QLabel("Extra parameters to pass to AVCONV for audio extraction"),5,0)
        grid.addWidget(QtGui.QLabel("Default parameters to pass to AVCONV\nfor audio remixing (audio mode)"),6,0)
        grid.addWidget(QtGui.QLabel("Default parameters to pass to AVCONV\nfor audio remixing (audio/video mode)"),7,0)
        grid.addWidget(self.tmp_dir_field,0,1)
        grid.addWidget(self.output_tmp_dir_field,1,1)
        grid.addWidget(self.avconv_field,2,1)
        grid.addWidget(self.shenidam_field,3,1)
        grid.addWidget(self.shenidam_extra_args_field,4,1)
        grid.addWidget(self.audio_export_params_field,5,1)
        grid.addWidget(self.default_audio_remix_params_field,6,1)
        grid.addWidget(self.default_av_audio_remix_params_field,7,1)
        b_close = QtGui.QPushButton("Close and save")
        b_close.clicked.connect(self.close)
        b_defaults = QtGui.QPushButton("Load Defaults")
        b_defaults.clicked.connect(self.load_defaults)
        hbox = QtGui.QHBoxLayout()
        hbox.addStretch(1)
        hbox.addWidget(b_defaults)
        hbox.addWidget(b_close)
        vbox = QtGui.QVBoxLayout()
        vbox.addLayout(grid)
        vbox.addLayout(hbox)
        self.setLayout(vbox)
        self.load_defaults()
        self.load()
    def load_defaults(self):
        self.tmp_dir_field.setText(tempfile.gettempdir())
        self.output_tmp_dir_field.setText(tempfile.gettempdir())
        self.avconv_field.setText("avconv")
        self.shenidam_field.setText("shenidam")
        self.shenidam_extra_args_field.setText("")
        self.audio_export_params_field.setText("-c:a pcm_s24le -f wav")
        self.default_audio_remix_params_field.setText("-c:a copy")
        self.default_av_audio_remix_params_field.setText("-c:a copy -c:v copy")
    def load(self):
        self.first_time = False
        try:
            with open(get_qshenidam_file_name(),'r')as f:
                d = json.load(f)
                if "tmp_dir" in d:
                    self.tmp_dir_field.setText(unicode(d["tmp_dir"]))
                if "output_tmp_dir" in d:
                    self.output_tmp_dir_field.setText(unicode(d["output_tmp_dir"]))
                if "avconv" in d:
                    self.avconv_field.setText(unicode(d["avconv"]))
                if "shenidam" in d:
                    self.shenidam_field.setText(unicode(d["shenidam"]))
                if "shenidam_extra_args" in d:
                    self.shenidam_extra_args_field.setText(unicode(d["shenidam_extra_args"]))
                if "audio_export_params" in d:
                    self.audio_export_params_field.setText(unicode(d["audio_export_params"]))
                if "default_audio_remix_params" in d:
                    self.default_audio_remix_params_field.setText(unicode(d["default_audio_remix_params"]))
                if "default_av_audio_remix_params" in d:
                    self.default_av_audio_remix_params_field.setText(unicode(d["default_av_audio_remix_params"]))
        except Exception:
            self.first_time = True
    def data(self):
        return {
        "tmp_dir":unicode(self.tmp_dir_field.text()),
        "avconv":unicode(self.avconv_field.text()),
        "shenidam":unicode(self.shenidam_field.text()),
        "shenidam_extra_args":unicode(self.shenidam_extra_args_field.text()),
        "audio_export_params":unicode(self.audio_export_params_field.text()),
        "output_tmp_dir":unicode(self.output_tmp_dir_field.text()),
        "default_audio_remix_params":unicode(self.default_audio_remix_params_field.text()),
        "default_av_audio_remix_params":unicode(self.default_av_audio_remix_params_field.text())
        }
    def save(self):
        with open(get_qshenidam_file_name(),'w')as f:
            json.dump(self.data(),f)
            self.first_time = False
    def closeEvent(self,event):
        self.save()
if __name__ == "__main__":
    
    
    application = QtGui.QApplication(sys.argv)
    frame = Frame()
    frame.show()
    if os.name == "darwin":
        frame.raise_()
    def new_excepthook(type,value,traceback):
        application.exit(1)
        sys.__excepthook__(type,value,traceback)
        return
        
    sys.excepthook = new_excepthook
    sys.exit(application.exec_())


