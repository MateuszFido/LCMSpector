from PyQt6.QtCore import QThread, pyqtSignal
import traceback

class Worker(QThread):
    progress_update = pyqtSignal(int)
    finished = pyqtSignal(tuple)  # Emit a tuple containing both results

    def __init__(self, model, ms_filelist, lc_filelist):
        super().__init__()
        self.model = model
        self.ms_filelist = ms_filelist
        self.lc_filelist = lc_filelist

    def run(self):
        results = self.model.process_data(self.ms_filelist, self.lc_filelist, self.progress_update.emit)
        self.finished.emit(results)  # Emit results as a tuple (lc_results, ms_results)

class AnnotationWorker(QThread):
    progress_update = pyqtSignal(int)
    finished = pyqtSignal(list)  # Signal to indicate processing is finished

    def __init__(self, function, *args):
        super().__init__()
        self.function = function
        self.args = args

    def run(self):
        try:
            results = self.function(*self.args, self.progress_update.emit)
            self.finished.emit(results)
        except Exception as e:
            print(f"Error in Worker: {e}")
            traceback.print_exc()
            self.finished.emit([])  # Emit an empty list or handle error appropriately
