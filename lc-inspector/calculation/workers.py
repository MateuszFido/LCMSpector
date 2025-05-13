from PyQt6.QtCore import QThread, QObject, pyqtSignal
import time, sys, traceback, multiprocessing, logging
from concurrent.futures import ProcessPoolExecutor, as_completed
from utils.classes import LCMeasurement, MSMeasurement
logger = logging.getLogger(__name__)
class WorkerSignals(QObject):
    '''
    Defines the signals available from a running worker thread.

    Supported signals are:

    finished
        No data

    error
        tuple (exctype, value, traceback.format_exc() )

    result
        object data returned from processing, anything

    progress
        int indicating % progress

    '''
    finished = pyqtSignal()
    error = pyqtSignal(tuple)
    result = pyqtSignal(object)
    progress = pyqtSignal(int)

class Worker(QThread):
    progressUpdated = pyqtSignal(int)
    finished = pyqtSignal(dict, dict)

    def __init__(self, model, mode):
        super().__init__()
        self.model = model
        self.mode = mode

    def run(self):
        st = time.time()
        lc_results = {}
        ms_results = {}
        total_files = len(self.model.lc_measurements) + len(self.model.ms_measurements)
        progress = 0

        def update_progress():
            nonlocal progress
            progress += 1
            self.progressUpdated.emit(int(progress / total_files * 100))

        if self.mode not in {"LC/GC-MS", "LC/GC Only", "MS Only"}:
            logger.error("ERROR: Invalid argument for process_data(mode): ", self.mode)
            return

        with ProcessPoolExecutor(max_workers=multiprocessing.cpu_count() - 3) as executor:
            if self.mode in {"LC/GC-MS", "LC/GC Only"}:
                lc_futures = {executor.submit(LCMeasurement, lc_file): lc_file for lc_file in self.model.lc_measurements}
            else:
                lc_futures = {}

            if self.mode in {"LC/GC-MS", "MS Only"}:
                ms_futures = {executor.submit(MSMeasurement, ms_file, self.model.compounds, 0.0001): ms_file for ms_file in self.model.ms_measurements}
            else:
                ms_futures = {}

            for future in as_completed(list(lc_futures) + list(ms_futures)):
                result = future.result()
                if future in lc_futures:
                    lc_results[result.filename] = result
                else:
                    ms_results[result.filename] = result
                update_progress()

        logger.info(f"Processed in {time.time() - st}")
        logger.info(f"Size in memory is LC: {sys.getsizeof(lc_results) / (1024 * 1024)} MB, MS: {sys.getsizeof(ms_results) / (1024 * 1024)} MB.")
        self.finished.emit(lc_results, ms_results)