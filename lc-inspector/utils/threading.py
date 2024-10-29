from PyQt6.QtCore import QThread, pyqtSignal

class Worker(QThread):
    progress_update = pyqtSignal(int)
    finished = pyqtSignal(list)  # Signal to indicate processing is finished

    def __init__(self, model, ms_filelist, lc_filelist):
        super().__init__()
        self.model = model
        self.ms_filelist = ms_filelist
        self.lc_filelist = lc_filelist

    def run(self):
        results = self.model.process_data(self.ms_filelist, self.lc_filelist, self.progress_update.emit)
        self.finished.emit(results)  # Emit results and errors when done

    def run_annotation(self):
        results = self.model.annotate_data(self.ms_filelist, self.lc_filelist, self.progress_update.emit)
        self.finished.emit(results)  # Emit results and errors when done