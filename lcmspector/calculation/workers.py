from PyQt6.QtCore import QThread, QObject, pyqtSignal
import time, logging
from lcmspector.utils.classes import LCMeasurement
import lcmspector_backend as lcms
import os

logger = logging.getLogger(__name__)

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

        # Validate mode

        # Validate mode
        if self.mode not in {"LC/GC-MS", "LC/GC Only", "MS Only"}:
            logger.error(f"ERROR: Invalid argument for process_data(mode): {self.mode}")
            return

        # Process LC files if applicable
        if self.mode in {"LC/GC-MS", "LC/GC Only"}:
            for lc_file in self.model.lc_measurements:
                lc_results[lc_file] = LCMeasurement(lc_file)
                self.progressUpdated.emit(int(len(lc_results) / len(self.model.lc_measurements) * 50))

        # Process MS files if applicable
        if self.mode in {"LC/GC-MS", "MS Only"} and self.model.ms_measurements:
            # Robust handling of ms_measurements
            try:
                if isinstance(self.model.ms_measurements, dict):
                    ms_file_paths = list(self.model.ms_measurements.keys())
                elif isinstance(self.model.ms_measurements, list):
                    ms_file_paths = self.model.ms_measurements
                else:
                    logger.error(f"Unexpected type for ms_measurements: {type(self.model.ms_measurements)}")
                    return

                rust_results = lcms.process_files_in_parallel(
                    file_paths=ms_file_paths,
                    mass_accuracy=0.0001,
                    ion_list_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')
                )
                # Convert Rust results to MSMeasurement objects
                ms_results = self.model._convert_rust_results_to_measurements(rust_results, ms_file_paths)
                self.progressUpdated.emit(100)
            except Exception as e:
                logger.error(f"Error processing MS files with Rust backend: {e}")
                logger.error(f"ms_measurements type: {type(self.model.ms_measurements)}")
                logger.error(f"ms_measurements content: {self.model.ms_measurements}")

        logger.info(f"Processing completed in {time.time() - st} seconds.")
        self.finished.emit(lc_results, ms_results)