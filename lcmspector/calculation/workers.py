from PyQt6.QtCore import QThread, QObject, pyqtSignal
import time, sys, traceback, multiprocessing, logging
from concurrent.futures import ProcessPoolExecutor, as_completed
from lcmspector.utils.classes import LCMeasurement, MSMeasurement
import lcmspector_backend as lcms
import os

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

                ms_futures = {}
                if self.mode in {"LC/GC-MS", "MS Only"}:
                    # Use Rust backend for MS file processing
                    if self.model.ms_measurements:
                        ms_file_paths = list(self.model.ms_measurements.keys())
                        try:
                            rust_results = lcms.process_files_in_parallel(
                                file_paths=ms_file_paths,
                                mass_accuracy=0.0001,
                                ion_list_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')
                            )
                            # Convert Rust results to MSMeasurement objects
                            ms_results = self.model._convert_rust_results_to_measurements(rust_results, ms_file_paths)
                        except Exception as e:
                            logger.error(f"Error processing MS files with Rust backend: {e}")
                            # Fallback to original processing if Rust processing fails
                            ms_futures = {executor.submit(MSMeasurement, ms_file, self.model.compounds, 0.0001): ms_file for ms_file in self.model.ms_measurements}
                            for future in as_completed(ms_futures):
                                try:
                                    result = future.result()
                                    ms_results[result.filename] = result
                                except Exception as e:
                                    logger.error(f"Error processing file: {e}")
                                update_progress()

                # Process LC and MS files
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
