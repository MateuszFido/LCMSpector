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
        try:
            total_files = len(self.model.lc_measurements) + len(self.model.ms_measurements)
            if total_files == 0:
                logger.warning("No files to process.")
                return
        except AttributeError:
            logger.error("Model attributes are not properly initialized.")
            return
        
        progress = 0

        def update_progress():
            nonlocal progress
            progress += 1
            self.progressUpdated.emit(int(progress / total_files * 100))

        if self.mode not in {"LC/GC-MS", "LC/GC Only", "MS Only"}:
            logger.error(f"ERROR: Invalid argument for process_data(mode): {self.mode}")
            return

        try:
            with ProcessPoolExecutor(max_workers=max(1, multiprocessing.cpu_count() - 3)) as executor:
                if self.mode in {"LC/GC-MS", "LC/GC Only"}:
                    lc_futures = {executor.submit(LCMeasurement, lc_file): lc_file for lc_file in self.model.lc_measurements}
                else:
                    lc_futures = {}

                if self.mode in {"LC/GC-MS", "MS Only"}:
                    ms_futures = {executor.submit(MSMeasurement, ms_file, self.model.compounds, 0.0001): ms_file for ms_file in self.model.ms_measurements}
                else:
                    ms_futures = {}

                for future in as_completed(list(lc_futures) + list(ms_futures)):
                    try:
                        result = future.result()
                        if future in lc_futures:
                            lc_results[result.filename] = result
                        else:
                            ms_results[result.filename] = result
                    except Exception as e:
                        logger.error(f"Error processing file: {e}")
                    update_progress()
        except Exception as e:
            logger.error(f"Error in processing pool: {e}")
            return

        logger.info(f"Processed in {time.time() - st} seconds.")
        self.finished.emit(lc_results, ms_results)
