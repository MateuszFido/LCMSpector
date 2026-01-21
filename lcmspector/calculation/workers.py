"""
Module for handling background workers in LC-Inspector application.

This module provides QThread-based worker classes for asynchronous loading and
processing of LC/GC-MS measurement data. It supports:
- Loading LC and MS measurement files in parallel
- Processing MS files with multiprocessing
- Emitting progress and result signals for UI updates

The module uses ProcessPoolExecutor for efficient parallel processing and
leverages PyQt6's signal-slot mechanism for thread communication.
"""

import time
import traceback
import multiprocessing
import logging
from concurrent.futures import ProcessPoolExecutor, as_completed

from PySide6.QtCore import QThread, QObject, Signal
from utils.classes import LCMeasurement, MSMeasurement
from utils.preprocessing import construct_xics

logger = logging.getLogger(__name__)


class WorkerSignals(QObject):
    """
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

    """

    finished = Signal()
    error = Signal(tuple)
    result = Signal(object)
    progress = Signal(int)


class LoadingWorker(QThread):
    progressUpdated = Signal(int, str)
    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, model, mode, file_paths, file_type):
        super().__init__()
        self.model = model
        self.mode = mode
        self.file_paths = file_paths
        self.file_type = file_type
        self.file_count = len(file_paths)

    def run(self):
        st = time.time()
        results = {}

        try:
            self.file_count
        except AttributeError:
            logger.error("File count attribute not properly initialized.")
            return

        if self.file_count == 0:
            logger.warning("No files to process.")
            return

        progress = 0

        def update_progress(filename):
            nonlocal progress
            progress += 1
            self.progressUpdated.emit(int(progress / self.file_count * 100), filename)

        if self.mode not in {"LC/GC-MS", "LC/GC Only", "MS Only"}:
            logger.error(f"Invalid argument for load(): {self.mode}, currently supported modes are LC/GC-MS, LC/GC Only, MS Only.")
            return

        try:
            with ProcessPoolExecutor(
                max_workers=max(1, multiprocessing.cpu_count() - 1)
            ) as executor:
                # Conditional loading based on mode and what is being uploaded
                if self.file_type == "LC":
                    futures = {
                        executor.submit(LCMeasurement, lc_file): lc_file
                        for lc_file in self.file_paths
                    }
                elif self.file_type == "MS":
                    futures = {
                        executor.submit(MSMeasurement, ms_file): ms_file
                        for ms_file in self.file_paths
                    }
                else:
                    logger.error(f"Invalid file type for load(): {self.file_type}, currently supported types are LC and MS.")
                    futures = {}

                for future in as_completed(futures):
                    try:
                        result = future.result()
                        results[result.filename] = result
                        update_progress(result.filename)
                    except Exception as e:
                        logger.error("Error loading file: %s", traceback.format_exc())
                        self.error.emit(str(e))
        except Exception as e:
            logger.error("Error in loading pool: %s", traceback.format_exc())
            self.error.emit(str(e))
            return

        logger.debug(
            f"Loaded {len(results)} {self.file_type} files in {time.time() - st} seconds.",
        )
        self.finished.emit(results)


class ProcessingWorker(QThread):
    progressUpdated = Signal(int)
    finished = Signal(list)
    error = Signal(str)

    def __init__(self, model, mode, mass_accuracy):
        super().__init__()
        self.model = model
        self.mode = mode
        self.mass_accuracy = mass_accuracy

    def run(self):
        st = time.time()

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
            logger.error(
                "ERROR: Invalid argument for process_data(mode): %s", self.mode
            )
            return
        results = []
        try:
            with ProcessPoolExecutor(
                max_workers=max(1, multiprocessing.cpu_count() - 3)
            ) as executor:
                # Only process MS files if in MS or LC/GC-MS mode
                if self.mode in {"LC/GC-MS", "MS Only"}:
                    # for every MS file, call construct_xics on its data and store the result
                    futures = {
                        executor.submit(
                            construct_xics,
                            ms_file.filename,
                            ms_file.data,
                            self.model.compounds,
                            self.mass_accuracy,
                        ): ms_file
                        for ms_file in self.model.ms_measurements.values()
                    }
                else:
                    futures = {}

                for future in as_completed(list(futures)):
                    try:
                        result = future.result()
                        results.append(result)
                    except AttributeError as e:
                        logger.error(
                            "Error in processing pool: %s", traceback.format_exc()
                        )
                        self.error.emit(str(e))
                    update_progress()
        except Exception as e:
            logger.error("Error in processing pool: %s", traceback.format_exc())
            self.error.emit(str(e))
            return

        logger.info(
            "Processed %d MS files in %.2f seconds.", len(results), time.time() - st
        )
        self.finished.emit(results)
