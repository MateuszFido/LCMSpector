from PyQt6.QtCore import QThread, QObject, pyqtSignal
import time, sys, traceback, multiprocessing, logging
from concurrent.futures import ProcessPoolExecutor, as_completed
from utils.classes import LCMeasurement, MSMeasurement
from utils.preprocessing import construct_xics
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

class LoadingWorker(QThread):
    progressUpdated = pyqtSignal(int, str)
    finished = pyqtSignal(dict, dict)
    error = pyqtSignal(str)

    def __init__(self, model, mode, file_type):
        super().__init__()
        self.model = model
        self.mode = mode
        self.file_type = file_type

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

        def update_progress(filename):
            nonlocal progress
            progress += 1
            self.progressUpdated.emit(int(progress / total_files * 200), filename)

        if self.mode not in {"LC/GC-MS", "LC/GC Only", "MS Only"}:
            logger.error(f"ERROR: Invalid argument for load_data(mode): {self.mode}")
            return

        try:
            with ProcessPoolExecutor(max_workers=max(1, multiprocessing.cpu_count() - 3)) as executor:
                # Conditional loading based on mode and what is being uploaded
                if self.mode in ("LC/GC-MS", "LC/GC Only") and self.file_type == "LC":
                    lc_futures = {executor.submit(LCMeasurement, lc_file): lc_file for lc_file in self.model.lc_measurements}
                else:
                    lc_futures = {}

                if self.mode in {"LC/GC-MS", "MS Only"} and self.file_type == "MS":
                    # Note: Removed specific mass accuracy parameter
                    ms_futures = {executor.submit(MSMeasurement, ms_file): ms_file for ms_file in self.model.ms_measurements}
                else:
                    ms_futures = {}

                for future in as_completed(list(lc_futures) + list(ms_futures)):
                    try:
                        result = future.result()
                        if future in lc_futures:
                            lc_results[result.filename] = result
                            #self.model.controller.view.statusbar.showMessage(f"Loaded LC file: {result.filename}", 1000)
                        else:
                            ms_results[result.filename] = result
                            #self.model.controller.view.statusbar.showMessage(f"Loaded MS file: {result.filename}", 1000)
                    except Exception as e:
                        logger.error(f"Error loading file: {traceback.format_exc()}")
                        self.error.emit(str(e))
                    update_progress(result.filename)
        except Exception as e:
            logger.error(f"Error in loading pool: {e}")
            self.error.emit(str(e))
            return

        logger.info(f"Loaded {len(lc_results)} LC files and {len(ms_results)} MS files for {self.mode} in {time.time() - st} seconds.")
        self.finished.emit(lc_results, ms_results)


class ProcessingWorker(QThread):
    progressUpdated = pyqtSignal(int)
    finished = pyqtSignal(dict, dict)
    error = pyqtSignal(str)

    def __init__(self, model, mode):
        super().__init__()
        self.model = model
        self.mode = mode

    def run(self):
        st = time.time()
        processed_ms_results = {}
        
        try:
            total_files = len(self.model.ms_measurements)
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
                # Only process MS files if in MS or LC/GC-MS mode
                if self.mode in {"LC/GC-MS", "MS Only"}:
                    # for every MS file, call construct_xics on its data and store the result
                    ms_futures = {executor.submit(construct_xics, ms_file.data, self.model.compounds, ms_file.mass_accuracy): ms_file for ms_file in self.model.ms_measurements}
                else:
                    ms_futures = {}

                for future in as_completed(list(ms_futures)):
                    try:
                        result = future.result()
                        processed_ms_results[ms_file.filename] = result
                    except Exception as e:
                        logger.error(f"Error processing file {ms_file.filename}: {e}")
                        self.error.emit(str(e))
                    update_progress()
        except Exception as e:
            logger.error(f"Error in processing pool: {e}")
            self.error.emit(str(e))
            return

        logger.info(f"Processed {len(processed_ms_results)} MS files in {time.time() - st} seconds.")
        self.finished.emit({}, processed_ms_results)
